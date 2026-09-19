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
DECISION = "canonical/decisions/FA3-DEC-HARDWARE-WORKLOAD-DRIVEN-BASELINE-2026-09-20.json"
ENFORCEMENT = "canonical/hardware-portability-enforcement.json"
GATE_RECORD = "canonical/FA3-GATE-HARDWARE-PORTABILITY-001.json"
HW_PROFILE = "canonical/profiles/FA3-HW-001.json"
HW_CONTRACT = "canonical/contracts/FA3-HW-CONTRACTS-001.json"
MGPU_PROFILE = "canonical/profiles/FA3-HW-MGPU-001.json"
HRB_PROFILE = "canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json"
HRB_CONTRACT = "canonical/contracts/FA3-HOST-RESOURCE-BROKER-CONTRACTS-001.json"
REFERENCE_EVIDENCE = "evidence/reference/hardware-workload-driven-reconciliation-2026-09-20.json"

GATE_ID = "FA3-HARDWARE-PORTABILITY-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-HARDWARE-PORTABILITY-001"
DECISION_ID = "FA3-DEC-HARDWARE-WORKLOAD-DRIVEN-BASELINE-2026-09-20"
CAPABILITY_COUNT = module_active_capability_count(__file__)

RUNTIME_PREFIXES = ("src/", "bin/", "deployment/", ".github/workflows/")
NON_NORMATIVE_PREFIXES = ("fa3-current-host/", "evidence/", "canonical/references/", "tests/", "examples/")
SKIP_TOP_LEVEL = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache"}
TEXT_SUFFIXES = {".json", ".py", ".md", ".sh", ".yml", ".yaml", ".csv", ".toml", ".ini", ".conf", ".service", ".socket", ".target", ".container", ".caddy", ".sql", ".txt", ".env", ".rules"}

HARD_RUNTIME_PATTERNS = (
    ("FIXED_CUDA_VISIBLE_DEVICES_LIST", re.compile(r"CUDA_VISIBLE_DEVICES[^\n=]{0,40}=\s*[\"']?\d+(?:\s*,\s*\d+)+")),
    ("FIXED_CPUAFFINITY", re.compile(r"(?mi)^\s*CPUAffinity\s*=\s*\d")),
    ("FIXED_NUMAMASK", re.compile(r"(?mi)^\s*NUMAMask\s*=\s*\d")),
    ("FIXED_TASKSET_CPU_LIST", re.compile(r"\btaskset\s+-c\s+\d", re.I)),
    ("FIXED_NUMACTL_BINDING", re.compile(r"\bnumactl\s+--(?:physcpubind|cpunodebind|membind)(?:=|\s+)\d", re.I)),
    ("FIXED_NVIDIA_SMI_ORDINAL", re.compile(r"\bnvidia-smi\s+-i\s+\d", re.I)),
)
CONCRETE_HOST_PATTERNS = (
    ("CPU_MODEL_E5_2696", re.compile(r"\bE5[- ]2696(?:\s+v4)?\b", re.I)),
    ("CPU_MODEL_E5_2697", re.compile(r"\bE5[- ]2697(?:\s+v4)?\b", re.I)),
    ("GPU_SKU_RTX3080", re.compile(r"\bRTX\s*3080\b", re.I)),
    ("GPU_SKU_RTX4000", re.compile(r"\b(?:Quadro\s+)?RTX\s*4000\b", re.I)),
    ("HOST_MODEL_T7910", re.compile(r"\b(?:T7910|Precision(?:\s+Tower)?\s+7910)\b", re.I)),
)
REFERENCE_MARKERS = ("reference", "fixture", "evidence", "historical", "supersed", "non-normative", "not canonical", "forbidden", "example", "provider-local")


def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def check(name: str, value: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if value else "FAIL", "detail": detail}


def portable_hardware_floor_valid(*, cpu_packages: int, physical_cores_per_qualifying_cpu: int, accelerator_count: int = 0, **_: Any) -> bool:
    """Global FA3 floor: CPU core floor only; accelerators are optional 0..N."""
    return (
        isinstance(cpu_packages, int)
        and isinstance(physical_cores_per_qualifying_cpu, int)
        and isinstance(accelerator_count, int)
        and cpu_packages >= 1
        and physical_cores_per_qualifying_cpu >= 8
        and accelerator_count >= 0
    )


def _is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.parent.name == "bin" or path.name.startswith("fa3-")


def _context(text: str, start: int, end: int, radius: int = 240) -> str:
    return text[max(0, start-radius):min(len(text), end+radius)].lower()


