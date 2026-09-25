#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fa3_release_baseline import module_active_capability_count

PROFILE_ID="FA3-AI-SECURITY-TESTING-FABRIC-001"
CONTRACT_ID="FA3-AI-SECURITY-TESTING-FABRIC-CONTRACTS-001"
GATE_ID="FA3-AI-SECURITY-TESTING-FABRIC-GATESET-001"
DECISION_ID="FA3-DEC-AI-SECURITY-TESTING-FABRIC-2026-09-25"
INTENT_ID="FA3-AI-SECURITY-TESTING-FABRIC-APPLICATION-INTENT-001"
ASSESSMENT_ID="FA3-AI-SECURITY-TESTING-FABRIC-REUSE-ASSESSMENT-001"
CAPABILITY_COUNT=module_active_capability_count(__file__)

LEGACY_PYRIT_PATHS=[
".github/workflows/fa3-pyrit-current-host.yml",
".github/workflows/pyrit-reference-gate.yml",
"canonical/FA3-GATE-PYRIT-001.json",
"canonical/FA3-PYRIT-RUNTIME-CONFORMANCE-001.json",
"canonical/decisions/FA3-DEC-PYRIT-2026-09-12.json",
"canonical/providers/FA3-PROVIDER-PYRIT-001.json",
"canonical/pyrit-enforcement.json",
"canonical/pyrit-runtime-admission.json",
"canonical/references/FA3-PYRIT-UPSTREAM-REFERENCE-2026-09-12.json",
"evidence/collect-pyrit-current-host.py",
"evidence/reference/pyrit-reference-pass.json",
"src/fa3_pyrit_gate.py",
"tests/test_pyrit_gate.py",
]
PATHS={
"profile":"canonical/profiles/FA3-AI-SECURITY-TESTING-FABRIC-001.json",
"parent":"canonical/profiles/FA3-AI-SEC-VALIDATION-001.json",
"contract":"canonical/contracts/FA3-AI-SECURITY-TESTING-FABRIC-CONTRACTS-001.json",
"decision":"canonical/decisions/FA3-DEC-AI-SECURITY-TESTING-FABRIC-2026-09-25.json",
"intent":"canonical/intents/FA3-AI-SECURITY-TESTING-FABRIC-APPLICATION-INTENT-001.json",
"assessment":"canonical/assessments/FA3-AI-SECURITY-TESTING-FABRIC-REUSE-ASSESSMENT-001.json",
"sources":"canonical/references/FA3-AI-SECURITY-TESTING-SOURCES-2026-09-25.json",
"enforcement":"canonical/ai-security-testing-fabric-enforcement.json",
"evidence":"evidence/reference/ai-security-testing-fabric-reference-pass.json",
"policy":"canonical/enforcement-policy.json",
"distribution_registry":"canonical/distribution-registry.json",
"distribution_manifest":"canonical/distribution-manifest.json",
}
def loadj(p:Path)->dict[str,Any]:
    return json.loads(p.read_text(encoding="utf-8"))
def finding(code:str,message:str,**details:Any)->dict[str,Any]:
    return {"code":code,"severity":"P0","message":message,**details}
