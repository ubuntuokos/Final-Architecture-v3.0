#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time
from pathlib import Path
from typing import Any
from fa3_mcp_gateway import GatewayDenied
from fa3_mcp_unix_client import request as unix_request
from fa3_pageindex_local_evidence import TOKEN,text_of,retrieval_evidence
from fa3_pageindex_local_provider import PageIndexLocalConfig
PROVIDER="FA3-PROVIDER-PAGEINDEX-LOCAL-001"
def wait_gateway(sock:Path,timeout:float=30)->dict[str,Any]:
    end=time.time()+timeout
    while time.time()<end:
        try:
            code,body=unix_request(str(sock),"GET","/readyz",timeout=3)
            if code==200 and body.get("ready") is True: return body
        except Exception: pass
        time.sleep(.25)
    raise RuntimeError("Central MCP Gateway not ready")
def wait_provider_socket(timeout:float=30)->bool:
    runtime=Path(os.environ.get("XDG_RUNTIME_DIR",f"/run/user/{os.getuid()}"))
    sock=runtime/"fa3-pageindex-local/pageindex-local.sock"
    end=time.time()+timeout
    while time.time()<end:
        if sock.exists() and sock.is_socket(): return True
        time.sleep(.25)
    return False
def payload(capid:str,args:dict[str,Any])->dict[str,Any]:
    return {"actor_id":"FA3-CURRENT-HOST-PAGEINDEX","client_id":"fa3-pageindex-local-e2e","session_id":"PAGEINDEX-LOCAL-E2E",
      "capability_id":capid,"provider_id":PROVIDER,"arguments":args,
      "policy_decision":{"authority":"SECURITY_GOVERNANCE_POLICY_PLANE","status":"ALLOW","capability_id":capid,"decision_id":"FA3-PAGEINDEX-LOCAL-CURRENT-HOST"}}
def invoke(sock:Path,capid:str,args:dict[str,Any])->dict[str,Any]:
    return unix_request(str(sock),"POST","/invoke",payload(capid,args),timeout=900)[1]
def probe(sock:Path,pdf:Path,allowed_root:Path)->dict[str,Any]:
    checks={}
    ready=wait_gateway(sock)
    checks["gateway_ready"]=ready.get("ready") is True
    router_url=os.environ.get("FA3_MODEL_ROUTER_URL","")
    index_route=os.environ.get("FA3_PAGEINDEX_INDEX_ROUTE","fa3-pageindex-index")
    reason_route=os.environ.get("FA3_PAGEINDEX_REASON_ROUTE","fa3-pageindex-reason")
    try:
        PageIndexLocalConfig(Path("/tmp/x"),(allowed_root,),router_url,index_route,reason_route).validate()
        checks["model_router_loopback_verified"]=True
        checks["logical_model_routes_verified"]=all(x.startswith("fa3-") and "://" not in x for x in (index_route,reason_route))
    except GatewayDenied:
        checks["model_router_loopback_verified"]=False
        checks["logical_model_routes_verified"]=False
    checks["provider_socket_ready"]=wait_provider_socket()
    if not checks["provider_socket_ready"]: raise RuntimeError("PageIndex Local provider socket not ready")
    try:
        PageIndexLocalConfig(Path("/tmp/x"),(allowed_root,),"http://192.0.2.1/v1","fa3-index","fa3-reason").validate()
        checks["nonloopback_model_route_denied"]=False
    except GatewayDenied as exc:
        checks["nonloopback_model_route_denied"]=exc.code=="PAGEINDEX_LOCAL_MODEL_ROUTER_EGRESS"
    bad=invoke(sock,"fa3.document.index",{"source":str(allowed_root.parent/"outside.pdf")})
    checks["path_escape_denied"]=bad.get("reason_code")=="PAGEINDEX_LOCAL_SCOPE_DENIED"
    idx=invoke(sock,"fa3.document.index",{"source":str(pdf)})
    if idx.get("result_status")!="success":
        raise RuntimeError("real PageIndex index failed: "+json.dumps(idx,ensure_ascii=False,sort_keys=True))
    doc_id=str(idx.get("result",{}).get("doc_id","")); checks["real_pdf_index"]=bool(doc_id)
    meta=invoke(sock,"fa3.document.retrieve",{"operation":"metadata","doc_id":doc_id})
    structure=invoke(sock,"fa3.document.retrieve",{"operation":"structure","doc_id":doc_id})
    pages=invoke(sock,"fa3.document.retrieve",{"operation":"pages","doc_id":doc_id,"pages":"1"})
    reason=invoke(sock,"fa3.document.retrieve",{"operation":"reason","doc_id":doc_id,"query":"What is the verification phrase? Return it exactly."})
    checks["metadata_retrieval"]=meta.get("result_status")=="success"
    checks["structure_retrieval"]=structure.get("result_status")=="success"
    checks["page_retrieval"]=pages.get("result_status")=="success" and TOKEN in text_of(pages.get("result"))
    checks["reason_retrieval"]=reason.get("result_status")=="success" and TOKEN in text_of(reason.get("result"))
    receipts=[idx,meta,structure,pages,reason]
    checks["central_gateway_provider_receipts"]=all(x.get("provider_id")==PROVIDER and str(x.get("adapter_id","")).startswith("fa3.adapter.pageindex.local.") for x in receipts)
    plan,trace,passport=retrieval_evidence(doc_id,receipts)
    checks["retrieval_plan_trace_passport"]=bool(plan.get("plan_id") and trace.get("trace_id") and passport.get("passport_id")) and passport.get("rebuildable") is True
    return {"schema":"fa3.pageindex-local.runtime-probe.v2","checks":checks,"doc_id":doc_id,"model_routes":{"index":index_route,"reason":reason_route},"retrieval_plan":plan,"retrieval_trace":trace,"context_passport":passport,"reason_text":text_of(reason.get("result")),"receipts":receipts}
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--socket",required=True); ap.add_argument("--pdf",required=True); ap.add_argument("--allowed-root",required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
    result=probe(Path(a.socket),Path(a.pdf),Path(a.allowed_root))
    Path(a.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False)); return 0 if all(result["checks"].values()) else 2
if __name__=="__main__": raise SystemExit(main())
