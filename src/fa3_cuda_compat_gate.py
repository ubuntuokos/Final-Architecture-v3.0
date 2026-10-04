#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_cuda_compat_native import (
    EXTERNAL_SCALE_RUNTIME_DEPENDENCY,
    NATIVE_BACKEND_NAME,
    analyze_cuda_source,
    translate_cuda_kernel_source,
)
from fa3_cuda_compat_shared import SHARED_APPLICATION_SCOPE
from fa3_release_baseline import module_active_capability_count

CAPABILITY_COUNT = module_active_capability_count(__file__)

PROVIDER = "canonical/providers/FA3-PROVIDER-CFA3-NATIVE-CUDA-COMPAT-001.json"
CONTRACT = "canonical/contracts/FA3-CUDA-COMPAT-NATIVE-CONTRACTS-001.json"
INTENT = "canonical/intents/FA3-CUDA-COMPAT-NATIVE-APPLICATION-INTENT-2026-10-04.json"
REUSE = "canonical/assessments/FA3-CUDA-COMPAT-NATIVE-REUSE-ASSESSMENT-2026-10-04.json"
IMPACT = "canonical/current-host-impact/FA3-CH-IMPACT-CUDA-COMPAT-NATIVE-20261004.json"
CUDA_POLICY = "canonical/FA3-CUDA-PORTABILITY-SHARED-FUNCTION-POLICY-001.json"


def loadj(root: Path, rel: str) -> dict[str, Any]:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[str] = []
    required = {
        "provider": PROVIDER,
        "contract": CONTRACT,
        "intent": INTENT,
        "reuse": REUSE,
        "impact": IMPACT,
        "cuda_policy": CUDA_POLICY,
    }
    data: dict[str, dict[str, Any]] = {}
    for key, rel in required.items():
        try:
            data[key] = loadj(root, rel)
        except Exception as exc:
            findings.append(f"missing-or-invalid:{rel}:{type(exc).__name__}")

    for rel in ("src/fa3_cuda_compat_native.py", "src/fa3_cuda_compat_shared.py"):
        if not (root / rel).is_file():
            findings.append(f"missing-native-source:{rel}")

    if EXTERNAL_SCALE_RUNTIME_DEPENDENCY:
        findings.append("external-scale-runtime-dependency-enabled")

    if not findings:
        provider = data["provider"]
        contract = data["contract"]
        intent = data["intent"]
        reuse = data["reuse"]
        impact = data["impact"]
        policy = data["cuda_policy"]

        if provider.get("id") != "FA3-PROVIDER-CFA3-NATIVE-CUDA-COMPAT-001":
            findings.append("provider-id")
        if provider.get("capability_count") != CAPABILITY_COUNT:
            findings.append("provider-capability-count")
        if provider.get("new_capability") is not False or provider.get("new_architectural_authority") is not False:
            findings.append("provider-baseline-delta")
        if provider.get("shared_only") is not True or provider.get("application_local_functional_core") != "FORBIDDEN":
            findings.append("shared-only-placement")
        impl = provider.get("implementation", {})
        if impl.get("ownership") != "CFA3_NATIVE":
            findings.append("native-ownership")
        if impl.get("external_scale_runtime_dependency") is not False or impl.get("external_scale_build_dependency") is not False:
            findings.append("external-scale-dependency")
        if impl.get("full_cuda_parity_claimed") is not False or impl.get("closed_cuda_binary_compatibility_claimed") is not False:
            findings.append("overclaim")

        backend = provider.get("backend", {})
        if backend.get("name") != NATIVE_BACKEND_NAME or backend.get("class") != "translation":
            findings.append("backend-identity")
        if backend.get("target_vendor_materialized") != ["AMD", "INTEL"]:
            findings.append("target-vendor-scope")
        if backend.get("translation_must_be_explicitly_allowed") is not True:
            findings.append("translation-not-explicit")

        access = provider.get("shared_application_access", {})
        if access.get("scope") != SHARED_APPLICATION_SCOPE:
            findings.append("shared-application-scope")
        if access.get("application_allowlist_required") is not False:
            findings.append("application-allowlist")
        if access.get("application_local_backend_implementation") != "FORBIDDEN":
            findings.append("application-local-backend")
        if access.get("central_entrypoint") != "src/fa3_cuda_compat_shared.py:resolve_cuda_compatibility":
            findings.append("central-entrypoint")

        if contract.get("provider_id") != provider.get("id"):
            findings.append("contract-provider-binding")
        bc = contract.get("backend_contract", {})
        if bc.get("external_scale_runtime_dependency") is not False:
            findings.append("contract-external-scale")
        ac = contract.get("application_access_contract", {})
        if ac.get("consumer_scope") != SHARED_APPLICATION_SCOPE or ac.get("per_application_allowlist") is not False:
            findings.append("contract-application-scope")
        if ac.get("application_may_authorize_execution") is not False or ac.get("hrb_lease_required_before_execution") is not True:
            findings.append("contract-hrb-authority")

        if intent.get("project_id") != provider.get("id"):
            findings.append("intent-provider-binding")
        if reuse.get("pending_or_unmerged_donors_consumed") is not False:
            findings.append("pending-donor-consumed")
        if reuse.get("donor_usage_edges_created") != 0:
            findings.append("unexpected-donor-edge")
        if impact.get("physical_current_host_pass_claimed") is not False:
            findings.append("false-current-host-pass")
        if impact.get("physical_requalification_required") is not True:
            findings.append("missing-physical-requalification")
        if policy.get("shared_placement_policy", {}).get("strongly_cuda_oriented_function_core") != "SHARED_LAYER_ONLY":
            findings.append("cuda-shared-policy")

        dist = provider.get("distribution", {})
        if dist.get("class") != "FA3_NATIVE" or dist.get("release_bundle_status") != "INCLUDED":
            findings.append("native-distribution")

    source = """
__global__ void saxpy(float *out, const float *x, float a, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) out[i] = a * x[i] + out[i];
}
"""
    amd = translate_cuda_kernel_source(source, target_vendor="AMD")
    intel = translate_cuda_kernel_source(source, target_vendor="INTEL")
    negative = analyze_cuda_source(
        source + "\nvoid run(float *p) { saxpy<<<1,32>>>(p,p,1.0f,32); cudaFree(p); }",
        target_vendor="AMD",
    )
    if amd.get("result") != "PASS" or amd.get("execution_authorized") is not False:
        findings.append("amd-native-translation-regression")
    if intel.get("result") != "PASS" or intel.get("execution_authorized") is not False:
        findings.append("intel-native-translation-regression")
    if negative.get("supported") is not False:
        findings.append("unsupported-cuda-fail-closed-regression")

    report = {
        "schema": "fa3.cuda-compat-native-gate-report.v1",
        "gate_id": "FA3-GATE-CUDA-COMPAT-NATIVE-001",
        "provider_id": "FA3-PROVIDER-CFA3-NATIVE-CUDA-COMPAT-001",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "external_scale_runtime_dependency": False,
        "shared_application_scope": SHARED_APPLICATION_SCOPE,
        "runtime_promotion_claim": False,
        "physical_current_host_pass_claimed": False,
        "physical_requalification_required": True,
    }
    out = root / "reports/cuda-compat-native-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