def scan_repository(root: Path) -> dict[str, Any]:
    blocking=[]; non_normative=[]; scanned=0; runtime_scanned=0; unreadable=0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel=path.relative_to(root).as_posix(); parts=Path(rel).parts
        if not parts or parts[0] in SKIP_TOP_LEVEL or "__pycache__" in parts or not _is_text_candidate(path):
            continue
        try:
            if path.stat().st_size > 2_000_000: continue
            data=path.read_bytes()
            if b"\x00" in data: continue
            text=data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            unreadable += 1; continue
        scanned += 1
        runtime=rel.startswith(RUNTIME_PREFIXES)
        if runtime: runtime_scanned += 1
        policy_or_test_code=rel.startswith("src/") and rel.endswith("_gate.py")
        current_host_tooling="current-host" in rel.lower() or "current_host" in rel.lower()
        explicitly_non_normative=rel.startswith(NON_NORMATIVE_PREFIXES) or policy_or_test_code or current_host_tooling
        for code,pattern in HARD_RUNTIME_PATTERNS:
            for match in pattern.finditer(text):
                item={"path":rel,"kind":code,"offset":match.start(),"sample":match.group(0)[:120]}
                (blocking if runtime else non_normative).append(item)
        for code,pattern in CONCRETE_HOST_PATTERNS:
            for match in pattern.finditer(text):
                ctx=_context(text,match.start(),match.end())
                marked=explicitly_non_normative or any(m in ctx for m in REFERENCE_MARKERS)
                item={"path":rel,"kind":code,"offset":match.start(),"sample":match.group(0)[:120]}
                if runtime and not marked: blocking.append(item)
                else: non_normative.append({**item,"classification":"REFERENCE_OR_EVIDENCE_CONTEXT" if marked else "NON_RUNTIME_TEXT"})
    return {
        "result":"PASS" if not blocking else "FAIL",
        "scanned_text_files":scanned,
        "runtime_surface_files_scanned":runtime_scanned,
        "unreadable_text_candidates":unreadable,
        "blocking_hardcoded_production_assumptions":len(blocking),
        "blocking_matches":blocking,
        "non_normative_hardware_mentions":len(non_normative),
        "non_normative_sample":non_normative[:100],
    }


