#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

PROFILE = "canonical/profiles/FA3-HARDWARE-BASELINE-001.json"
CONTRACT = "canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json"
DECISION = "canonical/decisions/FA3-DEC-HARDWARE-AUDIT-2026-09-20.json"
ENFORCEMENT = "canonical/hardware-portability-enforcement.json"
GATE_RECORD = "canonical/FA3-GATE-HARDWARE-PORTABILITY-001.json"
HW_PROFILE = "canonical/profiles/FA3-HW-001.json"
HW_CONTRACT = "canonical/contracts/FA3-HW-CONTRACTS-001.json"
MGPU_PROFILE = "canonical/profiles/FA3-HW-MGPU-001.json"
HRB_PROFILE = "canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json"
HRB_CONTRACT = "canonical/contracts/FA3-HOST-RESOURCE-BROKER-CONTRACTS-001.json"
EVIDENCE_REGISTRY = "evidence/evidence-registry.json"

GATE_ID = "FA3-HARDWARE-PORTABILITY-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-HARDWARE-PORTABILITY-001"
DECISION_ID = "FA3-DEC-HARDWARE-AUDIT-2026-09-20"
CAPABILITY_COUNT = module_active_capability_count(__file__)

REFERENCE_VENDOR_FAMILIES = {"NVIDIA", "AMD", "INTEL"}
REFERENCE_PLATFORM_FAMILIES = {"NVIDIA_DGX"}
CAPABILITY_BINDINGS = (
    "CAP-001", "CAP-006", "CAP-062", "CAP-063", "CAP-065",
    "CAP-130", "CAP-137", "CAP-142", "CAP-143",
)

RUNTIME_PREFIXES = ("src/", "bin/", "apps/", "deployment/", ".github/workflows/")
NON_NORMATIVE_PREFIXES = ("fa3-current-host/", "evidence/", "canonical/references/", "tests/", "examples/")
SKIP_TOP_LEVEL = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache"}
TEXT_SUFFIXES = {
    ".json", ".py", ".md", ".sh", ".yml", ".yaml", ".csv", ".toml", ".ini",
    ".conf", ".service", ".socket", ".target", ".container", ".caddy", ".sql",
    ".txt", ".env", ".rules", ".qml", ".cpp", ".cc", ".c", ".hpp", ".h",
    ".cmake", ".desktop",
}

HARD_RUNTIME_PATTERNS = (
    ("FIXED_CUDA_VISIBLE_DEVICES_LIST", re.compile(r"CUDA_VISIBLE_DEVICES[^\n=]{0,40}=\s*[\"']?\d+(?:\s*,\s*\d+)+")),
    ("FIXED_HIP_VISIBLE_DEVICES_LIST", re.compile(r"(?:HIP|ROCR)_VISIBLE_DEVICES[^\n=]{0,40}=\s*[\"']?\d+(?:\s*,\s*\d+)+", re.I)),
    ("FIXED_LEVEL_ZERO_AFFINITY", re.compile(r"ZE_AFFINITY_MASK[^\n=]{0,40}=\s*[\"']?\d+(?:\.\d+)?", re.I)),
    ("FIXED_CPUAFFINITY", re.compile(r"(?mi)^\s*CPUAffinity\s*=\s*\d")),
    ("FIXED_NUMAMASK", re.compile(r"(?mi)^\s*NUMAMask\s*=\s*\d")),
    ("FIXED_TASKSET_CPU_LIST", re.compile(r"\btaskset\s+-c\s+\d", re.I)),
    ("FIXED_NUMACTL_BINDING", re.compile(r"\bnumactl\s+--(?:physcpubind|cpunodebind|membind)(?:=|\s+)\d", re.I)),
    ("FIXED_VENDOR_ORDINAL", re.compile(r"\b(?:nvidia-smi|rocm-smi|xpu-smi)\s+(?:-i|--device)\s+\d", re.I)),
    ("FIXED_ACCELERATOR_COUNT_COMPARISON", re.compile(r"\b(?:gpu_count|num_gpus|device_count|accelerator_count)\s*(?:==|!=)\s*[1-9]\d*\b", re.I)),
    ("LITERAL_PCI_BDF", re.compile(r"\b[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]\b")),
)

