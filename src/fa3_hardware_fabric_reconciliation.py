#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

RECONCILIATION_ID = "FA3-HARDWARE-FABRIC-RECONCILIATION-001"
HRB_AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
CUDA_CC_MIN = 8.6
CAPABILITY_COUNT = module_active_capability_count(__file__)

PATHS = {
    "reconciliation": "canonical/FA3-HARDWARE-FABRIC-RECONCILIATION-001.json",
    "root_profile": "canonical/profiles/FA3-HW-001.json",
    "root_contract": "canonical/contracts/FA3-HW-CONTRACTS-001.json",
    "portable_profile": "canonical/profiles/FA3-HARDWARE-BASELINE-001.json",
    "discovery_contract": "canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json",
    "mgpu_profile": "canonical/profiles/FA3-HW-MGPU-001.json",
    "hrb_profile": "canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json",
    "runtime_orchestrator": "src/fa3_host_bootstrap_admission_orchestrator.py",
    "admission_gate": "src/fa3_resource_admission_current_host_gate.py",
    "current_host": "src/fa3_current_host.py",
    "gui_device_model": "apps/fa3-control-center/src/SystemDeviceModel.cpp",
    "framework_provider": "canonical/providers/FA3-PROVIDER-FRAMEWORK-NATIVE-CUDA-KERNEL-001.json",
    "openvino_provider": "canonical/providers/FA3-PROVIDER-OPENVINO-001.json",
    "tensorrt_rtx_provider": "canonical/providers/FA3-PROVIDER-TENSORRT-RTX-001.json",
    "ampere_provider": "canonical/providers/FA3-PROVIDER-AMPERE-KERNEL-RUNTIME-001.json",
    "legacy_reference_evidence": "evidence/reference/hardware-portability-ci-2026-09-03.json",
    "legacy_repository_audit": "evidence/reference/hardware-portability-repository-audit-2026-09-03.json",
    "reconciliation_evidence": "evidence/reference/hardware-fabric-reconciliation-2026-09-16.json",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def serialized(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def _float_equal(value: Any, expected: float) -> bool:
    try:
        return abs(float(value) - expected) < 0.0001
    except (TypeError, ValueError):
        return False


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    resolved = {name: root / rel for name, rel in PATHS.items()}

    missing = [str(path.relative_to(root)) for path in resolved.values() if not path.is_file()]
    if missing:
        return {
            "schema": "fa3.hardware-fabric-reconciliation-report.v1",
            "reconciliation_id": RECONCILIATION_ID,
            "result": "FAIL",
            "current_host_status": "PENDING_CURRENT_HOST",
            "global_promotion_claim": False,
            "findings": [finding("HWFR-001", "Required reconciliation surface is missing", missing=missing)],
        }

    data = {
        name: load_json(path)
        for name, path in resolved.items()
        if path.suffix == ".json"
    }
    text = {
        name: path.read_text(encoding="utf-8")
        for name, path in resolved.items()
        if path.suffix != ".json"
    }

    recon = data["reconciliation"]
    if not (
        recon.get("id") == RECONCILIATION_ID
        and recon.get("new_capability") is False
        and recon.get("new_architectural_authority") is False
        and recon.get("capability_count") == CAPABILITY_COUNT
        and recon.get("authority_rules", {}).get("resource_admission_placement_reservation_lease") == HRB_AUTHORITY
        and recon.get("authority_rules", {}).get("provider_records_may_redefine_global_hardware_floor") is False
        and recon.get("authority_rules", {}).get("gui_raw_probe_is_admission_authority") is False
    ):
        findings.append(finding("HWFR-002", "Reconciliation authority contract drift"))

    root_profile = data["root_profile"]
    root_gpu = root_profile.get("minimum_portable_hardware_envelope", {}).get("gpu", {})
    if not (
        root_profile.get("id") == "FA3-HW-001"
        and root_profile.get("authority", {}).get("admission_placement_reservation") == HRB_AUTHORITY
        and root_gpu.get("vendor") == "NVIDIA"
        and _float_equal(root_gpu.get("cuda_compute_capability_min"), CUDA_CC_MIN)
        and root_gpu.get("sku_series_admission_authority") is False
        and root_gpu.get("product_line_pin") == "FORBIDDEN"
        and root_gpu.get("exact_sku_pin") == "FORBIDDEN"
        and root_gpu.get("marketing_identity_required") is False
    ):
        findings.append(finding("HWFR-003", "Root hardware profile is not aligned to the capability-based portable GPU floor"))
    root_profile_text = serialized(root_profile)
    if "NVIDIA_RTX_30_SERIES" in root_profile_text or "architecture_equivalence_without_rtx30_or_newer_series_identity" in root_profile_text:
        findings.append(finding("HWFR-004", "Superseded RTX marketing-series admission semantics remain in the root hardware profile"))

    root_contract = data["root_contract"]
    contract_gpu = root_contract.get("portable_minimum_envelope", {}).get("gpu", {})
    contract_text = serialized(root_contract)
    if not (
        root_contract.get("id") == "FA3-HW-CONTRACTS-001"
        and contract_gpu.get("vendor") == "NVIDIA"
        and _float_equal(contract_gpu.get("cuda_compute_capability_min"), CUDA_CC_MIN)
        and contract_gpu.get("sku_series_is_admission_authority") is False
        and contract_gpu.get("marketing_identity_required") is False
        and "rtx_series_floor" not in contract_gpu
        and "GPU_MINIMUM_RTX_30_SERIES_OR_NEWER" not in contract_text
    ):
        findings.append(finding("HWFR-005", "Root hardware contract still exposes marketing-series admission authority"))

    portable = data["portable_profile"]
    portable_gpu = portable.get("portable_minimum", {}).get("gpu", {})
    if not (
        portable.get("relationship", {}).get("parent") == "FA3-HW-001"
        and portable.get("authority", {}).get("admission_placement_reservation_lease") == HRB_AUTHORITY
        and portable_gpu.get("vendor") == "NVIDIA"
        and _float_equal(portable_gpu.get("cuda_compute_capability_min"), CUDA_CC_MIN)
        and portable_gpu.get("sku_series_admission_authority") is False
        and portable_gpu.get("product_line_pin") == "FORBIDDEN"
    ):
        findings.append(finding("HWFR-006", "Portable hardware baseline drift"))

    discovery = data["discovery_contract"]
    discovery_gpu = discovery.get("portable_minimum_envelope", {})
    if not (
        discovery.get("parent_profile") == "FA3-HARDWARE-BASELINE-001"
        and discovery.get("provider_neutral") is True
        and discovery_gpu.get("gpu_vendor") == "NVIDIA"
        and _float_equal(discovery_gpu.get("cuda_compute_capability_min"), CUDA_CC_MIN)
        and discovery_gpu.get("sku_series_is_admission_authority") is False
        and discovery.get("discovery_semantics", {}).get("stable_accelerator_identity_when_available") == ["DEVICE_UUID", "PCI_BDF"]
    ):
        findings.append(finding("HWFR-007", "Hardware discovery contract is not aligned with the root portable floor and stable identity semantics"))

    mgpu = data["mgpu_profile"]
    mgpu_text = serialized(mgpu)
    if not (
        mgpu.get("relationship", {}).get("parent") == "FA3-HW-001"
        and mgpu.get("authority", {}).get("admission_placement_reservation_lease") == HRB_AUTHORITY
        and "GPU_MARKETING_SERIES_IS_NOT_GLOBAL_ADMISSION_AUTHORITY" in mgpu.get("invariants", [])
        and "NEWER_RTX_GENERATIONS_REMAIN_ELIGIBLE_SUBJECT_TO_RUNTIME_CAPABILITY" not in mgpu_text
    ):
        findings.append(finding("HWFR-008", "Multi-GPU profile hardware semantics drift"))

    hrb = data["hrb_profile"]
    if not (
        hrb.get("id") == "FA3-HOST-RESOURCE-BROKER-001"
        and hrb.get("existing_authority_id") == HRB_AUTHORITY
        and {"admission", "placement", "reservation", "lease"} <= set(hrb.get("authority_scope", []))
        and hrb.get("hardware_portability_baseline_profile") == "FA3-HARDWARE-BASELINE-001"
        and hrb.get("hardware_discovery_contract") == "FA3-HARDWARE-DISCOVERY-CONTRACTS-001"
    ):
        findings.append(finding("HWFR-009", "Host Resource Broker authority/binding drift"))

    orchestrator = text["runtime_orchestrator"]
    for token in ["gpu.cuda_compute_capability", "gpu.vram_gib", "uuid", "pci_bdf", HRB_AUTHORITY]:
        if token not in orchestrator:
            findings.append(finding("HWFR-010", "Runtime orchestrator capability/identity/authority token missing", token=token))
    if "NVIDIA_RTX_30_SERIES" in orchestrator or "RTX_30_SERIES" in orchestrator:
        findings.append(finding("HWFR-011", "Runtime orchestrator contains superseded marketing-series admission logic"))

    admission = text["admission_gate"]
    # The global portable GPU floor remains rooted in FA3-HW-001. Generic workload
    # admission must derive whether an accelerator is required and only then enforce
    # the HRB accelerator lease. A literal global CUDA floor in this gate would
    # incorrectly make CPU-only workloads accelerator-dependent.
    for token in [
        "classify_requirements",
        "accelerator_required",
        "ACCELERATOR_LEASE_SCHEMA",
        "accelerator_uuid",
        "pci_bus_id",
        "CURRENT_HOST_RESOURCE_ADMISSION_PASS",
    ]:
        if token not in admission:
            findings.append(finding("HWFR-012", "Admission gate workload/lease binding token missing", token=token))
    if "CUDA_COMPUTE_CAPABILITY_MIN = 8.6" in admission:
        findings.append(finding("HWFR-012", "Generic admission gate reintroduced a global CUDA floor instead of workload-conditional capability enforcement"))
    if "global_promotion_claim\": True" in admission or "GLOBAL_FA3_PROMOTION\"] if" in admission:
        findings.append(finding("HWFR-013", "Admission gate appears to promote current-host evidence globally"))

    current_host = text["current_host"]
    if "COLLECTED_UNVALIDATED" not in current_host or "pass_claim" not in current_host:
        findings.append(finding("HWFR-014", "Current-host collector does not preserve unvalidated evidence semantics"))

    provider_names = ["framework_provider", "openvino_provider", "tensorrt_rtx_provider", "ampere_provider"]
    for name in provider_names:
        provider = data[name]
        ptext = serialized(provider)
        if provider.get("canonical_root") is not False or provider.get("architectural_authority") is not False:
            findings.append(finding("HWFR-015", "Provider escaped execution-provider authority boundary", provider=provider.get("id")))
        if "HOST-RESOURCE-BROKER" not in ptext and "AUTHORIZED_HRB_LEASE" not in ptext:
            findings.append(finding("HWFR-016", "Provider does not retain HRB admission/lease binding", provider=provider.get("id")))

    trt = data["tensorrt_rtx_provider"]
    if not (
        trt.get("parent_profile") == "FA3-INFERENCE-PORTABILITY-001"
        and trt.get("runtime_cache_compatibility", {}).get("gpu_hardware_rule") == "RUNTIME_GPU_SKU_MUST_BE_EQUIVALENT_TO_CACHED_GPU_SKU"
        and trt.get("canonical_root") is False
    ):
        findings.append(finding("HWFR-017", "TensorRT-RTX provider-local cache compatibility boundary drift"))

    ampere = data["ampere_provider"]
    if not (
        ampere.get("target_architectures") == ["SM86"]
        and ampere.get("hardware_portability", {}).get("hardware_profile_id") == "FA3-HARDWARE-BASELINE-001"
        and ampere.get("hardware_portability", {}).get("exact_gpu_model") == "NOT_REQUIRED"
        and "cannot define the host baseline" in str(ampere.get("normative_constraint", ""))
    ):
        findings.append(finding("HWFR-018", "Provider-local SM86 optimization is not clearly bounded away from the global hardware baseline"))

    gui = text["gui_device_model"]
    for token in ["OBSERVED_NON_AUTHORITATIVE", "ADAPTER_GATED_NON_AUTHORITATIVE", "FA3 hardware discovery / HRB remains authoritative"]:
        if token not in gui:
            findings.append(finding("HWFR-019", "GUI hardware diagnostic authority boundary missing", token=token))
    accelerator_section = gui.split("const QDir devDir", 1)[0]
    if "QStringLiteral(\"DISCOVERED\")" in accelerator_section:
        findings.append(finding("HWFR-020", "GUI CPU/GPU/NPU/DGX raw probe still emits authoritative-looking DISCOVERED status"))

    legacy_reference = data["legacy_reference_evidence"]
    legacy_audit = data["legacy_repository_audit"]
    if not (
        legacy_reference.get("date") == "2026-09-03"
        and legacy_audit.get("date") == "2026-09-03"
        and ("RTX30" in serialized(legacy_reference) or "RTX_30" in serialized(legacy_audit))
    ):
        findings.append(finding("HWFR-021", "Historical portability evidence provenance unexpectedly changed"))

    evidence = data["reconciliation_evidence"]
    superseded = set(evidence.get("supersedes_semantic_content_of", []))
    required_superseded = {
        PATHS["legacy_reference_evidence"],
        PATHS["legacy_repository_audit"],
    }
    if not (
        evidence.get("reconciliation_id") == RECONCILIATION_ID
        and required_superseded <= superseded
        and evidence.get("historical_artifacts_are_preserved") is True
        and evidence.get("current_host_runtime_status") == "PENDING_CURRENT_HOST"
        and evidence.get("current_host_runtime_evidence") is False
        and evidence.get("global_promotion_claim") is False
        and evidence.get("new_capabilities") == 0
        and evidence.get("new_architectural_authorities") == 0
        and evidence.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(finding("HWFR-022", "Reconciliation evidence scope/supersedence drift"))

    current_host_receipt = root / "evidence/receipts/resource-admission-current-host.json"
    report = {
        "schema": "fa3.hardware-fabric-reconciliation-report.v1",
        "reconciliation_id": RECONCILIATION_ID,
        "result": "PASS" if not findings else "FAIL",
        "semantic_scope": "CANONICAL_RUNTIME_ADMISSION_PROVIDER_GUI_EVIDENCE",
        "current_host_status": "PENDING_CURRENT_HOST",
        "current_host_admission_receipt_present": current_host_receipt.is_file(),
        "global_promotion_claim": False,
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "findings": findings,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 hardware fabric semantic reconciliation gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default="reports/hardware-fabric-reconciliation-report.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = audit(root)
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = root / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
