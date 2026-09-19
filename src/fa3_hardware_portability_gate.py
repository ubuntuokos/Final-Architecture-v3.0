#!/usr/bin/env python3
from __future__ import annotations
from fa3_release_baseline import module_active_capability_count

import argparse
import json
import re
from pathlib import Path
from typing import Any

PROFILE = "canonical/profiles/FA3-HARDWARE-BASELINE-001.json"
CONTRACT = "canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json"
DECISION = "canonical/decisions/FA3-DEC-HARDWARE-PORTABILITY-2026-09-03.json"
ENFORCEMENT = "canonical/hardware-portability-enforcement.json"
GATE_RECORD = "canonical/FA3-GATE-HARDWARE-PORTABILITY-001.json"
HW_PROFILE = "canonical/profiles/FA3-HW-001.json"
HW_CONTRACT = "canonical/contracts/FA3-HW-CONTRACTS-001.json"
MGPU_PROFILE = "canonical/profiles/FA3-HW-MGPU-001.json"
HRB_PROFILE = "canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json"
HRB_CONTRACT = "canonical/contracts/FA3-HOST-RESOURCE-BROKER-CONTRACTS-001.json"
EVIDENCE_REGISTRY = "evidence/evidence-registry.json"
REFERENCE_EVIDENCE = "evidence/reference/hardware-portability-ci-2026-09-03.json"
AUDIT_EVIDENCE = "evidence/reference/hardware-portability-repository-audit-2026-09-03.json"
ENFORCEMENT_POLICY = "canonical/enforcement-policy.json"
DESKTOP_BASE = "canonical/FA3-DESKTOP-BASE-001.json"
DESKTOP_PROFILE = "canonical/profiles/FA3-DESKTOP-001.json"
RESOURCE_ADMISSION_CONTRACT = "canonical/FA3-RESOURCE-ADMISSION-CONTRACTS-001.json"
EVIDENCE_SCOPE_POLICY = "canonical/FA3-EVIDENCE-SCOPE-001.json"
RUNTIME_HARDENING_CONTRACT = "canonical/contracts/FA3-RUNTIME-HARDENING-CONTRACTS-001.json"
RUNTIME_HARDENING_CURRENT_HOST_ENFORCEMENT = "canonical/runtime-hardening-current-host-enforcement.json"
RELEASE_PROJECTION = "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"

GATE_ID = "FA3-HARDWARE-PORTABILITY-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-HARDWARE-PORTABILITY-001"
DECISION_ID = "FA3-DEC-HARDWARE-PORTABILITY-2026-09-03"
CAPABILITY_COUNT = module_active_capability_count(__file__)
CUDA_COMPUTE_CAPABILITY_MIN = 8.6
CAPABILITY_BINDINGS = (
    "CAP-001", "CAP-006", "CAP-062", "CAP-063", "CAP-065",
    "CAP-130", "CAP-137", "CAP-142", "CAP-143",
)

RUNTIME_PREFIXES = ("src/", "bin/", "deployment/", ".github/workflows/", "apps/")
NON_NORMATIVE_PREFIXES = (
    "fa3-current-host/", "evidence/", "canonical/references/",
    "tests/", "examples/",
)
SKIP_TOP_LEVEL = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache"}
TEXT_SUFFIXES = {
    ".json", ".py", ".md", ".sh", ".yml", ".yaml", ".csv", ".toml", ".ini",
    ".conf", ".service", ".socket", ".target", ".container", ".caddy", ".sql",
    ".txt", ".env", ".rules", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".qml",
}

