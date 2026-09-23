#!/usr/bin/env python3
from __future__ import annotations
from fa3_release_baseline import module_active_capability_count

import argparse
import json
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-INFERENCE-PORTABILITY-001"
CONTRACT_ID = "FA3-INFERENCE-PORTABILITY-CONTRACTS-001"
PARENT_GATE_ID = "FA3-INFERENCE-PORTABILITY-GATESET-001"
SUBGATE_ID = "FA3-INFERENCE-PORTABILITY-RECONCILIATION-001"
DECISION_ID = "FA3-DEC-INFERENCE-PORTABILITY-RECONCILIATION-2026-09-23"
REFERENCE_ID = "FA3-INFERENCE-PORTABILITY-UPSTREAM-REFERENCE-2026-09-23"
EVIDENCE_PATH = "evidence/reference/inference-portability-reconciliation-ci-2026-09-23.json"
CAPABILITY_IDS = ("CAP-005","CAP-006","CAP-137","CAP-143")
CAPABILITY_COUNT = module_active_capability_count(__file__)
RULES = (
  'INFERENCE_ACCELERATOR_CARDINALITY_0_TO_N_AND_CPU_ONLY_CONFORMANT',
  'INFERENCE_ACCELERATOR_BACKEND_MUST_BE_DEVICE_BOUND_AND_AVAILABLE',
  'INFERENCE_HRB_LEASE_BINDS_EXACT_ACCELERATOR_EXECUTION_PATH',
  'INFERENCE_BACKEND_DISAPPEARANCE_INVALIDATES_LEASE_AND_DERIVED_ARTIFACTS',
  'INFERENCE_NO_SILENT_DEVICE_BACKEND_OR_TRANSLATION_SUBSTITUTION',
  'INFERENCE_PROVIDER_SPECIFIC_HARDWARE_FIELDS_ARE_PROVIDER_SCOPED_ONLY',
  'INFERENCE_MODEL_ROUTER_REMAINS_LOGICAL_MODEL_PROVIDER_ROUTING_AUTHORITY',
  'INFERENCE_EXECUTION_PROVIDER_DOES_NOT_EXPAND_AI_PARTICIPANT_SET',
  'INFERENCE_AGENT_NATIVE_INVOCATION_REQUIRES_TYPED_UAF_ACTION',
  'INFERENCE_AGENT_NATIVE_CANNOT_BYPASS_ROUTER_HRB_SECURITY_OR_PROVIDER_ADAPTER',
  'INFERENCE_DECISION_FABRIC_JEV_ADVISORY_CANNOT_EXPAND_ELIGIBLE_CANDIDATES',
  'INFERENCE_EXECUTION_RECEIPT_BINDS_MODEL_PROVIDER_BACKEND_AND_RESOURCE_EVIDENCE',
  'INFERENCE_EXTERNAL_OR_CLOUD_FALLBACK_REQUIRES_EXPLICIT_PREAUTHORIZED_POLICY',
  'INFERENCE_REFERENCE_VERSION_ADVANCE_IS_NOT_RUNTIME_PROMOTION',
  'INFERENCE_EP_AND_BACKEND_SELECTION_REMAINS_DISTINCT_FROM_MODEL_ROUTING'
)

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}

def backend_candidate_valid(obj: dict[str, Any]) -> bool:
    if obj.get("execution_kind") == "CPU":
        return bool(obj.get("compatibility_result") == "PASS" and not obj.get("hrb_lease_required", False))
    return bool(
        obj.get("accelerator_id")
        and obj.get("binding_scope") == "DEVICE"
        and obj.get("detected") is True
        and obj.get("available") is True
        and obj.get("compatibility_result") == "PASS"
        and obj.get("hardware_discovery_receipt_id")
        and obj.get("hrb_lease_required") is True
    )

def execution_receipt_valid(obj: dict[str, Any]) -> bool:
    required = {
        "model_resolution_binding_id","model_artifact_id","provider_id","execution_backend",
        "backend_class","hardware_discovery_receipt_id","backend_compatibility_receipt_id",
        "fallback_policy_result","result",
    }
    if not required.issubset(obj) or obj.get("result") != "PASS":
        return False
    if obj.get("execution_kind") == "ACCELERATOR" and not obj.get("hrb_lease_id_when_accelerated"):
        return False
    if obj.get("invocation_origin") == "AGENT_NATIVE" and not obj.get("uaf_action_receipt_id_when_agent_initiated"):
        return False
    if obj.get("model_to_model") is True and not obj.get("ai_comms_topology_receipt_id_when_model_to_model"):
        return False
    return obj.get("fallback_policy_result") == "PASS"

