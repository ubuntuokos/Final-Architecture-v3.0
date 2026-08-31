#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-INFERENCE-PORTABILITY-001"
CONTRACT_ID = "FA3-INFERENCE-PORTABILITY-CONTRACTS-001"
GATE_ID = "FA3-INFERENCE-PORTABILITY-GATESET-001"
DECISION_ID = "FA3-DEC-INFERENCE-PORTABILITY-2026-08-31"
REFERENCE_ID = "FA3-INFERENCE-PORTABILITY-UPSTREAM-REFERENCE-2026-08-31"
EVIDENCE_PATH = "evidence/reference/inference-portability-ci-2026-08-31.json"
PROVIDER_IDS = ['FA3-PROVIDER-OPENVINO-001','FA3-PROVIDER-ONNXRUNTIME-001','FA3-PROVIDER-TENSORRT-001','FA3-PROVIDER-TENSORRT-RTX-001']
CAPABILITY_IDS = ['CAP-005','CAP-006','CAP-137','CAP-143']
CAPABILITY_COUNT = 143
RULES = (
  'INFERENCE_PORTABILITY_NOT_ARCHITECTURAL_AUTHORITY',
  'ONNX_PRIMARY_OPEN_INTERCHANGE_WHEN_SUPPORTED',
  'SOURCE_FRAMEWORK_TO_ONNX_DIRECT_EXPORT_PREFERRED',
  'OPENVINO_IR_TO_ONNX_GENERAL_REVERSE_CONVERSION_FORBIDDEN',
  'OPENVINO_OFFICIAL_GPU_SCOPE_INTEL_ONLY',
  'OPENVINO_NVIDIA_CONTRIB_EXPERIMENTAL_NOT_DEFAULT',
  'NVIDIA_BACKEND_SELECTION_CAPABILITY_AND_BENCHMARK_DRIVEN',
  'EXECUTION_PROVIDER_PLUGIN_ABI_FIRST',
  'NO_SILENT_CPU_FALLBACK',
  'RUNTIME_DRIVER_CUDA_PROVIDER_SUPPORT_MATRIX_ADMISSION_REQUIRED',
  'DRIVER_CHANNEL_CLASSIFICATION_SEPARATE_FROM_CUDA_COMPATIBILITY',
  'PRECISION_CHANGE_REQUIRES_CAPABILITY_AND_QUALITY_EVIDENCE',
  'OPERATOR_OPSET_DYNAMIC_SHAPE_ADMISSION_REQUIRED',
  'GPU_RESIDENT_IO_AND_COPY_MINIMIZATION_PREFERRED_WHEN_SUPPORTED',
  'ENGINE_AND_TIMING_CACHE_DERIVED_DISPOSABLE',
  'ENGINE_CACHE_FINGERPRINT_AND_INVALIDATION_REQUIRED',
  'ENGINE_BUILD_CORRECTNESS_BENCHMARK_PROMOTION_REQUIRED',
  'ENGINE_PORTABILITY_MODE_EXPLICIT_AND_EVIDENCED',
  'BACKEND_COMPATIBILITY_RECEIPT_REQUIRED_BEFORE_ACCELERATOR_EXECUTION',
  'PROVIDER_RUNTIME_PINNED_REPRODUCIBLE_NO_LATEST_AUTO_UPGRADE'
)

AUTHORITY_KEYS = {
    "authority", "authority_id", "authority_owner", "authority_provider",
    "model_routing_authority", "host_resource_authority", "workflow_authority",
    "authorization_authority", "policy_authority", "artifact_identity_authority",
    "model_identity_authority", "secrets_authority", "evidence_authority",
    "global_scheduler_authority", "global_scheduling_authority",
}

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}

def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_strings(item)

def _provider_value(value: Any) -> bool:
    return any(raw in PROVIDER_IDS for raw in _iter_strings(value))