HARD_RUNTIME_PATTERNS = (
    ("FIXED_CUDA_VISIBLE_DEVICES_LIST", re.compile(r"CUDA_VISIBLE_DEVICES[^\n=]{0,40}=\s*[\"']?\d+(?:\s*,\s*\d+)*[\"']?")),
    ("FIXED_CPUAFFINITY", re.compile(r"(?mi)^\s*CPUAffinity\s*=\s*\d")),
    ("FIXED_NUMAMASK", re.compile(r"(?mi)^\s*NUMAMask\s*=\s*\d")),
    ("FIXED_NUMA_NODE_ASSIGNMENT", re.compile(r"\b(?:NUMA_NODE|numa_node|NUMANode)\s*[=:]\s*[\"']?\d+\b")),
    ("FIXED_TASKSET_CPU_LIST", re.compile(r"\btaskset\s+-c\s+\d", re.I)),
    ("FIXED_NUMACTL_BINDING", re.compile(r"\bnumactl\s+--(?:physcpubind|cpunodebind|membind)(?:=|\s+)\d", re.I)),
    ("FIXED_NVIDIA_SMI_ORDINAL", re.compile(r"\bnvidia-smi[^\n]{0,160}?\s-i\s+\d+\b", re.I)),
    ("FIXED_GPU_COUNT_COMPARISON", re.compile(r"\b(?:gpu_count|num_gpus|device_count)\s*(?:==|!=)\s*[1-9]\d*\b", re.I)),
)

CONCRETE_HOST_PATTERNS = (
    ("CPU_MODEL_XEON_E5_SKU", re.compile(r"\b(?:Intel\s+)?(?:Xeon(?:\s+CPU)?\s+)?E5[- ]\d{4}(?:\s+v\d)?\b", re.I)),
    ("CPU_MODEL_EPYC_SKU", re.compile(r"\b(?:AMD\s+)?EPYC\s+\d{4}[A-Z]?\b", re.I)),
    ("GPU_SKU_RTX", re.compile(r"\b(?:(?:GeForce|Quadro)\s+)?RTX\s*(?:A\s*)?\d{3,4}(?:\s*(?:Ti|SUPER))?\b", re.I)),
    ("HOST_MODEL_PRECISION", re.compile(r"\b(?:Dell\s+)?Precision(?:\s+Tower)?\s+\d{4}\b", re.I)),
    ("REFERENCE_CORE_THREAD_TOPOLOGY", re.compile(r"\b\d{1,3}C\s*/\s*\d{1,3}T\b", re.I)),
    ("LITERAL_PCI_BDF", re.compile(r"\b(?:[0-9A-F]{4,8}:)?[0-9A-F]{2}:[0-9A-F]{2}\.[0-7]\b", re.I)),
)

REFERENCE_MARKERS = (
    "reference", "fixture", "evidence", "historical", "supersed",
    "non-normative", "not canonical", "forbidden", "example",
)


def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def check(name: str, value: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if value else "FAIL", "detail": detail}


def portable_hardware_floor_valid(
    *,
    cpu_packages: int,
    physical_cores_per_qualifying_cpu: int,
    gpu_count: int,
    gpu_compute_capability: float,
    gpu_vendor: str = "NVIDIA",
) -> bool:
    """Global hardware floor only. VRAM/SKU/model are deliberately not inputs."""
    return (
        isinstance(cpu_packages, int)
        and isinstance(physical_cores_per_qualifying_cpu, int)
        and isinstance(gpu_count, int)
        and isinstance(gpu_compute_capability, (int, float))
        and not isinstance(gpu_compute_capability, bool)
        and isinstance(gpu_vendor, str)
        and cpu_packages >= 1
        and physical_cores_per_qualifying_cpu >= 8
        and gpu_count >= 1
        and gpu_vendor.strip().upper() == "NVIDIA"
        and float(gpu_compute_capability) >= CUDA_COMPUTE_CAPABILITY_MIN
    )


def _is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.parent.name == "bin" or path.name.startswith("fa3-")


def _context(text: str, start: int, end: int, radius: int = 240) -> str:
    return text[max(0, start - radius): min(len(text), end + radius)].lower()


