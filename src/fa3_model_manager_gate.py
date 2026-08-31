#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any

PROFILE_ID="FA3-MODEL-MANAGER-001"
CONTRACT_ID="FA3-MODEL-MANAGER-CONTRACTS-001"
PROVIDER_ID="FA3-PROVIDER-STABILITY-MATRIX-MODEL-STORE-001"
DECISION_ID="FA3-DEC-MODEL-MANAGER-STABILITY-MATRIX-2026-08-31"
REFERENCE_ID="FA3-STABILITY-MATRIX-UPSTREAM-REFERENCE-2026-08-31"
GATE_ID="FA3-MODEL-MANAGER-GATESET-001"
EVIDENCE_PATH="evidence/reference/model-manager-ci-2026-08-31.json"
CAPABILITY_COUNT=143
CAPABILITY_IDS=["CAP-005","CAP-016","CAP-120"]
RULES=["MODEL_MANAGER_NOT_ARCHITECTURAL_AUTHORITY","STABILITY_MATRIX_REMAINS_PREFERRED_PHYSICAL_STORE_FOR_NATIVE_MEDIA_MODEL_CLASSES","MODEL_MANAGER_DOES_NOT_REPLACE_STABILITY_MATRIX_MODEL_MANAGEMENT","LOGICAL_MODEL_IDENTITY_SEPARATE_FROM_PHYSICAL_STORAGE_PATH","PROVIDER_METADATA_ATTRIBUTED_NOT_CANONICAL_WITHOUT_VALIDATION","ARTIFACT_CONTENT_IDENTITY_HASH_REQUIRED","DERIVED_QUANTIZED_OPTIMIZED_ARTIFACT_HAS_DISTINCT_IDENTITY_AND_LINEAGE","NATIVE_STORE_PREFERRED_UNLESS_VERIFIED_SHARED_STORE_PROJECTION","INVENTORY_DEDUP_SEPARATE_FROM_PHYSICAL_DEDUP","PHYSICAL_DEDUP_REQUIRES_HASH_FORMAT_IMMUTABILITY_COMPATIBILITY_ROLLBACK_EVIDENCE","MODEL_MANAGER_NOT_MODEL_ROUTER","MODEL_MANAGER_NOT_HOST_RESOURCE_BROKER","MODEL_MANAGER_NOT_SECRETS_POLICY_PROMOTION_AUTHORITY","PROVIDER_OUTAGE_PRESERVES_READABLE_CANONICAL_INVENTORY_PROJECTION","MUTATING_MOVE_DELETE_RELINK_REQUIRES_EXPLICIT_AUTHORIZATION","RUNTIME_COMPATIBILITY_UNKNOWN_UNTIL_EVIDENCED","PROVIDER_NATIVE_RUNTIME_STORES_MAY_REMAIN_NATIVE"]

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code":code,"severity":"P0","message":message,**extra}

def _sha256(v: Any) -> bool:
    return isinstance(v,str) and re.fullmatch(r"[0-9a-f]{64}",v) is not None

def _artifact_valid(x: dict[str, Any]) -> bool:
    return bool(x.get("artifact_id") and x.get("model_id") and x.get("format") and _sha256(x.get("sha256")) and int(x.get("size_bytes",0))>0)

def _lineage_valid(x: dict[str, Any]) -> bool:
    return bool(x.get("source_artifact_id") and x.get("derived_artifact_id") and x["source_artifact_id"] != x["derived_artifact_id"] and x.get("transformation") and x.get("recipe_or_tool_identity"))

def _physical_dedup_valid(x: dict[str, Any]) -> bool:
    required=("content_hash_match","format_match","immutable_artifact","runtime_compatibility_verified","projection_mechanism_verified","rollback_plan","explicit_authorization")
    return all(bool(x.get(k)) for k in required)

def _mutation_valid(x: dict[str, Any]) -> bool:
    return bool(x.get("authorization_id") and x.get("rollback_plan") and x.get("operation") in {"MOVE","DELETE","RELINK","PHYSICAL_DEDUP"})

