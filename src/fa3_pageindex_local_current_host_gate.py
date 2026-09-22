#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,json,subprocess
from pathlib import Path
from typing import Any
PROVIDER="FA3-PROVIDER-PAGEINDEX-LOCAL-001"
CONF="FA3-PAGEINDEX-LOCAL-RUNTIME-CONFORMANCE-001"
GATE="FA3-PAGEINDEX-LOCAL-CURRENT-HOST-GATESET-001"
REQUIRED_FLAGS=(
 "pinned_source_clean","pageindex_version_verified","isolated_venv_verified",
 "model_router_loopback_verified","provider_socket_ready","nonloopback_model_route_denied","systemd_egress_hardening",
 "path_escape_denied","real_pdf_index","metadata_retrieval","structure_retrieval",
 "page_retrieval","reason_retrieval","central_gateway_provider_receipts","gateway_ready",
 "retrieval_plan_trace_passport","canonical_registry_unchanged","persistent_services_active",
 "persistent_services_enabled",
)
def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def finding(code:str,message:str,**extra:Any)->dict[str,Any]: return {"code":code,"severity":"P0","message":message,**extra}
def static_findings(root:Path)->tuple[list[dict[str,Any]],dict[str,Any]]:
    fs=[]; conf={}
    try:
        conf=loadj(root/"canonical/FA3-PAGEINDEX-LOCAL-RUNTIME-CONFORMANCE-001.json")
        prov=loadj(root/"canonical/providers/FA3-PROVIDER-PAGEINDEX-LOCAL-001.json")
        reg=loadj(root/"canonical/mcp-capability-registry.json")
        if prov.get("upstream",{}).get("commit")!="9a8dd6658278fec90347e8ac3388a205305667a3" or prov.get("upstream",{}).get("package_version")!="0.2.10":
            fs.append(finding("PIL-001","PageIndex upstream pin drift"))
        local_unit=(root/"deployment/pageindex-local/fa3-pageindex-local.service.in").read_text(encoding="utf-8")
        router_unit=(root/"deployment/pageindex-local/fa3-pageindex-model-router.service.in").read_text(encoding="utf-8")
        installer=(root/"bin/fa3-pageindex-local-install").read_text(encoding="utf-8")
        if "RuntimeDirectory=fa3-pageindex-local" not in local_unit or "RuntimeDirectory=fa3\n" in local_unit:
            fs.append(finding("PIL-016","PageIndex provider must own a dedicated runtime directory"))
        if "After=default.target" in router_unit:
            fs.append(finding("PIL-017","PageIndex model-router ordering cycle regression"))
        if "%t/fa3-pageindex-local/pageindex-local.sock" not in installer or "restart fa3-pageindex-local.service" not in installer:
            fs.append(finding("PIL-018","PageIndex installer must bind dedicated socket and restart provider"))
        if prov.get("architectural_authority") is not False or prov.get("capability_count")!=143:
            fs.append(finding("PIL-002","authority/capability invariant drift"))
        expected="CONNECTED" if conf.get("status")=="CURRENT_HOST_ADMITTED" else "PENDING_CURRENT_HOST"
        expected_ref="evidence/reference/pageindex-local-current-host-admission-2026-09-19.json"
        provider_rows=[x for x in prov.get("capability_bindings",[]) if x.get("capability_id") in {"fa3.document.index","fa3.document.retrieve"}]
        if len(provider_rows)!=2:
            fs.append(finding("PIL-003","provider capability bindings missing/duplicated"))
        for row in provider_rows:
            if row.get("state")!=expected:
                fs.append(finding("PIL-004","provider binding/conformance state mismatch",capability=row.get("capability_id"),state=row.get("state")))
            if expected=="CONNECTED" and row.get("evidence_ref")!=expected_ref:
                fs.append(finding("PIL-005","provider CONNECTED binding lacks admission evidence",capability=row.get("capability_id")))
        rows=[]
        for cap in reg.get("capabilities",[]):
            if cap.get("capability_id") in {"fa3.document.index","fa3.document.retrieve"}:
                rows += [(cap.get("capability_id"),x) for x in cap.get("providers",[]) if x.get("provider_id")==PROVIDER]
        if len(rows)!=2: fs.append(finding("PIL-006","registry PageIndex bindings missing/duplicated"))
        for capid,row in rows:
            if row.get("transport")!="unix-user-service":
                fs.append(finding("PIL-007","provider transport must be unix-user-service",capability=capid))
            if row.get("state")!=expected:
                fs.append(finding("PIL-008","registry binding/conformance state mismatch",capability=capid,state=row.get("state")))
            if expected=="CONNECTED" and row.get("evidence_ref")!=expected_ref:
                fs.append(finding("PIL-009","registry CONNECTED binding lacks admission evidence",capability=capid))
        if conf.get("status") not in {"PENDING_CURRENT_HOST","CURRENT_HOST_ADMITTED"}:
            fs.append(finding("PIL-010","unknown conformance status"))
        if conf.get("status")=="CURRENT_HOST_ADMITTED":
            if prov.get("status")!="CURRENT_HOST_ADMITTED" or conf.get("production_binding_connected") is not True or conf.get("evidence_present") is not True:
                fs.append(finding("PIL-011","admitted provider/conformance flags inconsistent"))
            if conf.get("evidence_ref")!=expected_ref or not (root/expected_ref).is_file():
                fs.append(finding("PIL-012","admission evidence reference missing"))
            else:
                admission=loadj(root/expected_ref)
                candidate=admission.get("candidate_evidence",{})
                if admission.get("decision")!="ADMIT_FOR_FINAL_CURRENT_HOST_VALIDATION" or admission.get("global_promotion_claim") is not False:
                    fs.append(finding("PIL-013","admission decision/global scope invalid"))
                if candidate.get("result")!="PASS" or candidate.get("status")!="CANDIDATE_PASS" or candidate.get("canonical_binding_state")!="PENDING_CURRENT_HOST":
                    fs.append(finding("PIL-014","candidate evidence is not a valid pre-admission PASS"))
                digest=str(candidate.get("workflow_artifact_digest",""))
                receipt_sha=str(candidate.get("receipt_sha256",""))
                if not digest.startswith("sha256:") or len(digest)!=71 or len(receipt_sha)!=64:
                    fs.append(finding("PIL-015","candidate evidence hash binding invalid"))
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
            if rec.get("schema")!="fa3.pageindex-local.current-host-evidence.v1" or rec.get("provider_id")!=PROVIDER or rec.get("gate_id")!=GATE:
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
                if rec.get("checks",{}).get(key) is not True:
                    fs.append(finding("PIL-HOST-005","required evidence flag missing",flag=key))
            if conf.get("status")=="CURRENT_HOST_ADMITTED":
                if rec.get("status")!="CURRENT_HOST_PASS" or rec.get("canonical_binding_state")!="CONNECTED" or rec.get("service_left_enabled") is not True:
                    fs.append(finding("PIL-HOST-006","admitted state requires live persistent CURRENT_HOST_PASS"))
            elif rec.get("status")!="CANDIDATE_PASS" or rec.get("canonical_binding_state")!="PENDING_CURRENT_HOST":
                fs.append(finding("PIL-HOST-007","pending state requires candidate PASS"))
        except Exception as exc:
            fs.append(finding("PIL-HOST-000","current-host receipt missing/unreadable",error=repr(exc)))
    return {"schema":"fa3.pageindex-local-current-host-gate.v1","gate_id":GATE,"result":"PASS" if not fs else "FAIL","findings":fs,"status":conf.get("status"),"global_promotion_claim":False}
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--receipt"); ap.add_argument("--require-evidence",action="store_true"); a=ap.parse_args()
    r=gate(Path(a.root),Path(a.receipt) if a.receipt else None,a.require_evidence)
    print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
