#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,json,subprocess
from pathlib import Path
from typing import Any
PROVIDER="FA3-PROVIDER-PAGEINDEX-LOCAL-001"
GATE="FA3-PAGEINDEX-LOCAL-CURRENT-HOST-GATESET-001"
REQUIRED_FLAGS=(
 "pinned_source_clean","pageindex_version_verified","isolated_venv_verified",
 "model_router_loopback_verified","logical_model_routes_verified","central_model_router_receipt_verified",
 "provider_socket_ready","nonloopback_model_route_denied","systemd_egress_hardening",
 "path_escape_denied","real_pdf_index","metadata_retrieval","structure_retrieval","page_retrieval",
 "reason_retrieval","central_gateway_provider_receipts","gateway_ready","retrieval_plan_trace_passport",
 "canonical_registry_unchanged","persistent_services_active","persistent_services_enabled",
 "pageindex_owned_model_router_absent",
)
def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def finding(code:str,message:str,**extra:Any)->dict[str,Any]: return {"code":code,"severity":"P0","message":message,**extra}
def static_findings(root:Path)->tuple[list[dict[str,Any]],dict[str,Any]]:
    fs=[]; conf={}
    try:
        conf=loadj(root/"canonical/FA3-PAGEINDEX-LOCAL-RUNTIME-CONFORMANCE-001.json")
        prov=loadj(root/"canonical/providers/FA3-PROVIDER-PAGEINDEX-LOCAL-001.json")
        reg=loadj(root/"canonical/mcp-capability-registry.json")
        enforcement=loadj(root/"canonical/pageindex-local-current-host-enforcement.json")
        if prov.get("upstream",{}).get("commit")!="9a8dd6658278fec90347e8ac3388a205305667a3" or prov.get("upstream",{}).get("package_version")!="0.2.10":
            fs.append(finding("PIL-001","PageIndex upstream pin drift"))
        local_unit=(root/"deployment/pageindex-local/fa3-pageindex-local.service.in").read_text(encoding="utf-8")
        installer=(root/"bin/fa3-pageindex-local-install").read_text(encoding="utf-8")
        provider_src=(root/"src/fa3_pageindex_local_provider.py").read_text(encoding="utf-8")
        if "RuntimeDirectory=fa3-pageindex-local" not in local_unit or "RuntimeDirectory=fa3\n" in local_unit:
            fs.append(finding("PIL-016","PageIndex provider must own a dedicated runtime directory"))
        if (root/"deployment/pageindex-local/fa3-pageindex-model-router.service.in").exists() or (root/"src/fa3_pageindex_model_router.py").exists():
            fs.append(finding("PIL-017","PageIndex must not materialize a private Model Router"))
        forbidden=("127.0.0.1:11434","/api/tags","FA3_PAGEINDEX_MODEL=","enable fa3-pageindex-model-router.service","restart fa3-pageindex-model-router.service","fa3-pageindex-model-router.service.in")
        if any(token in installer for token in forbidden):
            fs.append(finding("PIL-021","PageIndex installer contains a provider/model-specific routing pin"))
        required=("FA3_MODEL_ROUTER_URL","FA3_PAGEINDEX_INDEX_ROUTE","FA3_PAGEINDEX_REASON_ROUTE")
        if any(token not in installer for token in required):
            fs.append(finding("PIL-022","PageIndex installer must consume central Model Router URL and logical route aliases"))
        if "Requires=fa3-pageindex-model-router.service" in local_unit or "After=fa3-pageindex-model-router.service" in local_unit:
            fs.append(finding("PIL-023","PageIndex service must not own or order a Model Router service"))
        legacy_socket="%t/fa3/pageindex-local.sock"
        if legacy_socket in installer or 'PAGEINDEX_SOCKET="$PAGEINDEX_RUNTIME_DIR/pageindex-local.sock"' not in installer or "restart fa3-pageindex-local.service" not in installer:
            fs.append(finding("PIL-018","PageIndex provider and gateway must share one absolute dedicated socket contract and restart provider"))
        if 'BindReadOnlyPaths="$PAGEINDEX_RUNTIME_DIR"' not in installer:
            fs.append(finding("PIL-019","Gateway sandbox must explicitly bind the PageIndex runtime directory read-only"))
        if 'FA3_PAGEINDEX_LOCAL_SOCKET=$PAGEINDEX_SOCKET' not in installer or 'Gateway PageIndex socket environment mismatch' not in installer:
            fs.append(finding("PIL-020","Gateway PageIndex socket environment must be exact and fail-closed"))
        local=prov.get("local_runtime",{})
        if (local.get("model_access")!="FA3_CENTRAL_MODEL_ROUTER_ONLY"
            or local.get("model_router_authority")!="FA3-AUTH-MODEL-ROUTER-001"
            or local.get("physical_backend_binding")!="ROUTER_RUNTIME_DECISION_ONLY"
            or local.get("physical_model_binding")!="ROUTER_RUNTIME_DECISION_ONLY"
            or local.get("pageindex_owned_router_service")!="DENY"):
            fs.append(finding("PIL-024","PageIndex central Model Router authority/route contract mismatch"))
        if enforcement.get("physical_backend_pin")!="DENY" or enforcement.get("physical_model_pin")!="DENY" or enforcement.get("pageindex_owned_model_router")!="DENY":
            fs.append(finding("PIL-025","PageIndex enforcement does not forbid provider/model/private-router pinning"))
        if "index_route" not in provider_src or "reason_route" not in provider_src or "index_model" in provider_src or "chat_model" in provider_src:
            fs.append(finding("PIL-026","PageIndex SDK adapter must expose logical routes, not physical model slots"))
        if prov.get("architectural_authority") is not False or prov.get("capability_count")!=143:
            fs.append(finding("PIL-002","authority/capability invariant drift"))
        expected="CONNECTED" if conf.get("status")=="CURRENT_HOST_ADMITTED" else "PENDING_CURRENT_HOST"
        provider_rows=[x for x in prov.get("capability_bindings",[]) if x.get("capability_id") in {"fa3.document.index","fa3.document.retrieve"}]
        if len(provider_rows)!=2: fs.append(finding("PIL-003","provider capability bindings missing/duplicated"))
        for row in provider_rows:
            if row.get("state")!=expected: fs.append(finding("PIL-004","provider binding/conformance state mismatch",capability=row.get("capability_id"),state=row.get("state")))
            if expected=="CONNECTED" and not row.get("evidence_ref"): fs.append(finding("PIL-005","provider CONNECTED binding lacks admission evidence",capability=row.get("capability_id")))
        rows=[]
        for cap in reg.get("capabilities",[]):
            if cap.get("capability_id") in {"fa3.document.index","fa3.document.retrieve"}:
                rows += [(cap.get("capability_id"),x) for x in cap.get("providers",[]) if x.get("provider_id")==PROVIDER]
        if len(rows)!=2: fs.append(finding("PIL-006","registry PageIndex bindings missing/duplicated"))
        for capid,row in rows:
            if row.get("transport")!="unix-user-service": fs.append(finding("PIL-007","provider transport must be unix-user-service",capability=capid))
            if row.get("state")!=expected: fs.append(finding("PIL-008","registry binding/conformance state mismatch",capability=capid,state=row.get("state")))
            if expected=="CONNECTED" and not row.get("evidence_ref"): fs.append(finding("PIL-009","registry CONNECTED binding lacks admission evidence",capability=capid))
            if row.get("model_routing")!="FA3-AUTH-MODEL-ROUTER-001" or row.get("physical_model_pin")!="DENY":
                fs.append(finding("PIL-027","registry PageIndex binding bypasses provider-neutral Model Router semantics",capability=capid))
        if conf.get("status") not in {"PENDING_CURRENT_HOST","CURRENT_HOST_ADMITTED"}: fs.append(finding("PIL-010","unknown conformance status"))
        if conf.get("status")=="CURRENT_HOST_ADMITTED":
            if prov.get("status")!="CURRENT_HOST_ADMITTED" or conf.get("production_binding_connected") is not True or conf.get("evidence_present") is not True:
                fs.append(finding("PIL-011","admitted provider/conformance flags inconsistent"))
            evidence_ref=conf.get("evidence_ref")
            if not isinstance(evidence_ref,str) or not evidence_ref or not (root/evidence_ref).is_file():
                fs.append(finding("PIL-012","admission evidence reference missing"))
    except Exception as exc:
        fs.append(finding("PIL-000","static materialization unreadable",error=repr(exc)))
    return fs,conf
