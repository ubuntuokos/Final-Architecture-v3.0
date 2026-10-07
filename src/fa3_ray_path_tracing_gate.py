#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

from fa3_ray_path_tracing_fabric import RayTracingBackendDescriptor, cpu_software_reference_descriptor, resolve_ray_path_tracing

PROFILE_ID = "FA3-SHARED-RAY-PATH-TRACING-001"
CONTRACT_ID = "FA3-SHARED-RAY-PATH-TRACING-CONTRACTS-001"
GATESET_ID = "FA3-RAY-PATH-TRACING-GATESET-001"
ENGINE_ID = "FA3-ENGINE-FA3-RAY-PATH-TRACING-001"
CAPS = module_active_capability_count(__file__)
USAGE = {"FA3-USAGE-PROJECT10-OPENRT-RAY-PATH-TRACING-001":"FA3-DONOR-PROJECT-10-OPENRT-001","FA3-USAGE-GPUOPEN-GPURT-RAY-PATH-TRACING-001":"FA3-DONOR-GPUOPEN-GPURT-001","FA3-USAGE-GPUOPEN-RRA-RAY-PATH-TRACING-001":"FA3-DONOR-GPUOPEN-RRA-001","FA3-USAGE-INTEL-L0RT-RAY-PATH-TRACING-001":"FA3-DONOR-INTEL-LEVEL-ZERO-RAYTRACING-SUPPORT-001","FA3-USAGE-INTEL-RTPTRF-RAY-PATH-TRACING-001":"FA3-DONOR-INTEL-REALTIME-PATH-TRACING-RESEARCH-FRAMEWORK-001","FA3-USAGE-RUST-RAYTRACER-CPU-PATH-001":"FA3-DONOR-ANCIENTKINGG-RUST-RAYTRACER-001","FA3-USAGE-NVIDIA-RTX-RAY-PATH-TRACING-001":"FA3-DONOR-NVIDIA-RTX-ORG-001"}