def scan_repository(root: Path) -> dict[str, Any]:
    blocking: list[dict[str, Any]] = []
    non_normative: list[dict[str, Any]] = []
    scanned = 0
    runtime_scanned = 0
    unreadable = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        parts = Path(rel).parts
        if not parts or parts[0] in SKIP_TOP_LEVEL or "__pycache__" in parts or not _is_text_candidate(path):
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            data = path.read_bytes()
            if b"\x00" in data:
                continue
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            unreadable += 1
            continue

        scanned += 1
        runtime = rel.startswith(RUNTIME_PREFIXES)
        if runtime:
            runtime_scanned += 1
        if rel == "src/fa3_hardware_portability_gate.py":
            # Do not let this scanner's own regex literals become findings.
            continue
        explicitly_non_normative = rel.startswith(NON_NORMATIVE_PREFIXES)

        for code, pattern in HARD_RUNTIME_PATTERNS:
            for match in pattern.finditer(text):
                item = {"path": rel, "kind": code, "offset": match.start(), "sample": match.group(0)[:120]}
                if runtime:
                    blocking.append(item)
                else:
                    non_normative.append({**item, "classification": "NON_RUNTIME_TEXT"})

        for code, pattern in CONCRETE_HOST_PATTERNS:
            for match in pattern.finditer(text):
                ctx = _context(text, match.start(), match.end())
                marked_reference = explicitly_non_normative or any(marker in ctx for marker in REFERENCE_MARKERS)
                item = {"path": rel, "kind": code, "offset": match.start(), "sample": match.group(0)[:120]}
                if runtime and not marked_reference:
                    blocking.append(item)
                else:
                    non_normative.append({
                        **item,
                        "classification": "REFERENCE_OR_EVIDENCE_CONTEXT" if marked_reference else "NON_RUNTIME_TEXT",
                    })

    return {
        "result": "PASS" if not blocking else "FAIL",
        "scanned_text_files": scanned,
        "runtime_surface_files_scanned": runtime_scanned,
        "unreadable_text_candidates": unreadable,
        "blocking_hardcoded_production_assumptions": len(blocking),
        "blocking_matches": blocking,
        "non_normative_hardware_mentions": len(non_normative),
        "non_normative_sample": non_normative[:100],
    }