CONCRETE_HOST_PATTERNS = (
    ("CPU_MODEL_LITERAL", re.compile(r"\b(?:Xeon(?:\s+(?:Gold|Silver|Bronze|Platinum))?\s+[A-Z]?\d{4,5}[A-Z]?|E5[- ]\d{4}(?:\s+v\d)?|EPYC\s+\d{4}[A-Z]?|Core\s+i[3579]-\d{4,5}[A-Z]*)\b", re.I)),
    ("NVIDIA_SKU_LITERAL", re.compile(r"\b(?:GeForce\s+)?RTX\s+(?:A?\d{3,4}|PRO\s+\d+)|\bDGX(?:\s+(?:A100|H100|H200|B200|Station|Spark))?\b", re.I)),
    ("AMD_SKU_LITERAL", re.compile(r"\b(?:Radeon\s+RX\s+\d{4}[A-Z]*|Instinct\s+MI\d{2,3}[A-Z]*|MI\d{2,3}[A-Z]*)\b", re.I)),
    ("INTEL_GPU_SKU_LITERAL", re.compile(r"\bIntel\s+Arc\s+[AB]\d{3}\b", re.I)),
)


def _join(*parts: str) -> str:
    return "".join(parts)

LEGACY_REPOSITORY_PATTERNS = (
    ("LEGACY_WORKSTATION_MODEL", re.compile(r"\bT" + _join("79", "10") + r"\b", re.I)),
    ("LEGACY_WORKSTATION_NAME", re.compile(r"\bPrecision(?:\s+Tower)?\s+" + _join("79", "10") + r"\b", re.I)),
    ("LEGACY_CPU_MODEL_A", re.compile(r"\bE5[-_ ]?" + _join("26", "96") + r"(?:\s*v4)?\b", re.I)),
    ("LEGACY_CPU_MODEL_B", re.compile(r"\bE5[-_ ]?" + _join("26", "97") + r"(?:\s*v4)?\b", re.I)),
    ("LEGACY_GPU_MODEL_A", re.compile(r"\bRTX[\s_-]*" + _join("30", "90") + r"\b", re.I)),
    ("LEGACY_GPU_MODEL_B", re.compile(r"\bRTX[\s_-]*A" + _join("10", "00") + r"\b", re.I)),
    ("LEGACY_GPU_MODEL_C", re.compile(r"\bRTX[\s_-]*" + _join("30", "80") + r"\b", re.I)),
    ("LEGACY_GPU_MODEL_D", re.compile(r"\b(?:Quadro\s+)?RTX[\s_-]*" + _join("40", "00") + r"\b", re.I)),
    ("LEGACY_PCI_BDF_A", re.compile(r"\b" + _join("0000:", "05:00.0") + r"\b", re.I)),
    ("LEGACY_PCI_BDF_B", re.compile(r"\b" + _join("0000:", "a5:00.0") + r"\b", re.I)),
    ("LEGACY_TOPOLOGY_A", re.compile(r"\b" + _join("44", "C") + r"\s*[-/]\s*" + _join("88", "T") + r"\b", re.I)),
    ("LEGACY_TOPOLOGY_B", re.compile(r"\b" + _join("36", "C") + r"\s*[-/]\s*" + _join("72", "T") + r"\b", re.I)),
    ("LEGACY_AUDIT_DECISION", re.compile(re.escape(_join("FA3-DEC-HARDWARE-PORTABILITY-", "2026-09-03")), re.I)),
    ("LEGACY_AUDIT_CI", re.compile(re.escape(_join("hardware-portability-ci-", "2026-09-03")), re.I)),
    ("LEGACY_AUDIT_REPOSITORY", re.compile(re.escape(_join("hardware-portability-repository-audit-", "2026-09-03")), re.I)),
    ("LEGACY_HARDWARE_FABRIC", re.compile(re.escape(_join("FA3-HARDWARE-FABRIC-", "RECONCILIATION-001")), re.I)),
    ("LEGACY_HARDWARE_FABRIC_EVIDENCE", re.compile(re.escape(_join("hardware-fabric-reconciliation-", "2026-09-16")), re.I)),
    ("LEGACY_CPU_NUMA_REFERENCE", re.compile(re.escape(_join("FA3-", "T79", "10-CPU-NUMA-REFERENCE-2026-09-02")), re.I)),
    ("LEGACY_CPU_NUMA_EVIDENCE", re.compile(re.escape(_join("cpu-numa-threading-ci-", "2026-09-02")), re.I)),
)

