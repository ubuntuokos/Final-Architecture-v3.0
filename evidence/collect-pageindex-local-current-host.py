#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from fa3_pageindex_local_evidence import write_fixture_pdf
PROVIDER="FA3-PROVIDER-PAGEINDEX-LOCAL-001"
PIN="9a8dd6658278fec90347e8ac3388a205305667a3"
ROUTER_AUTHORITY="FA3-AUTH-MODEL-ROUTER-001"
def local_binding(reg,capid):
    cap=next(x for x in reg["capabilities"] if x.get("capability_id")==capid)
    return next(x for x in cap["providers"] if x.get("provider_id")==PROVIDER)
def run(cmd,timeout=120,env=None):
    subprocess.run(cmd,cwd=ROOT,check=True,timeout=timeout,env=env)
def load_router_receipt(path:Path,router_url:str,index_route:str,reason_route:str)->dict:
    if not path.is_file(): raise SystemExit(f"Central FA3 Model Router current-host receipt missing: {path}")
    rec=json.loads(path.read_text(encoding="utf-8"))
    routes=rec.get("logical_routes",[])
    if rec.get("authority")!=ROUTER_AUTHORITY or rec.get("result")!="PASS" or rec.get("provider_neutral") is not True:
        raise SystemExit("Central Model Router receipt does not prove provider-neutral FA3 routing authority")
    if str(rec.get("endpoint","")).rstrip("/")!=router_url.rstrip("/"):
        raise SystemExit("Central Model Router receipt endpoint does not match FA3_MODEL_ROUTER_URL")
    if not isinstance(routes,list) or not {index_route,reason_route}.issubset(set(routes)):
        raise SystemExit("Central Model Router receipt does not admit the required PageIndex logical routes")
    if rec.get("physical_backend_pinned") is not False or rec.get("physical_model_pinned") is not False:
        raise SystemExit("Central Model Router receipt must prove runtime-selected, non-pinned backend/model routing")
    return rec
