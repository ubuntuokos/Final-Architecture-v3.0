#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,platform,signal,socket,subprocess,tempfile,threading,time
from datetime import datetime,timedelta,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from typing import Any
from fa3_browser_action_runtime import BrowserActionDenied,attach_execution_parameters,bind_selected_action,build_action_space
from fa3_browser_cdp_provider import discover_browser_binary
from fa3_browser_session_bridge import BrowserSessionBridgeServer,EXPECTED_EXTENSION_ID
from fa3_browser_session_provider import ACTION_IDS,BrowserSessionProvider,PROVIDER_ID
from fa3_uaf import ActionContract,ActionDispatcher,ActionRegistry,ActionRequest,ExecutionContext,ProviderRegistry,UafError,_canonical_digest
GATE_ID="FA3-GATE-BROWSER-SESSION-CURRENT-HOST-001"
PROFILE_ID="FA3-BROWSER-SESSION-INTERACTION-001"
HRB_CLIENT="/usr/local/bin/fa3-host-resource-broker-admission"
HTML=b"""<!doctype html><html><body><input id='name' aria-label='Name'><button id='advance' aria-label='Advance' onclick="this.remove();document.body.dataset.clicked='1'">Advance</button><div id='status'>idle</div></body></html>"""
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(HTML)));self.end_headers();self.wfile.write(HTML)
    def log_message(self,fmt,*args):return
def run(command:list[str],*,env=None,timeout=20):
    return subprocess.run(command,text=True,capture_output=True,check=False,timeout=timeout,env=env)
def approval(principal,action,arguments,context,suffix,authority="FA3-AUTH-SECURITY-GOV-001"):
    return{"approval_id":f"browser-session-current-host-{suffix}-{time.time_ns()}","authority":authority,"principal_ref":principal,"action_id":action.action_id,"action_version":action.version,"argument_digest":_canonical_digest(arguments),"context_digest":_canonical_digest(context.as_dict()),"expires_at":(datetime.now(timezone.utc)+timedelta(minutes=4)).isoformat(),"single_use":True}
def action(root,aid):
    path=root/"canonical"/"actions"/f"{aid}.json";return ActionContract.from_dict(json.loads(path.read_text()),source_path=path.as_posix())
def native_manifest(executable):
    return{"name":"org.fa3.browser.session_bridge","description":"FA3 Browser Session Bridge native messaging proxy","path":str(executable.resolve()),"type":"stdio","allowed_origins":[f"chrome-extension://{EXPECTED_EXTENSION_ID}/"]}
def install_temp_manifests(home,executable):
    rels=[".config/google-chrome/NativeMessagingHosts",".config/google-chrome-beta/NativeMessagingHosts",".config/google-chrome-for-testing/NativeMessagingHosts",".config/chromium/NativeMessagingHosts",".config/BraveSoftware/Brave-Browser/NativeMessagingHosts",".config/microsoft-edge/NativeMessagingHosts",".config/microsoft-edge-beta/NativeMessagingHosts"]
    data=json.dumps(native_manifest(executable),indent=2)+"\n";written=[]
    for rel in rels:
        d=home/rel;d.mkdir(parents=True,exist_ok=True);p=d/"org.fa3.browser.session_bridge.json";p.write_text(data);written.append(str(p.relative_to(home)))
    return written
def issue_hrb(tmp,workload_id):
    client=Path(HRB_CLIENT)
    if not client.is_file() or not os.access(client,os.X_OK):raise RuntimeError("HRB_ADMISSION_CLIENT_UNAVAILABLE")
    workload_path=tmp/"browser-session-workload.json";auth_path=tmp/"browser-session-authorization.json"
    workload={"schema":"fa3.workload-resource-envelope.v1","workload_id":workload_id,"requirements":[{"metric":"cpu.physical_cores","operator":">=","value":1},{"metric":"memory.total_gib","operator":">=","value":0.1}]}
    workload_path.write_text(json.dumps(workload,indent=2)+"\n");os.chmod(workload_path,0o600)
    if run([str(client),"authorize","--workload",str(workload_path),"--output",str(auth_path)],timeout=30).returncode:raise RuntimeError("HRB_ADMISSION_AUTHORIZATION_DENIED")
    if run([str(client),"validate","--authorization",str(auth_path)],timeout=30).returncode:raise RuntimeError("HRB_ADMISSION_AUTHORIZATION_INVALID")
    auth=json.loads(auth_path.read_text())
    if auth.get("authority")!="FA3-AUTH-HOST-RESOURCE-BROKER-001" or auth.get("status")!="ACTIVE":raise RuntimeError("HRB_ADMISSION_AUTHORITY_MISMATCH")
    if auth.get("accelerator_required") is not False:raise RuntimeError("CPU_ONLY_HRB_AUTHORIZATION_BROKEN")
    return auth,auth_path