REFERENCE_MARKERS = (
    "reference", "fixture", "evidence", "historical", "supersed", "non-normative",
    "not canonical", "forbidden", "example", "provider-local", "provider specific",
    "provider-specific", "compatibility only", "workload-specific",
)

def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))

def check(name: str, value: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if value else "FAIL", "detail": detail}

def portable_hardware_floor_valid(
    *,
    cpu_packages: int,
    physical_cores_per_qualifying_cpu: int,
    accelerator_count: int | None = None,
    accelerator_vendor: str | None = None,
    workload_compatible: bool = True,
    gpu_count: int | None = None,
    gpu_compute_capability: float | None = None,
    gpu_vendor: str | None = None,
) -> bool:
    """Global floor only: vendor/runtime API are not admission inputs."""
    count = accelerator_count if accelerator_count is not None else gpu_count
    vendor = accelerator_vendor if accelerator_vendor is not None else gpu_vendor
    return (
        isinstance(cpu_packages, int)
        and isinstance(physical_cores_per_qualifying_cpu, int)
        and isinstance(count, int)
        and cpu_packages >= 1
        and physical_cores_per_qualifying_cpu >= 8
        and count >= 1
        and workload_compatible is True
        and (vendor is None or (isinstance(vendor, str) and bool(vendor.strip())))
    )

def _is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.parent.name == "bin" or path.name.startswith("fa3-")

def _context(text: str, start: int, end: int, radius: int = 260) -> str:
    return text[max(0, start - radius): min(len(text), end + radius)].lower()

def scan_repository(root: Path) -> dict[str, Any]:
    blocking: list[dict[str, Any]] = []
    legacy_blocking: list[dict[str, Any]] = []
    non_normative: list[dict[str, Any]] = []
    scanned = runtime_scanned = unreadable = 0

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
        policy_or_test_code = rel.startswith("src/") and rel.endswith("_gate.py")
        current_host_tooling = "current-host" in rel.lower() or "current_host" in rel.lower()
        explicitly_non_normative = rel.startswith(NON_NORMATIVE_PREFIXES) or policy_or_test_code or current_host_tooling

        for code, pattern in LEGACY_REPOSITORY_PATTERNS:
            for match in pattern.finditer(text):
                item = {"path": rel, "kind": code, "offset": match.start(), "sample": match.group(0)[:120]}
                legacy_blocking.append(item)
                blocking.append(item)

        for code, pattern in HARD_RUNTIME_PATTERNS:
            for match in pattern.finditer(text):
                ctx = _context(text, match.start(), match.end())
                marked = explicitly_non_normative or any(marker in ctx for marker in REFERENCE_MARKERS)
                item = {"path": rel, "kind": code, "offset": match.start(), "sample": match.group(0)[:120]}
                if runtime and not marked:
                    blocking.append(item)
                else:
                    non_normative.append({**item, "classification": "REFERENCE_OR_PROVIDER_SCOPED" if marked else "NON_RUNTIME_TEXT"})

        for code, pattern in CONCRETE_HOST_PATTERNS:
            for match in pattern.finditer(text):
                ctx = _context(text, match.start(), match.end())
                marked = explicitly_non_normative or any(marker in ctx for marker in REFERENCE_MARKERS)
                item = {"path": rel, "kind": code, "offset": match.start(), "sample": match.group(0)[:120]}
                if runtime and not marked:
                    blocking.append(item)
                else:
                    non_normative.append({**item, "classification": "REFERENCE_OR_PROVIDER_SCOPED" if marked else "NON_RUNTIME_TEXT"})

    return {
        "result": "PASS" if not blocking else "FAIL",
        "scanned_text_files": scanned,
        "runtime_surface_files_scanned": runtime_scanned,
        "unreadable_text_candidates": unreadable,
        "blocking_hardcoded_production_assumptions": len(blocking),
        "legacy_repository_reference_count": len(legacy_blocking),
        "legacy_repository_matches": legacy_blocking,
        "blocking_matches": blocking,
        "non_normative_hardware_mentions": len(non_normative),
        "non_normative_sample": non_normative[:100],
    }

