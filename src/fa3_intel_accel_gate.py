#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

PROFILE = "canonical/profiles/FA3-INTEL-ACCEL-001.json"
CONTRACT = "canonical/contracts/FA3-INTEL-ACCEL-CONTRACTS-001.json"
GUARD_PROFILE = "canonical/profiles/FA3-ACCEL-GUARD-001.json"
GUARD_CONTRACT = "canonical/contracts/FA3-ACCEL-GUARD-CONTRACTS-001.json"
FAMILY = "canonical/registries/FA3-PROVIDER-FAMILY-INTEL-001.json"
GUI = "canonical/FA3-INTEL-ACCEL-GUI-MAPPING-001.json"
ENFORCEMENT = "canonical/intel-accel-enforcement.json"
DECISION = "canonical/decisions/FA3-DEC-INTEL-ACCEL-2026-09-16.json"
GATE_RECORD = "canonical/FA3-GATE-INTEL-ACCEL-001.json"
HARDWARE_BASELINE = "canonical/profiles/FA3-HARDWARE-BASELINE-001.json"
OPENVINO = "canonical/providers/FA3-PROVIDER-OPENVINO-001.json"
MODEL_MANAGER = "canonical/profiles/FA3-MODEL-MANAGER-001.json"
REFERENCE_EVIDENCE = "evidence/reference/intel-accel-ci-2026-09-16.json"
AUDIT_EVIDENCE = "evidence/reference/intel-accel-repository-audit-2026-09-16.json"

PROVIDERS = (
    "canonical/providers/FA3-PROVIDER-OPENVINO-001.json",
    "canonical/providers/FA3-PROVIDER-INTEL-XPU-001.json",
    "canonical/providers/FA3-PROVIDER-INTEL-NPU-001.json",
    "canonical/providers/FA3-PROVIDER-INTEL-COMPUTE-RUNTIME-001.json",
    "canonical/providers/FA3-PROVIDER-INTEL-NC-001.json",
    "canonical/providers/FA3-PROVIDER-INTEL-TRITON-XPU-001.json",
    "canonical/providers/FA3-PROVIDER-XPUM-001.json",
)

PROVIDER_IDS = {
    "FA3-PROVIDER-OPENVINO-001",
    "FA3-PROVIDER-INTEL-XPU-001",
    "FA3-PROVIDER-INTEL-NPU-001",
    "FA3-PROVIDER-INTEL-COMPUTE-RUNTIME-001",
    "FA3-PROVIDER-INTEL-NC-001",
    "FA3-PROVIDER-INTEL-TRITON-XPU-001",
    "FA3-PROVIDER-XPUM-001",
}

ACCEL_GUARD_REQUIRED = {
    "FA3-PROVIDER-OPENVINO-001",
    "FA3-PROVIDER-INTEL-XPU-001",
    "FA3-PROVIDER-INTEL-NPU-001",
    "FA3-PROVIDER-INTEL-TRITON-XPU-001",
}

CAPABILITY_COUNT = module_active_capability_count(__file__)


def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def check(name: str, value: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if value else "FAIL", "detail": detail}