def gate(root:Path,receipt_path:Path|None=None,require_evidence:bool=False)->dict[str,Any]:
    root=root.resolve(); fs,conf=static_findings(root)
    if require_evidence and not fs:
        path=receipt_path or root/"evidence/receipts/pageindex-local-current-host.json"
        if not path.is_absolute(): path=root/path
        try:
            rec=loadj(path)
            if rec.get("schema")!="fa3.pageindex-local.current-host-evidence.v2" or rec.get("provider_id")!=PROVIDER or rec.get("gate_id")!=GATE:
                fs.append(finding("PIL-HOST-001","receipt binding mismatch"))
            if rec.get("result")!="PASS": fs.append(finding("PIL-HOST-002","current-host result is not PASS"))
            try:
                captured=dt.datetime.fromisoformat(str(rec.get("captured_at","")).replace("Z","+00:00"))
                age=dt.datetime.now(dt.timezone.utc)-captured.astimezone(dt.timezone.utc)
                if age<dt.timedelta(0) or age>dt.timedelta(hours=24): raise ValueError("stale")
            except Exception: fs.append(finding("PIL-HOST-003","receipt stale/invalid"))
            h=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
            if rec.get("repository_head")!=h: fs.append(finding("PIL-HOST-004","receipt not bound to checkout HEAD"))
            for key in REQUIRED_FLAGS:
                if rec.get("checks",{}).get(key) is not True: fs.append(finding("PIL-HOST-005","required evidence flag missing",flag=key))
            router=rec.get("model_router",{})
            route_bindings=router.get("route_bindings",{})
            if (router.get("authority")!="FA3-AUTH-MODEL-ROUTER-001"
                or len(router.get("logical_routes",[]))<2
                or router.get("runtime_selected") is not True
                or not isinstance(route_bindings,dict)
                or any(not isinstance(v,dict) or not v.get("provider_id") or not v.get("runtime_id") or not v.get("model") or v.get("selection")!="RUNTIME_DISCOVERED" for v in route_bindings.values())):
                fs.append(finding("PIL-HOST-008","central Model Router evidence is missing, not authority-bound, or lacks runtime route provenance"))
            if conf.get("status")=="CURRENT_HOST_ADMITTED":
                if rec.get("status")!="CURRENT_HOST_PASS" or rec.get("canonical_binding_state")!="CONNECTED" or rec.get("service_left_enabled") is not True:
                    fs.append(finding("PIL-HOST-006","admitted state requires live persistent CURRENT_HOST_PASS"))
            elif rec.get("status")!="CANDIDATE_PASS" or rec.get("canonical_binding_state")!="PENDING_CURRENT_HOST":
                fs.append(finding("PIL-HOST-007","pending state requires candidate PASS"))
        except Exception as exc:
            fs.append(finding("PIL-HOST-000","current-host receipt missing/unreadable",error=repr(exc)))
    return {"schema":"fa3.pageindex-local-current-host-gate.v2","gate_id":GATE,"result":"PASS" if not fs else "FAIL","findings":fs,"status":conf.get("status"),"global_promotion_claim":False}
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--receipt"); ap.add_argument("--require-evidence",action="store_true"); a=ap.parse_args()
    r=gate(Path(a.root),Path(a.receipt) if a.receipt else None,a.require_evidence)
    print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