def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    profile = loadj(root, PROFILE)
    contract = loadj(root, CONTRACT)
    decision = loadj(root, DECISION)
    enforcement = loadj(root, ENFORCEMENT)
    gate_record = loadj(root, GATE_RECORD)
    hw_profile = loadj(root, HW_PROFILE)
    hw_contract = loadj(root, HW_CONTRACT)
    mgpu_profile = loadj(root, MGPU_PROFILE)
    hrb_profile = loadj(root, HRB_PROFILE)
    hrb_contract = loadj(root, HRB_CONTRACT)
    evidence_registry = loadj(root, EVIDENCE_REGISTRY)
    reference_evidence = loadj(root, REFERENCE_EVIDENCE)
    audit_evidence = loadj(root, AUDIT_EVIDENCE)
    enforcement_policy = loadj(root, ENFORCEMENT_POLICY)
    desktop_base = loadj(root, DESKTOP_BASE)
    desktop_profile = loadj(root, DESKTOP_PROFILE)
    resource_admission = loadj(root, RESOURCE_ADMISSION_CONTRACT)
    evidence_scope = loadj(root, EVIDENCE_SCOPE_POLICY)
    runtime_hardening = loadj(root, RUNTIME_HARDENING_CONTRACT)
    runtime_hardening_current_host = loadj(root, RUNTIME_HARDENING_CURRENT_HOST_ENFORCEMENT)
    release_projection = loadj(root, RELEASE_PROJECTION)

    pmin = profile.get("portable_minimum", {})
    cpu = pmin.get("cpu", {})
    gpu = pmin.get("gpu", {})
    discovery = contract.get("discovery_semantics", {})
    envelope = contract.get("portable_minimum_envelope", {})
    pin_text = json.dumps(profile, sort_keys=True)
    bound_records = [item for item in evidence_registry.get("records", []) if item.get("subject_id") in CAPABILITY_BINDINGS]

    checks = [
        check("profile-parent", profile.get("relationship", {}).get("parent") == "FA3-HW-001" and profile.get("canonical_root") is False, "portability baseline is a non-root subprofile of FA3-HW-001"),
        check("capability-count-stable", profile.get("capability_count") == contract.get("capability_count") == decision.get("capability_count_after") == CAPABILITY_COUNT, "canonical capability count unchanged"),
        check("no-new-authority", profile.get("new_architectural_authority") is False and decision.get("new_architectural_authority") is False, "no new architectural authority"),
        check("cpu-floor", cpu.get("package_count_min") == 1 and cpu.get("physical_cores_per_qualifying_cpu_min") == 8, "CPU floor is 1 package and >=8 physical cores per qualifying CPU"),
        check("cpu-unbounded-cardinality", cpu.get("package_count_max") == "UNBOUNDED_BY_FA3" and cpu.get("fixed_socket_count") == "FORBIDDEN", "CPU count is dynamic 1..N"),
        check("gpu-floor", gpu.get("qualifying_device_count_min") == 1 and gpu.get("vendor") == "NVIDIA" and float(gpu.get("cuda_compute_capability_min", 0)) == CUDA_COMPUTE_CAPABILITY_MIN, "GPU floor is NVIDIA CUDA compute capability >=8.6"),
        check("gpu-series-nonauthoritative", gpu.get("sku_series_admission_authority") is False and envelope.get("sku_series_is_admission_authority") is False, "SKU/marketing series is not admission authority"),
        check("gpu-unbounded-cardinality", gpu.get("qualifying_device_count_max") == "UNBOUNDED_BY_FA3" and gpu.get("fixed_device_count") == "FORBIDDEN", "GPU count is dynamic 1..N"),
        check("contract-gpu-floor", envelope.get("gpu_vendor") == "NVIDIA" and float(envelope.get("cuda_compute_capability_min", 0)) == CUDA_COMPUTE_CAPABILITY_MIN, "discovery contract uses the same capability floor"),
        check("no-cpu-model-pin", cpu.get("vendor_pin") == cpu.get("model_pin") == "FORBIDDEN", "CPU vendor/model pins are forbidden"),
        check("no-gpu-sku-pin", all(str(gpu.get(k, "")).startswith("FORBIDDEN") for k in ("product_line_pin", "exact_sku_pin", "vram_size_pin", "sm_name_pin")), "GPU product line/SKU/VRAM/SM-name global pins are forbidden"),
        check("dynamic-discovery", discovery.get("enumeration") == "DYNAMIC_1_TO_N" and discovery.get("admission_revalidation") is True and discovery.get("topology_change_revalidation") is True, "live discovery and revalidation are mandatory"),
        check("stable-accelerator-identity", discovery.get("ephemeral_runtime_indices_are_identity") is False and set(discovery.get("stable_accelerator_identity_when_available", [])) == {"DEVICE_UUID", "PCI_BDF"}, "CUDA ordinal is not canonical identity"),
        check("minimum-positive", portable_hardware_floor_valid(cpu_packages=1, physical_cores_per_qualifying_cpu=8, gpu_count=1, gpu_compute_capability=8.6), "Ampere-class CC 8.6 minimum host is admitted independent of SKU naming"),
        check("newer-multigpu-positive", portable_hardware_floor_valid(cpu_packages=4, physical_cores_per_qualifying_cpu=32, gpu_count=8, gpu_compute_capability=12.0), "larger/newer NVIDIA host is admitted"),
        check("under-core-negative", not portable_hardware_floor_valid(cpu_packages=1, physical_cores_per_qualifying_cpu=7, gpu_count=1, gpu_compute_capability=8.6), "under-core host is rejected"),
        check("no-gpu-negative", not portable_hardware_floor_valid(cpu_packages=1, physical_cores_per_qualifying_cpu=8, gpu_count=0, gpu_compute_capability=12.0), "host without qualifying GPU is rejected"),
        check("old-capability-negative", not portable_hardware_floor_valid(cpu_packages=1, physical_cores_per_qualifying_cpu=8, gpu_count=1, gpu_compute_capability=8.0), "GPU below CUDA compute capability 8.6 is rejected"),
        check("wrong-vendor-negative", not portable_hardware_floor_valid(cpu_packages=1, physical_cores_per_qualifying_cpu=8, gpu_count=1, gpu_compute_capability=12.0, gpu_vendor="OTHER"), "non-NVIDIA device does not satisfy this baseline"),
        check("root-hw-linked", "FA3-HARDWARE-DISCOVERY-CONTRACTS-001" in hw_profile.get("contracts", []) and "FA3-HARDWARE-BASELINE-001" in hw_profile.get("mandatory_subprofiles", []), "FA3-HW root binds portability baseline and discovery contract"),
        check("hw-contract-linked", "FA3-HARDWARE-DISCOVERY-CONTRACTS-001" in hw_contract.get("contract_family_bindings", []), "hardware contract family binds discovery contract"),
        check("mgpu-dynamic", "ACCELERATOR_CARDINALITY_DYNAMIC_1_TO_N" in mgpu_profile.get("invariants", []) and "FIXED_GPU_COUNT_OR_RUNTIME_ORDINAL_FORBIDDEN" in mgpu_profile.get("invariants", []), "multi-GPU profile remains dynamic"),
        check("hrb-linked", "FA3-HARDWARE-DISCOVERY-CONTRACTS-001" in hrb_profile.get("contracts", []) and hrb_profile.get("hardware_portability_baseline_profile") == "FA3-HARDWARE-BASELINE-001", "HRB consumes discovery contract without losing authority"),
        check("hrb-contract-dynamic", "DYNAMIC_CPU_AND_GPU_CARDINALITY_DISCOVERY_REQUIRED" in hrb_contract.get("invariants", []) and "FIXED_GPU_COUNT_CPU_LIST_NUMA_NODE_OR_CUDA_ORDINAL_IS_NOT_PORTABLE_PLACEMENT" in hrb_contract.get("invariants", []), "HRB contract forbids fixed topology assumptions"),
        check("enforcement-complete", enforcement.get("fail_closed") is True and enforcement.get("mandatory_rule_count") == 31 and len(enforcement.get("rules", [])) == 31, "31 mandatory P0 primary hardware-audit rules remain fail-closed"),
        check("capability-rule-enforced", any(r.get("invariant") == "GPU_MINIMUM_NVIDIA_CUDA_COMPUTE_CAPABILITY_8_6_OR_NEWER" for r in enforcement.get("rules", [])), "capability-based GPU floor is an executable mandatory rule"),
        check("evidence-bindings", len(bound_records) == len(CAPABILITY_BINDINGS) and all(DECISION_ID in item.get("source_decision_ids", []) and REFERENCE_EVIDENCE in item.get("evidence_artifacts", []) for item in bound_records), "hardware capability evidence remains bound"),
        check("reference-not-promotion", reference_evidence.get("status") == "PASS" and reference_evidence.get("current_host_runtime_promotion_claim") is False and audit_evidence.get("current_host_runtime_promotion_claim") is False, "reference/audit PASS cannot promote current-host runtime"),
        check("decision-supersedes-fixed-interpretations", decision.get("supersedence", {}).get("scope") == "CANONICAL_INTERPRETATION_ONLY" and decision.get("supersedence", {}).get("historical_and_current_host_evidence") == "PRESERVED_AS_EVIDENCE_NOT_PORTABLE_DEFAULT", "fixed canonical interpretations are superseded while evidence is preserved"),
        check("no-accidental-exact-pin-in-profile", "rtx_series_floor" not in pin_text.lower() and "E5-2696" not in pin_text and "T7910" not in pin_text, "portable profile contains no current-host SKU/model identity"),
        check("gate-record", gate_record.get("gateset_id") == GATE_ID and gate_record.get("id") == EXECUTABLE_GATE_ID and gate_record.get("fail_closed") is True and gate_record.get("primary_audit_precondition") is True, "canonical executable gate record is bound as the primary audit precondition"),
        check("primary-enforcement-order", enforcement_policy.get("mandatory_reference_gates", [None])[0] == GATE_ID and enforcement_policy.get("hardware_audit_primary_gate") is True and enforcement_policy.get("hardware_audit_primary_gate_order") == 1, "hardware audit is the first mandatory cross-cutting enforcement gate"),
        check("global-policy-rules-aligned", set(enforcement_policy.get("hardware_portability_mandatory_p0_rules", [])) == set(enforcement.get("p0_invariants", [])), "global enforcement policy and hardware audit expose the same mandatory P0 invariant set"),
        check("desktop-wayland-x11-agnostic", desktop_base.get("policy", {}).get("wayland") == "PREFERRED" and desktop_base.get("policy", {}).get("x11") == "SUPPORTED_COMPATIBILITY" and desktop_base.get("policy", {}).get("plasma_is_reference_not_core_dependency") is True and desktop_profile.get("runtime", {}).get("display_protocol") == "WAYLAND_PRIMARY" and "X11" in desktop_profile.get("runtime", {}).get("display_protocol_compatibility", []) and desktop_profile.get("runtime", {}).get("display_protocol_exclusive") is False and desktop_profile.get("runtime", {}).get("desktop_environment_binding") == "DESKTOP_AGNOSTIC_XDG_DBUS_PORTAL_BASELINE", "Wayland remains preferred while X11 compatibility and desktop-agnostic core semantics are mandatory"),
        check("hrb-resource-admission-authority", resource_admission.get("authoritative_admission_authority") == "FA3-AUTH-HOST-RESOURCE-BROKER-001" and resource_admission.get("required_input_semantics", {}).get("HRB_ADMISSION_AUTHORIZATION") == "REQUIRED_FOR_ALL_WORKLOADS_AND_MUST_ORIGINATE_FROM_FA3_AUTH_HOST_RESOURCE_BROKER_001" and "HRB_REMAINS_EXCLUSIVE_ADMISSION_PLACEMENT_RESERVATION_LEASE_AUTHORITY" in resource_admission.get("invariants", []), "all workload admission remains HRB-authorized and accelerator execution remains lease-bound"),
        check("static-vs-current-host-evidence", evidence_scope.get("evidence_classes", {}).get("DESIGN_OR_REFERENCE", {}).get("may_prove_current_host_runtime") is False and evidence_scope.get("evidence_classes", {}).get("POSITIVE_CURRENT_HOST", {}).get("requires_real_current_host_execution") is True and evidence_scope.get("authority_boundaries", {}).get("reference_ci_cannot_promote_runtime") is True, "static/reference PASS cannot become physical current-host evidence"),
        check("pcie-proof-semantics", runtime_hardening.get("pcie_copy_budget", {}).get("role") == "SUPPORTING_COPY_BUDGET_NOT_ZERO_COPY_PROOF" and runtime_hardening.get("frame_copy_telemetry", {}).get("host_to_device_frame_copy_count_max") == 0 and runtime_hardening.get("frame_copy_telemetry", {}).get("device_to_host_frame_copy_count_max") == 0 and runtime_hardening.get("frame_copy_telemetry", {}).get("host_frame_round_trips_max") == 0 and runtime_hardening.get("frame_copy_telemetry", {}).get("full_pipeline_true_zero_copy_claim_requires_separate_proof") is True and runtime_hardening_current_host.get("current_host_status") == "PENDING_REAL_EXECUTION" and runtime_hardening_current_host.get("rules", {}).get("global_promotion_effect") == "NONE", "PCIe budget is supporting telemetry only; zero-host-round-trip requires copy trace and real current-host execution"),
        check("release-projection-primary-audit", release_projection.get("hardware_portability_reconciliation", {}).get("primary_mandatory_gate") is True and release_projection.get("hardware_portability_reconciliation", {}).get("primary_gate_order") == 1 and release_projection.get("hardware_portability_reconciliation", {}).get("static_reference_pass_is_current_host_pass") is False, "release projection carries primary hardware-audit and evidence-scope semantics"),
    ]

    audit = scan_repository(root)
    checks.append(check("repository-wide-hardcoded-hardware-audit", audit["result"] == "PASS", f"repository text audit blockers={audit['blocking_hardcoded_production_assumptions']}"))

    passed = all(item["status"] == "PASS" for item in checks)
    return {
        "schema": "fa3.hardware-portability-gate-report.v1",
        "gate_id": GATE_ID,
        "executable_gate_id": EXECUTABLE_GATE_ID,
        "profile_id": profile.get("id"),
        "contract_id": contract.get("id"),
        "decision_id": decision.get("id"),
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if passed else "FAIL",
        "current_host_runtime_promotion_claim": False,
        "audit_role": "FIRST_MANDATORY_CROSS_CUTTING_ARCHITECTURE_GATE",
        "gpu_floor": {"vendor": "NVIDIA", "cuda_compute_capability_min": CUDA_COMPUTE_CAPABILITY_MIN, "sku_series_authority": False},
        "checks": checks,
        "summary": {"passed": sum(item["status"] == "PASS" for item in checks), "total": len(checks)},
        "repository_audit": audit,
    }


def gate(root: Path) -> dict[str, Any]:
    report = evaluate(root)
    out = root / "reports/hardware-portability-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 hardware portability and hardcoded-assumption regression gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