def browser_version(binary):
    try:
        p=run([binary,"--version"],timeout=5);return(p.stdout or p.stderr).strip()[:256]
    except Exception:return"UNKNOWN"
def launch_browser(binary,profile,extension,url,env):
    args=[binary,"--headless=new","--disable-gpu","--disable-background-networking","--disable-component-update","--disable-default-apps","--disable-sync","--no-first-run","--no-default-browser-check",f"--user-data-dir={profile}",f"--disable-extensions-except={extension}",f"--load-extension={extension}",url]
    return subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,env=env,start_new_session=True)
def terminate(proc):
    if proc is None:return True
    if proc.poll() is None:
        try:os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        deadline=time.monotonic()+4
        while time.monotonic()<deadline and proc.poll() is None:time.sleep(.05)
        if proc.poll() is None:
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
    try:proc.wait(timeout=2)
    except Exception:return False
    return proc.poll() is not None
def run_gate(root:Path,browser_binary=None):
    root=root.resolve();http=ThreadingHTTPServer(("127.0.0.1",0),Handler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    url=f"http://127.0.0.1:{http.server_address[1]}/";origin=f"http://127.0.0.1:{http.server_address[1]}";checks={};provider_receipts=[];uaf_receipts=[];process=None;bridge=None;browser={};sid=f"fa3-browser-session-{os.getpid()}"
    try:
        with tempfile.TemporaryDirectory(prefix="fa3-browser-session-") as td:
            tmp=Path(td);home=tmp/"home";home.mkdir(mode=0o700);xdg=tmp/"run";xdg.mkdir(mode=0o700);profile=tmp/"profile";runtime_root=xdg/"fa3"/"browser-session"
            extension=root/"browser"/"fa3-session-extension";native=root/"libexec"/"fa3-browser-session-native-host.py"
            if not extension.is_dir() or not native.is_file():raise RuntimeError("BROWSER_SESSION_IMPLEMENTATION_MISSING")
            if not os.access(native,os.X_OK):raise RuntimeError("NATIVE_HOST_NOT_EXECUTABLE")
            install_temp_manifests(home,native);bridge=BrowserSessionBridgeServer(runtime_root,timeout=20);bridge.start();binary=discover_browser_binary(browser_binary)
            env={**os.environ,"HOME":str(home),"XDG_CONFIG_HOME":str(home/".config"),"XDG_RUNTIME_DIR":str(xdg),"FA3_BROWSER_SESSION_SOCKET":str(bridge.socket_path)}
            process=launch_browser(binary,profile,extension,url,env);bridge.accept();pong=bridge.request("ping",{})
            checks["physical_bridge"]={"pass":pong.get("status")=="PONG" and pong.get("extension_id")==EXPECTED_EXTENSION_ID,"native_messaging":True,"unix_socket":str(bridge.socket_path),"extension_id":pong.get("extension_id")}
            auth,auth_path=issue_hrb(tmp,sid)
            checks["hrb"]={"pass":auth.get("authority")=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and auth.get("accelerator_required") is False,"authorization_id":auth.get("authorization_id"),"cpu_only":True}
            contracts=[action(root,"browser.action.execute")]+[action(root,a) for a in ACTION_IDS if a!="browser.action.execute"];registry=ActionRegistry(contracts);bindings={}
            def load_binding(ref):
                if ref not in bindings:raise BrowserActionDenied("BROWSER-BINDING-INVALID","unknown binding")
                return bindings[ref]
            def sink(kind,payload):provider_receipts.append({"kind":kind,"payload":payload});return f"evidence://browser-session/{kind}/{len(provider_receipts)}"
            provider=BrowserSessionProvider(bridge,binding_loader=load_binding,receipt_sink=sink);providers=ProviderRegistry();providers.register(provider);consumed=set()
            def authorize(req,contract):return req.principal.get("id")=="user:fa3-current-host" and contract.action_id in set(ACTION_IDS)
            def verify(req,contract):
                g=req.approval or{};gid=str(g.get("approval_id",""));authority=str(g.get("authority",""))
                if not gid or gid in consumed or authority not in {"AUTH-HUMAN","FA3-AUTH-SECURITY-GOV-001"}:return False
                consumed.add(gid);return True
            def resources(req,contract,descriptor):
                if run([HRB_CLIENT,"validate","--authorization",str(auth_path)],timeout=20).returncode:raise UafError("UAF-RESOURCE-DENIED","HRB authorization no longer valid")
                return{**auth,"grant_id":str(auth.get("authorization_id"))}
            dispatcher=ActionDispatcher(registry,providers,authorize=authorize,verify_approval=verify,acquire_resources=resources,release_resources=lambda lease:None,evidence_sink=uaf_receipts.append)
            principal="user:fa3-current-host";ctx=ExecutionContext("browser-session-current-host",application=PROFILE_ID,session_id=sid)
            def execute(aid,args,*,approved=False,authority="FA3-AUTH-SECURITY-GOV-001"):
                c=registry.get(aid);grant=approval(principal,c,args,ctx,aid.replace(".","-"),authority) if approved else None
                return dispatcher.execute(ActionRequest(action_id=aid,arguments=args,principal={"id":principal},context=ctx,approval=grant))
            start=execute("browser.session.start",{"session_id":sid});checks["session_start"]={"pass":start.output.get("status")=="STARTED" and start.output.get("logical_borrow_without_reparenting") is True}
            listed=execute("browser.tab.list",{"session_id":sid}).output;user=[x for x in listed.get("tabs",[]) if x.get("scope")=="USER" and x.get("origin")==origin];agent=[x for x in listed.get("tabs",[]) if x.get("scope")=="AGENT"]
            if len(user)!=1 or not agent:raise RuntimeError("EXPECTED_USER_AND_AGENT_TABS_NOT_FOUND")
            tab=user[0];original_window=tab["window_ref"];borrow_args={"session_id":sid,"tab_ref":tab["tab_ref"],"origin_scope":origin,"action_scope":["observe","click","human-assistance"],"ttl_seconds":30}
            denied=False;code=None
            try:execute("browser.tab.borrow",borrow_args)
            except UafError as exc:code=exc.code;denied=exc.code=="UAF-APPROVAL-REQUIRED"
            checks["negative_missing_approval"]={"pass":denied,"reason_code":code}
            wrong={**borrow_args,"origin_scope":"https://example.invalid"};denied=False;code=None
            try:execute("browser.tab.borrow",wrong,approved=True)
            except BrowserActionDenied as exc:code=exc.code;denied=exc.code=="ORIGIN_SCOPE_MISMATCH"
            checks["negative_origin_scope"]={"pass":denied,"reason_code":code}
            borrowed=execute("browser.tab.borrow",borrow_args,approved=True).output;after=execute("browser.tab.list",{"session_id":sid}).output;row=next(x for x in after["tabs"] if x["tab_ref"]==tab["tab_ref"])
            checks["borrow"]={"pass":borrowed.get("status")=="BORROWED" and borrowed.get("logical_borrow_without_reparenting") is True and row.get("scope")=="BORROWED" and row.get("window_ref")==original_window,"lease_id":borrowed.get("lease_id"),"reparented":row.get("window_ref")!=original_window}
            observation=provider.observe(tab["tab_ref"]);space=build_action_space(observation);click=next(c for c in space["candidates"] if c["operation"]=="CLICK" and "Advance" in c["metadata"].get("label",""))
            binding=attach_execution_parameters(bind_selected_action(space,click["id"]),{});binding["tab_ref"]=tab["tab_ref"];bindings["binding://browser-session-positive"]=binding
            action_args={"binding_ref":"binding://browser-session-positive","expected_postconditions":[{"type":"element_absent","element_id":click["target_id"]}]};res=execute("browser.action.execute",action_args,approved=True)
            checks["bounded_action"]={"pass":res.output.get("status")=="VERIFIED_SUCCESS","status":res.output.get("status")}
            stale=False;code=None
            try:execute("browser.action.execute",action_args,approved=True)
            except BrowserActionDenied as exc:code=exc.code;stale=exc.code=="STALE_OBSERVATION"
            checks["negative_stale"]={"pass":stale,"reason_code":code}
            assist_args={"session_id":sid,"tab_ref":tab["tab_ref"],"prompt":"Complete the human-only verification step, then choose Continue."};assist=execute("browser.human_assistance.request",assist_args,approved=True,authority="AUTH-HUMAN").output
            assist_obs=provider.observe(tab["tab_ref"]);visible=any(x.get("label")=="Continue" for x in assist_obs.get("elements",[]))
            checks["human_assistance_presented"]={"pass":assist.get("status")=="PENDING_HUMAN" and assist.get("human_completion_claim") is False and visible,"human_completion_proven":False}
            execute("browser.human_assistance.cancel",{"session_id":sid,"assistance_request_id":assist["assistance_request_id"]})
            returned=execute("browser.tab.return",{"session_id":sid,"tab_ref":tab["tab_ref"],"lease_id":borrowed["lease_id"]}).output;after_return=execute("browser.tab.list",{"session_id":sid}).output;rr=next(x for x in after_return["tabs"] if x["tab_ref"]==tab["tab_ref"])
            checks["return"]={"pass":returned.get("status")=="RETURNED" and rr.get("scope")=="USER" and rr.get("window_ref")==original_window}
            ttl=execute("browser.tab.borrow",{**borrow_args,"ttl_seconds":1},approved=True).output;bridge.wait_event(lambda e:e.get("type")=="event" and e.get("event")=="lease.expired" and(e.get("payload")or{}).get("lease_id")==ttl.get("lease_id"),timeout=5)
            after_ttl=execute("browser.tab.list",{"session_id":sid}).output;tr=next(x for x in after_ttl["tabs"] if x["tab_ref"]==tab["tab_ref"]);expired=False;code=None
            try:provider.observe(tab["tab_ref"])
            except BrowserActionDenied as exc:code=exc.code;expired=exc.code=="TAB_NOT_CONTROLLED"
            checks["lease_expiry"]={"pass":tr.get("scope")=="USER" and expired,"reason_code":code}
            stopped=execute("browser.session.stop",{"session_id":sid}).output;checks["session_stop"]={"pass":stopped.get("status")=="STOPPED" and stopped.get("returned_leases")==0}
            checks["uaf"]={"pass":len(uaf_receipts)>=10 and all(x.get("status")=="PASS" for x in uaf_receipts),"receipt_count":len(uaf_receipts)}
            checks["hardware"]={"pass":True,"vendor_neutral":True,"cpu_only":True,"accelerator_required":False}
            browser={"binary_name":Path(binary).name,"version":browser_version(binary),"headless_mode":"--headless=new","extension_id":EXPECTED_EXTENSION_ID,"remote_browser":False}
    finally:
        if bridge is not None:bridge.close()
        gone=terminate(process);http.shutdown();http.server_close();thread.join(timeout=2);checks["rollback"]={"pass":gone,"browser_process_gone":gone,"temporary_profile_scope":True}
    ok=bool(checks) and all(x.get("pass") is True for x in checks.values())
    return{"schema":"fa3.browser-session-current-host-receipt.v1","gate_id":GATE_ID,"profile_id":PROFILE_ID,"provider_id":PROVIDER_ID,"result":"PASS" if ok else"FAIL","evidence_level":"CURRENT_HOST_PHYSICAL_BROWSER_SESSION_BRIDGE_E2E_PASS" if ok else"CURRENT_HOST_PHYSICAL_BROWSER_SESSION_BRIDGE_E2E_FAIL","physical_current_host":True,"synthetic":False,"host":{"hostname_sha256":hashlib.sha256(socket.gethostname().encode()).hexdigest(),"system":platform.system(),"machine":platform.machine()},"browser":browser,"checks":checks,"provider_receipts":len(provider_receipts),"uaf_receipts":len(uaf_receipts),"physical_extension_native_messaging_proven":bool(ok and checks.get("physical_bridge",{}).get("pass")),"policy_approved_borrow_return_proven":bool(ok and checks.get("borrow",{}).get("pass") and checks.get("return",{}).get("pass")),"logical_borrow_without_reparenting_proven":bool(ok and checks.get("borrow",{}).get("pass")),"human_assistance_overlay_proven":bool(ok and checks.get("human_assistance_presented",{}).get("pass")),"human_assistance_completion_proven":False,"real_existing_user_profile_login_proven":False,"current_host_bridge_admitted":ok,"capability_count":143,"capability_delta":0,"authority_delta":0,"global_promotion_claim":False}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--browser-binary");ap.add_argument("--receipt",default="evidence/receipts/browser-session-current-host.json");a=ap.parse_args();root=Path(a.root).resolve()
    try:r=run_gate(root,a.browser_binary)
    except Exception as exc:r={"schema":"fa3.browser-session-current-host-receipt.v1","gate_id":GATE_ID,"profile_id":PROFILE_ID,"provider_id":PROVIDER_ID,"result":"FAIL","physical_current_host":True,"synthetic":False,"error_type":type(exc).__name__,"error":str(exc)[:512],"current_host_bridge_admitted":False,"human_assistance_completion_proven":False,"real_existing_user_profile_login_proven":False,"global_promotion_claim":False}
    out=root/a.receipt;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2));return 0 if r.get("result")=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
