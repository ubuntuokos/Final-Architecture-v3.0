#!/usr/bin/env python3
from __future__ import annotations

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

GATE_ID = "FA3-HARDWARE-PORTABILITY-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-HARDWARE-PORTABILITY-001"
DECISION_ID = "FA3-DEC-HARDWARE-PORTABILITY-2026-09-03"
CAPABILITY_COUNT = 143
CAPABILITY_BINDINGS = (
    "CAP-001", "CAP-006", "CAP-062", "CAP-063", "CAP-065",
    "CAP-130", "CAP-137", "CAP-142", "CAP-143",
)

RUNTIME_PREFIXES = ("src/", "bin/", "deployment/", ".github/workflows/")
NON_NORMATIVE_PREFIXES = (
    "fa3-current-host/", "evidence/", "canonical/references/",
    "tests/", "examples/",
)
SKIP_TOP_LEVEL = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache"}
TEXT_SUFFIXES = {
    ".json", ".py", ".md", ".sh", ".yml", ".yaml", ".csv", ".toml", ".ini",
    ".conf", ".service", ".socket", ".target", ".container", ".caddy", ".sql",
    ".txt", ".env", ".rules",
}

HARD_RUNTIME_PATTERNS = (
    ("FIXED_CUDA_VISIBLE_DEVICES_LIST", re.compile(r"CUDA_VISIBLE_DEVICES[^\\n=]{0,40}=\\s*[\\\"\']?\\d+(?:\\s*,\\s*\\d+)+")),
    ("FIXED_CPUAFFINITY", re.compile(r"(?mi)^\s*CPUAffinity\s*=\s*\d")),
    ("FIXED_NUMAMASK", re.compile(r"(?mi)^\s*NUMAMask\s*=\s*\d")),
    ("FIXED_TASKSET_CPU_LIST", re.compile(r"\btaskset\s+-c\s+\d", re.I)),
    ("FIXED_NUMACTL_BINDING", re.compile(r"\bnumactl\s+--(?:physcpubind|cpunodebind|membind)(?:=|\s+)\d", re.I)),
    ("FIXED_NVIDIA_SMI_ORDINAL", re.compile(r"\bnvidia-smi\s+-i\s+\d", re.I)),
    ("FIXED_GPU_COUNT_COMPARISON", re.compile(r"\b(?:gpu_count|num_gpus|device_count)\s*(?:==|!=)\s*[1-9]\d*\b", re.I)),
)

CONCRETE_HOST_PATTERNS = (
    ("CPU_MODEL_E5_2696", re.compile(r"\bE5[- ]2696(?:\s+v4)?\b", re.I)),
    ("CPU_MODEL_E5_2697", re.compile(r"\bE5[- ]2697(?:\s+v4)?\b", re.I)),
    ("GPU_SKU_RTX3080", re.compile(r"\bRTX\s*3080\b", re.I)),
    ("GPU_SKU_RTX4000", re.compile(r"\b(?:Quadro\s+)?RTX\s*4000\b", re.I)),
    ("HOST_MODEL_T7910", re.compile(r"\b(?:T7910|Precision(?:\s+Tower)?\s+7910)\b", re.I)),
    ("REFERENCE_TOPOLOGY_44C88T", re.compile(r"\b44C\s*/\s*88T\b", re.I)),
    ("REFERENCE_TOPOLOGY_36C72T", re.compile(r"\b36C\s*/\s*72T\b", re.I)),
    ("REFERENCE_PCI_BDF_05", re.compile(r"\b0000:05:00\.0\b", re.I)),
    ("REFERENCE_PCI_BDF_A5", re.compile(r"\b0000:A5:00\.0\b", re.I)),
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
    gpu_rtx_series: int,
) -> bool:
    return (
        isinstance(cpu_packages, int)
        and isinstance(physical_cores_per_qualifying_cpu, int)
        and isinstance(gpu_count, int)
        and isinstance(gpu_rtx_series, int)
        and cpu_packages >= 1
        and physical_cores_per_qualifying_cpu >= 8
        and gpu_count >= 1
        and gpu_rtx_series >= 30
    )


