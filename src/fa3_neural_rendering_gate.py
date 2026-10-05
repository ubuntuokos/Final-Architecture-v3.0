#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from fa3_release_baseline import load_active_release_baseline
from fa3_uaf import ActionRegistry

GATE_ID="FA3-NEURAL-RENDERING-GATESET-001"; PROFILE_ID="FA3-NEURAL-RENDERING-001"
CONTRACT_ID="FA3-NEURAL-RENDERING-CONTRACTS-001"; PROVIDER_ID="FA3-PROVIDER-OPENDLSS-NR-001"
DECISION_ID="FA3-DEC-NEURAL-RENDERING-OPENDLSS-NR-2026-09-23"; PIN="9d08f4184bbcb9d858e2fb7a7834ec0837a9d2f1"
ACTION_IDS={"render.neural.evaluate","render.neural.execute","render.neural.browser.execute"}

def _load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(f"object required: {path}")
    return value

def _finding(code:str,message:str,**details:Any)->dict[str,Any]: return {"code":code,"message":message,**details}

def validate(root:Path)->list[dict[str,Any]]:
    root=root.resolve(); findings=[]
    paths={
      "profile":root/"canonical/profiles/FA3-NEURAL-RENDERING-001.json",
      "contract":root/"canonical/contracts/FA3-NEURAL-RENDERING-CONTRACTS-001.json",
      "provider":root/"canonical/providers/FA3-PROVIDER-OPENDLSS-NR-001.json",
      "decision":root/"canonical/decisions/FA3-DEC-NEURAL-RENDERING-OPENDLSS-NR-2026-09-23.json",
      "gate":root/"canonical/FA3-GATE-NEURAL-RENDERING-001.json",
      "runtime":root/"canonical/FA3-NEURAL-RENDERING-RUNTIME-CONFORMANCE-001.json",
      "enforcement":root/"canonical/neural-rendering-enforcement.json",
      "lock":root/"canonical/FA3-UPSTREAM-LOCK-REGISTRY-001.json",
      "neural_media":root/"canonical/profiles/FA3-NEURAL-MEDIA-EXECUTION-001.json",
      "web_ai":root/"canonical/profiles/FA3-WEB-AI-001.json",
      "evidence_registry":root/"evidence/evidence-registry.json",
      "reference":root/"evidence/reference/neural-rendering-opendlss-nr-reference-2026-09-23.json",
      "upstream_reference":root/"canonical/references/FA3-OPENDLSS-NR-UPSTREAM-REFERENCE-2026-09-23.json",
      "jev_adapter":root/"src/fa3_neural_rendering_jev_adapter.py",
      "projection":root/"canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
      "adapter":root/"src/fa3_opendlss_nr_provider.py","decision_impl":root/"src/fa3_neural_rendering.py",
      "intent":root/"canonical/intents/FA3-NEURAL-RENDERING-APPLICATION-INTENT-001.json",
      "reuse_assessment":root/"canonical/assessments/FA3-NEURAL-RENDERING-REUSE-ASSESSMENT-001.json",
      "derived_patterns":root/"canonical/references/FA3-OPENDLSS-NR-DERIVED-PATTERNS-001.json"}
    for name,path in paths.items():
        if not path.is_file(): findings.append(_finding("NR-GATE-001","required file missing",name=name,path=path.as_posix()))
    if findings: return findings
    count=load_active_release_baseline(root).capability_count
    profile=_load(paths["profile"]); contract=_load(paths["contract"]); provider=_load(paths["provider"]); decision=_load(paths["decision"])
    gate_record=_load(paths["gate"]); runtime=_load(paths["runtime"]); enforcement=_load(paths["enforcement"]); lock=_load(paths["lock"])
    neural_media=_load(paths["neural_media"]); web_ai=_load(paths["web_ai"]); registry=_load(paths["evidence_registry"])
    reference=_load(paths["reference"]); projection=_load(paths["projection"])
    intent=_load(paths["intent"]); reuse_assessment=_load(paths["reuse_assessment"]); derived_patterns=_load(paths["derived_patterns"])
    checks=[
      (isinstance(count,int) and count>0,"NR-GATE-002","active capability baseline is invalid"),
      (profile.get("id")==PROFILE_ID and profile.get("provider_neutral") is True and profile.get("fail_closed") is True,"NR-GATE-003","profile identity/provider-neutral/fail-closed mismatch"),
      (profile.get("new_capability") is False and profile.get("new_architectural_authority") is False and profile.get("capability_count")==count,"NR-GATE-004","profile changes capability or authority baseline"),
      (contract.get("id")==CONTRACT_ID and contract.get("profile")==PROFILE_ID and contract.get("new_capability") is False and contract.get("new_architectural_authority") is False,"NR-GATE-005","contract identity/baseline mismatch"),
      (decision.get("id")==DECISION_ID and decision.get("new_capabilities")==0 and decision.get("new_architectural_authorities")==0 and isinstance(decision.get("capability_count_after"),int) and decision.get("capability_count_after")<=count,"NR-GATE-006","decision changes baseline"),
      (provider.get("id")==PROVIDER_ID and provider.get("architectural_authority") is False and provider.get("activation",{}).get("production_admitted") is False,"NR-GATE-007","provider authority/admission boundary invalid"),
      (provider.get("upstream",{}).get("commit")==PIN and provider.get("upstream",{}).get("license")=="MIT","NR-GATE-008","upstream immutable identity/license mismatch"),
      (provider.get("upstream",{}).get("commit_signature_verified") is False and provider.get("supply_chain",{}).get("production_attestation_or_review_required") is True,"NR-GATE-009","unsigned-upstream supply-chain boundary weakened"),
      (provider.get("model_artifact",{}).get("weights_bundled") is False and provider.get("model_artifact",{}).get("license_and_output_rights_admission_required") is True,"NR-GATE-010","model-data rights boundary invalid"),
      (provider.get("execution_classes",{}).get("HOST_NATIVE_VULKAN_PTX",{}).get("fa3_global_hardware_requirement") is False,"NR-GATE-011","provider-specific native requirements leaked into global hardware policy"),
      (contract.get("decision_fabric",{}).get("jev_role")=="OPTIONAL_ADVISORY_PROVIDER_NOT_AUTHORITY" and contract.get("decision_fabric",{}).get("candidate_expansion_forbidden") is True,"NR-GATE-012","Jev advisory boundary invalid"),
      (contract.get("agent_native",{}).get("fabric")=="FA3-UNIFIED-ACTION-FABRIC-001" and contract.get("agent_native",{}).get("direct_agent_provider_bypass_forbidden") is True,"NR-GATE-013","Agent Native/UAF boundary invalid"),
      (contract.get("execution_policy",{}).get("implicit_cpu_gpu_backend_provider_precision_or_cloud_fallback") is False,"NR-GATE-014","silent fallback prohibition missing"),
      (profile.get("authority",{}).get("host_resource_admission_placement_reservation_lease")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","NR-GATE-015","HRB authority not preserved"),
      (profile.get("authority",{}).get("geometry_semantics")=="FA3-3D-GEOM-001","NR-GATE-016","geometry authority not preserved"),
      (gate_record.get("gateset_id")==GATE_ID and gate_record.get("fail_closed") is True and gate_record.get("static_pass_promotes_provider_runtime") is False,"NR-GATE-017","gate record invalid"),
      (runtime.get("current_host_production_provider_admission") is False and runtime.get("static_or_hosted_reference_pass_is_provider_e2e") is False,"NR-GATE-018","current-host boundary weakened"),
      (reference.get("status")=="PASS" and reference.get("evidence_level")=="STATIC_REFERENCE_EXECUTABLE_PASS_NOT_PROVIDER_RUNTIME_E2E" and reference.get("current_host_provider_e2e_claim") is False and reference.get("github_actions",{}).get("executable_core_tests",{}).get("passed")>=10,"NR-GATE-019","reference evidence semantics invalid"),
      (_load(paths["upstream_reference"]).get("immutable_commit")==PIN and _load(paths["upstream_reference"]).get("commit_signature_verified") is False,"NR-GATE-019A","upstream reference identity/signature semantics invalid"),
      (neural_media.get("neural_rendering_projection",{}).get("profile_id")==PROFILE_ID and PROVIDER_ID in neural_media.get("reference_providers",[]),"NR-GATE-020","neural-media integration missing"),
      (web_ai.get("neural_rendering_projection",{}).get("provider_id")==PROVIDER_ID and web_ai.get("neural_rendering_projection",{}).get("authority") is False,"NR-GATE-021","Web-AI projection missing/authoritative"),
      (registry.get("neural_rendering_reconciliation",{}).get("provider_id")==PROVIDER_ID and registry.get("neural_rendering_reconciliation",{}).get("production_provider_admission") is False,"NR-GATE-022","Evidence Registry reconciliation missing or promoted"),
      (projection.get("neural_rendering_reconciliation",{}).get("provider_id")==PROVIDER_ID and projection.get("neural_rendering_reconciliation",{}).get("capability_count_after")==count,"NR-GATE-023","release projection reconciliation missing"),
      (enforcement.get("new_capabilities")==0 and enforcement.get("new_architectural_authorities")==0 and enforcement.get("capability_count")==count,"NR-GATE-024","enforcement baseline mismatch"),
      (intent.get("schema")=="fa3.application-intent.v1" and intent.get("project_id")==PROFILE_ID and intent.get("proposed_authority_roles")==[] and intent.get("declared_new_capabilities")==[],"NR-GATE-034","ApplicationIntent identity or baseline delta invalid"),
      (intent.get("hardware_audit",{}).get("vendor_neutral") is True and intent.get("hardware_audit",{}).get("cpu_only_viable") is True and intent.get("hardware_audit",{}).get("accelerator_cardinality")=="0..N" and intent.get("hardware_audit",{}).get("global_accelerator_requirement") is False,"NR-GATE-035","ApplicationIntent hardware audit invalid"),
      (intent.get("namespace_claims",{}).get("requires_upstream_uninstall") is False and intent.get("namespace_claims",{}).get("global_environment_mutation") is False and intent.get("namespace_claims",{}).get("claims_default_port") is False,"NR-GATE-036","ApplicationIntent coexistence namespace boundary invalid"),
      (reuse_assessment.get("schema")=="fa3.reuse-assessment.v1" and reuse_assessment.get("project_id")==PROFILE_ID and reuse_assessment.get("result")=="PASS" and PROFILE_ID in reuse_assessment.get("covered_ids",[]) and PROVIDER_ID in reuse_assessment.get("covered_ids",[]),"NR-GATE-037","ReuseAssessment missing profile/provider PASS coverage"),
      (reuse_assessment.get("coexistence",{}).get("result")=="PASS" and reuse_assessment.get("coexistence",{}).get("upstream_uninstall_required") is False and reuse_assessment.get("coexistence",{}).get("global_mutation") is False and reuse_assessment.get("coexistence",{}).get("default_port_hijack") is False,"NR-GATE-038","ReuseAssessment coexistence boundary invalid"),
      (reuse_assessment.get("hardware_audit",{}).get("vendor_neutral") is True and reuse_assessment.get("hardware_audit",{}).get("cpu_only_viable") is True and reuse_assessment.get("hardware_audit",{}).get("accelerator_cardinality")=="0..N" and reuse_assessment.get("current_host_runtime_promotion_claim") is False and reuse_assessment.get("global_promotion_claim") is False,"NR-GATE-039","ReuseAssessment hardware/promotion boundary invalid"),
      (reuse_assessment.get("new_capabilities")==0 and reuse_assessment.get("new_architectural_authorities")==0 and isinstance(reuse_assessment.get("capability_count_after"),int) and reuse_assessment.get("capability_count_after")<=count,"NR-GATE-040","ReuseAssessment changes capability or authority baseline"),
      (derived_patterns.get("authority") is False and derived_patterns.get("runtime_dependency_implied") is False and derived_patterns.get("current_host_claim") is False and len(derived_patterns.get("patterns",[]))>=5,"NR-GATE-041","OpenDLSS-NR derived-pattern reference boundary invalid")]
    for ok,code,message in checks:
        if not ok: findings.append(_finding(code,message))
    opendlss_lock=lock.get("locks",{}).get("opendlss_nr",{})
    if opendlss_lock.get("provider_id")!=PROVIDER_ID or opendlss_lock.get("revision")!=PIN or opendlss_lock.get("update_policy")!="CONTROLLED":
        findings.append(_finding("NR-GATE-025","upstream lock missing or drifted"))
    registry_actions=ActionRegistry.from_directory(root/"canonical/actions")
    actions={a.action_id:a for a in registry_actions.list() if a.action_id in ACTION_IDS}
    if set(actions)!=ACTION_IDS: findings.append(_finding("NR-GATE-026","UAF neural-rendering action inventory incomplete",missing=sorted(ACTION_IDS-set(actions))))
    for action_id,action in actions.items():
        if action.security.get("authentication")!="required" or action.security.get("authorization")!="required": findings.append(_finding("NR-GATE-027","action lacks authn/authz",action=action_id))
        if action.evidence.get("required") is not True or action.evidence.get("decision_receipt_required") is not True: findings.append(_finding("NR-GATE-028","action lacks evidence/decision receipt",action=action_id))
        if action.provider.get("selection")!="policy-bounded-capability-match": findings.append(_finding("NR-GATE-029","action provider selection not policy-bounded",action=action_id))
        if action.resources.get("accelerator",{}).get("cardinality")!="0..N": findings.append(_finding("NR-GATE-030","accelerator cardinality not portable",action=action_id))
    if actions.get("render.neural.execute") and actions["render.neural.execute"].resources.get("hrb_required") is not True: findings.append(_finding("NR-GATE-031","host execution action does not require HRB"))
    if actions.get("render.neural.browser.execute") and actions["render.neural.browser.execute"].resources.get("hrb_required") is not False: findings.append(_finding("NR-GATE-032","browser execution incorrectly claims host HRB lease"))
    policy_text=json.dumps({"profile_hardware":profile.get("hardware_policy"),"action_resources":{k:v.resources for k,v in actions.items()}},sort_keys=True).lower()
    for forbidden in ("nvidia","cuda","ada","windows","vk_nv_"):
        if forbidden in policy_text: findings.append(_finding("NR-GATE-033","provider-specific hardware leaked into global/action hardware policy",token=forbidden))
    return findings

def gate(root:Path)->dict[str,Any]:
    findings=validate(root)
    report={"schema_id":"FA3-ENFORCEMENT-RESULT-001","schema_version":"1.0.0","gate":{"id":GATE_ID,"mode":"STATIC_CANONICAL_AND_REFERENCE"},
            "result":"PASS" if not findings else "BLOCKED",
            "decision":{"reason_code":"NEURAL_RENDERING_STATIC_REFERENCE_PASS" if not findings else "NEURAL_RENDERING_BLOCKED",
                        "promotion_effect":"STATIC_REFERENCE_ONLY_PROVIDER_RUNTIME_ADMISSION_UNCHANGED","exit_code":0 if not findings else 2},
            "findings":findings,"action_count":len(ACTION_IDS),"capability_delta":0,"authority_delta":0,
            "current_host_provider_e2e_claim":False,"global_promotion_claim":False}
    out=root.resolve()/"reports/neural-rendering-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); return report

def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); args=parser.parse_args()
    report=gate(Path(args.root)); print(json.dumps(report,indent=2,ensure_ascii=False)); return int(report["decision"]["exit_code"])
if __name__=="__main__": raise SystemExit(main())