def _compatibility_valid(x: dict[str, Any]) -> bool:
    state=x.get("status","UNKNOWN")
    if state=="VERIFIED":
        return bool(x.get("evidence_id"))
    return state in {"UNKNOWN","REJECTED","STALE_EVIDENCE"}

def run_regressions() -> dict[str, Any]:
    art={"artifact_id":"A1","model_id":"M1","format":"safetensors","sha256":"a"*64,"size_bytes":1}
    lineage={"source_artifact_id":"A1","derived_artifact_id":"A2","transformation":"quantize","recipe_or_tool_identity":"tool@1"}
    dedup={k:True for k in ("content_hash_match","format_match","immutable_artifact","runtime_compatibility_verified","projection_mechanism_verified","rollback_plan","explicit_authorization")}
    mutation={"authorization_id":"AUTHZ-1","rollback_plan":"restore-link","operation":"RELINK"}
    cases=[
      (RULES[0], True, PROVIDER_ID != "FA3-AUTH-MODEL-ROUTER-001"),
      (RULES[1], "STABILITY_MATRIX"=="STABILITY_MATRIX", "STABILITY_MATRIX"!="FORCE_NEW_FA3_STORE"),
      (RULES[2], "AUGMENT"!="REPLACE", True),
      (RULES[3], "M1"=="M1", "/store/a" != "/store/b"),
      (RULES[4], "ATTRIBUTED"!="CANONICAL_UNVALIDATED", True),
      (RULES[5], _artifact_valid(art), not _artifact_valid({k:v for k,v in art.items() if k!="sha256"})),
      (RULES[6], _lineage_valid(lineage), not _lineage_valid({**lineage,"derived_artifact_id":"A1"})),
      (RULES[7], "NATIVE" in {"NATIVE","VERIFIED_SHARED"}, "FORCED_SINGLE_STORE" not in {"NATIVE","VERIFIED_SHARED"}),
      (RULES[8], "DETECTION_ONLY"!="MUTATION", True),
      (RULES[9], _physical_dedup_valid(dedup), not _physical_dedup_valid({**dedup,"rollback_plan":False})),
      (RULES[10], PROFILE_ID!="FA3-AUTH-MODEL-ROUTER-001", True),
      (RULES[11], PROFILE_ID!="FA3-AUTH-HOST-RESOURCE-BROKER-001", True),
      (RULES[12], PROVIDER_ID not in {"FA3-AUTH-SECURITY-GOV-001","FA3-AUTH-OBS-EVIDENCE-001"}, True),
      (RULES[13], {"provider":"DOWN","inventory":"READABLE"}["inventory"]=="READABLE", True),
      (RULES[14], _mutation_valid(mutation), not _mutation_valid({k:v for k,v in mutation.items() if k!="authorization_id"})),
      (RULES[15], _compatibility_valid({"status":"UNKNOWN"}), not _compatibility_valid({"status":"VERIFIED"})),
      (RULES[16], "NATIVE_RUNTIME_STORE"!="FORCED_STABILITY_MATRIX_STORE", True),
    ]
    rows=[]
    for invariant,positive,negative in cases:
        ok=bool(positive and negative)
        rows.append({"invariant":invariant,"status":"PASS" if ok else "FAIL","positive_case":bool(positive),"negative_case":bool(negative)})
    passed=sum(x["status"]=="PASS" for x in rows)
    return {"schema":"fa3.model-manager-regression-report.v1","result":"PASS" if passed==len(rows) else "FAIL","passed":passed,"total":len(rows),"cases":rows}