def classify_fixture(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Classify a normalized Intel capability fixture without requiring Intel hardware in CI."""
    intel_gpu = bool(snapshot.get("intel_gpu"))
    intel_npu = bool(snapshot.get("intel_npu"))
    openvino = set(snapshot.get("openvino_devices", []))
    torch_xpu = bool(snapshot.get("torch_xpu_available"))
    external_busy = set(snapshot.get("external_busy", []))
    fa3_leased = set(snapshot.get("fa3_leased", []))

    devices: dict[str, str] = {}
    if intel_gpu:
        if "GPU" in external_busy:
            devices["GPU"] = "BUSY_EXTERNAL"
        elif "GPU" in fa3_leased:
            devices["GPU"] = "LEASED_FA3"
        elif "GPU" in openvino or torch_xpu:
            devices["GPU"] = "READY"
        else:
            devices["GPU"] = "DETECTED"
    if intel_npu:
        if "NPU" in external_busy:
            devices["NPU"] = "BUSY_EXTERNAL"
        elif "NPU" in fa3_leased:
            devices["NPU"] = "LEASED_FA3"
        elif "NPU" in openvino:
            devices["NPU"] = "READY"
        else:
            devices["NPU"] = "DETECTED"

    return {
        "intel_cpu": bool(snapshot.get("intel_cpu")),
        "intel_gpu": intel_gpu,
        "intel_npu": intel_npu,
        "openvino_cpu_ready": "CPU" in openvino,
        "openvino_gpu_ready": intel_gpu and "GPU" in openvino,
        "openvino_npu_ready": intel_npu and "NPU" in openvino,
        "torch_xpu_ready": intel_gpu and torch_xpu,
        "device_states": devices,
        "not_applicable": not intel_gpu and not intel_npu and not bool(snapshot.get("intel_cpu")),
    }


def dedup_aliases(aliases: list[dict[str, str]]) -> dict[str, list[str]]:
    """Collapse OpenVINO/Level Zero/torch.xpu aliases onto stable physical keys."""
    result: dict[str, list[str]] = {}
    for item in aliases:
        key = item.get("pci_bdf") or item.get("accel_node") or item.get("sysfs_device")
        if not key:
            raise ValueError("accelerator alias lacks stable physical identity")
        result.setdefault(key, []).append(item.get("alias", "UNKNOWN"))
    return result


def scan_runtime_for_retired_dependencies(root: Path) -> dict[str, Any]:
    hits: list[dict[str, str]] = []
    runtime_roots = ("apps", "src", "bin", "deployment", "libexec")
    retired = ("intel_extension_for_pytorch", "intel/ipex-llm")
    for top in runtime_roots:
        base = root / top
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.name == "fa3_intel_accel_gate.py":
                continue
            try:
                if path.stat().st_size > 1_500_000:
                    continue
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for token in retired:
                if token in text:
                    hits.append({"path": path.relative_to(root).as_posix(), "token": token})
    return {"result": "PASS" if not hits else "FAIL", "blocking_hits": hits}


def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    profile = loadj(root, PROFILE)
    contract = loadj(root, CONTRACT)
    guard = loadj(root, GUARD_PROFILE)
    guard_contract = loadj(root, GUARD_CONTRACT)
    family = loadj(root, FAMILY)
    gui = loadj(root, GUI)
    enforcement = loadj(root, ENFORCEMENT)
    decision = loadj(root, DECISION)
    gate = loadj(root, GATE_RECORD)
    baseline = loadj(root, HARDWARE_BASELINE)
    model_manager = loadj(root, MODEL_MANAGER)
    reference = loadj(root, REFERENCE_EVIDENCE)
    audit_reference = loadj(root, AUDIT_EVIDENCE)
    providers = [loadj(root, p) for p in PROVIDERS]
    providers_by_id = {p["id"]: p for p in providers}
    runtime_audit = scan_runtime_for_retired_dependencies(root)

    gui_provider_ids = {section.get("provider_id") for section in gui.get("sections", [])}
    family_ids = set(family.get("provider_members", []))
    profile_ids = set(profile.get("providers", []))
    guarded: set[str] = set()
    for provider in providers:
        binding = provider.get("accelerator_guard", {})
        if binding.get("required") is True:
            guarded.add(provider["id"])
    openvino = providers_by_id["FA3-PROVIDER-OPENVINO-001"]
    openvino_paths = openvino.get("device_paths", {})
    if openvino_paths.get("GPU", {}).get("guard_required") and openvino_paths.get("NPU", {}).get("guard_required"):
        guarded.add("FA3-PROVIDER-OPENVINO-001")

    no_intel = classify_fixture({})
    intel_cpu = classify_fixture({"intel_cpu": True, "openvino_devices": ["CPU"]})
    intel_gpu = classify_fixture({"intel_gpu": True, "openvino_devices": ["GPU"], "torch_xpu_available": True})
    intel_npu = classify_fixture({"intel_npu": True, "openvino_devices": ["NPU"]})
    busy = classify_fixture({"intel_gpu": True, "openvino_devices": ["GPU"], "external_busy": ["GPU"]})
    alias_fixture = dedup_aliases([
        {"pci_bdf": "0000:03:00.0", "alias": "OPENVINO:GPU.0"},
        {"pci_bdf": "0000:03:00.0", "alias": "LEVEL_ZERO:0"},
        {"pci_bdf": "0000:03:00.0", "alias": "TORCH_XPU:0"},
    ])

    checks = [
        check("profile-canonical", profile.get("status") == "CANONICAL" and profile.get("canonical_root") is False, "Intel accelerator profile is canonical non-root"),
        check("capability-count-stable", profile.get("capability_count") == contract.get("capability_count") == decision.get("capability_count_after") == CAPABILITY_COUNT, "canonical capability count remains unchanged"),
        check("no-new-authority", profile.get("new_architectural_authority") is False and guard.get("new_architectural_authority") is False, "Intel and Guard overlays add no architectural authority"),
        check("baseline-unchanged", baseline.get("portable_minimum", {}).get("gpu", {}).get("vendor") == "NVIDIA" and decision.get("hardware_baseline_effect", "").startswith("NONE"), "optional Intel acceleration does not replace the global hardware floor"),
        check("provider-family-complete", family_ids == PROVIDER_IDS, "provider family contains exactly the canonical Intel provider set"),
        check("profile-provider-complete", profile_ids == PROVIDER_IDS, "profile provider set matches provider family"),
        check("openvino-preferred", profile.get("provider_policy", {}).get("preferred_inference_provider") == "FA3-PROVIDER-OPENVINO-001", "OpenVINO is preferred Intel inference provider"),
        check("guard-authority-boundary", guard.get("authority", {}).get("resource_admission_placement_reservation_lease") == "FA3-AUTH-HOST-RESOURCE-BROKER-001" and guard_contract.get("authority_boundary", {}).get("guard_may_lease") is False, "Accelerator Guard observes/recommends; HRB owns leases"),
        check("guard-default-user-decision", guard.get("default_mode") == "RECOMMEND" and guard.get("conflict_resolution", {}).get("default") == "NOTIFY_USER_AND_LEAVE_PRIORITY_DECISION_TO_USER", "conflict priority defaults to user decision"),
        check("bidirectional-contention", len(guard.get("observation_directions", [])) == 2, "pre-existing and runtime-arriving contention are both covered"),
        check("guard-bindings", ACCEL_GUARD_REQUIRED.issubset(guarded), "all accelerated selectable Intel paths are guard-bound"),
        check("no-silent-fallback", profile.get("fallback_policy", {}).get("silent_accelerator_to_cpu_fallback") == "FORBIDDEN" and openvino.get("fallback_policy", {}).get("silent_gpu_or_npu_to_cpu_fallback") == "FORBIDDEN", "silent accelerator/provider fallback is forbidden"),
        check("compute-runtime-hidden", providers_by_id["FA3-PROVIDER-INTEL-COMPUTE-RUNTIME-001"].get("user_selectable") is False, "Level Zero/OpenCL runtime remains dependency-only"),
        check("neural-compressor-model-manager", providers_by_id["FA3-PROVIDER-INTEL-NC-001"].get("parent_profile") == "FA3-MODEL-MANAGER-001" and providers_by_id["FA3-PROVIDER-INTEL-NC-001"].get("runtime_selector_exposure") is False, "Neural Compressor is a Model Manager optimization provider"),
        check("triton-explicit-opt-in", providers_by_id["FA3-PROVIDER-INTEL-TRITON-XPU-001"].get("activation_mode") == "EXPLICIT_OPT_IN_ONLY" and providers_by_id["FA3-PROVIDER-INTEL-TRITON-XPU-001"].get("auto_install") is False, "Triton XPU remains experimental and explicit opt-in"),
        check("xpum-hardware-conditioned", providers_by_id["FA3-PROVIDER-XPUM-001"].get("activation_mode") == "OPTIONAL_DATA_CENTER_GPU_CONDITIONED", "XPUM is only applicable to supported Intel data center GPUs"),
        check("legacy-denylist", {x.get("name") for x in family.get("retired_new_dependency_denylist", [])} == {"intel_extension_for_pytorch", "ipex-llm"}, "retired IPEX paths are denied as new dependencies"),
        check("runtime-no-retired-dependency", runtime_audit["result"] == "PASS", "runtime surfaces do not depend on retired IPEX paths"),
        check("gui-provider-coverage", PROVIDER_IDS.issubset(gui_provider_ids), "GUI mapping covers every Intel provider"),
        check("gui-no-direct-resource-mutation", gui.get("direct_resource_mutation") is False and gui.get("actions", {}).get("direct_device_lease") == "FORBIDDEN", "GUI is presentation/intent only"),
        check("fixture-no-intel-valid", no_intel["not_applicable"] is True, "hosts without Intel acceleration remain valid and Intel family is not applicable"),
        check("fixture-cpu-valid", intel_cpu["openvino_cpu_ready"] is True, "Intel CPU/OpenVINO CPU capability fixture classifies ready"),
        check("fixture-gpu-npu-busy-valid", intel_gpu["openvino_gpu_ready"] is True and intel_gpu["torch_xpu_ready"] is True and intel_npu["openvino_npu_ready"] is True and busy["device_states"].get("GPU") == "BUSY_EXTERNAL", "GPU/NPU readiness and external contention fixtures classify correctly"),
        check("alias-dedup", list(alias_fixture.keys()) == ["0000:03:00.0"] and len(alias_fixture["0000:03:00.0"]) == 3, "OpenVINO/Level Zero/torch.xpu aliases deduplicate to one physical device"),
    ]

    # Model Manager remains the owner of optimization projection; the provider may be added as an extension without changing model-store semantics.
    checks.append(check("model-manager-authority-preserved", model_manager.get("authority", {}).get("model_routing") == "FA3-AUTH-MODEL-ROUTER-001", "Intel optimization provider does not create a new model authority"))
    checks.append(check("reference-evidence-bound", reference.get("status") == "PASS" and reference.get("current_host_runtime_promotion_claim") is False and audit_reference.get("status") == "PASS", "reference evidence is PASS but explicitly non-promoting for current host"))

    failed = [item for item in checks if item["status"] != "PASS"]
    return {
        "schema": "fa3.intel-accel-gate-report.v1",
        "gate_id": "FA3-INTEL-ACCEL-GATESET-001",
        "result": "FAIL" if failed else "PASS",
        "capability_count": CAPABILITY_COUNT,
        "checks": checks,
        "failed_checks": [item["name"] for item in failed],
        "repository_audit": runtime_audit,
        "current_host_runtime_promotion_claim": False,
        "current_host_runtime_evidence": "PENDING_REAL_CURRENT_HOST_EXECUTION",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default="reports/intel-accel-gate-report.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = evaluate(root)
    report_path = root / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