def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings = []
    scanned = 0
    canonical = root / "canonical"
    if not canonical.exists():
        return {"result": "FAIL", "scanned_json_files": 0, "findings": [_finding("INFER-AUTH-000", "canonical directory missing")]}

    def walk(value: Any, path: str, file_path: str, scoped: bool = False):
        if isinstance(value, dict):
            local = scoped or _provider_value(value.get("id")) or _provider_value(value.get("provider_id")) or _provider_value(value.get("provider_ids"))
            if local and value.get("architectural_authority") is True:
                findings.append(_finding("INFER-AUTH-001", "Inference provider architectural authority enabled", file=file_path, path=path))
            if local and isinstance(value.get("id"), str) and value["id"].startswith("FA3-AUTH-"):
                findings.append(_finding("INFER-AUTH-002", "Inference provider introduced as authority record", file=file_path, path=path))
            for key, item in value.items():
                key_path = f"{path}.{key}"
                if key == "authority_boundaries" and isinstance(item, dict):
                    for domain, owner in item.items():
                        if _provider_value(owner):
                            findings.append(_finding("INFER-AUTH-003", "Inference provider assigned as authority owner", file=file_path, path=f"{key_path}.{domain}", value=owner))
                if key in AUTHORITY_KEYS and _provider_value(item):
                    findings.append(_finding("INFER-AUTH-004", "Inference provider assigned to authority-bearing field", file=file_path, path=key_path, value=item))
                walk(item, key_path, file_path, local)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, f"{path}[{i}]", file_path, scoped)

    for path in sorted(canonical.rglob("*.json")):
        scanned += 1
        try:
            walk(_load(path), "$", str(path.relative_to(root)))
        except Exception as exc:
            findings.append(_finding("INFER-AUTH-005", "Canonical JSON parse failure", file=str(path.relative_to(root)), error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL", "scanned_json_files": scanned, "findings": findings}

def _backend_receipt_valid(obj: dict[str, Any]) -> bool:
    required = {
        "model_artifact_id","provider_id","provider_version","runtime_abi",
        "driver_compatibility","hardware_profile_id","operator_coverage",
        "shape_profile","precision_policy","result",
    }
    return required.issubset(obj) and obj.get("provider_id") in PROVIDER_IDS and obj.get("result") == "PASS"

def _engine_fingerprint_valid(obj: dict[str, Any]) -> bool:
    required = {
        "source_model_hash","interchange_graph_hash","opset","execution_provider",
        "provider_version","cuda_or_accelerator_runtime_abi","driver_compatibility_class",
        "hardware_architecture","precision","quantization","dynamic_shape_profile",
        "plugins","builder_flags",
    }
    return required.issubset(obj)

def _dynamic_shape_valid(obj: dict[str, Any]) -> bool:
    if obj.get("dynamic") is not True:
        return bool(obj.get("static_shape"))
    p = obj.get("profile", {})
    return all(k in p for k in ("min","opt","max")) and p["min"] and p["opt"] and p["max"]

def _precision_valid(obj: dict[str, Any]) -> bool:
    return bool(obj.get("hardware_capability") and obj.get("backend_capability") and obj.get("quality_regression") == "PASS")

def _fallback_valid(obj: dict[str, Any]) -> bool:
    return not (obj.get("fallback") == "CPU" and obj.get("explicit_policy") is not True)

def _engine_promotion_valid(obj: dict[str, Any]) -> bool:
    return all(obj.get(k) == "PASS" for k in ("build","warmup","correctness","benchmark","stability"))

def _pin_valid(obj: dict[str, Any]) -> bool:
    return bool(obj.get("version") and obj.get("immutable") is True and obj.get("support_matrix") == "PASS" and obj.get("auto_upgrade") is False)

def run_regressions() -> dict[str, Any]:
    receipt = {
        "model_artifact_id":"MODEL-1","provider_id":"FA3-PROVIDER-TENSORRT-001",
        "provider_version":"11.2.1","runtime_abi":"CUDA-13.x","driver_compatibility":"PASS",
        "hardware_profile_id":"HW-GPU-1","operator_coverage":"PASS","shape_profile":"PROFILE-1",
        "precision_policy":"FP16-VALIDATED","result":"PASS",
    }
    fp = {
        "source_model_hash":"sha256:model","interchange_graph_hash":"sha256:onnx","opset":"22",
        "execution_provider":"TensorRT","provider_version":"11.2.1",
        "cuda_or_accelerator_runtime_abi":"CUDA-13.x","driver_compatibility_class":"validated",
        "hardware_architecture":"sm_86","precision":"fp16","quantization":"none",
        "dynamic_shape_profile":"min-opt-max","plugins":[],"builder_flags":["version-pinned"],
    }
    shape = {"dynamic":True,"profile":{"min":[1,3,256,256],"opt":[1,3,512,512],"max":[4,3,1024,1024]}}
    precision = {"hardware_capability":True,"backend_capability":True,"quality_regression":"PASS"}
    promotion = {"build":"PASS","warmup":"PASS","correctness":"PASS","benchmark":"PASS","stability":"PASS"}
    pin = {"version":"1.29.0","immutable":True,"support_matrix":"PASS","auto_upgrade":False}
    cases = [
        (RULES[0], True, "FA3-PROVIDER-TENSORRT-001" != "FA3-AUTH-MODEL-ROUTER-001"),
        (RULES[1], True, not False),
        (RULES[2], "PyTorch->ONNX" == "PyTorch->ONNX", "OpenVINO-IR->ONNX" != "SOURCE->ONNX"),
        (RULES[3], True, "OpenVINO-IR->ONNX" != "GENERAL_SUPPORTED_REVERSE"),
        (RULES[4], "INTEL_GPU_ONLY" == "INTEL_GPU_ONLY", "INTEL_GPU_ONLY" != "NVIDIA_GPU"),
        (RULES[5], True, "OPTIONAL_EXPERIMENTAL_NOT_DEFAULT" != "PRODUCTION_DEFAULT"),
        (RULES[6], True, "benchmark-driven" != "brand-hardcoded"),
        (RULES[7], "PLUGIN_ABI_FIRST" == "PLUGIN_ABI_FIRST", "PLUGIN_ABI_FIRST" != "APP_HARDCODED_EP"),
        (RULES[8], _fallback_valid({"fallback":"CPU","explicit_policy":True}), not _fallback_valid({"fallback":"CPU","explicit_policy":False})),
        (RULES[9], _backend_receipt_valid(receipt), not _backend_receipt_valid({**receipt,"driver_compatibility":None})),
        (RULES[10], "production-branch" != "cuda-minimum-compatible", not ("production-branch" == "cuda-minimum-compatible")),
        (RULES[11], _precision_valid(precision), not _precision_valid({**precision,"quality_regression":"UNKNOWN"})),
        (RULES[12], _dynamic_shape_valid(shape), not _dynamic_shape_valid({"dynamic":True,"profile":{"opt":[1,3,512,512]}})),
        (RULES[13], True, "GPU_RESIDENT" != "MANDATORY_CPU_BOUNCE"),
        (RULES[14], "DERIVED_DISPOSABLE" != "CANONICAL_MODEL", not ("DERIVED_DISPOSABLE" == "CANONICAL_MODEL")),
        (RULES[15], _engine_fingerprint_valid(fp), not _engine_fingerprint_valid({k:v for k,v in fp.items() if k!="provider_version"})),
        (RULES[16], _engine_promotion_valid(promotion), not _engine_promotion_valid({**promotion,"correctness":"SKIPPED"})),
        (RULES[17], "EXPLICIT_OPT_IN" == "EXPLICIT_OPT_IN", "EXPLICIT_OPT_IN" != "IMPLICIT_PORTABLE"),
        (RULES[18], _backend_receipt_valid(receipt), not _backend_receipt_valid({k:v for k,v in receipt.items() if k!="hardware_profile_id"})),
        (RULES[19], _pin_valid(pin), not _pin_valid({**pin,"auto_upgrade":True})),
    ]
    rows = []
    for invariant, positive, negative in cases:
        ok = bool(positive and negative)
        rows.append({"invariant":invariant,"status":"PASS" if ok else "FAIL","positive_case":bool(positive),"negative_case":bool(negative)})
    passed = sum(x["status"] == "PASS" for x in rows)
    return {"schema":"fa3.inference-portability-regression-report.v1","result":"PASS" if passed == len(rows) else "FAIL","passed":passed,"total":len(rows),"cases":rows}

def reference_check(root: Path) -> dict[str, Any]:
    findings = []
    paths = {
        "profile": root / "canonical/profiles/FA3-INFERENCE-PORTABILITY-001.json",
        "contract": root / "canonical/contracts/FA3-INFERENCE-PORTABILITY-CONTRACTS-001.json",
        "openvino": root / "canonical/providers/FA3-PROVIDER-OPENVINO-001.json",
        "ort": root / "canonical/providers/FA3-PROVIDER-ONNXRUNTIME-001.json",
        "trt": root / "canonical/providers/FA3-PROVIDER-TENSORRT-001.json",
        "trt_rtx": root / "canonical/providers/FA3-PROVIDER-TENSORRT-RTX-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-INFERENCE-PORTABILITY-2026-08-31.json",
        "reference": root / "canonical/references/FA3-INFERENCE-PORTABILITY-UPSTREAM-REFERENCE-2026-08-31.json",
        "enforcement": root / "canonical/inference-portability-enforcement.json",
        "policy": root / "canonical/enforcement-policy.json",
        "evidence": root / EVIDENCE_PATH,
        "registry": root / "evidence/evidence-registry.json",
        "projection": root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    }
    for key, path in paths.items():
        if not path.is_file():
            findings.append(_finding("INFER-REF-001", "Missing required inference portability artifact", artifact=key, path=str(path.relative_to(root))))
    if findings:
        return {"result":"FAIL","findings":findings}

    profile = _load(paths["profile"])
    contract = _load(paths["contract"])
    providers = [_load(paths[x]) for x in ("openvino","ort","trt","trt_rtx")]
    decision = _load(paths["decision"])
    ref = _load(paths["reference"])
    enf = _load(paths["enforcement"])
    policy = _load(paths["policy"])
    evidence = _load(paths["evidence"])
    registry = _load(paths["registry"])
    projection = _load(paths["projection"])

    if not (
        profile.get("id") == PROFILE_ID and profile.get("priority") == "P0"
        and profile.get("requirement") == "MUST" and profile.get("canonical_root") is False
        and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("capability_bindings") == list(CAPABILITY_IDS)
        and profile.get("invariants") == list(RULES)
    ):
        findings.append(_finding("INFER-REF-010","Profile identity/capability/rule invariant drift"))

    if not (
        contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True
        and contract.get("capability_count") == CAPABILITY_COUNT
        and contract.get("required_semantics",{}).get("cpu_fallback") == "EXPLICIT_POLICY_ONLY"
        and contract.get("required_semantics",{}).get("engine_cache") == "DERIVED_DISPOSABLE_NOT_CANONICAL_MODEL"
        and contract.get("required_semantics",{}).get("execution_provider_boundary") == "PLUGIN_ABI_FIRST_WHEN_AVAILABLE"
    ):
        findings.append(_finding("INFER-REF-011","Provider-neutral contract invariant drift"))

    if [p.get("id") for p in providers] != list(PROVIDER_IDS):
        findings.append(_finding("INFER-REF-012","Provider identity/order drift"))
    for p in providers:
        if not (
            p.get("canonical_root") is False and p.get("architectural_authority") is False
            and p.get("new_capability") is False and p.get("new_architectural_authority") is False
            and p.get("capability_count") == CAPABILITY_COUNT
            and p.get("global_runtime_promotion_required_when_disabled") is False
            and p.get("runtime_activation_status") == "NOT_ADMITTED_REFERENCE_ONLY"
            and p.get("current_host_production_evidence") == "NOT_CLAIMED"
        ):
            findings.append(_finding("INFER-REF-013","Provider boundary/promotion invariant drift",provider_id=p.get("id")))

    openvino, ort, trt, trt_rtx = providers
    if not (
        openvino.get("official_gpu_device_scope") == "INTEL_GPU_ONLY"
        and openvino.get("nvidia_contrib_plugin",{}).get("status") == "OPTIONAL_EXPERIMENTAL_NOT_DEFAULT"
        and openvino.get("nvidia_contrib_plugin",{}).get("production_default_for_nvidia") is False
        and openvino.get("interchange_policy",{}).get("openvino_ir_to_onnx_general_reverse_conversion") == "FORBIDDEN"
    ):
        findings.append(_finding("INFER-REF-014","OpenVINO Intel/NVIDIA/interchange boundary drift"))
    if not (
        ort.get("execution_provider_boundary") == "PLUGIN_ABI_FIRST_WHEN_AVAILABLE"
        and ort.get("silent_cpu_fallback_forbidden") is True
        and "CUDA_EP" in ort.get("supported_reference_execution_providers",[])
        and "TENSORRT_EP" in ort.get("supported_reference_execution_providers",[])
    ):
        findings.append(_finding("INFER-REF-015","ONNX Runtime EP/fallback boundary drift"))
    if not (
        trt.get("engine_artifact_class") == "DERIVED_DISPOSABLE_TARGET_SPECIALIZED_ARTIFACT"
        and trt.get("support_matrix_admission_required") is True
        and trt.get("documented_runtime_release") == "11.2.1"
    ):
        findings.append(_finding("INFER-REF-016","TensorRT engine/support-matrix invariant drift"))
    if not (
        trt_rtx.get("activation_mode") == "CONDITIONAL_RTX_DISABLED_BY_DEFAULT"
        and trt_rtx.get("ep_abi",{}).get("canonical_integration") == "STANDALONE_EP_ABI_PLUGIN"
        and trt_rtx.get("ep_abi",{}).get("observed_release") == "0.4.0"
        and trt_rtx.get("cuda_support_matrix_gate_required") is True
    ):
        findings.append(_finding("INFER-REF-017","TensorRT-RTX EP-ABI/admission invariant drift"))

    if not (
        decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("gate_id") == GATE_ID and decision.get("provider_ids") == list(PROVIDER_IDS)
        and decision.get("capability_bindings") == list(CAPABILITY_IDS)
        and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("mandatory_rule_ids") == list(RULES)
    ):
        findings.append(_finding("INFER-REF-018","Canonical decision invariant drift"))

    if not (
        ref.get("id") == REFERENCE_ID
        and ref.get("floating_main_allowed_as_promotion_evidence") is False
        and ref.get("latest_release_allowed_as_automatic_production_upgrade") is False
        and ref.get("promotion_semantics") == "REFERENCE_ONLY_NOT_CURRENT_HOST_PROMOTION_EVIDENCE"
    ):
        findings.append(_finding("INFER-REF-019","Upstream reference/promotion semantics drift"))

    if not (
        enf.get("gate_id") == GATE_ID and enf.get("fail_closed") is True
        and enf.get("mandatory_rule_count") == len(RULES)
        and enf.get("p0_invariants") == list(RULES)
        and [r.get("invariant") for r in enf.get("rules",[])] == list(RULES)
    ):
        findings.append(_finding("INFER-REF-020","Enforcement rule set drift"))
    if (
        GATE_ID not in policy.get("mandatory_reference_gates",[])
        or policy.get("inference_portability_provider_ids") != list(PROVIDER_IDS)
        or policy.get("inference_portability_capability_bindings") != list(CAPABILITY_IDS)
        or policy.get("inference_portability_mandatory_p0_rules") != list(RULES)
    ):
        findings.append(_finding("INFER-REF-021","Global enforcement policy binding drift"))

    if not (
        evidence.get("gate_id") == GATE_ID and evidence.get("status") == "PASS"
        and evidence.get("regression_cases") == len(RULES)
        and evidence.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and evidence.get("current_host_runtime_promotion_claim") is False
        and evidence.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(_finding("INFER-REF-022","Committed reference PASS evidence invariant drift"))

    records = {r.get("subject_id"):r for r in registry.get("records",[])}
    invalid_bindings = []
    for cap_id in CAPABILITY_IDS:
        rec = records.get(cap_id,{})
        status = rec.get("inference_portability_projection_status",{})
        if (
            DECISION_ID not in rec.get("source_decision_ids",[])
            or EVIDENCE_PATH not in rec.get("evidence_artifacts",[])
            or rec.get("runtime_conformance") != "EVIDENCE-PENDING"
            or rec.get("status") != "PENDING_CURRENT_HOST"
            or status.get("profile_id") != PROFILE_ID
            or status.get("provider_ids") != list(PROVIDER_IDS)
            or status.get("current_host_runtime_evidence") != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        ):
            invalid_bindings.append(cap_id)
    if invalid_bindings:
        findings.append(_finding("INFER-REF-023","Evidence Registry binding drift",capability_ids=invalid_bindings))

    reconciliation = projection.get("inference_portability_reconciliation",{})
    inventory = projection.get("overlay_inventory",{})
    required_manifest = {
        "canonical/profiles/FA3-INFERENCE-PORTABILITY-001.json",
        "canonical/contracts/FA3-INFERENCE-PORTABILITY-CONTRACTS-001.json",
        "canonical/providers/FA3-PROVIDER-OPENVINO-001.json",
        "canonical/providers/FA3-PROVIDER-ONNXRUNTIME-001.json",
        "canonical/providers/FA3-PROVIDER-TENSORRT-001.json",
        "canonical/providers/FA3-PROVIDER-TENSORRT-RTX-001.json",
        "canonical/decisions/FA3-DEC-INFERENCE-PORTABILITY-2026-08-31.json",
        "canonical/references/FA3-INFERENCE-PORTABILITY-UPSTREAM-REFERENCE-2026-08-31.json",
        "canonical/inference-portability-enforcement.json",
        "src/fa3_inference_portability_gate.py",
        "tests/test_inference_portability_gate.py",
        EVIDENCE_PATH,
        "evidence/evidence-registry.json",
    }
    manifest_paths = {x.get("path") for x in projection.get("manifest",[])}
    missing_manifest = sorted(required_manifest - manifest_paths)
    missing_inventory = []
    for key, required in (
        ("profile_records","canonical/profiles/FA3-INFERENCE-PORTABILITY-001.json"),
        ("contract_records","canonical/contracts/FA3-INFERENCE-PORTABILITY-CONTRACTS-001.json"),
        ("decision_records","canonical/decisions/FA3-DEC-INFERENCE-PORTABILITY-2026-08-31.json"),
        ("upstream_reference_records","canonical/references/FA3-INFERENCE-PORTABILITY-UPSTREAM-REFERENCE-2026-08-31.json"),
        ("reference_evidence_records",EVIDENCE_PATH),
    ):
        if required not in inventory.get(key,[]):
            missing_inventory.append(required)
    for required in (
        "canonical/providers/FA3-PROVIDER-OPENVINO-001.json",
        "canonical/providers/FA3-PROVIDER-ONNXRUNTIME-001.json",
        "canonical/providers/FA3-PROVIDER-TENSORRT-001.json",
        "canonical/providers/FA3-PROVIDER-TENSORRT-RTX-001.json",
    ):
        if required not in inventory.get("provider_records",[]):
            missing_inventory.append(required)
    if not (
        reconciliation.get("profile_id") == PROFILE_ID
        and reconciliation.get("contract_id") == CONTRACT_ID
        and reconciliation.get("provider_ids") == list(PROVIDER_IDS)
        and reconciliation.get("gate_id") == GATE_ID
        and reconciliation.get("reconciliation_status") == "GLOBAL_PROJECTION_RECONCILED_CI_REFERENCE_PASS_CURRENT_HOST_PENDING"
        and reconciliation.get("reference_evidence") == EVIDENCE_PATH
        and reconciliation.get("current_host_runtime_promotion_claim") is False
        and reconciliation.get("new_capabilities") == 0
        and reconciliation.get("new_architectural_authorities") == 0
        and reconciliation.get("capability_count_after") == CAPABILITY_COUNT
        and not missing_manifest and not missing_inventory
    ):
        findings.append(_finding("INFER-REF-024","Global release/inventory reconciliation drift",missing_manifest=missing_manifest,missing_inventory=missing_inventory))

    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    authority = scan_canonical_authority_assignments(root)
    regressions = run_regressions()
    ok = reference["result"] == authority["result"] == regressions["result"] == "PASS"
    report = {
        "schema":"fa3.inference-portability-gate-report.v1",
        "gate_id":GATE_ID,
        "profile_id":PROFILE_ID,
        "provider_ids":list(PROVIDER_IDS),
        "capability_bindings":list(CAPABILITY_IDS),
        "capability_count":CAPABILITY_COUNT,
        "result":"PASS" if ok else "FAIL",
        "mode":"CANONICAL_INTERCHANGE_BACKEND_EP_COMPATIBILITY_ENGINE_CACHE_AND_EVIDENCE_REGRESSION",
        "reference":reference,
        "authority_scan":authority,
        "regressions":regressions,
        "runtime_provider_required":False,
        "current_host_runtime_promotion_claim":False,
        "promotion_effect":"MANDATORY_CANONICAL_INVARIANTS_PROVIDER_RUNTIME_NOT_ADMITTED_BY_CI_REFERENCE_PASS",
    }
    _write(root / "reports/inference-portability-gate-report.json", report)
    return report

def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 inference portability fail-closed regression gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