def _neutral_gpu_record(gpu: dict[str, Any]) -> bool:
    return (
        gpu.get("qualifying_device_count_min", gpu.get("minimum_qualifying_device_count")) == 1
        and gpu.get("vendor_pin") == "FORBIDDEN"
        and gpu.get("global_runtime_api_pin") == "FORBIDDEN"
        and str(gpu.get("global_cuda_compute_capability_floor", "FORBIDDEN")).startswith("FORBIDDEN")
        and gpu.get("workload_runtime_compatibility", "REQUIRED") in {"REQUIRED", True}
        and gpu.get("provider_capability_negotiation", "REQUIRED") in {"REQUIRED", True}
        and REFERENCE_VENDOR_FAMILIES <= set(gpu.get("supported_reference_vendor_families", []))
        and REFERENCE_PLATFORM_FAMILIES <= set(gpu.get("supported_reference_platform_families", []))
    )

def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    profile=loadj(root,PROFILE); contract=loadj(root,CONTRACT); decision=loadj(root,DECISION)
    enforcement=loadj(root,ENFORCEMENT); gate_record=loadj(root,GATE_RECORD)
    hw_profile=loadj(root,HW_PROFILE); hw_contract=loadj(root,HW_CONTRACT); mgpu=loadj(root,MGPU_PROFILE)
    hrb_profile=loadj(root,HRB_PROFILE); hrb_contract=loadj(root,HRB_CONTRACT)
    evidence_registry=loadj(root,EVIDENCE_REGISTRY)

    cpu=profile.get("portable_minimum",{}).get("cpu",{}); gpu=profile.get("portable_minimum",{}).get("gpu",{})
    discovery=contract.get("discovery_semantics",{}); envelope=contract.get("portable_minimum_envelope",{})
    bound=[x for x in evidence_registry.get("records",[]) if x.get("subject_id") in CAPABILITY_BINDINGS]

    checks=[
      check("cpu-floor", cpu.get("package_count_min")==1 and cpu.get("physical_cores_per_qualifying_cpu_min")==8, "CPU floor remains vendor/model agnostic"),
      check("vendor-neutral-portable-profile", _neutral_gpu_record(gpu), "global accelerator floor has no vendor/runtime API pin"),
      check("vendor-neutral-root-profile", _neutral_gpu_record(hw_profile.get("minimum_portable_hardware_envelope",{}).get("gpu",{})), "FA3-HW root is vendor-neutral"),
      check("vendor-neutral-root-contract", _neutral_gpu_record(hw_contract.get("portable_minimum_envelope",{}).get("gpu",{})), "root hardware contract is vendor-neutral"),
      check("vendor-neutral-discovery-contract", envelope.get("accelerator_vendor_pin")=="FORBIDDEN" and envelope.get("global_runtime_api_pin")=="FORBIDDEN" and envelope.get("global_vendor_capability_floor")=="FORBIDDEN", "discovery contract is vendor-neutral"),
      check("nvidia-supported", portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=8,accelerator_count=1,accelerator_vendor="NVIDIA"), "NVIDIA supported"),
      check("amd-supported", portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=8,accelerator_count=1,accelerator_vendor="AMD"), "AMD supported"),
      check("intel-supported", portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=8,accelerator_count=1,accelerator_vendor="INTEL"), "Intel supported"),
      check("dgx-supported", "NVIDIA_DGX" in gpu.get("supported_reference_platform_families",[]), "DGX supported as platform family"),
      check("provider-compatibility-fail-closed", not portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=8,accelerator_count=1,accelerator_vendor="AMD",workload_compatible=False), "workload/provider incompatibility fails closed"),
      check("no-accelerator-negative", not portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=8,accelerator_count=0), "below global minimum fails"),
      check("dynamic-discovery", discovery.get("enumeration")=="DYNAMIC_1_TO_N" and discovery.get("admission_revalidation") is True and discovery.get("topology_change_revalidation") is True, "live discovery/revalidation required"),
      check("stable-identity", discovery.get("ephemeral_runtime_indices_are_identity") is False and set(discovery.get("stable_accelerator_identity_when_available",[]))=={"DEVICE_UUID","PCI_BDF"}, "runtime ordinal not canonical identity"),
      check("hrb-linked", hrb_profile.get("hardware_portability_baseline_profile")=="FA3-HARDWARE-BASELINE-001" and "FA3-HARDWARE-DISCOVERY-CONTRACTS-001" in hrb_profile.get("contracts",[]), "HRB remains sole authority"),
      check("hrb-dynamic", "DYNAMIC_CPU_AND_GPU_CARDINALITY_DISCOVERY_REQUIRED" in hrb_contract.get("invariants",[]), "HRB consumes dynamic topology"),
      check("mgpu-vendor-neutral", "ACCELERATOR_VENDOR_OR_MARKETING_SERIES_IS_NOT_GLOBAL_ADMISSION_AUTHORITY" in mgpu.get("invariants",[]) and "FIXED_ACCELERATOR_COUNT_OR_RUNTIME_ORDINAL_FORBIDDEN" in mgpu.get("invariants",[]), "multi-accelerator profile vendor-neutral"),
      check("enforcement-vendor-neutral", any(r.get("invariant")=="NO_VENDOR_OR_RUNTIME_API_DEFINES_THE_GLOBAL_ACCELERATOR_FLOOR" for r in enforcement.get("rules",[])), "vendor-neutral floor mandatory"),
      check(
          "decision-vendor-neutral",
          decision.get("decision")=="SINGLE_CURRENT_VENDOR_NEUTRAL_HARDWARE_AUDIT_NO_LEGACY_HOST_BASELINE"
          and decision.get("evidence_policy",{}).get("legacy_hardware_audit_artifacts")=="REMOVE_FROM_REPOSITORY"
          and decision.get("evidence_policy",{}).get("legacy_host_specific_records")=="REMOVE_FROM_REPOSITORY"
          and decision.get("evidence_policy",{}).get("static_pass_is_current_host_pass") is False,
          "current hardware-audit decision is vendor-neutral and forbids legacy host/audit inheritance",
      ),
      check("evidence-bindings", len(bound)==len(CAPABILITY_BINDINGS) and all(DECISION_ID in x.get("source_decision_ids",[]) for x in bound), "evidence bindings retained"),
      check("gate-record", gate_record.get("id")==EXECUTABLE_GATE_ID and gate_record.get("gateset_id")==GATE_ID and gate_record.get("fail_closed") is True, "gate record bound"),
    ]
    audit=scan_repository(root)
    checks.append(check(
        "repository-wide-hardcoded-hardware-audit",
        audit["result"]=="PASS",
        f"repository blockers={audit['blocking_hardcoded_production_assumptions']} legacy={audit['legacy_repository_reference_count']}",
    ))
    passed=all(x["status"]=="PASS" for x in checks)
    return {
      "schema":"fa3.hardware-portability-gate-report.v3",
      "gate_id":GATE_ID,
      "executable_gate_id":EXECUTABLE_GATE_ID,
      "capability_count":CAPABILITY_COUNT,
      "result":"PASS" if passed else "FAIL",
      "current_host_runtime_promotion_claim":False,
      "legacy_host_evidence_accepted":False,
      "fresh_current_host_evidence_required":True,
      "accelerator_floor":{"vendor_pin":"FORBIDDEN","runtime_api_pin":"FORBIDDEN","minimum_device_count":1,"compatibility":"WORKLOAD_PROVIDER_SCOPED"},
      "supported_reference_vendor_families":sorted(REFERENCE_VENDOR_FAMILIES),
      "supported_reference_platform_families":sorted(REFERENCE_PLATFORM_FAMILIES),
      "checks":checks,
      "summary":{"passed":sum(x["status"]=="PASS" for x in checks),"total":len(checks)},
      "repository_audit":audit,
    }

def gate(root: Path) -> dict[str, Any]:
    report=evaluate(root)
    out=root/"reports/hardware-portability-gate-report.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main() -> int:
    parser=argparse.ArgumentParser(description="FA3 vendor-neutral hardware portability audit")
    parser.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    args=parser.parse_args()
    report=gate(Path(args.root))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
