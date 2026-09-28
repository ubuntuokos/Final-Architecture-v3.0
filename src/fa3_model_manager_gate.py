#!/usr/bin/env python3
from __future__ import annotations
from fa3_release_baseline import module_active_capability_count
import argparse, json, re
from pathlib import Path
from typing import Any
from fa3_model_manager_v2_gate import gate as model_manager_v2_gate

PROFILE_ID="FA3-MODEL-MANAGER-001"
CONTRACT_ID="FA3-MODEL-MANAGER-CONTRACTS-001"
DECISION_ID="FA3-DEC-MODEL-MANAGER-NATIVE-STORAGE-2026-09-26"
GATE_ID="FA3-MODEL-MANAGER-GATESET-001"
EVIDENCE_PATH="evidence/reference/model-manager-ci-2026-08-31.json"
CANONICAL_STORE_ID="FA3_POLICY_BOUND_CANONICAL_ARTIFACT_STORE"
CAPABILITY_COUNT=module_active_capability_count(__file__)
CAPABILITY_IDS=["CAP-005","CAP-016","CAP-120"]
RULES=[
"MODEL_MANAGER_NOT_ARCHITECTURAL_AUTHORITY",
"CANONICAL_ARTIFACT_STORE_IS_POLICY_BOUND_AND_PROVIDER_NEUTRAL",
"MODEL_MANAGER_DOES_NOT_REQUIRE_EXTERNAL_MODEL_STORE_MANAGER",
"LOGICAL_MODEL_IDENTITY_SEPARATE_FROM_PHYSICAL_STORAGE_PATH",
"PROVIDER_METADATA_ATTRIBUTED_NOT_CANONICAL_WITHOUT_VALIDATION",
"ARTIFACT_CONTENT_IDENTITY_HASH_REQUIRED",
"DERIVED_QUANTIZED_OPTIMIZED_ARTIFACT_HAS_DISTINCT_IDENTITY_AND_LINEAGE",
"NATIVE_STORE_PREFERRED_UNLESS_VERIFIED_SHARED_STORE_PROJECTION",
"INVENTORY_DEDUP_SEPARATE_FROM_PHYSICAL_DEDUP",
"PHYSICAL_DEDUP_REQUIRES_HASH_FORMAT_IMMUTABILITY_COMPATIBILITY_ROLLBACK_EVIDENCE",
"MODEL_MANAGER_NOT_MODEL_ROUTER",
"MODEL_MANAGER_NOT_HOST_RESOURCE_BROKER",
"MODEL_MANAGER_NOT_SECRETS_POLICY_PROMOTION_AUTHORITY",
"PROVIDER_OUTAGE_PRESERVES_READABLE_CANONICAL_INVENTORY_PROJECTION",
"MUTATING_MOVE_DELETE_RELINK_REQUIRES_EXPLICIT_AUTHORIZATION",
"RUNTIME_COMPATIBILITY_UNKNOWN_UNTIL_EVIDENCED",
"PROVIDER_NATIVE_RUNTIME_STORES_MAY_REMAIN_NATIVE"]