def gate(root:Path)->dict[str,Any]:
    root=Path(root).resolve()
    fs=[]
    for name,rel in PATHS.items():
        if not (root/rel).is_file():
            fs.append(finding("AISEC-FABRIC-001","Missing required Fabric artifact",name=name,path=rel))
    for rel in LEGACY_PYRIT_PATHS:
        if (root/rel).exists():
            fs.append(finding("AISEC-FABRIC-002","Legacy PyRIT integration artifact must be absent",path=rel))
    if fs:
        return _finish(root,fs)
    p=loadj(root/PATHS["profile"]); parent=loadj(root/PATHS["parent"])
    c=loadj(root/PATHS["contract"]); d=loadj(root/PATHS["decision"])
    i=loadj(root/PATHS["intent"]); a=loadj(root/PATHS["assessment"])
    s=loadj(root/PATHS["sources"]); e=loadj(root/PATHS["enforcement"]); ev=loadj(root/PATHS["evidence"])
    policy=loadj(root/PATHS["policy"]); distreg=loadj(root/PATHS["distribution_registry"]); distman=loadj(root/PATHS["distribution_manifest"])
    if not (p.get("id")==PROFILE_ID and p.get("parent_profile")=="FA3-AI-SEC-VALIDATION-001" and p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==CAPABILITY_COUNT):
        fs.append(finding("AISEC-FABRIC-003","Fabric profile boundary drift"))
    if "FA3-PROVIDER-PYRIT-001" in json.dumps(parent):
        fs.append(finding("AISEC-FABRIC-004","Parent AI security profile still references legacy PyRIT provider identity"))
    hw=i.get("hardware_audit",{}); ns=i.get("namespace_claims",{})
    if not (i.get("id")==INTENT_ID and i.get("proposed_authority_roles")==[] and i.get("declared_new_capabilities")==[] and hw.get("vendor_neutral") is True and hw.get("cpu_only_viable") is True and hw.get("accelerator_cardinality")=="0..N" and hw.get("global_accelerator_requirement") is False):
        fs.append(finding("AISEC-FABRIC-005","Hardware Audit boundary drift"))
    if not (ns.get("requires_upstream_uninstall") is False and ns.get("global_environment_mutation") is False and ns.get("claims_default_port") is False):
        fs.append(finding("AISEC-FABRIC-006","Software coexistence/host non-interference drift"))
    if not (a.get("id")==ASSESSMENT_ID and a.get("result")=="PASS" and a.get("coexistence",{}).get("result")=="PASS" and a.get("current_host_runtime_promotion_claim") is False and a.get("global_promotion_claim") is False):
        fs.append(finding("AISEC-FABRIC-007","Reuse assessment drift"))
    if not (c.get("id")==CONTRACT_ID and c.get("provider_neutral") is True and c.get("new_architectural_authority") is False and c.get("capability_count")==CAPABILITY_COUNT and "UNDETERMINED_NEVER_COUNTS_AS_PASS" in c.get("invariants",[])):
        fs.append(finding("AISEC-FABRIC-008","Contract boundary drift"))
    if not (d.get("id")==DECISION_ID and d.get("status")=="CANONICAL_CLOSED" and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0 and d.get("history_policy")=="LEGACY_PYRIT_INTEGRATION_FILES_ARE_DELETED_NOT_ARCHIVED_IN_REPOSITORY"):
        fs.append(finding("AISEC-FABRIC-009","Canonical decision drift"))
    by_name={x.get("name"):x for x in s.get("sources",[])}
    if not (by_name.get("PyRIT",{}).get("role")=="ADVERSARIAL_ENGINE_CANDIDATE" and by_name.get("PyRIT",{}).get("runtime_status")=="PENDING_FABRIC_ENGINE_ADMISSION"):
        fs.append(finding("AISEC-FABRIC-010","PyRIT must remain an engine candidate, not a provider authority"))
    if by_name.get("garak",{}).get("runtime_status")!="REUSE_EXISTING_FA3_GARAK_RUNTIME_NO_DUPLICATE_INSTALL":
        fs.append(finding("AISEC-FABRIC-011","Existing garak runtime reuse invariant drift"))
    refs={"Inspect AI","AgentDojo","Agent Scan","Promptfoo","DeepTeam"}
    if any(by_name.get(x,{}).get("runtime_status")!="REFERENCE_ONLY" for x in refs):
        fs.append(finding("AISEC-FABRIC-012","Pattern sources must remain reference-only until separate admission"))
    if not (e.get("gate_id")==GATE_ID and e.get("fail_closed") is True and "LEGACY_PYRIT_INTEGRATION_ARTIFACTS_ABSENT" in e.get("mandatory_rules",[])):
        fs.append(finding("AISEC-FABRIC-013","Enforcement record drift"))
    if not (ev.get("status")=="PASS" and ev.get("current_host_runtime_evidence") is False and ev.get("production_runtime_promoted") is False):
        fs.append(finding("AISEC-FABRIC-014","Reference evidence scope drift"))
    if not (
        GATE_ID in policy.get("mandatory_reference_gates",[])
        and policy.get("ai_security_testing_fabric_profile_id")==PROFILE_ID
        and policy.get("ai_security_testing_fabric_contract_id")==CONTRACT_ID
        and policy.get("ai_security_testing_fabric_gate_id")==GATE_ID
        and policy.get("ai_security_testing_fabric_mandatory_p0_rules")==e.get("mandatory_rules",[])
        and policy.get("legacy_pyrit_integration_files_allowed") is False
    ):
        fs.append(finding("AISEC-FABRIC-016","Global enforcement policy binding drift"))
    source_id="FA3-AI-SECURITY-TESTING-SOURCES-2026-09-25"
    distrows={x.get("subject_id"):x for x in distreg.get("records",[]) if isinstance(x,dict)}
    excluded={x.get("subject_id"):x for x in distman.get("excluded",[]) if isinstance(x,dict)}
    if not (
        distrows.get(source_id,{}).get("class")=="REFERENCE_ONLY"
        and distrows.get(source_id,{}).get("release_bundle_status")=="EXCLUDED"
        and excluded.get(source_id,{}).get("class")=="REFERENCE_ONLY"
        and excluded.get(source_id,{}).get("release_bundle_status")=="EXCLUDED"
    ):
        fs.append(finding("AISEC-FABRIC-017","Security testing source-set distribution classification drift"))
    legacy_ids=("FA3-PROVIDER-PYRIT-001","FA3-PYRIT-RUNTIME-ADMISSION-001","FA3-PYRIT-RUNTIME-CONFORMANCE-001","FA3-PYRIT-GATESET-001")
    for path in (root/"canonical").rglob("*.json"):
        if path in [root/PATHS["decision"]]:
            continue
        txt=path.read_text(encoding="utf-8")
        for legacy_id in legacy_ids:
            if legacy_id in txt:
                fs.append(finding("AISEC-FABRIC-015","Legacy PyRIT canonical identifier remains referenced",path=str(path.relative_to(root)),legacy_id=legacy_id))
    return _finish(root,fs)
def _finish(root:Path,fs:list[dict[str,Any]])->dict[str,Any]:
    report={"schema":"fa3.ai-security-testing-fabric-gate-report.v1","gate_set_id":GATE_ID,
    "profile_id":PROFILE_ID,"result":"PASS" if not fs else "FAIL","blocking_findings":len(fs),
    "findings":fs,"current_host_runtime_promotion_claim":False,"global_promotion_claim":False,
    "new_capabilities":0,"new_architectural_authorities":0,"capability_count_after":CAPABILITY_COUNT}
    out=root/"reports/ai-security-testing-fabric-gate-report.json"
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report
if __name__=="__main__":
    result=gate(Path(__file__).resolve().parents[1])
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result["result"]=="PASS" else 2)
