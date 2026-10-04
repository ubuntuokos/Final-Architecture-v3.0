#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from fa3_cuda_compat_build import make_build_plan
from fa3_cuda_compat_native import (
    EXTERNAL_SCALE_RUNTIME_DEPENDENCY,
    NATIVE_BACKEND_NAME,
    analyze_cuda_source,
    translate_cuda_kernel_source,
)
from fa3_cuda_compat_runtime import runtime_api_support
from fa3_cuda_compat_shared import SHARED_APPLICATION_SCOPE
from fa3_release_baseline import module_active_capability_count

CAPABILITY_COUNT = module_active_capability_count(__file__)
GATESET_ID = "FA3-CUDA-COMPAT-NATIVE-GATESET-001"
GATE_RECORD_ID = "FA3-GATE-CUDA-COMPAT-NATIVE-001"

PROVIDER = "canonical/providers/FA3-PROVIDER-CFA3-NATIVE-CUDA-COMPAT-001.json"
CONTRACT = "canonical/contracts/FA3-CUDA-COMPAT-NATIVE-CONTRACTS-001.json"
INTENT = "canonical/intents/FA3-CUDA-COMPAT-NATIVE-APPLICATION-INTENT-2026-10-04.json"
REUSE = "canonical/assessments/FA3-CUDA-COMPAT-NATIVE-REUSE-ASSESSMENT-2026-10-04.json"
IMPACT = "canonical/current-host-impact/FA3-CH-IMPACT-CUDA-COMPAT-NATIVE-20261004.json"
CONFORMANCE = "canonical/FA3-CUDA-COMPAT-NATIVE-CURRENT-HOST-CONFORMANCE-001.json"
CUDA_POLICY = "canonical/FA3-CUDA-PORTABILITY-SHARED-FUNCTION-POLICY-001.json"
GATE_RECORD = "canonical/FA3-GATE-CUDA-COMPAT-NATIVE-001.json"
GATE_REGISTRY = "canonical/FA3-GATE-REGISTRY-001.json"
ENFORCEMENT_POLICY = "canonical/enforcement-policy.json"
APPLICATION_DONOR_LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
PLAN = "docs/cfa3-native-cuda-compat-final-plan-2026-10-04.md"
PLAN_APPROVAL = "canonical/decisions/FA3-DEC-CUDA-COMPAT-NATIVE-PLAN-APPROVAL-2026-10-04.json"
DONOR_DECISIONS = (
    "canonical/decisions/FA3-DEC-CUDA-COMPAT-OROCHI-DONOR-USE-2026-10-04.json",
    "canonical/decisions/FA3-DEC-CUDA-COMPAT-ROCM-EXAMPLES-DONOR-USE-2026-10-04.json",
)
EXPECTED_USAGE = {
    "FA3-USAGE-GPUOPEN-OROCHI-CUDA-COMPAT-001": "FA3-DONOR-GPUOPEN-OROCHI-001",
    "FA3-USAGE-ROCM-EXAMPLES-CUDA-COMPAT-001": "FA3-DONOR-ROCM-EXAMPLES-001",
}
SOURCE_FILES = (
    "src/fa3_cuda_compat_ir.py",
    "src/fa3_cuda_compat_frontend.py",
    "src/fa3_cuda_compat_backends.py",
    "src/fa3_cuda_compat_runtime.py",
    "src/fa3_cuda_compat_build.py",
    "src/fa3_cuda_compat_native.py",
    "src/fa3_cuda_compat_shared.py",
)