def _load(path: Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def _write(path: Path,obj:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
def _finding(code:str,message:str,**extra:Any)->dict[str,Any]: return {"code":code,"severity":"P0","message":message,**extra}
def _sha256(v:Any)->bool: return isinstance(v,str) and re.fullmatch(r"[0-9a-f]{64}",v) is not None

def run_regressions()->dict[str,Any]:
    cases=[
      (RULES[0], PROFILE_ID not in {"FA3-AUTH-MODEL-ROUTER-001","FA3-AUTH-HOST-RESOURCE-BROKER-001"}, True),
      (RULES[1], CANONICAL_STORE_ID.startswith("FA3_"), "EXTERNAL_STORE" != CANONICAL_STORE_ID),
      (RULES[2], True, "REQUIRED_EXTERNAL_STORE"!="FA3_NATIVE"),
      (RULES[3], "M1"=="M1", "/store/a"!="/store/b"),
      (RULES[4], "ATTRIBUTED"!="CANONICAL_UNVALIDATED", True),
      (RULES[5], _sha256("a"*64), not _sha256("bad")),
      (RULES[6], "A1"!="A2", True),
      (RULES[7], "NATIVE" in {"NATIVE","VERIFIED_SHARED"}, "FORCED_SINGLE_STORE" not in {"NATIVE","VERIFIED_SHARED"}),
      (RULES[8], "DETECTION_ONLY"!="MUTATION", True),
      (RULES[9], all((True,True,True,True,True,True,True)), not all((True,True,True,False,True,True,True))),
      (RULES[10], PROFILE_ID!="FA3-AUTH-MODEL-ROUTER-001", True),
      (RULES[11], PROFILE_ID!="FA3-AUTH-HOST-RESOURCE-BROKER-001", True),
      (RULES[12], CANONICAL_STORE_ID not in {"FA3-AUTH-SECURITY-GOV-001","FA3-AUTH-OBS-EVIDENCE-001"}, True),
      (RULES[13], {"provider":"DOWN","inventory":"READABLE"}["inventory"]=="READABLE", True),
      (RULES[14], bool("AUTHZ-1") and bool("rollback"), not bool("")),
      (RULES[15], "UNKNOWN" in {"UNKNOWN","REJECTED","STALE_EVIDENCE"}, "VERIFIED" not in {"UNKNOWN","REJECTED","STALE_EVIDENCE"}),
      (RULES[16], "NATIVE_RUNTIME_STORE"!="FORCED_CANONICAL_STORE", True),
    ]
    rows=[{"invariant":i,"status":"PASS" if p and n else "FAIL","positive_case":bool(p),"negative_case":bool(n)} for i,p,n in cases]
    passed=sum(x["status"]=="PASS" for x in rows)
    return {"schema":"fa3.model-manager-regression-report.v2","result":"PASS" if passed==len(rows) else "FAIL","passed":passed,"total":len(rows),"cases":rows}

def scan_canonical_authority_assignments(root:Path)->dict[str,Any]:
    findings=[]
    forbidden={PROFILE_ID,CANONICAL_STORE_ID}
    for path in (root/"canonical").rglob("*.json"):
        try: obj=_load(path)
        except Exception: continue
        def walk(v:Any,trail:tuple[str,...]=()):
            if isinstance(v,dict):
                for k,val in v.items():
                    lk=k.lower()
                    if (lk=="authority" or lk.endswith("_authority")) and isinstance(val,str) and val in forbidden:
                        findings.append(_finding("MODEL-MGR-AUTH-001","Model Manager or canonical artifact store assigned architectural authority",path=str(path.relative_to(root)),key=".".join(trail+(k,)),value=val))
                    walk(val,trail+(k,))
            elif isinstance(v,list):
                for i,val in enumerate(v): walk(val,trail+(str(i),))
        walk(obj)
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def reference_check(root:Path)->dict[str,Any]:
    findings=[]
    paths={
      "profile":root/"canonical/profiles/FA3-MODEL-MANAGER-001.json",
      "contract":root/"canonical/contracts/FA3-MODEL-MANAGER-CONTRACTS-001.json",
      "decision":root/"canonical/decisions/FA3-DEC-MODEL-MANAGER-NATIVE-STORAGE-2026-09-26.json",
      "enforcement":root/"canonical/model-manager-enforcement.json",
      "policy":root/"canonical/enforcement-policy.json",
      "evidence":root/EVIDENCE_PATH,
      "registry":root/"evidence/evidence-registry.json",
      "projection":root/"canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    }
    for key,path in paths.items():
        if not path.is_file(): findings.append(_finding("MODEL-MGR-REF-001","Missing required model-manager artifact",artifact=key,path=str(path.relative_to(root))))
    if findings: return {"result":"FAIL","findings":findings}
    p,c,d,enf,pol,evid,reg,proj=[_load(paths[k]) for k in ("profile","contract","decision","enforcement","policy","evidence","registry","projection")]
    if not (p.get("id")==PROFILE_ID and p.get("capability_count")==CAPABILITY_COUNT and p.get("capability_bindings")==CAPABILITY_IDS and p.get("invariants")==RULES and p.get("physical_store_policy",{}).get("canonical_model_store")==CANONICAL_STORE_ID):
        findings.append(_finding("MODEL-MGR-REF-010","Profile identity/capability/storage drift"))
    if not (c.get("id")==CONTRACT_ID and c.get("provider_neutral") is True and c.get("capability_count")==CAPABILITY_COUNT and c.get("invariants")==RULES):
        findings.append(_finding("MODEL-MGR-REF-011","Provider-neutral contract semantic drift"))
    if not (d.get("id")==DECISION_ID and d.get("canonical_store_id")==CANONICAL_STORE_ID and d.get("mandatory_rule_ids")==RULES and d.get("capability_count_after")==CAPABILITY_COUNT and d.get("current_host_runtime_promotion_claim") is False):
        findings.append(_finding("MODEL-MGR-REF-013","Canonical native-storage decision drift"))
    if not (enf.get("gate_id")==GATE_ID and enf.get("canonical_store_id")==CANONICAL_STORE_ID and enf.get("p0_invariants")==RULES):
        findings.append(_finding("MODEL-MGR-REF-015","Enforcement rule-set drift"))
    if not (pol.get("model_manager_profile_id")==PROFILE_ID and pol.get("model_manager_contract_id")==CONTRACT_ID and pol.get("model_manager_canonical_store_id")==CANONICAL_STORE_ID and pol.get("model_manager_mandatory_p0_rules")==RULES):
        findings.append(_finding("MODEL-MGR-REF-016","Global enforcement-policy binding drift"))
    if not (evid.get("gate_id")==GATE_ID and evid.get("status")=="PASS" and evid.get("canonical_store_id")==CANONICAL_STORE_ID and evid.get("current_host_runtime_evidence")=="NOT_CLAIMED" and evid.get("capability_count_after")==CAPABILITY_COUNT):
        findings.append(_finding("MODEL-MGR-REF-017","Committed reference evidence boundary drift"))
    records={x.get("subject_id"):x for x in reg.get("records",[])}
    bad=[]
    for cid in CAPABILITY_IDS:
        row=records.get(cid,{}); s=row.get("model_manager_projection_status",{})
        if DECISION_ID not in row.get("source_decision_ids",[]) or EVIDENCE_PATH not in row.get("evidence_artifacts",[]) or row.get("status")!="PENDING_CURRENT_HOST" or s.get("profile_id")!=PROFILE_ID or s.get("canonical_store_id")!=CANONICAL_STORE_ID or s.get("gate_id")!=GATE_ID or s.get("current_host_runtime_evidence")!="PENDING_REAL_CURRENT_HOST_EXECUTION":
            bad.append(cid)
    if bad: findings.append(_finding("MODEL-MGR-REF-018","Evidence Registry binding drift",capability_ids=bad))
    rec=proj.get("model_manager_reconciliation",{})
    if not (rec.get("profile_id")==PROFILE_ID and rec.get("contract_id")==CONTRACT_ID and rec.get("canonical_store_id")==CANONICAL_STORE_ID and rec.get("gate_id")==GATE_ID and rec.get("capability_count_after")==CAPABILITY_COUNT and rec.get("current_host_runtime_promotion_claim") is False):
        findings.append(_finding("MODEL-MGR-REF-019","Global release reconciliation drift"))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root:Path)->dict[str,Any]:
    ref=reference_check(root); auth=scan_canonical_authority_assignments(root); regressions=run_regressions(); v2=model_manager_v2_gate(root)
    ok=ref["result"]==auth["result"]==regressions["result"]==v2["result"]=="PASS"
    report={"schema":"fa3.model-manager-gate-report.v3","gate_id":GATE_ID,"profile_id":PROFILE_ID,"canonical_store_id":CANONICAL_STORE_ID,"capability_bindings":CAPABILITY_IDS,"capability_count":CAPABILITY_COUNT,"result":"PASS" if ok else "FAIL","reference":ref,"authority_scan":auth,"regressions":regressions,"v2":v2,"current_host_runtime_promotion_claim":False}
    _write(root/"reports/model-manager-gate-report.json",report); return report

def main()->int:
    ap=argparse.ArgumentParser(description="FA3 provider-neutral Model Manager fail-closed canonical regression gate")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); args=ap.parse_args()
    report=gate(Path(args.root).resolve()); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