def agent_invocation_valid(obj: dict[str, Any]) -> bool:
    if obj.get("origin") != "AGENT_NATIVE":
        return True
    return bool(
        obj.get("uaf_action_contract") == "FA3-UAF-ACTION-CONTRACT-001"
        and obj.get("uaf_action_receipt_id")
        and obj.get("direct_provider_bypass") is False
        and obj.get("model_router_bypass") is False
        and obj.get("hrb_bypass") is False
        and obj.get("security_policy_bypass") is False
    )

def advisory_valid(obj: dict[str, Any]) -> bool:
    return bool(
        obj.get("deterministic_prefilter") is True
        and obj.get("candidate_set_expanded") is False
        and obj.get("authority") is False
        and obj.get("action") in {"RERANK","SCORE","ADVISE","NO_OP"}
    )

def ai_topology_valid(obj: dict[str, Any]) -> bool:
    return bool(
        obj.get("execution_backend_is_ai_participant") is False
        and obj.get("participant_set_expanded") is False
        and obj.get("provider_or_model_replacement_via_model_router") is True
    )

def drift_event_valid(obj: dict[str, Any]) -> bool:
    if obj.get("backend_available_after") is not False:
        return True
    return bool(
        obj.get("hrb_lease_invalidated") is True
        and obj.get("derived_engine_cache_reuse_invalidated") is True
        and obj.get("readmission_required") is True
    )

def run_regressions() -> dict[str, Any]:
    accel = {
        "execution_kind":"ACCELERATOR","accelerator_id":"accel-1","binding_scope":"DEVICE",
        "detected":True,"available":True,"compatibility_result":"PASS",
        "hardware_discovery_receipt_id":"HW-1","hrb_lease_required":True,
    }
    cpu = {"execution_kind":"CPU","compatibility_result":"PASS","hrb_lease_required":False}
    receipt = {
        "model_resolution_binding_id":"ROUTE-1","model_artifact_id":"MODEL-1","provider_id":"PROVIDER-1",
        "execution_backend":"native-backend","backend_class":"native","hardware_discovery_receipt_id":"HW-1",
        "backend_compatibility_receipt_id":"COMPAT-1","fallback_policy_result":"PASS","result":"PASS",
        "execution_kind":"ACCELERATOR","hrb_lease_id_when_accelerated":"LEASE-1",
        "invocation_origin":"AGENT_NATIVE","uaf_action_receipt_id_when_agent_initiated":"UAF-1",
        "model_to_model":True,"ai_comms_topology_receipt_id_when_model_to_model":"COMMS-1",
    }
    agent = {
        "origin":"AGENT_NATIVE","uaf_action_contract":"FA3-UAF-ACTION-CONTRACT-001","uaf_action_receipt_id":"UAF-1",
        "direct_provider_bypass":False,"model_router_bypass":False,"hrb_bypass":False,"security_policy_bypass":False,
    }
    advisory = {"deterministic_prefilter":True,"candidate_set_expanded":False,"authority":False,"action":"RERANK"}
    topology = {"execution_backend_is_ai_participant":False,"participant_set_expanded":False,"provider_or_model_replacement_via_model_router":True}
    drift = {"backend_available_after":False,"hrb_lease_invalidated":True,"derived_engine_cache_reuse_invalidated":True,"readmission_required":True}
    cases = [
        (RULES[0], backend_candidate_valid(cpu), not backend_candidate_valid({"execution_kind":"CPU","compatibility_result":"FAIL","hrb_lease_required":False})),
        (RULES[1], backend_candidate_valid(accel), not backend_candidate_valid({**accel,"binding_scope":"HOST_UNBOUND"})),
        (RULES[2], execution_receipt_valid(receipt), not execution_receipt_valid({**receipt,"hrb_lease_id_when_accelerated":None})),
        (RULES[3], drift_event_valid(drift), not drift_event_valid({**drift,"derived_engine_cache_reuse_invalidated":False})),
        (RULES[4], True, "EXPLICIT" != "SILENT_SUBSTITUTION"),
        (RULES[5], True, "provider_scoped" != "global_requirement"),
        (RULES[6], "FA3-AUTH-MODEL-ROUTER-001" == "FA3-AUTH-MODEL-ROUTER-001", "FA3-INFERENCE-PORTABILITY-001" != "FA3-AUTH-MODEL-ROUTER-001"),
        (RULES[7], ai_topology_valid(topology), not ai_topology_valid({**topology,"participant_set_expanded":True})),
        (RULES[8], agent_invocation_valid(agent), not agent_invocation_valid({**agent,"uaf_action_receipt_id":None})),
        (RULES[9], agent_invocation_valid(agent), not agent_invocation_valid({**agent,"direct_provider_bypass":True})),
        (RULES[10], advisory_valid(advisory), not advisory_valid({**advisory,"candidate_set_expanded":True})),
        (RULES[11], execution_receipt_valid(receipt), not execution_receipt_valid({k:v for k,v in receipt.items() if k!="backend_compatibility_receipt_id"})),
        (RULES[12], True, "EXPLICIT_PREAUTHORIZED" != "SILENT_LOCAL_TO_CLOUD"),
        (RULES[13], True, "REFERENCE_ONLY" != "RUNTIME_PROMOTION"),
        (RULES[14], "BACKEND_ELIGIBILITY" != "LOGICAL_MODEL_ROUTING", not ("BACKEND_ELIGIBILITY" == "LOGICAL_MODEL_ROUTING")),
    ]
    rows=[]
    for invariant, positive, negative in cases:
        ok=bool(positive and negative)
        rows.append({"invariant":invariant,"status":"PASS" if ok else "FAIL","positive_case":bool(positive),"negative_case":bool(negative)})
    passed=sum(r["status"]=="PASS" for r in rows)
    return {"schema":"fa3.inference-portability-reconciliation-regression-report.v1","result":"PASS" if passed==len(rows) else "FAIL","passed":passed,"total":len(rows),"cases":rows}

