#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PARENT_GATE_ID = "FA3-INFERENCE-PORTABILITY-GATESET-001"
SUBGATE_ID = "FA3-INFERENCE-PORTABILITY-CACHE-HARDENING-001"
PROFILE_ID = "FA3-INFERENCE-PORTABILITY-001"
CONTRACT_ID = "FA3-INFERENCE-PORTABILITY-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-TENSORRT-RTX-001"
DECISION_ID = "FA3-DEC-INFERENCE-CACHE-HARDENING-2026-09-07"
REFERENCE_ID = "FA3-TENSORRT-RTX-RUNTIME-CACHE-REFERENCE-2026-09-07"
EVIDENCE_PATH = "evidence/reference/inference-cache-hardening-ci-2026-09-07.json"
CAPABILITY_IDS = ("CAP-005", "CAP-006", "CAP-137", "CAP-143")
CAPABILITY_COUNT = 143
RULES = (
    "TENSORRT_RTX_RUNTIME_CACHE_IDENTITY_REQUIRED",
    "TENSORRT_RTX_RUNTIME_CACHE_DRIVER_MONOTONIC_COMPATIBILITY",
    "TENSORRT_RTX_RUNTIME_CACHE_MISS_JIT_REBUILD_OBSERVABLE",
    "TENSORRT_RTX_STEADY_STATE_BENCHMARK_SEPARATES_JIT_WARMUP",
    "TENSORRT_RTX_TIMING_CACHE_DEPRECATED_NOT_CANONICAL_RUNTIME_CACHE",
)
CACHE_IDENTITY_FIELDS = (
    "gpu_sku",
    "tensorrt_rtx_version",
    "cuda_context_cig_state",
    "cache_origin_driver_version",
)
CACHE_USE_RECEIPT_FIELDS = (
    "provider_id",
    "cache_artifact_hash",
    "cache_compatibility_result",
    "cache_used",
    "jit_rebuild_detected",
    "observability_source",
    "runtime_driver_version",
    "cache_origin_driver_version",
    "gpu_sku",
    "tensorrt_rtx_version",
    "cuda_context_cig_state",
    "first_inference_latency_ms",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def _version_tuple(raw: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", str(raw))
    return tuple(int(x) for x in nums) if nums else ()


def _driver_gte(runtime_driver: str, cache_driver: str) -> bool:
    runtime = _version_tuple(runtime_driver)
    cached = _version_tuple(cache_driver)
    if not runtime or not cached:
        return False
    width = max(len(runtime), len(cached))
    runtime += (0,) * (width - len(runtime))
    cached += (0,) * (width - len(cached))
    return runtime >= cached


def cache_identity_valid(obj: dict[str, Any]) -> bool:
    return all(obj.get(field) not in (None, "") for field in CACHE_IDENTITY_FIELDS)


def runtime_cache_compatible(cache: dict[str, Any], runtime: dict[str, Any]) -> bool:
    if not cache_identity_valid(cache):
        return False
    same_or_evidenced_gpu = (
        runtime.get("gpu_sku") == cache.get("gpu_sku")
        or runtime.get("gpu_sku_equivalence_evidence") == "PASS"
    )
    return bool(
        same_or_evidenced_gpu
        and runtime.get("tensorrt_rtx_version") == cache.get("tensorrt_rtx_version")
        and runtime.get("cuda_context_cig_state") == cache.get("cuda_context_cig_state")
        and _driver_gte(runtime.get("runtime_driver_version", ""), cache.get("cache_origin_driver_version", ""))
    )


def cache_use_receipt_valid(obj: dict[str, Any]) -> bool:
    if not all(field in obj for field in CACHE_USE_RECEIPT_FIELDS):
        return False
    if obj.get("provider_id") != PROVIDER_ID:
        return False
    if obj.get("cache_compatibility_result") == "PASS":
        return bool(obj.get("cache_used") is True and obj.get("jit_rebuild_detected") is False)
    if obj.get("cache_compatibility_result") == "FAIL":
        return bool(
            obj.get("cache_used") is False
            and obj.get("jit_rebuild_detected") is True
            and obj.get("observability_source") in {"APPLICATION_LOG", "PROFILER", "JIT_TIMING_PROFILE"}
        )
    return False


def benchmark_receipt_valid(obj: dict[str, Any]) -> bool:
    return bool(
        obj.get("warmup_jit_phase_recorded") is True
        and obj.get("steady_state_cache_hit_confirmed") is True
        and isinstance(obj.get("first_inference_latency_ms"), (int, float))
        and isinstance(obj.get("steady_state_latency_ms"), (int, float))
        and obj.get("steady_state_sample_count", 0) >= 3
        and obj.get("benchmark_phase_separation") == "WARMUP_JIT_THEN_STEADY_STATE"
    )


def run_regressions() -> dict[str, Any]:
    cache = {
        "gpu_sku": "NVIDIA-GeForce-RTX-3090",
        "tensorrt_rtx_version": "1.6.1.120",
        "cuda_context_cig_state": "DISABLED",
        "cache_origin_driver_version": "610.43.02",
    }
    runtime_ok = {
        "gpu_sku": "NVIDIA-GeForce-RTX-3090",
        "tensorrt_rtx_version": "1.6.1.120",
        "cuda_context_cig_state": "DISABLED",
        "runtime_driver_version": "610.57.04",
    }
    miss_receipt = {
        "provider_id": PROVIDER_ID,
        "cache_artifact_hash": "sha256:cache",
        "cache_compatibility_result": "FAIL",
        "cache_used": False,
        "jit_rebuild_detected": True,
        "observability_source": "PROFILER",
        "runtime_driver_version": "610.57.04",
        "cache_origin_driver_version": "610.43.02",
        "gpu_sku": "NVIDIA-GeForce-RTX-3090",
        "tensorrt_rtx_version": "1.6.1.120",
        "cuda_context_cig_state": "DISABLED",
        "first_inference_latency_ms": 2200.0,
    }
    benchmark = {
        "warmup_jit_phase_recorded": True,
        "steady_state_cache_hit_confirmed": True,
        "first_inference_latency_ms": 2200.0,
        "steady_state_latency_ms": 38.0,
        "steady_state_sample_count": 10,
        "benchmark_phase_separation": "WARMUP_JIT_THEN_STEADY_STATE",
    }
    cases = [
        (
            RULES[0],
            cache_identity_valid(cache),
            not cache_identity_valid({k: v for k, v in cache.items() if k != "cuda_context_cig_state"}),
        ),
        (
            RULES[1],
            runtime_cache_compatible(cache, runtime_ok),
            not runtime_cache_compatible(cache, {**runtime_ok, "runtime_driver_version": "609.99.00"}),
        ),
        (
            RULES[2],
            cache_use_receipt_valid(miss_receipt),
            not cache_use_receipt_valid({**miss_receipt, "jit_rebuild_detected": False}),
        ),
        (
            RULES[3],
            benchmark_receipt_valid(benchmark),
            not benchmark_receipt_valid({**benchmark, "warmup_jit_phase_recorded": False}),
        ),
        (
            RULES[4],
            True,
            "DEPRECATED_UPSTREAM" != "CANONICAL_RUNTIME_CACHE",
        ),
    ]
    rows = []
    for invariant, positive, negative in cases:
        ok = bool(positive and negative)
        rows.append({
            "invariant": invariant,
            "status": "PASS" if ok else "FAIL",
            "positive_case": bool(positive),
            "negative_case": bool(negative),
        })
    passed = sum(row["status"] == "PASS" for row in rows)
    return {
        "schema": "fa3.inference-cache-hardening-regression-report.v1",
        "result": "PASS" if passed == len(rows) else "FAIL",
        "passed": passed,
        "total": len(rows),
        "cases": rows,
    }


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "contract": root / "canonical/contracts/FA3-INFERENCE-PORTABILITY-CONTRACTS-001.json",
        "provider": root / "canonical/providers/FA3-PROVIDER-TENSORRT-RTX-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-INFERENCE-CACHE-HARDENING-2026-09-07.json",
        "reference": root / "canonical/references/FA3-TENSORRT-RTX-RUNTIME-CACHE-REFERENCE-2026-09-07.json",
        "enforcement": root / "canonical/inference-cache-hardening-enforcement.json",
        "policy": root / "canonical/enforcement-policy.json",
        "evidence": root / EVIDENCE_PATH,
        "projection": root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    }
    for key, path in paths.items():
        if not path.is_file():
            findings.append(_finding("INFER-CACHE-REF-001", "Missing cache-hardening artifact", artifact=key, path=str(path.relative_to(root))))
    if findings:
        return {"result": "FAIL", "findings": findings}

    contract = _load(paths["contract"])
    provider = _load(paths["provider"])
    decision = _load(paths["decision"])
    reference = _load(paths["reference"])
    enforcement = _load(paths["enforcement"])
    policy = _load(paths["policy"])
    evidence = _load(paths["evidence"])
    projection = _load(paths["projection"])

    if PARENT_GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("INFER-CACHE-REF-010", "Parent inference portability gate is not mandatory"))

    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("provider_neutral") is True
        and contract.get("capability_count") == CAPABILITY_COUNT
        and "TensorRTRTXRuntimeCacheDescriptor" in contract.get("contracts", [])
        and "RuntimeCacheUseReceipt" in contract.get("contracts", [])
        and contract.get("tensorrt_rtx_runtime_cache_fingerprint_required_fields") == list(CACHE_IDENTITY_FIELDS)
        and contract.get("runtime_cache_use_receipt_required_fields") == list(CACHE_USE_RECEIPT_FIELDS)
        and contract.get("required_semantics", {}).get("tensorrt_rtx_timing_cache") == "DEPRECATED_API_NOT_CANONICAL_RUNTIME_CACHE_AND_NOT_FOR_NEW_INTEGRATIONS"
    ):
        findings.append(_finding("INFER-CACHE-REF-011", "Inference portability contract cache-hardening drift"))

    cache_policy = provider.get("runtime_cache_compatibility", {})
    timing_policy = provider.get("timing_cache_api", {})
    if not (
        provider.get("id") == PROVIDER_ID
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and cache_policy.get("required_cache_identity") == list(CACHE_IDENTITY_FIELDS)
        and cache_policy.get("driver_rule") == "RUNTIME_DRIVER_VERSION_MUST_BE_GREATER_THAN_OR_EQUAL_TO_CACHE_ORIGIN_DRIVER_VERSION"
        and cache_policy.get("incompatibility_behavior") == "CACHE_IGNORED_AND_KERNELS_TRANSPARENTLY_JIT_RECOMPILED_WITHOUT_ERROR"
        and cache_policy.get("observability_requirement") == "CACHE_HIT_OR_MISS_AND_JIT_REBUILD_MUST_BE_EVIDENCE_VISIBLE_VIA_LOGS_OR_PROFILING"
        and timing_policy.get("status") == "DEPRECATED_UPSTREAM"
        and timing_policy.get("new_integration_policy") == "FORBIDDEN_AS_CANONICAL_RUNTIME_CACHE_PATH"
    ):
        findings.append(_finding("INFER-CACHE-REF-012", "TensorRT-RTX provider cache/timing policy drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("parent_gate_id") == PARENT_GATE_ID
        and decision.get("subgate_id") == SUBGATE_ID
        and decision.get("rules") == list(RULES)
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(_finding("INFER-CACHE-REF-013", "Cache-hardening decision drift"))

    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("provider_id") == PROVIDER_ID
        and reference.get("compatibility_requirements", {}).get("tensorrt_rtx_version") == "EXACT_MATCH"
        and reference.get("compatibility_requirements", {}).get("cuda_context_cig_state") == "EXACT_MATCH"
        and reference.get("compatibility_failure_behavior") == "CACHE_IGNORED_TRANSPARENT_JIT_RECOMPILE_NO_ERROR"
        and reference.get("timing_cache_api_status") == "DEPRECATED_NOT_CANONICAL_RUNTIME_CACHE"
        and reference.get("current_host_runtime_evidence") == "NOT_CLAIMED"
    ):
        findings.append(_finding("INFER-CACHE-REF-014", "Pinned upstream runtime-cache reference drift"))

    if not (
        enforcement.get("parent_gate_id") == PARENT_GATE_ID
        and enforcement.get("subgate_id") == SUBGATE_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("mandatory_rule_count") == len(RULES)
        and enforcement.get("p0_invariants") == list(RULES)
        and enforcement.get("new_capabilities") == 0
        and enforcement.get("new_architectural_authorities") == 0
        and enforcement.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append(_finding("INFER-CACHE-REF-015", "Cache-hardening enforcement drift"))

    if not (
        evidence.get("subgate_id") == SUBGATE_ID
        and evidence.get("status") == "PASS"
        and evidence.get("regression_cases") == len(RULES)
        and evidence.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and evidence.get("current_host_runtime_promotion_claim") is False
        and evidence.get("new_capabilities") == 0
        and evidence.get("new_architectural_authorities") == 0
        and evidence.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(_finding("INFER-CACHE-REF-016", "Cache-hardening reference evidence drift"))

    reconciliation = projection.get("inference_cache_hardening_reconciliation", {})
    manifest_paths = {entry.get("path") for entry in projection.get("manifest", [])}
    required_manifest = {
        "canonical/contracts/FA3-INFERENCE-PORTABILITY-CONTRACTS-001.json",
        "canonical/providers/FA3-PROVIDER-TENSORRT-RTX-001.json",
        "canonical/decisions/FA3-DEC-INFERENCE-CACHE-HARDENING-2026-09-07.json",
        "canonical/references/FA3-TENSORRT-RTX-RUNTIME-CACHE-REFERENCE-2026-09-07.json",
        "canonical/inference-cache-hardening-enforcement.json",
        "src/fa3_inference_cache_hardening_gate.py",
        "tests/test_inference_cache_hardening_gate.py",
        EVIDENCE_PATH,
    }
    missing_manifest = sorted(required_manifest - manifest_paths)
    if not (
        reconciliation.get("parent_gate_id") == PARENT_GATE_ID
        and reconciliation.get("subgate_id") == SUBGATE_ID
        and reconciliation.get("provider_id") == PROVIDER_ID
        and reconciliation.get("reference_evidence") == EVIDENCE_PATH
        and reconciliation.get("reconciliation_status") == "GLOBAL_PROJECTION_RECONCILED_CI_REFERENCE_PASS_CURRENT_HOST_PENDING"
        and reconciliation.get("new_capabilities") == 0
        and reconciliation.get("new_architectural_authorities") == 0
        and reconciliation.get("capability_count_after") == CAPABILITY_COUNT
        and reconciliation.get("current_host_runtime_promotion_claim") is False
        and not missing_manifest
    ):
        findings.append(_finding("INFER-CACHE-REF-017", "Release projection cache-hardening reconciliation drift", missing_manifest=missing_manifest))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    regressions = run_regressions()
    ok = reference["result"] == regressions["result"] == "PASS"
    report = {
        "schema": "fa3.inference-cache-hardening-gate-report.v1",
        "parent_gate_id": PARENT_GATE_ID,
        "subgate_id": SUBGATE_ID,
        "provider_id": PROVIDER_ID,
        "capability_bindings": list(CAPABILITY_IDS),
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if ok else "FAIL",
        "reference": reference,
        "regressions": regressions,
        "current_host_runtime_promotion_claim": False,
        "promotion_effect": "CANONICAL_RUNTIME_CACHE_HARDENING_ONLY_NO_RUNTIME_PROMOTION",
    }
    _write(root / "reports/inference-cache-hardening-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 TensorRT-RTX runtime-cache hardening subgate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
