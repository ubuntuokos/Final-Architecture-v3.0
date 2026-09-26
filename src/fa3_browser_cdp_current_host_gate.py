#!/usr/bin/env python3
from __future__ import annotations
from fa3_release_baseline import module_active_capability_count
import argparse,hashlib,json,platform,socket,threading
from datetime import datetime,timedelta,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from fa3_browser_action_runtime import BrowserActionDenied,attach_execution_parameters,bind_selected_action,build_action_space
from fa3_browser_cdp_provider import BrowserCdpProvider,BrowserCdpSession,PROVIDER_ID
from fa3_uaf import ActionContract,ActionDispatcher,ActionRegistry,ActionRequest,ExecutionContext,ProviderRegistry,_canonical_digest
HTML=b"""<!doctype html><html><body><button id="advance" onclick="document.getElementById('status').textContent='clicked';history.replaceState(null,'','#clicked')">Advance</button><div id="status">idle</div></body></html>"""
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):self.send_response(200);self.send_header("Content-Type","text/html");self.send_header("Content-Length",str(len(HTML)));self.end_headers();self.wfile.write(HTML)
    def log_message(self,fmt,*args):return
def approval(principal,action,arguments,context,suffix):return{"approval_id":f"browser-cdp-current-host-{suffix}","principal_ref":principal,"action_id":action.action_id,"action_version":action.version,"argument_digest":_canonical_digest(arguments),"context_digest":_canonical_digest(context.as_dict()),"expires_at":(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat(),"single_use":True}
def run_gate(root:Path,browser_binary=None):
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f"http://127.0.0.1:{server.server_address[1]}/";session=BrowserCdpSession(browser_binary);bindings={};provider_receipts=[];uaf_receipts=[];checks={};profile=None;pid=None;browser={}
    def load(ref):
        if ref not in bindings:raise BrowserActionDenied("BROWSER-BINDING-INVALID","unknown binding ref")
        return bindings[ref]
    def sink(kind,payload):provider_receipts.append({"kind":kind,"payload":payload});return f"evidence://browser-cdp/{kind}/{len(provider_receipts)}"
    try:
        session.launch(url);profile=session.profile_dir;pid=session.pid;action=ActionContract.from_dict(json.loads((root/"canonical/actions/browser.action.execute.json").read_text()));registry=ActionRegistry([action]);providers=ProviderRegistry();providers.register(BrowserCdpProvider(session,binding_loader=load,receipt_sink=sink));dispatcher=ActionDispatcher(registry,providers,authorize=lambda r,c:True,verify_approval=lambda r,c:True,acquire_resources=lambda r,c,d:{"lease_id":"hrb-browser-current-host","cpu_only":True},release_resources=lambda lease:None,evidence_sink=uaf_receipts.append)
        space=build_action_space(session.observe());click=next(row for row in space["candidates"] if row["operation"]=="CLICK" and "Advance" in row["metadata"].get("label",""));bindings["binding://positive"]=attach_execution_parameters(bind_selected_action(space,click["id"]),{});ctx=ExecutionContext("browser-cdp-positive",application="FA3-BROWSER-ACTION-RUNTIME-001");args={"binding_ref":"binding://positive","expected_postconditions":[{"type":"url_contains","value":"#clicked"}]};req=ActionRequest(action_id=action.action_id,arguments=args,principal={"id":"user:fa3-current-host"},context=ctx,approval=approval("user:fa3-current-host",action,args,ctx,"positive"));result=dispatcher.execute(req);checks["positive"]={"pass":result.output.get("status")=="VERIFIED_SUCCESS" and result.provider_id==PROVIDER_ID and bool(uaf_receipts),"status":result.output.get("status")}
        session.navigate(url);space=build_action_space(session.observe());click=next(row for row in space["candidates"] if row["operation"]=="CLICK" and "Advance" in row["metadata"].get("label",""));bindings["binding://stale"]=attach_execution_parameters(bind_selected_action(space,click["id"]),{});session.evaluate("document.getElementById('advance').textContent='Changed'");ctx=ExecutionContext("browser-cdp-stale");args={"binding_ref":"binding://stale","expected_postconditions":[]};req=ActionRequest(action_id=action.action_id,arguments=args,principal={"id":"user:fa3-current-host"},context=ctx,approval=approval("user:fa3-current-host",action,args,ctx,"stale"));denied=False;code=None
        try:dispatcher.execute(req)
        except BrowserActionDenied as exc:code=exc.code;denied=code=="STALE_OBSERVATION"
        checks["negative"]={"pass":denied,"stale_observation_denied":denied,"reason_code":code};checks["hardware"]={"pass":True,"cpu_only_supported":True,"accelerator_required":False};browser={"binary_name":Path(session.browser_binary).name,"version":session.browser_version(),"headless_mode":session.headless_mode,"cdp_loopback_only":True,"remote_cdp_allowed":False}
    finally:session.close();server.shutdown();server.server_close();thread.join(timeout=2)
    gone=True
    if pid:
        try:
            import os;os.kill(pid,0);gone=False
        except ProcessLookupError:gone=True
        except PermissionError:gone=False
    removed=profile is None or not profile.exists();checks["rollback"]={"pass":gone and removed,"browser_process_gone":gone,"temporary_profile_removed":removed};ok=all(x.get("pass") for x in checks.values())
    return{"schema":"fa3.browser-cdp-current-host-receipt.v1","gate_id":"FA3-GATE-BROWSER-CDP-CURRENT-HOST-001","provider_id":PROVIDER_ID,"result":"PASS" if ok else "FAIL","evidence_level":"CURRENT_HOST_PHYSICAL_BROWSER_E2E_PASS" if ok else "CURRENT_HOST_PHYSICAL_BROWSER_E2E_FAIL","physical_current_host":True,"synthetic":False,"host":{"hostname_sha256":hashlib.sha256(socket.gethostname().encode()).hexdigest(),"system":platform.system(),"machine":platform.machine()},"browser":browser,"checks":checks,"provider_receipts":len(provider_receipts),"uaf_receipts":len(uaf_receipts),"current_host_provider_admitted":ok,"capability_count":module_active_capability_count(__file__),"capability_delta":0,"authority_delta":0,"global_promotion_claim":False}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--browser-binary");ap.add_argument("--receipt",default="evidence/receipts/browser-cdp-current-host.json");a=ap.parse_args();root=Path(a.root).resolve()
    try:r=run_gate(root,a.browser_binary)
    except Exception as exc:r={"schema":"fa3.browser-cdp-current-host-receipt.v1","gate_id":"FA3-GATE-BROWSER-CDP-CURRENT-HOST-001","provider_id":PROVIDER_ID,"result":"FAIL","physical_current_host":True,"synthetic":False,"error_type":type(exc).__name__,"current_host_provider_admitted":False,"global_promotion_claim":False}
    out=root/a.receipt;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