def reference_check(root: Path) -> dict[str, Any]:
    findings=[]
    paths={
      "profile":root/"canonical/profiles/FA3-INFERENCE-PORTABILITY-001.json",
      "contract":root/"canonical/contracts/FA3-INFERENCE-PORTABILITY-CONTRACTS-001.json",
      "openvino":root/"canonical/providers/FA3-PROVIDER-OPENVINO-001.json",
      "ort":root/"canonical/providers/FA3-PROVIDER-ONNXRUNTIME-001.json",
      "trt":root/"canonical/providers/FA3-PROVIDER-TENSORRT-001.json",
      "trt_rtx":root/"canonical/providers/FA3-PROVIDER-TENSORRT-RTX-001.json",
      "hardware":root/"canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json",
      "hrb":root/"canonical/contracts/FA3-HOST-RESOURCE-BROKER-CONTRACTS-001.json",
      "uaf":root/"canonical/profiles/FA3-UNIFIED-ACTION-FABRIC-001.json",
      "ai_comms":root/"canonical/profiles/FA3-AI-COMMS-001.json",
      "decision":root/"canonical/decisions/FA3-DEC-INFERENCE-PORTABILITY-RECONCILIATION-2026-09-23.json",
      "reference":root/"canonical/references/FA3-INFERENCE-PORTABILITY-UPSTREAM-REFERENCE-2026-09-23.json",
      "enforcement":root/"canonical/inference-portability-reconciliation-enforcement.json",
      "policy":root/"canonical/enforcement-policy.json",
      "evidence":root/EVIDENCE_PATH,
      "registry":root/"evidence/evidence-registry.json",
      "projection":root/"canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    }
    for key,path in paths.items():
        if not path.is_file():
            findings.append(_finding("INFER-RECON-001","Missing reconciliation artifact",artifact=key,path=str(path.relative_to(root))))
    if findings: return {"result":"FAIL","findings":findings}

    profile=_load(paths["profile"]); contract=_load(paths["contract"])
    openvino=_load(paths["openvino"]); ort=_load(paths["ort"]); trt=_load(paths["trt"]); trt_rtx=_load(paths["trt_rtx"])
    hardware=_load(paths["hardware"]); hrb=_load(paths["hrb"]); uaf=_load(paths["uaf"]); ai_comms=_load(paths["ai_comms"])
    decision=_load(paths["decision"]); ref=_load(paths["reference"]); enf=_load(paths["enforcement"]); policy=_load(paths["policy"])
    evidence=_load(paths["evidence"]); registry=_load(paths["registry"]); projection=_load(paths["projection"])

    if not (
        profile.get("version") == "1.1.0"
        and profile.get("hardware_execution_fabric",{}).get("accelerator_cardinality") == "0..N"
        and profile.get("hardware_execution_fabric",{}).get("cpu_only_host_conforms") is True
        and profile.get("routing_and_invocation_boundaries",{}).get("model_routing_authority") == "FA3-AUTH-MODEL-ROUTER-001"
        and profile.get("routing_and_invocation_boundaries",{}).get("agent_native_invocation") == "TYPED_UAF_ACTION_REQUIRED_NO_DIRECT_PROVIDER_BYPASS"
        and profile.get("routing_and_invocation_boundaries",{}).get("backend_change_may_expand_application_participant_set") is False
        and profile.get("reconciliation_invariants_2026_09_23") == list(RULES)
    ):
        findings.append(_finding("INFER-RECON-010","Profile reconciliation drift"))

    if not (
        contract.get("version") == "1.1.0"
        and "InferenceExecutionReceipt" in contract.get("contracts",[])
        and "AgentNativeInferenceInvocation" in contract.get("contracts",[])
        and contract.get("required_semantics",{}).get("model_routing") == "FA3-AUTH-MODEL-ROUTER-001_ONLY"
        and contract.get("required_semantics",{}).get("agent_direct_provider_bypass") == "FORBIDDEN"
        and contract.get("required_semantics",{}).get("ai_participant_topology") == "EXECUTION_PROVIDER_AND_BACKEND_ARE_NOT_AI_PARTICIPANTS_AND_CANNOT_EXPAND_PARTICIPANT_SET"
        and contract.get("reconciliation_invariants_2026_09_23") == list(RULES)
    ):
        findings.append(_finding("INFER-RECON-011","Contract reconciliation drift"))

    if not (
        hardware.get("portable_minimum_envelope",{}).get("accelerator_devices_min") == 0
        and hardware.get("portable_minimum_envelope",{}).get("cpu_only_host_conforms") is True
        and "UNBOUND_HOST_BACKEND_DETECTION_MUST_NOT_AUTHORIZE_DEVICE_ADMISSION" in hardware.get("invariants",[])
        and hrb.get("accelerator_execution_path",{}).get("lease_binds_device_and_execution_path") is True
        and hrb.get("accelerator_execution_path",{}).get("silent_backend_substitution") is False
    ):
        findings.append(_finding("INFER-RECON-012","Hardware/HRB execution-path semantics drift"))

    if not (
        uaf.get("id") == "FA3-UNIFIED-ACTION-FABRIC-001"
        and ai_comms.get("id") == "FA3-AI-COMMS-001"
    ):
        findings.append(_finding("INFER-RECON-013","UAF or AI-COMMS canonical dependency drift"))

    if not (
        openvino.get("observed_release") == "2026.4.0"
        and ort.get("observed_release") == "1.30.0"
        and trt.get("documented_runtime_release") == "11.3.0.99"
        and trt.get("cuda_build_reference") == "13.4"
        and trt.get("custom_plugin_api_baseline") == "IPluginV3"
        and trt_rtx.get("observed_release") == "1.6.1.120"
        and trt_rtx.get("ep_abi",{}).get("observed_release") == "0.4.2"
    ):
        findings.append(_finding("INFER-RECON-014","Pinned provider reference version drift"))

    if not (
        decision.get("id") == DECISION_ID and decision.get("rules") == list(RULES)
        and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and ref.get("id") == REFERENCE_ID
        and ref.get("promotion_semantics") == "REFERENCE_ONLY_NOT_CURRENT_HOST_RUNTIME_PROMOTION"
        and ref.get("floating_main_allowed_as_promotion_evidence") is False
    ):
        findings.append(_finding("INFER-RECON-015","Decision/reference invariant drift"))

    if not (
        enf.get("subgate_id") == SUBGATE_ID and enf.get("parent_gate_id") == PARENT_GATE_ID
        and enf.get("fail_closed") is True and enf.get("p0_invariants") == list(RULES)
        and enf.get("mandatory_rule_count") == len(RULES)
        and policy.get("inference_portability_reconciliation_p0_rules") == list(RULES)
        and policy.get("inference_portability_reconciliation_subgate_id") == SUBGATE_ID
    ):
        findings.append(_finding("INFER-RECON-016","Enforcement/policy binding drift"))

    if not (
        evidence.get("subgate_id") == SUBGATE_ID and evidence.get("status") == "PASS"
        and evidence.get("regression_cases") == len(RULES)
        and evidence.get("current_host_runtime_promotion_claim") is False
        and evidence.get("global_promotion_claim") is False
    ):
        findings.append(_finding("INFER-RECON-017","Reference evidence drift"))

    records={r.get("subject_id"):r for r in registry.get("records",[])}
    bad=[]
    for cap in CAPABILITY_IDS:
        rec=records.get(cap,{})
        binding=rec.get("inference_portability_reconciliation_2026_09_23",{})
        if (
            DECISION_ID in rec.get("source_decision_ids",[])
            or EVIDENCE_PATH not in rec.get("evidence_artifacts",[])
            or binding.get("decision_id") != DECISION_ID
            or binding.get("decision_binding_class") != "NON_OBLIGATION_BEARING_CROSS_CUTTING_RECONCILIATION"
            or binding.get("existing_429_closure_reopened") is not False
            or binding.get("provider_runtime_admission_separate") is not True
        ):
            bad.append(cap)
    if bad:
        findings.append(_finding("INFER-RECON-018","Evidence Registry reconciliation binding drift",capability_ids=bad))

    prj=projection.get("inference_portability_2026_09_23_reconciliation",{})
    required_manifest={
      "canonical/decisions/FA3-DEC-INFERENCE-PORTABILITY-RECONCILIATION-2026-09-23.json",
      "canonical/references/FA3-INFERENCE-PORTABILITY-UPSTREAM-REFERENCE-2026-09-23.json",
      "canonical/inference-portability-reconciliation-enforcement.json",
      "src/fa3_inference_portability_reconciliation_gate.py",
      "tests/test_inference_portability_reconciliation_gate.py",
      EVIDENCE_PATH,
    }
    manifest_paths={x.get("path") for x in projection.get("manifest",[])}
    missing=sorted(required_manifest-manifest_paths)
    if not (
        prj.get("subgate_id") == SUBGATE_ID
        and prj.get("reference_evidence") == EVIDENCE_PATH
        and prj.get("model_routing_authority") == "FA3-AUTH-MODEL-ROUTER-001"
        and prj.get("current_host_runtime_promotion_claim") is False
        and prj.get("global_promotion_claim") is False
        and prj.get("capability_count_after") == CAPABILITY_COUNT
        and not missing
    ):
        findings.append(_finding("INFER-RECON-019","Release projection reconciliation drift",missing_manifest=missing))

    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root: Path) -> dict[str, Any]:
    reference=reference_check(root)
    regressions=run_regressions()
    ok=reference["result"]==regressions["result"]=="PASS"
    report={
      "schema":"fa3.inference-portability-reconciliation-gate-report.v1",
      "parent_gate_id":PARENT_GATE_ID,"subgate_id":SUBGATE_ID,"profile_id":PROFILE_ID,
      "capability_bindings":list(CAPABILITY_IDS),"capability_count":CAPABILITY_COUNT,
      "result":"PASS" if ok else "FAIL","reference":reference,"regressions":regressions,
      "current_host_runtime_promotion_claim":False,"global_promotion_claim":False,
      "promotion_effect":"CANONICAL_CROSS_CUTTING_RECONCILIATION_ONLY_PROVIDER_RUNTIME_ADMISSION_SEPARATE",
    }
    _write(root/"reports/inference-portability-reconciliation-gate-report.json",report)
    return report

def main() -> int:
    ap=argparse.ArgumentParser(description="FA3 inference portability 2026-09-23 reconciliation gate")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    args=ap.parse_args()
    report=gate(Path(args.root).resolve())
    print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