def evaluate(root: Path) -> dict[str, Any]:
    root=root.resolve()
    profile=loadj(root,PROFILE); contract=loadj(root,CONTRACT); decision=loadj(root,DECISION)
    enforcement=loadj(root,ENFORCEMENT); gate_record=loadj(root,GATE_RECORD)
    hw_profile=loadj(root,HW_PROFILE); hw_contract=loadj(root,HW_CONTRACT)
    mgpu=loadj(root,MGPU_PROFILE); hrb=loadj(root,HRB_PROFILE); hrb_contract=loadj(root,HRB_CONTRACT)
    evidence=loadj(root,REFERENCE_EVIDENCE)
    cpu=profile.get("portable_minimum",{}).get("cpu",{})
    gpu=profile.get("portable_minimum",{}).get("gpu",{})
    accel=profile.get("portable_minimum",{}).get("accelerator",{})
    discovery=contract.get("discovery_semantics",{})
    env=contract.get("portable_minimum_envelope",{})
    checks=[
        check("profile-parent",profile.get("relationship",{}).get("parent")=="FA3-HW-001" and profile.get("canonical_root") is False,"portability baseline remains subordinate to FA3-HW-001"),
        check("capability-count-stable",profile.get("capability_count")==contract.get("capability_count")==decision.get("capability_count_after")==CAPABILITY_COUNT,"capability count unchanged"),
        check("no-new-authority",profile.get("new_architectural_authority") is False and decision.get("new_architectural_authority") is False,"no new authority"),
        check("cpu-floor",cpu.get("package_count_min")==1 and cpu.get("physical_cores_per_qualifying_cpu_min")==8,"CPU floor is 1 package and >=8 physical cores"),
        check("cpu-unbounded",cpu.get("package_count_max")=="UNBOUNDED_BY_FA3" and cpu.get("fixed_socket_count")=="FORBIDDEN","CPU cardinality is dynamic"),
        check("accelerator-zero-min",gpu.get("qualifying_device_count_min")==0 and accel.get("device_count_min")==0,"global accelerator minimum is zero"),
        check("no-global-accelerator-floor",gpu.get("required_globally") is False and gpu.get("cuda_compute_capability_min") is None and accel.get("global_vendor_runtime_architecture_floor") is None,"no global accelerator vendor/runtime/architecture/CC floor"),
        check("accelerator-conditional",accel.get("requirement_semantics")=="WORKLOAD_AND_PROVIDER_CONDITIONAL","accelerator requirements are workload/provider conditional"),
        check("dynamic-discovery",discovery.get("enumeration")=="CPU_1_TO_N_ACCELERATOR_0_TO_N" and discovery.get("admission_revalidation") is True,"live CPU+optional accelerator discovery"),
        check("stable-identity",discovery.get("ephemeral_runtime_indices_are_identity") is False and set(discovery.get("stable_accelerator_identity_when_available",[]))=={"DEVICE_UUID","PCI_BDF"},"stable accelerator identity when available"),
        check("cpu-only-positive",portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=8,accelerator_count=0),"CPU-only host satisfies global floor"),
        check("accelerator-present-positive",portable_hardware_floor_valid(cpu_packages=2,physical_cores_per_qualifying_cpu=24,accelerator_count=8,accelerator_vendor="ANY"),"accelerator presence does not redefine global floor"),
        check("under-core-negative",not portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=7,accelerator_count=8),"under-core host rejected"),
        check("root-optional",hw_profile.get("minimum_portable_hardware_envelope",{}).get("accelerator",{}).get("minimum_device_count")==0,"root hardware profile has optional accelerators"),
        check("root-contract-optional",hw_contract.get("portable_minimum_envelope",{}).get("accelerator",{}).get("device_count_min")==0,"root contract has optional accelerators"),
        check("mgpu-conditional",mgpu.get("cardinality_policy",{}).get("minimum_qualifying_gpu_count")==0 and "ACCELERATOR_CARDINALITY_DYNAMIC_0_TO_N_AT_HOST_BASELINE" in mgpu.get("invariants",[]),"MGPU profile does not create global GPU requirement"),
        check("hrb-linked",hrb.get("hardware_portability_baseline_profile")=="FA3-HARDWARE-BASELINE-001" and hrb.get("hardware_discovery_contract")=="FA3-HARDWARE-DISCOVERY-CONTRACTS-001","HRB remains bound"),
        check("hrb-conditional","GLOBAL_ACCELERATOR_MINIMUM_IS_ZERO" in hrb_contract.get("invariants",[]) and "ACCELERATOR_LEASE_REQUIRED_ONLY_WHEN_ACCELERATOR_RESOURCE_CLASS_IS_REQUESTED" in hrb_contract.get("invariants",[]),"HRB accelerator lease conditional"),
        check("enforcement-complete",enforcement.get("fail_closed") is True and enforcement.get("mandatory_rule_count")==24 and len(enforcement.get("rules",[]))==24,"24 fail-closed rules"),
        check("decision-bound",gate_record.get("decision_id")==DECISION_ID and decision.get("id")==DECISION_ID,"gate bound to workload-driven decision"),
        check("decision-no-global-accelerator",all(x in decision.get("invariants",[]) for x in ["NO_GLOBAL_NVIDIA_REQUIREMENT","NO_GLOBAL_CUDA_REQUIREMENT","NO_GLOBAL_COMPUTE_CAPABILITY_MINIMUM","NO_GLOBAL_GPU_OR_NPU_DEVICE_REQUIREMENT"]),"decision forbids global accelerator floor"),
        check("evidence-nonpromotion",evidence.get("current_host_runtime_evidence") is False and evidence.get("global_promotion_claim") is False,"reference evidence cannot promote runtime"),
        check("provider-neutral-discovery",contract.get("provider_neutral") is True and env.get("accelerator_devices_min")==0 and env.get("global_accelerator_vendor_runtime_architecture_floor") is None,"discovery contract provider-neutral"),
        check("gate-record",gate_record.get("gateset_id")==GATE_ID and gate_record.get("id")==EXECUTABLE_GATE_ID and gate_record.get("fail_closed") is True,"gate record intact"),
    ]
    audit=scan_repository(root)
    checks.append(check("repository-wide-hardcoded-hardware-audit",audit["result"]=="PASS",f"repository blockers={audit['blocking_hardcoded_production_assumptions']}"))
    passed=all(x["status"]=="PASS" for x in checks)
    return {
        "schema":"fa3.hardware-portability-gate-report.v2",
        "gate_id":GATE_ID,
        "executable_gate_id":EXECUTABLE_GATE_ID,
        "profile_id":profile.get("id"),
        "contract_id":contract.get("id"),
        "decision_id":DECISION_ID,
        "capability_count":CAPABILITY_COUNT,
        "result":"PASS" if passed else "FAIL",
        "current_host_runtime_promotion_claim":False,
        "global_hardware_floor":{"cpu":{"package_count_min":1,"physical_cores_min":8},"accelerator":{"device_count_min":0,"vendor_runtime_architecture_compute_capability_floor":None}},
        "checks":checks,
        "summary":{"passed":sum(x["status"]=="PASS" for x in checks),"total":len(checks)},
        "repository_audit":audit,
    }


def gate(root: Path) -> dict[str, Any]:
    report=evaluate(root)
    out=root/"reports/hardware-portability-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=p.parse_args()
    report=gate(Path(a.root)); print(json.dumps(report,ensure_ascii=False,indent=2)); return 0 if report["result"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