def loadj(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {rel}")
    return value


def gate(root: Path) -> dict[str, Any]:
    root = Path(root)
    findings: list[str] = []
    profile = loadj(root, "canonical/profiles/FA3-SHARED-RAY-PATH-TRACING-001.json")
    contract = loadj(root, "canonical/contracts/FA3-SHARED-RAY-PATH-TRACING-CONTRACTS-001.json")
    decision = loadj(root, "canonical/decisions/FA3-DEC-SHARED-RAY-PATH-TRACING-2026-10-05.json")
    reuse = loadj(root, "canonical/assessments/FA3-SHARED-RAY-PATH-TRACING-REUSE-ASSESSMENT-2026-10-05.json")
    links = loadj(root, "canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
    engines = loadj(root, "canonical/FA3-ENGINE-REGISTRY-001.json")
    gate_record = loadj(root, "canonical/FA3-GATE-RAY-PATH-TRACING-001.json")
    gate_registry = loadj(root, "canonical/FA3-GATE-REGISTRY-001.json")
    enforcement = loadj(root, "canonical/enforcement-policy.json")
    impact = loadj(root, "canonical/current-host-impact/FA3-CH-IMPACT-SHARED-RAY-PATH-TRACING-20261005.json")

    if profile.get("id") != PROFILE_ID or profile.get("capability_count") != CAPS:
        findings.append("profile-baseline")
    if profile.get("new_capability") is not False or profile.get("new_architectural_authority") is not False:
        findings.append("profile-authority-capability-delta")
    if set(profile.get("capability_bindings", [])) != {"CAP-025", "CAP-083", "CAP-127", "CAP-161", "CAP-163"}:
        findings.append("profile-capability-binding")
    bp = profile.get("backend_policy", {})
    if bp.get("cpu_software_path_required") is not True or bp.get("automatic_backend_selection") is not False or bp.get("silent_fallback") is not False:
        findings.append("backend-policy")

    if contract.get("parent_profile") != PROFILE_ID or contract.get("capability_count") != CAPS:
        findings.append("contract-binding")
    ep = contract.get("execution_policy", {})
    if ep.get("resolver_authorizes_execution") is not False or ep.get("silent_fallback") is not False or ep.get("automatic_backend_selection") is not False:
        findings.append("execution-authority")
    if ep.get("resource_lease_authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001":
        findings.append("hrb-authority")

    if decision.get("status") != "OWNER_APPROVED_MATERIALIZATION" or decision.get("invariants", {}).get("capability_baseline") != CAPS:
        findings.append("owner-decision")
    if reuse.get("result") != "PASS" or reuse.get("pending_or_unmerged_donors_consumed") is not False:
        findings.append("reuse")
    if reuse.get("donor_usage_edges_created") != 7:
        findings.append("usage-edge-count")

    usage = {x.get("id"): x for x in links.get("donor_usage_records", []) if isinstance(x, dict)}
    for uid, did in USAGE.items():
        row = usage.get(uid)
        if not row or row.get("donor_id") != did or row.get("code_imported") is not False or row.get("runtime_dependency") is not False:
            findings.append(f"donor-usage:{uid}")

    shared = {x.get("id"): x for x in links.get("shared_capabilities", []) if isinstance(x, dict)}
    if PROFILE_ID not in shared or shared[PROFILE_ID].get("authority") is not False:
        findings.append("shared-capability-index")

    engine = next((x for x in engines.get("engine_records", []) if x.get("engine_id") == ENGINE_ID), None)
    if not engine or "CAP-127" not in engine.get("capability_projection", []) or engine.get("automatic_backend_selection") is not False:
        findings.append("engine-registry")
    if not {"RAY_TRACING", "PATH_TRACING"}.issubset(set(engines.get("engine_classes", []))):
        findings.append("engine-class-registry")

    if gate_record.get("enforcement_id") != GATESET_ID or gate_record.get("entrypoint") != "src/fa3_ray_path_tracing_gate.py::gate":
        findings.append("gate-record")
    if GATESET_ID not in gate_registry.get("mandatory_reference_gates", []):
        findings.append("gate-registry")
    if GATESET_ID not in enforcement.get("mandatory_reference_gates", []):
        findings.append("enforcement-registry")
    if gate_registry.get("mandatory_reference_gates", []) != enforcement.get("mandatory_reference_gates", []):
        findings.append("gate-policy-mirror")
    if enforcement.get("ray_path_tracing_profile_id") != PROFILE_ID or enforcement.get("ray_path_tracing_contract_id") != CONTRACT_ID:
        findings.append("enforcement-binding")

    if impact.get("status") != "NO_RUNTIME_IMPACT" or impact.get("physical_requalification_required") is not False:
        findings.append("current-host-impact")
    if impact.get("physical_current_host_pass_claimed") is not False or impact.get("historical_evidence_reused") is not False:
        findings.append("current-host-proof-claim")

    cpu_blocked = resolve_ray_path_tracing(
        [cpu_software_reference_descriptor()],
        application_id="test.app", workload_id="w1", trace_mode="RAY_TRACING",
    )
    if cpu_blocked.get("result") != "UNAVAILABLE" or not cpu_blocked.get("blocked_candidates"):
        findings.append("cpu-admission-fail-closed")
    cpu_ready = resolve_ray_path_tracing(
        [cpu_software_reference_descriptor(provider_admitted=True, runtime_admitted=True)],
        application_id="test.app", workload_id="w2", trace_mode="PATH_TRACING", hardware_traversal="DISABLED",
    )
    if cpu_ready.get("result") != "CANDIDATE_AVAILABLE" or cpu_ready.get("execution_authorized") is not False:
        findings.append("cpu-path-regression")
    gpu = RayTracingBackendDescriptor(
        backend_id="gpu0", vendor="AMD", api="VULKAN_RT", available=True, device_bound=True,
        supported_modes=("RAY_TRACING", "PATH_TRACING"), hardware_traversal=True, compatibility_class="PORTABLE",
        provider_admitted=True, runtime_admitted=True,
    )
    explicit = resolve_ray_path_tracing(
        [gpu], application_id="test.app", workload_id="w3", trace_mode="RAY_TRACING", requested_backend_id="missing",
    )
    if explicit.get("result") != "UNAVAILABLE" or explicit.get("reason") != "EXPLICIT_BACKEND_NOT_FOUND":
        findings.append("explicit-backend-fail-closed")

    report = {
        "schema": "fa3.ray-path-tracing-gate-report.v1",
        "gate_id": GATESET_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "capability_count": CAPS,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "runtime_promotion_claim": False,
        "physical_current_host_pass_claimed": False,
    }
    out = root / "reports/ray-path-tracing-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = p.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