def _is_text_candidate(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return path.parent.name == "bin" or path.name.startswith("fa3-")


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
        if not parts or parts[0] in SKIP_TOP_LEVEL or "__pycache__" in parts:
            continue
        if not _is_text_candidate(path):
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
        policy_or_test_code = rel.startswith("src/") and rel.endswith("_gate.py")\n        current_host_tooling = "current-host" in rel.lower() or "current_host" in rel.lower()\n        explicitly_non_normative = (\n            rel.startswith(NON_NORMATIVE_PREFIXES)\n            or policy_or_test_code\n            or current_host_tooling\n        )\n
        for code, pattern in HARD_RUNTIME_PATTERNS:
            for match in pattern.finditer(text):
                item = {
                    "path": rel,
                    "kind": code,
                    "offset": match.start(),
                    "sample": match.group(0)[:120],
                }
                if runtime:
                    blocking.append(item)
                else:
                    non_normative.append({**item, "classification": "NON_RUNTIME_TEXT"})

        for code, pattern in CONCRETE_HOST_PATTERNS:
            for match in pattern.finditer(text):
                ctx = _context(text, match.start(), match.end())
                marked_reference = explicitly_non_normative or any(marker in ctx for marker in REFERENCE_MARKERS)
                item = {
                    "path": rel,
                    "kind": code,
                    "offset": match.start(),
                    "sample": match.group(0)[:120],
                }
                if runtime and not marked_reference:
                    blocking.append(item)
                else:
                    non_normative.append({
                        **item,
                        "classification": (
                            "REFERENCE_OR_EVIDENCE_CONTEXT"
                            if marked_reference
                            else "NON_RUNTIME_TEXT"
                        ),
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

    pmin = profile.get("portable_minimum", {})
    cpu = pmin.get("cpu", {})
    gpu = pmin.get("gpu", {})
    discovery = contract.get("discovery_semantics", {})
    envelope = contract.get("portable_minimum_envelope", {})
    pin_text = json.dumps(profile, sort_keys=True)
    bound_records = [
        item for item in evidence_registry.get("records", [])
        if item.get("subject_id") in CAPABILITY_BINDINGS
    ]

    checks = [
        check("profile-parent", profile.get("relationship", {}).get("parent") == "FA3-HW-001" and profile.get("canonical_root") is False, "portability baseline is a non-root subprofile of FA3-HW-001"),
        check("capability-count-stable", profile.get("capability_count") == contract.get("capability_count") == decision.get("capability_count_after") == CAPABILITY_COUNT, "canonical capability count remains 143"),
        check("no-new-authority", profile.get("new_architectural_authority") is False and decision.get("new_architectural_authority") is False, "no new architectural authority"),
        check("cpu-floor", cpu.get("package_count_min") == 1 and cpu.get("physical_cores_per_qualifying_cpu_min") == 8, "CPU floor is 1 package and >=8 physical cores per qualifying CPU"),
        check("cpu-unbounded-cardinality", cpu.get("package_count_max") == "UNBOUNDED_BY_FA3" and cpu.get("fixed_socket_count") == "FORBIDDEN", "CPU count is dynamic 1..N"),
        check("gpu-floor", gpu.get("qualifying_device_count_min") == 1 and gpu.get("rtx_series_floor") == 30, "GPU floor is >=1 NVIDIA RTX 30-series"),
        check("gpu-unbounded-cardinality", gpu.get("qualifying_device_count_max") == "UNBOUNDED_BY_FA3" and gpu.get("fixed_device_count") == "FORBIDDEN", "GPU count is dynamic 1..N"),
        check("newer-gpus-accepted", "MUST_ACCEPT" in gpu.get("newer_generations", "") and envelope.get("newer_rtx_series_allowed") is True, "newer RTX generations are explicitly accepted"),
        check("no-cpu-model-pin", cpu.get("vendor_pin") == cpu.get("model_pin") == "FORBIDDEN", "CPU vendor/model pins are forbidden"),
        check("no-gpu-sku-pin", all(gpu.get(k, "").startswith("FORBIDDEN") for k in ("exact_sku_pin", "vram_size_pin", "sm_pin")), "GPU SKU/VRAM/SM global pins are forbidden"),
        check("dynamic-discovery", discovery.get("enumeration") == "DYNAMIC_1_TO_N" and discovery.get("admission_revalidation") is True and discovery.get("topology_change_revalidation") is True, "live discovery and revalidation are mandatory"),
        check("stable-accelerator-identity", discovery.get("ephemeral_runtime_indices_are_identity") is False and set(discovery.get("stable_accelerator_identity_when_available", [])) == {"DEVICE_UUID", "PCI_BDF"}, "CUDA ordinal is not canonical identity"),
        check("minimum-positive", portable_hardware_floor_valid(cpu_packages=1, physical_cores_per_qualifying_cpu=8, gpu_count=1, gpu_rtx_series=30), "minimum host is admitted"),
        check("newer-multigpu-positive", portable_hardware_floor_valid(cpu_packages=4, physical_cores_per_qualifying_cpu=32, gpu_count=8, gpu_rtx_series=60), "larger multi-CPU/multi-GPU newer RTX host is admitted"),
        check("under-core-negative", not portable_hardware_floor_valid(cpu_packages=1, physical_cores_per_qualifying_cpu=7, gpu_count=1, gpu_rtx_series=30), "under-core host is rejected"),
        check("no-gpu-negative", not portable_hardware_floor_valid(cpu_packages=1, physical_cores_per_qualifying_cpu=8, gpu_count=0, gpu_rtx_series=50), "host without qualifying GPU is rejected"),
        check("old-gpu-negative", not portable_hardware_floor_valid(cpu_packages=1, physical_cores_per_qualifying_cpu=8, gpu_count=1, gpu_rtx_series=20), "RTX pre-30 generation does not satisfy FA3 floor"),
        check("root-hw-linked", "FA3-HARDWARE-DISCOVERY-CONTRACTS-001" in hw_profile.get("contracts", []) and "FA3-HARDWARE-BASELINE-001" in hw_profile.get("mandatory_subprofiles", []), "FA3-HW root binds portability baseline and discovery contract"),
        check("hw-contract-linked", "FA3-HARDWARE-DISCOVERY-CONTRACTS-001" in hw_contract.get("contract_family_bindings", []), "hardware contract family binds discovery contract"),
        check("mgpu-dynamic", "ACCELERATOR_CARDINALITY_DYNAMIC_1_TO_N" in mgpu_profile.get("invariants", []) and "FIXED_GPU_COUNT_OR_RUNTIME_ORDINAL_FORBIDDEN" in mgpu_profile.get("invariants", []), "multi-GPU profile is dynamic rather than fixed-count"),
        check("hrb-linked", "FA3-HARDWARE-DISCOVERY-CONTRACTS-001" in hrb_profile.get("contracts", []) and hrb_profile.get("hardware_portability_baseline_profile") == "FA3-HARDWARE-BASELINE-001", "HRB consumes discovery contract without losing authority"),
        check("hrb-contract-dynamic", "DYNAMIC_CPU_AND_GPU_CARDINALITY_DISCOVERY_REQUIRED" in hrb_contract.get("invariants", []) and "FIXED_GPU_COUNT_CPU_LIST_NUMA_NODE_OR_CUDA_ORDINAL_IS_NOT_PORTABLE_PLACEMENT" in hrb_contract.get("invariants", []), "HRB contract forbids fixed topology assumptions"),
        check("enforcement-complete", enforcement.get("fail_closed") is True and enforcement.get("mandatory_rule_count") == 24 and len(enforcement.get("rules", [])) == 24, "24 mandatory P0 portability rules are fail-closed"),
        check("evidence-bindings", len(bound_records) == len(CAPABILITY_BINDINGS) and all(DECISION_ID in item.get("source_decision_ids", []) and REFERENCE_EVIDENCE in item.get("evidence_artifacts", []) for item in bound_records), "all hardware-related capability evidence records bind the portability decision/evidence"),
        check("reference-not-promotion", reference_evidence.get("status") == "PASS" and reference_evidence.get("current_host_runtime_promotion_claim") is False and audit_evidence.get("current_host_runtime_promotion_claim") is False, "reference/audit PASS cannot promote current-host runtime"),
        check("decision-supersedes-fixed-interpretations", decision.get("supersedence", {}).get("scope") == "CANONICAL_INTERPRETATION_ONLY" and decision.get("supersedence", {}).get("historical_and_current_host_evidence") == "PRESERVED_AS_EVIDENCE_NOT_PORTABLE_DEFAULT", "fixed canonical interpretations are superseded while evidence is preserved"),
        check("no-accidental-exact-pin-in-profile", "RTX 3080" not in pin_text and "E5-2696" not in pin_text and "T7910" not in pin_text, "portable profile contains no current-host SKU/model identity"),
        check("gate-record", gate_record.get("gateset_id") == GATE_ID and gate_record.get("id") == EXECUTABLE_GATE_ID and gate_record.get("fail_closed") is True, "canonical executable gate record is bound"),
    ]

    audit = scan_repository(root)
    checks.append(check(
        "repository-wide-hardcoded-hardware-audit",
        audit["result"] == "PASS",
        f"repository text audit blockers={audit['blocking_hardcoded_production_assumptions']}",
    ))

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
        "checks": checks,
        "summary": {
            "passed": sum(item["status"] == "PASS" for item in checks),
            "total": len(checks),
        },
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