def loadj(root: Path, rel: str) -> dict[str, Any]:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[str] = []
    required = {
        "provider": PROVIDER,
        "contract": CONTRACT,
        "intent": INTENT,
        "reuse": REUSE,
        "impact": IMPACT,
        "conformance": CONFORMANCE,
        "cuda_policy": CUDA_POLICY,
        "gate_record": GATE_RECORD,
        "gate_registry": GATE_REGISTRY,
        "enforcement_policy": ENFORCEMENT_POLICY,
        "application_donor_links": APPLICATION_DONOR_LINKS,
        "plan_approval": PLAN_APPROVAL,
    }
    data: dict[str, dict[str, Any]] = {}
    for key, rel in required.items():
        try:
            data[key] = loadj(root, rel)
        except Exception as exc:
            findings.append(f"missing-or-invalid:{rel}:{type(exc).__name__}")
    for rel in (*SOURCE_FILES, PLAN, *DONOR_DECISIONS):
        if not (root / rel).is_file():
            findings.append(f"missing-materialization:{rel}")
    if EXTERNAL_SCALE_RUNTIME_DEPENDENCY:
        findings.append("external-scale-runtime-dependency-enabled")

    if not findings:
        provider=data["provider"]; contract=data["contract"]; intent=data["intent"]
        reuse=data["reuse"]; impact=data["impact"]; conformance=data["conformance"]
        policy=data["cuda_policy"]; gate_record=data["gate_record"]
        gate_registry=data["gate_registry"]; enforcement=data["enforcement_policy"]
        links=data["application_donor_links"]; approval=data["plan_approval"]

        if provider.get("id")!="FA3-PROVIDER-CFA3-NATIVE-CUDA-COMPAT-001": findings.append("provider-id")
        if provider.get("version")!="2.0.0": findings.append("provider-version")
        if provider.get("capability_count")!=CAPABILITY_COUNT: findings.append("provider-capability-count")
        if provider.get("new_capability") is not False or provider.get("new_architectural_authority") is not False: findings.append("provider-baseline-delta")
        if provider.get("shared_only") is not True or provider.get("application_local_functional_core")!="FORBIDDEN": findings.append("shared-only-placement")
        impl=provider.get("implementation",{})
        if impl.get("ownership")!="CFA3_NATIVE": findings.append("native-ownership")
        if impl.get("external_scale_runtime_dependency") is not False or impl.get("external_scale_build_dependency") is not False: findings.append("external-scale-dependency")
        if impl.get("full_cuda_parity_claimed") is not False or impl.get("closed_cuda_binary_compatibility_claimed") is not False: findings.append("overclaim")
        if impl.get("frontend")!="src/fa3_cuda_compat_frontend.py" or impl.get("ir")!="src/fa3_cuda_compat_ir.py": findings.append("structured-frontend-ir-binding")

        backend=provider.get("backend",{})
        if backend.get("name")!=NATIVE_BACKEND_NAME or backend.get("class")!="translation": findings.append("backend-identity")
        if backend.get("target_vendor_materialized")!=["AMD","INTEL"]: findings.append("target-vendor-scope")
        if backend.get("compatibility_result_enum")!=["FULL_EQUIVALENCE","FUNCTIONALLY_REDUCED","UNAVAILABLE"]: findings.append("classification-enum")
        if backend.get("AMD",{}).get("compatibility_result_for_supported_subset")!="FULL_EQUIVALENCE": findings.append("amd-classification")
        intel=backend.get("INTEL",{})
        if intel.get("default_target_backend")!="sycl" or intel.get("secondary_lowering")!="OPENCL_C": findings.append("intel-target-order")
        if intel.get("compatibility_result_for_supported_subset")!="FUNCTIONALLY_REDUCED": findings.append("intel-classification")
        access=provider.get("shared_application_access",{})
        if access.get("scope")!=SHARED_APPLICATION_SCOPE or access.get("application_allowlist_required") is not False: findings.append("shared-application-scope")
        if access.get("application_local_backend_implementation")!="FORBIDDEN": findings.append("application-local-backend")
        for key,val in {
            "central_entrypoint":"src/fa3_cuda_compat_shared.py:resolve_cuda_compatibility",
            "translation_entrypoint":"src/fa3_cuda_compat_shared.py:prepare_cuda_compat_translation",
            "build_entrypoint":"src/fa3_cuda_compat_shared.py:prepare_cuda_compat_build",
            "runtime_inspection_entrypoint":"src/fa3_cuda_compat_shared.py:inspect_cuda_runtime_compatibility",
        }.items():
            if access.get(key)!=val: findings.append(f"shared-entrypoint:{key}")

        if contract.get("provider_id")!=provider.get("id") or contract.get("version")!="2.0.0": findings.append("contract-provider-version-binding")
        if contract.get("backend_contract",{}).get("external_scale_runtime_dependency") is not False: findings.append("contract-external-scale")
        if contract.get("build_compatibility_contract",{}).get("unknown_option_effect")!="DENY_FAIL_CLOSED": findings.append("build-fail-closed-contract")
        if contract.get("runtime_compatibility_contract",{}).get("execution_authorized") is not False: findings.append("runtime-map-authority")
        ac=contract.get("application_access_contract",{})
        if ac.get("consumer_scope")!=SHARED_APPLICATION_SCOPE or ac.get("per_application_allowlist") is not False: findings.append("contract-application-scope")
        if ac.get("application_may_authorize_execution") is not False or ac.get("hrb_lease_required_before_execution") is not True: findings.append("contract-hrb-authority")

        if intent.get("project_id")!=provider.get("id") or intent.get("approved_plan")!=PLAN: findings.append("intent-plan-provider-binding")
        if reuse.get("pending_or_unmerged_donors_consumed") is not False: findings.append("pending-donor-consumed")
        if reuse.get("donor_review")!="REVIEWED_MATCH" or reuse.get("donor_usage_edges_created")!=2: findings.append("donor-reuse-review")
        adopted={x.get("donor_id"):x for x in reuse.get("adopted_donors",[]) if isinstance(x,dict)}
        for did in EXPECTED_USAGE.values():
            if did not in adopted or adopted[did].get("decision")!="EXPLICITLY_APPROVED" or adopted[did].get("mode")!="APPROVED_CAPABILITY_PATTERN": findings.append(f"donor-adoption:{did}")
        usage={x.get("id"):x for x in links.get("donor_usage_records",[]) if isinstance(x,dict)}
        for uid,did in EXPECTED_USAGE.items():
            if uid not in usage or usage[uid].get("donor_id")!=did or usage[uid].get("code_imported") is not False or usage[uid].get("runtime_dependency") is not False: findings.append(f"donor-usage-edge:{uid}")
        for rel in DONOR_DECISIONS:
            d=loadj(root,rel)
            if d.get("status")!="APPROVED" or d.get("explicit_user_approval") is not True or d.get("donor_id") not in EXPECTED_USAGE.values(): findings.append(f"donor-decision:{rel}")

        if approval.get("status")!="APPROVED" or approval.get("explicit_user_approval") is not True: findings.append("plan-approval")
        if approval.get("approved_plan")!=PLAN or approval.get("approved_plan_sha256")!=_sha256(root/PLAN): findings.append("plan-digest-binding")
        if impact.get("physical_current_host_pass_claimed") is not False or impact.get("physical_requalification_required") is not True: findings.append("current-host-physical-state")
        if conformance.get("physical_pass_claimed") is not False or conformance.get("status")!="PENDING_FRESH_PHYSICAL_CURRENT_HOST_REQUALIFICATION": findings.append("conformance-physical-state")
        if policy.get("shared_placement_policy",{}).get("strongly_cuda_oriented_function_core")!="SHARED_LAYER_ONLY": findings.append("cuda-shared-policy")

        if gate_record.get("enforcement_id")!=GATESET_ID or gate_record.get("entrypoint")!="src/fa3_cuda_compat_gate.py::gate": findings.append("gate-record")
        if GATESET_ID not in gate_registry.get("mandatory_reference_gates",[]): findings.append("gate-registry-membership")
        if GATESET_ID not in enforcement.get("mandatory_reference_gates",[]): findings.append("enforcement-membership")
        if gate_registry.get("mandatory_reference_gates",[])!=enforcement.get("mandatory_reference_gates",[]): findings.append("gate-registry-policy-mirror")

    source="""
__global__ void saxpy(float *out, const float *x, float a, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) out[i] = a * x[i] + out[i];
}
"""
    amd=translate_cuda_kernel_source(source,target_vendor="AMD")
    intel_sycl=translate_cuda_kernel_source(source,target_vendor="INTEL",target_backend="sycl")
    intel_opencl=translate_cuda_kernel_source(source,target_vendor="INTEL",target_backend="opencl")
    negative=analyze_cuda_source(source+"\nvoid run(float *p) { saxpy<<<1,32>>>(p,p,1.0f,32); }",target_vendor="AMD")
    bad_build=make_build_plan(sources=["kernel.cu"],nvcc_args=["--invented-cuda-option"],target_vendor="AMD",target_backend="hip")
    amd_runtime=runtime_api_support(["cudaMalloc","cudaFree","cudaMemcpy"],target_vendor="AMD",target_backend="hip")
    intel_runtime=runtime_api_support(["cudaMalloc","cudaFree","cudaMemcpy"],target_vendor="INTEL",target_backend="sycl")

    if amd.get("result")!="PASS" or amd.get("compatibility_result")!="FULL_EQUIVALENCE" or amd.get("execution_authorized") is not False: findings.append("amd-v2-translation-regression")
    if intel_sycl.get("result")!="PASS" or intel_sycl.get("compatibility_result")!="FUNCTIONALLY_REDUCED": findings.append("intel-sycl-v2-regression")
    if intel_opencl.get("result")!="PASS" or intel_opencl.get("compatibility_result")!="FUNCTIONALLY_REDUCED": findings.append("intel-opencl-v2-regression")
    if negative.get("supported") is not False or negative.get("compatibility_result")!="UNAVAILABLE": findings.append("unsupported-cuda-fail-closed-regression")
    if bad_build.get("result")!="DENY" or bad_build.get("silent_option_drop") is not False: findings.append("nvcc-option-fail-closed-regression")
    if amd_runtime.get("classification")!="FULL_EQUIVALENCE" or intel_runtime.get("classification")!="FUNCTIONALLY_REDUCED": findings.append("runtime-map-classification-regression")

    report={
        "schema":"fa3.cuda-compat-native-gate-report.v2","gate_id":GATESET_ID,"gate_record_id":GATE_RECORD_ID,
        "provider_id":"FA3-PROVIDER-CFA3-NATIVE-CUDA-COMPAT-001","result":"PASS" if not findings else "FAIL","findings":findings,
        "capability_count":CAPABILITY_COUNT,"new_capabilities":0,"new_architectural_authorities":0,
        "external_scale_runtime_dependency":False,"shared_application_scope":SHARED_APPLICATION_SCOPE,
        "compatibility_result_enum":["FULL_EQUIVALENCE","FUNCTIONALLY_REDUCED","UNAVAILABLE"],
        "runtime_promotion_claim":False,"physical_current_host_pass_claimed":False,"physical_requalification_required":True,
    }
    out=root/"reports/cuda-compat-native-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); args=parser.parse_args()
    report=gate(Path(args.root)); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
