#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from fa3_release_baseline import load_active_release_baseline
from fa3_modernization_integration import ai_quality_evaluator_valid,cross_host_execution_valid,degraded_execution_valid,finops_projection_valid,inference_execution_valid,knowledge_accelerator_valid,runtime_enforcement_valid,structured_knowledge_metadata_valid,usage_rights_valid

GATE_ID="FA3-MODERNIZATION-INTEGRATION-GATESET-001"
PATHS={"contract":"canonical/contracts/FA3-MODERNIZATION-INTEGRATION-CONTRACTS-001.json","decision":"canonical/decisions/FA3-DEC-MODERNIZATION-INTEGRATION-2026-09-25.json","reference":"canonical/references/FA3-MODERNIZATION-PROVIDER-CANDIDATES-2026-09-25.json","intent":"canonical/intents/FA3-MODERNIZATION-INTEGRATION-APPLICATION-INTENT-001.json","assessment":"canonical/assessments/FA3-MODERNIZATION-INTEGRATION-REUSE-ASSESSMENT-001.json","enforcement":"canonical/modernization-integration-enforcement.json","gate":"canonical/FA3-GATE-MODERNIZATION-INTEGRATION-001.json","policy":"canonical/enforcement-policy.json"}

def _load(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def _finding(code:str,message:str,**extra:Any)->dict[str,Any]: return {"code":code,"severity":"P0","message":message,**extra}

def regressions()->list[dict[str,Any]]:
    cases=[]
    def add(name,positive,negative_refusal): cases.append({"name":name,"positive":bool(positive),"negative_refusal":bool(negative_refusal),"result":"PASS" if positive and negative_refusal else "FAIL"})
    inf={"model_router_authority":"FA3-AUTH-MODEL-ROUTER-001","resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001","provider_runtime_profile":"FA3-PROVIDER-RUNTIME-001","supply_chain_admitted":True,"silent_fallback":False,"canonical_route_contains_physical_model_id":False,"accelerator_requested":True,"hrb_lease_id":"lease-test"}
    add("inference-router-hrb-boundary",inference_execution_valid(inf),not inference_execution_valid({**inf,"silent_fallback":True}))
    run={"security_authority":"FA3-AUTH-SECURITY-GOV-001","provider_is_authority":False,"direct_unscoped_host_mutation":False,"phase":"ENFORCE","policy_authorized":True,"operation_prevention_proven":True,"policy_receipt":"policy-receipt-test"}
    add("runtime-enforcement-authority-and-block-proof",runtime_enforcement_valid(run),not runtime_enforcement_valid({**run,"operation_prevention_proven":False}))
    rights={"rights_asset_id":"rights-test","subject_ref":"subject-test","asset_type":"VOICE","issuer":"issuer-test","valid_from":"2026-01-01T00:00:00Z","valid_until":"2027-01-01T00:00:00Z","allowed_purposes":["creative"],"forbidden_purposes":["fraud"],"source_asset_hashes":["sha256:test"],"signature":"detached-signature-test","signature_key_id":"key-test","evidence_refs":["evidence-test"],"signature_verified":True,"issuer_trusted":True,"revocation_checked":True,"revoked":False}
    now=datetime(2026,9,25,tzinfo=timezone.utc)
    add("usage-rights-fail-closed",usage_rights_valid(rights,requested_purpose="creative",now=now),not usage_rights_valid({**rights,"revoked":True},requested_purpose="creative",now=now))
    know={"knowledge_authority":"FA3-KNOWLEDGE-001","provider_is_authority":False,"derived_rebuildable":True,"native_source_preserved":True,"embedding_model_self_selected":False,"direct_application_bypass":False}
    add("knowledge-accelerator-derived-only",knowledge_accelerator_valid(know),not knowledge_accelerator_valid({**know,"provider_is_authority":True}))
    fin={"hrb_financial_authority":False,"derived_projection":True,"authoritative_promotion_evidence":False,"tariff_source":"operator-config","exchange_rate_source":"versioned-rate-input","amortization_policy_source":"operator-policy","usage_receipt_ref":"hrb-receipt-test"}
    add("finops-derived-not-authority",finops_projection_valid(fin),not finops_projection_valid({**fin,"tariff_source":"HARDCODED"}))
    judge={"advisory_only":True,"model_router_authority":"FA3-AUTH-MODEL-ROUTER-001","single_score_truth_authority":False,"evaluation_trace_ref":"eval-trace-test"}
    add("ai-quality-advisory-only",ai_quality_evaluator_valid(judge),not ai_quality_evaluator_valid({**judge,"single_score_truth_authority":True}))
    cross={"coordination_profile":"FA3-AGENT-FEDERATION-001","federation_is_resource_authority":False,"remote_resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001","remote_provider_runtime_admitted":True,"remote_hrb_receipt":"remote-hrb-test","authenticated_transport":True,"signed_envelope":True,"hop_bounded":True,"production_cross_host_claim":True,"distinct_host_identities_proven":True,"cross_host_transport_proven":True,"local_multi_node_only":False}
    add("cross-host-federation-remote-hrb-boundary",cross_host_execution_valid(cross),not cross_host_execution_valid({**cross,"remote_resource_authority":"FA3-AGENT-FEDERATION-001"}))
    meta={"knowledge_authority":"FA3-KNOWLEDGE-001","metadata_is_derived_projection":True,"native_source_preserved":True,"domain_extension_replaces_core":False,"schema_version":"1","document_id":"doc-test","content_type":"NOTE","source_type":"NATIVE_FILE","created_at":"2026-09-25T00:00:00Z","provenance":{"source":"test"},"language":"hu-HU","approval_state":"APPROVED","evidence_refs":["evidence-test"],"ai_generated":False,"human_modified":True}
    add("structured-knowledge-metadata-native-source",structured_knowledge_metadata_valid(meta),not structured_knowledge_metadata_valid({**meta,"native_source_preserved":False}))
    degraded={"silent_fallback":False,"explicit_reroute_policy":True,"new_resource_admission":True,"original_route_evidence":"route-failure-test","reroute_receipt":"reroute-test","execution_receipt":"execution-test"}
    add("degraded-execution-explicit-reroute",degraded_execution_valid(degraded),not degraded_execution_valid({**degraded,"silent_fallback":True}))
    return cases

def gate(root:Path)->dict[str,Any]:
    root=root.resolve(); capability_count=load_active_release_baseline(root).capability_count; findings=[]; data={}
    for key,rel in PATHS.items():
        try: data[key]=_load(root/rel)
        except Exception as exc: findings.append(_finding("MODERN-000","Required modernization materialization unreadable",path=rel,error=repr(exc)))
    if not findings:
        contract=data["contract"]; decision=data["decision"]; reference=data["reference"]; intent=data["intent"]; assessment=data["assessment"]; enforcement=data["enforcement"]; gate_record=data["gate"]; policy=data["policy"]
        if not (contract.get("id")=="FA3-MODERNIZATION-INTEGRATION-CONTRACTS-001" and contract.get("provider_neutral") is True and contract.get("new_capability") is False and contract.get("new_architectural_authority") is False and contract.get("capability_count")==capability_count): findings.append(_finding("MODERN-001","Modernization contract authority/capability invariant drift"))
        expected={"model_routing":"FA3-AUTH-MODEL-ROUTER-001","host_resources":"FA3-AUTH-HOST-RESOURCE-BROKER-001","knowledge":"FA3-KNOWLEDGE-001","security":"FA3-AUTH-SECURITY-GOV-001","actions":"FA3-UNIFIED-ACTION-FABRIC-001","evidence":"FA3-AUTH-OBS-EVIDENCE-001","provider_runtime":"FA3-PROVIDER-RUNTIME-001"}
        if contract.get("authority_bindings",{})!=expected: findings.append(_finding("MODERN-002","Existing authority bindings changed or duplicated"))
        cross_contract=contract.get("contracts",{}).get("cross_host_execution",{})
        if not (cross_contract.get("coordination_profile")=="FA3-AGENT-FEDERATION-001" and cross_contract.get("federation_is_resource_authority") is False and cross_contract.get("remote_resource_admission_authority")=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and cross_contract.get("local_multi_node_protocol_pass_is_not_cross_host_production_pass") is True): findings.append(_finding("MODERN-017","Cross-host execution no longer reuses Agent Federation plus remote HRB"))
        meta_contract=contract.get("contracts",{}).get("structured_knowledge_metadata",{})
        if not (meta_contract.get("authority")=="FA3-KNOWLEDGE-001" and meta_contract.get("metadata_is_derived_projection") is True and meta_contract.get("native_source_preservation_required") is True): findings.append(_finding("MODERN-018","Structured knowledge metadata escaped Knowledge/native-source boundary"))
        degraded_contract=contract.get("contracts",{}).get("degraded_execution",{})
        if not (degraded_contract.get("silent_fallback_forbidden") is True and degraded_contract.get("explicit_reroute_receipt_required") is True and degraded_contract.get("reroute_requires_new_resource_admission") is True): findings.append(_finding("MODERN-019","Degraded execution reroute no longer fail-closed and explicit"))
        hw=intent.get("hardware_audit",{})
        if not (intent.get("project_type")=="MATERIAL_EXTENSION" and intent.get("proposed_authority_roles")==[] and intent.get("declared_new_capabilities")==[] and hw.get("vendor_neutral") is True and hw.get("cpu_only_viable") is True and hw.get("accelerator_cardinality")=="0..N" and hw.get("global_accelerator_requirement") is False): findings.append(_finding("MODERN-003","ApplicationIntent violates mandatory Hardware Audit boundary"))
        ns=intent.get("namespace_claims",{})
        if not (ns.get("requires_upstream_uninstall") is False and ns.get("global_environment_mutation") is False and ns.get("claims_default_port") is False): findings.append(_finding("MODERN-004","Software coexistence/host non-interference invariant drift"))
        if not (assessment.get("result")=="PASS" and assessment.get("intent_id")==intent.get("id") and assessment.get("hardware_audit",{}).get("cpu_only_viable") is True and assessment.get("hardware_audit",{}).get("accelerator_cardinality")=="0..N" and assessment.get("coexistence",{}).get("result")=="PASS" and assessment.get("current_host_runtime_promotion_claim") is False and assessment.get("global_promotion_claim") is False): findings.append(_finding("MODERN-005","Reuse assessment is not fail-closed PASS with hardware/coexistence boundaries"))
        req={"NEW_UNIFIED_EXECUTION_ENGINE_AUTHORITY","NEW_DISTRIBUTED_HRB_AUTHORITY","NEW_SEMANTIC_ROUTER_AUTHORITY","NEW_HRB_FINANCIAL_AUTHORITY","MODEL_PROVIDER_DEVICE_OR_CLOUD_SILENT_FALLBACK","DOCUMENT_DERIVED_CURRENT_HOST_PASS"}
        if not req.issubset(set(decision.get("rejected",[]))): findings.append(_finding("MODERN-006","Decision no longer rejects known authority/fallback anti-patterns"))
        if not (decision.get("baseline",{}).get("capability_count_after")==capability_count and decision.get("baseline",{}).get("new_architectural_authorities")==0 and decision.get("closure_semantics",{}).get("current_host_surfaces")=="PENDING_CURRENT_HOST" and decision.get("closure_semantics",{}).get("global_promotion_claim") is False): findings.append(_finding("MODERN-007","Decision overclaims closure or changes authority/capability baseline"))
        candidates=reference.get("candidates",[]); seen={str(c.get("candidate_id")) for c in candidates}
        if seen!={"VLLM","STABLEHLO","TVM","TETRAGON","LANCEDB"}: findings.append(_finding("MODERN-008","Provider candidate reference set drift",seen=sorted(seen)))
        for c in candidates:
            commit=str(c.get("immutable_reference_commit",""))
            if c.get("admission_status")!="NOT_ADMITTED_REFERENCE_ONLY" or c.get("supply_chain_admission_required") is not True or c.get("current_host_e2e_required") is not True or len(commit)!=40 or any(ch not in "0123456789abcdef" for ch in commit.lower()): findings.append(_finding("MODERN-009","Reference candidate illegally implies admission or lacks immutable identity",candidate=c.get("candidate_id")))
        if not (enforcement.get("gate_id")==GATE_ID and enforcement.get("fail_closed") is True and enforcement.get("capability_count")==capability_count and enforcement.get("authority_delta")==0 and enforcement.get("mandatory_rule_count")==len(enforcement.get("p0_invariants",[])) and enforcement.get("current_host_promotion_claim") is False and enforcement.get("global_promotion_claim") is False): findings.append(_finding("MODERN-010","Enforcement record invariant drift"))
        if not (gate_record.get("gateset_id")==GATE_ID and gate_record.get("fail_closed") is True and gate_record.get("capability_count")==capability_count and gate_record.get("new_capability") is False and gate_record.get("new_architectural_authority") is False and gate_record.get("current_host_promotion_claim") is False and gate_record.get("global_promotion_claim") is False): findings.append(_finding("MODERN-011","Executable gate record invariant drift"))
        if GATE_ID not in policy.get("mandatory_reference_gates",[]): findings.append(_finding("MODERN-012","Modernization gate is not bound into permanent enforcement policy"))
        if policy.get("modernization_integration_gate_id")!=GATE_ID: findings.append(_finding("MODERN-013","Permanent policy missing modernization gate identity"))
        if policy.get("modernization_integration_contract_id")!=contract.get("id"): findings.append(_finding("MODERN-014","Permanent policy missing modernization contract identity"))
        if policy.get("modernization_integration_mandatory_p0_rules")!=enforcement.get("p0_invariants"): findings.append(_finding("MODERN-015","Permanent policy modernization P0 rule set drift"))
    rows=regressions()
    if any(row["result"]!="PASS" for row in rows): findings.append(_finding("MODERN-016","Executable modernization boundary regression failed"))
    return {"schema":"fa3.modernization-integration-gate-report.v1","gate_id":GATE_ID,"result":"PASS" if not findings else "FAIL","status":"STATIC_MATERIALIZED_CURRENT_HOST_PENDING" if not findings else "BLOCKED","capability_count":capability_count,"new_capabilities":0,"new_architectural_authorities":0,"current_host_promotion_claim":False,"global_promotion_claim":False,"regressions":rows,"findings":findings}

def main()->int:
    p=argparse.ArgumentParser(description="FA3 modernization integration canonical gate"); p.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=p.parse_args(); root=Path(a.root).resolve(); report=gate(root)
    out=root/"reports/modernization-integration-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(report,ensure_ascii=False,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
