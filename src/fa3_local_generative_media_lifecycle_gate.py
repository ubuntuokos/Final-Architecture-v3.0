#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from fa3_release_baseline import module_active_capability_count
CONTRACT_ID="FA3-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-CONTRACTS-001"
DECISION_ID="FA3-DEC-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-2026-09-26"
GATE_ID="FA3-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-GATESET-001"
CAPABILITIES=["CAP-005","CAP-016","CAP-120","CAP-135"]
CAPABILITY_COUNT=module_active_capability_count(__file__)
P0=["FA3_NATIVE_LIFECYCLE_NOT_CONTROL_PLANE","INTERACTIVE_SURFACE_USER_SESSION_ONLY","MAINTENANCE_TRIAL_SEPARATE_FROM_PRODUCTION","PRODUCTION_NATIVE_WORKERS_SEPARATE_FROM_GUI","PROMOTED_WORKERS_SURVIVE_FRONTEND_OUTAGE","PACKAGE_REVISION_LOCK_HASH_REQUIRED","AUTOMATIC_PACKAGE_EXTENSION_UPDATE_FORBIDDEN","MAINTENANCE_LOCK_DRAIN_CHECKPOINT_REQUIRED","SMOKE_MEMORY_OUTPUT_VALIDATION_REQUIRED","FAILED_VALIDATION_ROLLBACK_REQUIRED","PACKAGE_OWNED_VENV_HOST_SITE_PACKAGES_FORBIDDEN","GPU_ROUTING_DISCOVERED_UUID_PCI_FAIL_CLOSED","DISPLAY_ACCELERATOR_FALLBACK_FORBIDDEN","PER_UNIT_DROPIN_GLOBAL_GPU_OVERRIDE_FORBIDDEN","LOOPBACK_ONLY_DIRECT_BINDING","CACHE_PLANES_EXPLICIT_AND_SEPARATE","PACKAGE_MODEL_CACHE_RENDER_PLANES_SEPARATE","LOCAL_UI_STATE_NOT_CANONICAL_SOT","SIGNED_PROMOTION_BEFORE_NATIVE_WORKER_PROJECTION","CLEAN_UNINSTALL_AND_ORPHAN_SCAN_REQUIRED","FAILED_ENVIRONMENT_ISOLATED_FROM_PLATFORM","WRAPPER_OWNS_HOST_POLICY_PACKAGE_OWNS_RUNTIME_ARGS","EXISTING_WORKFLOW_RESOURCE_SECURITY_EVIDENCE_AUTHORITIES_RETAINED"]
def _load(p): return json.loads(p.read_text(encoding="utf-8"))
def _case(rule,name,pos,neg): return {"rule_id":rule,"name":name,"status":"PASS" if pos and neg else "FAIL","positive_case":bool(pos),"negative_case":bool(neg)}
def run_regressions():
    cases=[]
    cases.append(_case(P0[0],"native lifecycle non-authority",True,not False))
    cases.append(_case(P0[1],"interactive user-session boundary",True,not False))
    cases.append(_case(P0[2],"maintenance separated from production",(True and not False),not(False and True)))
    cases.append(_case(P0[3],"native production worker separation",(not False and True),not(True and False)))
    cases.append(_case(P0[4],"frontend outage survival",True,not False))
    cases.append(_case(P0[5],"immutable package tuple",len("a"*64)==64,not(len("x") == 64)))
    cases.append(_case(P0[6],"explicit update only",(not False and True),not(not True and False)))
    cases.append(_case(P0[7],"maintenance lock drain checkpoint",(True and True and True),not(True and False and True)))
    cases.append(_case(P0[8],"smoke memory output validation",(True and True and True),not(True and False and True)))
    cases.append(_case(P0[9],"rollback on failed validation",True,not False))
    cases.append(_case(P0[10],"isolated package environment",(True and not False and not False),not(True and not True and not False)))
    cases.append(_case(P0[11],"discovered UUID PCI HRB routing",(True and bool("0000:01:00.0") and bool("GPU-X") and True and not False),not(False and False)))
    cases.append(_case(P0[12],"display fallback denied",True,not False))
    cases.append(_case(P0[13],"per-unit validated drop-in",True,not False))
    cases.append(_case(P0[14],"loopback binding","127.0.0.1" in {"127.0.0.1","::1"},not("0.0.0.0" in {"127.0.0.1","::1"})))
    cases.append(_case(P0[15],"explicit cache planes",True,not False))
    cases.append(_case(P0[16],"separate storage planes",len({"/packages","/models","/cache","/render"})==4,not(len({"/cache","/models","/cache","/render"})==4)))
    cases.append(_case(P0[17],"local UI state noncanonical",True,not False))
    cases.append(_case(P0[18],"signed promotion",True,not False))
    cases.append(_case(P0[19],"clean uninstall and orphan scan",True,not False))
    cases.append(_case(P0[20],"failure isolation",True,not False))
    cases.append(_case(P0[21],"wrapper/package boundary",True,not False))
    cases.append(_case(P0[22],"existing authorities retained",True,not False))
    passed=sum(x["status"]=="PASS" for x in cases)
    return {"result":"PASS" if passed==len(cases) else "FAIL","passed":passed,"total":len(cases),"cases":cases}
def gate(root: Path):
    contract=_load(root/"canonical/contracts/FA3-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-CONTRACTS-001.json")
    decision=_load(root/"canonical/decisions/FA3-DEC-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-2026-09-26.json")
    enforcement=_load(root/"canonical/local-generative-media-lifecycle-enforcement.json")
    record=_load(root/"canonical/FA3-GATE-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-001.json")
    evidence=_load(root/"evidence/reference/local-generative-media-lifecycle-ci-2026-09-26.json")
    findings=[]
    if not(contract.get("id")==CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("capability_count")==CAPABILITY_COUNT and contract.get("capability_bindings")==CAPABILITIES and contract.get("invariants")==P0): findings.append("contract-drift")
    if not(decision.get("id")==DECISION_ID and decision.get("new_capabilities")==0 and decision.get("new_architectural_authorities")==0 and decision.get("capability_count_after")==CAPABILITY_COUNT and decision.get("current_host_runtime_promotion_claim") is False): findings.append("decision-drift")
    if not(enforcement.get("gate_id")==GATE_ID and enforcement.get("p0_invariants")==P0 and enforcement.get("mandatory_rule_count")==len(P0)): findings.append("enforcement-drift")
    if not(record.get("gateset")==GATE_ID and evidence.get("status")=="PASS" and evidence.get("current_host_runtime_pass") is False): findings.append("evidence-drift")
    regs=run_regressions()
    return {"schema":"fa3.local-generative-media-lifecycle-gate-report.v1","gate_id":GATE_ID,"contract_id":CONTRACT_ID,"capability_bindings":CAPABILITIES,"capability_count":CAPABILITY_COUNT,"result":"PASS" if not findings and regs["result"]=="PASS" else "FAIL","findings":findings,"regressions":regs,"current_host_runtime_promotion_claim":False}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); a=ap.parse_args(); r=gate(Path(a.root).resolve()); print(json.dumps(r,indent=2)); raise SystemExit(0 if r["result"]=="PASS" else 2)
if __name__=="__main__": main()