def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="evidence/receipts/pageindex-local-current-host.json")
    ap.add_argument("--model-router-receipt",default=os.environ.get("FA3_MODEL_ROUTER_RECEIPT",""))
    a=ap.parse_args()
    router_url=os.environ.get("FA3_MODEL_ROUTER_URL","").strip()
    index_route=os.environ.get("FA3_PAGEINDEX_INDEX_ROUTE","fa3-pageindex-index").strip()
    reason_route=os.environ.get("FA3_PAGEINDEX_REASON_ROUTE","fa3-pageindex-reason").strip()
    if not router_url: raise SystemExit("FA3_MODEL_ROUTER_URL is required; PageIndex may not select a backend itself")
    u=urlparse(router_url)
    if u.scheme not in {"http","https"} or u.hostname not in {"127.0.0.1","::1","localhost"}:
        raise SystemExit("FA3_MODEL_ROUTER_URL must reference the loopback central Model Router")
    if not a.model_router_receipt: raise SystemExit("FA3_MODEL_ROUTER_RECEIPT or --model-router-receipt is required")
    router_receipt_path=Path(a.model_router_receipt).expanduser().resolve()
    router_receipt=load_router_receipt(router_receipt_path,router_url,index_route,reason_route)

    canonical=ROOT/"canonical/mcp-capability-registry.json"; original=canonical.read_bytes(); reg=json.loads(original)
    states={local_binding(reg,c)["state"] for c in ("fa3.document.index","fa3.document.retrieve")}
    if len(states)!=1 or next(iter(states)) not in {"PENDING_CURRENT_HOST","CONNECTED"}: raise SystemExit("invalid canonical binding state")
    source_state=next(iter(states)); passed=False
    ingest=Path.home()/".local/share/fa3/knowledge-ingest"; ingest.mkdir(parents=True,exist_ok=True)
    pdf=ingest/"fa3-pageindex-current-host.pdf"; sample_sha=write_fixture_pdf(pdf)
    runtime=Path.home()/".local/share/fa3/providers/pageindex-local"/PIN; source=runtime/"source"
    manifest=json.loads((runtime/"runtime-manifest.json").read_text(encoding="utf-8"))
    for capid in ("fa3.document.index","fa3.document.retrieve"):
        row=local_binding(reg,capid); row["state"]="CONNECTED"; row["evidence_ref"]="CURRENT_HOST_PROVISIONAL"
    tmp_registry=None; probe_file=Path(tempfile.mkstemp(prefix="fa3-pageindex-probe-",suffix=".json")[1])
    checks={}
    env=os.environ.copy()
    env["FA3_MODEL_ROUTER_URL"]=router_url
    env["FA3_PAGEINDEX_INDEX_ROUTE"]=index_route
    env["FA3_PAGEINDEX_REASON_ROUTE"]=reason_route
    try:
        with tempfile.NamedTemporaryFile("w",delete=False,suffix=".json") as fh:
            json.dump(reg,fh); tmp_registry=Path(fh.name)
        run(["bash",str(ROOT/"bin/fa3-os-mcp-agent-exposure-install"),"--registry",str(tmp_registry),"--start"],60,env)
        run(["bash",str(ROOT/"bin/fa3-pageindex-local-install"),"--allowed-root",str(ingest),"--start"],60,env)
        sock=Path(os.environ.get("XDG_RUNTIME_DIR",f"/run/user/{os.getuid()}"))/"fa3/mcp-gateway.sock"
        run([sys.executable,str(SRC/"fa3_pageindex_local_runtime_probe.py"),"--socket",str(sock),"--pdf",str(pdf),"--allowed-root",str(ingest),"--output",str(probe_file)],1200,env)
        probe=json.loads(probe_file.read_text(encoding="utf-8")); checks.update(probe["checks"])
        checks["central_model_router_receipt_verified"]=True
        checks["pinned_source_clean"]=subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],text=True).strip()==PIN and not subprocess.check_output(["git","-C",str(source),"status","--porcelain"],text=True).strip()
        checks["pageindex_version_verified"]=manifest.get("pageindex_version")=="0.2.10" and manifest.get("upstream_commit")==PIN
        checks["isolated_venv_verified"]=(runtime/"venv/bin/python").is_file()
        unit=subprocess.check_output(["systemctl","--user","cat","fa3-pageindex-local.service"],text=True)
        checks["systemd_egress_hardening"]="IPAddressDeny=any" in unit and "IPAddressAllow=localhost" in unit
        names=("fa3-pageindex-local.service","fa3-mcp-gateway.service")
        checks["persistent_services_active"]=all(subprocess.run(["systemctl","--user","is-active","--quiet",n]).returncode==0 for n in names)
        checks["persistent_services_enabled"]=subprocess.run(["systemctl","--user","is-enabled","--quiet","fa3-pageindex-local.service"]).returncode==0
        checks["pageindex_owned_model_router_absent"]=subprocess.run(["systemctl","--user","is-active","--quiet","fa3-pageindex-model-router.service"]).returncode!=0
        checks["canonical_registry_unchanged"]=hashlib.sha256(canonical.read_bytes()).hexdigest()==hashlib.sha256(original).hexdigest()
        passed=all(checks.values())
        receipt={"schema":"fa3.pageindex-local.current-host-evidence.v2","conformance_id":"FA3-PAGEINDEX-LOCAL-RUNTIME-CONFORMANCE-001","gate_id":"FA3-PAGEINDEX-LOCAL-CURRENT-HOST-GATESET-001","provider_id":PROVIDER,"result":"PASS" if passed else "FAIL","status":"CURRENT_HOST_PASS" if passed and source_state=="CONNECTED" else "CANDIDATE_PASS" if passed else "FAIL","captured_at":dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z"),"repository_head":subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip(),"canonical_binding_state":source_state,"service_left_enabled":bool(passed and source_state=="CONNECTED"),"sample_pdf_sha256":sample_sha,"runtime_manifest":manifest,"model_router":{"authority":ROUTER_AUTHORITY,"endpoint":router_url,"logical_routes":[index_route,reason_route],"receipt_path":str(router_receipt_path),"receipt_sha256":hashlib.sha256(router_receipt_path.read_bytes()).hexdigest(),"physical_backend":router_receipt.get("executed_backend"),"physical_model":router_receipt.get("executed_model")},"checks":checks,"retrieval_plan":probe.get("retrieval_plan"),"retrieval_trace":probe.get("retrieval_trace"),"context_passport":probe.get("context_passport"),"global_promotion_claim":False}
        out=ROOT/a.output; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); print(json.dumps(receipt,indent=2,ensure_ascii=False))
    finally:
        if tmp_registry: tmp_registry.unlink(missing_ok=True)
        probe_file.unlink(missing_ok=True); pdf.unlink(missing_ok=True)
        if source_state!="CONNECTED" or not passed:
            subprocess.run(["bash",str(ROOT/"bin/fa3-pageindex-local-install"),"--stop"],cwd=ROOT,check=False,env=env)
            subprocess.run(["bash",str(ROOT/"bin/fa3-os-mcp-agent-exposure-install"),"--registry",str(canonical),"--start"],cwd=ROOT,check=False,env=env)
    return 0 if passed else 2
if __name__=="__main__": raise SystemExit(main())