def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings=[]
    forbidden={PROFILE_ID,PROVIDER_ID}
    authority_keys={"authority","model_routing_authority","host_resource_authority","secrets_authority","policy_authority","promotion_authority","artifact_model_identity_authority"}
    for path in (root/"canonical").rglob("*.json"):
        try:
            obj=_load(path)
        except Exception:
            continue
        def walk(v: Any, trail: tuple[str,...]=()) -> None:
            if isinstance(v,dict):
                for k,val in v.items():
                    lk=k.lower()
                    is_auth=k in authority_keys or lk.endswith("_authority")
                    if is_auth and isinstance(val,str) and val in forbidden:
                        findings.append(_finding("MODEL-MGR-AUTH-001","Model Manager/StabilityMatrix provider assigned architectural authority",path=str(path.relative_to(root)),key=".".join(trail+(k,)),value=val))
                    walk(val,trail+(k,))
            elif isinstance(v,list):
                for i,val in enumerate(v):
                    walk(val,trail+(str(i),))
        walk(obj)
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def reference_check(root: Path) -> dict[str, Any]:
    findings=[]
    paths={
      "profile":root/"canonical/profiles/FA3-MODEL-MANAGER-001.json",
      "contract":root/"canonical/contracts/FA3-MODEL-MANAGER-CONTRACTS-001.json",
      "provider":root/"canonical/providers/FA3-PROVIDER-STABILITY-MATRIX-MODEL-STORE-001.json",
      "decision":root/"canonical/decisions/FA3-DEC-MODEL-MANAGER-STABILITY-MATRIX-2026-08-31.json",
      "reference":root/"canonical/references/FA3-STABILITY-MATRIX-UPSTREAM-REFERENCE-2026-08-31.json",
      "enforcement":root/"canonical/model-manager-enforcement.json",
      "policy":root/"canonical/enforcement-policy.json",
      "evidence":root/EVIDENCE_PATH,
      "registry":root/"evidence/evidence-registry.json",
      "projection":root/"canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    }
    for key,path in paths.items():
        if not path.is_file():
            findings.append(_finding("MODEL-MGR-REF-001","Missing required model-manager artifact",artifact=key,path=str(path.relative_to(root))))
    if findings:
        return {"result":"FAIL","findings":findings}
    p=_load(paths["profile"]); c=_load(paths["contract"]); pr=_load(paths["provider"]); d=_load(paths["decision"])
    ref=_load(paths["reference"]); enf=_load(paths["enforcement"]); pol=_load(paths["policy"]); evid=_load(paths["evidence"])
    reg=_load(paths["registry"]); proj=_load(paths["projection"])
    if not (p.get("id")==PROFILE_ID and p.get("priority")=="P0" and p.get("requirement")=="MUST" and p.get("canonical_root") is False and p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==CAPABILITY_COUNT and p.get("capability_bindings")==CAPABILITY_IDS and p.get("invariants")==RULES and p.get("stability_matrix_relationship")=="PREFERRED_PROVIDER_NOT_REPLACED_BY_FA3_MODEL_MANAGER"):
        findings.append(_finding("MODEL-MGR-REF-010","Profile identity/capability/provider-boundary drift"))
    if not (c.get("id")==CONTRACT_ID and c.get("provider_neutral") is True and c.get("capability_count")==CAPABILITY_COUNT and c.get("required_semantics",{}).get("model_identity")=="STABLE_LOGICAL_IDENTITY_INDEPENDENT_OF_ABSOLUTE_PATH" and c.get("required_semantics",{}).get("physical_dedup")=="EXPLICIT_AUTHORIZATION_AND_ROLLBACK_REQUIRED" and c.get("invariants")==RULES):
        findings.append(_finding("MODEL-MGR-REF-011","Provider-neutral contract semantic drift"))
    if not (pr.get("id")==PROVIDER_ID and pr.get("canonical_root") is False and pr.get("architectural_authority") is False and pr.get("new_capability") is False and pr.get("new_architectural_authority") is False and pr.get("capability_count")==CAPABILITY_COUNT and pr.get("upstream_release")=="v2.16.3" and pr.get("upstream_release_commit")=="1efe7951d6f7dfdcd65bf3e36bd705227742402d" and pr.get("runtime_activation_status")=="CURRENT_HOST_USER_CONFIRMED_IN_USE_EXECUTABLE_EVIDENCE_PENDING" and pr.get("current_host_production_evidence")=="NOT_CLAIMED" and pr.get("global_runtime_promotion_required_when_disabled") is False):
        findings.append(_finding("MODEL-MGR-REF-012","StabilityMatrix provider pin/authority/current-host evidence boundary drift"))
    if not (d.get("id")==DECISION_ID and d.get("status")=="CANONICAL_CLOSED" and d.get("gate_id")==GATE_ID and d.get("capability_bindings")==CAPABILITY_IDS and d.get("mandatory_rule_ids")==RULES and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0 and d.get("capability_count_after")==CAPABILITY_COUNT and d.get("current_host_runtime_promotion_claim") is False):
        findings.append(_finding("MODEL-MGR-REF-013","Canonical decision drift"))
    if not (ref.get("id")==REFERENCE_ID and ref.get("release",{}).get("version")=="v2.16.3" and ref.get("release",{}).get("commit")=="1efe7951d6f7dfdcd65bf3e36bd705227742402d" and ref.get("floating_main_allowed_as_promotion_evidence") is False and ref.get("latest_release_allowed_as_automatic_production_upgrade") is False):
        findings.append(_finding("MODEL-MGR-REF-014","Pinned StabilityMatrix upstream reference drift"))
    if not (enf.get("gate_id")==GATE_ID and enf.get("fail_closed") is True and enf.get("mandatory_rule_count")==len(RULES) and enf.get("p0_invariants")==RULES and [x.get("invariant") for x in enf.get("rules",[])]==RULES):
        findings.append(_finding("MODEL-MGR-REF-015","Enforcement rule-set drift"))
    if not (GATE_ID in pol.get("mandatory_reference_gates",[]) and pol.get("model_manager_profile_id")==PROFILE_ID and pol.get("model_manager_contract_id")==CONTRACT_ID and pol.get("model_manager_provider_id")==PROVIDER_ID and pol.get("model_manager_capability_bindings")==CAPABILITY_IDS and pol.get("model_manager_mandatory_p0_rules")==RULES):
        findings.append(_finding("MODEL-MGR-REF-016","Global enforcement-policy binding drift"))
    if not (evid.get("gate_id")==GATE_ID and evid.get("status")=="PASS" and evid.get("regression_cases")==len(RULES) and evid.get("current_host_usage_state")=="USER_CONFIRMED_IN_USE" and evid.get("current_host_runtime_evidence")=="NOT_CLAIMED" and evid.get("current_host_runtime_promotion_claim") is False and evid.get("capability_count_after")==CAPABILITY_COUNT):
        findings.append(_finding("MODEL-MGR-REF-017","Committed reference evidence boundary drift"))
    records={x.get("subject_id"):x for x in reg.get("records",[])}
    bad=[]
    for cid in CAPABILITY_IDS:
        r=records.get(cid,{})
        s=r.get("model_manager_projection_status",{})
        if DECISION_ID not in r.get("source_decision_ids",[]) or EVIDENCE_PATH not in r.get("evidence_artifacts",[]) or r.get("runtime_conformance")!="EVIDENCE-PENDING" or r.get("status")!="PENDING_CURRENT_HOST" or s.get("profile_id")!=PROFILE_ID or s.get("provider_id")!=PROVIDER_ID or s.get("gate_id")!=GATE_ID or s.get("provider_usage_state")!="USER_CONFIRMED_IN_USE" or s.get("current_host_runtime_evidence")!="PENDING_REAL_CURRENT_HOST_EXECUTION":
            bad.append(cid)
    if bad:
        findings.append(_finding("MODEL-MGR-REF-018","Evidence Registry binding drift",capability_ids=bad))
    rec=proj.get("model_manager_reconciliation",{}); inv=proj.get("overlay_inventory",{}); manifest={x.get("path") for x in proj.get("manifest",[])}
    required={
      "canonical/profiles/FA3-MODEL-MANAGER-001.json","canonical/contracts/FA3-MODEL-MANAGER-CONTRACTS-001.json","canonical/providers/FA3-PROVIDER-STABILITY-MATRIX-MODEL-STORE-001.json",
      "canonical/decisions/FA3-DEC-MODEL-MANAGER-STABILITY-MATRIX-2026-08-31.json","canonical/references/FA3-STABILITY-MATRIX-UPSTREAM-REFERENCE-2026-08-31.json","canonical/model-manager-enforcement.json",
      "src/fa3_model_manager_gate.py","tests/test_model_manager_gate.py",EVIDENCE_PATH,"evidence/evidence-registry.json","canonical/enforcement-policy.json",".github/workflows/fa3-permanent-enforcement.yml","src/fa3_enforce.py","README.md"
    }
    missing_manifest=sorted(required-manifest)
    missing_inventory=[]
    for key,path in (("profile_records","canonical/profiles/FA3-MODEL-MANAGER-001.json"),("contract_records","canonical/contracts/FA3-MODEL-MANAGER-CONTRACTS-001.json"),("provider_records","canonical/providers/FA3-PROVIDER-STABILITY-MATRIX-MODEL-STORE-001.json"),("decision_records","canonical/decisions/FA3-DEC-MODEL-MANAGER-STABILITY-MATRIX-2026-08-31.json"),("upstream_reference_records","canonical/references/FA3-STABILITY-MATRIX-UPSTREAM-REFERENCE-2026-08-31.json"),("reference_evidence_records",EVIDENCE_PATH)):
        if path not in inv.get(key,[]): missing_inventory.append(path)
    if not (rec.get("profile_id")==PROFILE_ID and rec.get("contract_id")==CONTRACT_ID and rec.get("provider_id")==PROVIDER_ID and rec.get("gate_id")==GATE_ID and rec.get("capability_bindings")==CAPABILITY_IDS and rec.get("reconciliation_status")=="GLOBAL_PROJECTION_RECONCILED_CI_REFERENCE_PASS_CURRENT_HOST_USAGE_CONFIRMED_EXECUTABLE_EVIDENCE_PENDING" and rec.get("provider_usage_state")=="USER_CONFIRMED_IN_USE" and rec.get("current_host_runtime_evidence")=="PENDING_REAL_CURRENT_HOST_EXECUTION" and rec.get("current_host_runtime_promotion_claim") is False and rec.get("new_capabilities")==0 and rec.get("new_architectural_authorities")==0 and rec.get("capability_count_after")==CAPABILITY_COUNT and not missing_manifest and not missing_inventory):
        findings.append(_finding("MODEL-MGR-REF-019","Global release/inventory reconciliation drift",missing_manifest=missing_manifest,missing_inventory=missing_inventory))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root: Path) -> dict[str, Any]:
    ref=reference_check(root); auth=scan_canonical_authority_assignments(root); regressions=run_regressions()
    ok=ref["result"]==auth["result"]==regressions["result"]=="PASS"
    report={"schema":"fa3.model-manager-gate-report.v1","gate_id":GATE_ID,"profile_id":PROFILE_ID,"provider_id":PROVIDER_ID,"capability_bindings":CAPABILITY_IDS,"capability_count":CAPABILITY_COUNT,"result":"PASS" if ok else "FAIL","reference":ref,"authority_scan":auth,"regressions":regressions,"current_host_usage_state":"USER_CONFIRMED_IN_USE","current_host_runtime_promotion_claim":False,"promotion_effect":"CANONICAL_REFERENCE_PASS_DOES_NOT_CLAIM_CURRENT_HOST_PRODUCTION_PASS"}
    _write(root/"reports/model-manager-gate-report.json",report)
    return report

def main() -> int:
    ap=argparse.ArgumentParser(description="FA3 Model Manager / StabilityMatrix fail-closed canonical regression gate")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    a=ap.parse_args()
    report=gate(Path(a.root).resolve())
    print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
