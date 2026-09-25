#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from fa3_resource_admission_policy import classify_requirements, validate_workload_requirements
from fa3_resource_evidence_normalization_gate import gate as normalization_gate, validate_evidence_envelope

GATE_ID = "FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001"
RECEIPT = Path("evidence/receipts/resource-admission-current-host.json")
CLAIM = "CURRENT_HOST_RESOURCE_ADMISSION_PASS"
ACCELERATOR_LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
ADMISSION_AUTH_SCHEMA = "fa3.hrb-admission-authorization.v1"
HRB_AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
_BDF_RE = re.compile(r"^(?P<domain>[0-9a-fA-F]{4,8}):(?P<bus>[0-9a-fA-F]{2}):(?P<device>[0-9a-fA-F]{2})\.(?P<function>[0-7])$")


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def normalize_bdf(value: Any) -> str:
    text = str(value or "").strip().lower()
    match = _BDF_RE.fullmatch(text)
    if not match:
        return text
    return f"{match.group('domain')[-4:].lower()}:{match.group('bus').lower()}:{match.group('device').lower()}.{match.group('function')}"


def purpose_matches_workload(purpose: Any, workload_id: Any) -> bool:
    purpose_text = str(purpose or "").strip().lower()
    workload_text = str(workload_id or "").strip().lower()
    return bool(workload_text) and (purpose_text == workload_text or workload_text in purpose_text)


def approx_equal(left: Any, right: Any, tolerance: float = 0.002) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False


def _validate_hrb_authorization(
    payload: dict[str, Any],
    workload_id: Any,
    attestation: dict[str, Any],
    requested_classes: list[str],
    accelerator_required: bool,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    authorization = payload.get("hrb_authorization", {})
    if not isinstance(authorization, dict):
        authorization = {}
    if (
        authorization.get("authority") != HRB_AUTHORITY
        or authorization.get("status") != "VALID"
        or not str(authorization.get("authorization_id", "")).strip()
        or authorization.get("broker_validation") is not True
    ):
        findings.append(finding("RA-HOST-012", "Current workload lacks externally validated HRB admission authorization"))
        return findings
    if str(authorization.get("workload_id", "")) != str(workload_id or ""):
        findings.append(finding("RA-HOST-015", "HRB admission authorization is not workload-scope-bound"))
    source = authorization.get("source")
    if source == "ADMISSION_AUTHORIZATION":
        if authorization.get("schema") != ADMISSION_AUTH_SCHEMA:
            findings.append(finding("RA-HOST-027", "Generic HRB admission authorization schema mismatch"))
        if authorization.get("host") != attestation.get("host"):
            findings.append(finding("RA-HOST-028", "Generic HRB admission authorization host binding mismatch"))
        if authorization.get("workload_envelope_sha256") != payload.get("workload_resource_envelope_sha256"):
            findings.append(finding("RA-HOST-029", "Generic HRB admission authorization workload digest mismatch"))
        if authorization.get("requested_resource_classes") != requested_classes or authorization.get("accelerator_required") is not accelerator_required:
            findings.append(finding("RA-HOST-030", "Generic HRB admission authorization resource scope mismatch"))
        try:
            if int(authorization.get("expires_epoch", 0)) <= int(time.time()):
                findings.append(finding("RA-HOST-031", "Generic HRB admission authorization expired"))
        except (TypeError, ValueError):
            findings.append(finding("RA-HOST-031", "Generic HRB admission authorization expiry invalid"))
        if accelerator_required:
            findings.append(finding("RA-HOST-032", "Accelerator workload must use accelerator lease as its HRB authorization source"))
    elif source == "ACCELERATOR_EXECUTION_LEASE":
        if not accelerator_required:
            findings.append(finding("RA-HOST-033", "CPU-only workload cannot use accelerator lease as authorization source"))
    else:
        findings.append(finding("RA-HOST-034", "Unknown HRB admission authorization source"))
    return findings


def _validate_accelerator_lease(
    payload: dict[str, Any],
    attestation: dict[str, Any],
    profile: dict[str, Any],
    workload_id: Any,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lease = payload.get("hrb_lease_identity", {})
    if not isinstance(lease, dict):
        lease = {}
    if (
        lease.get("schema") != ACCELERATOR_LEASE_SCHEMA
        or lease.get("issuer") != "FA3-HOST-RESOURCE-BROKER-001"
        or lease.get("status") != "ACTIVE"
        or lease.get("broker_validation") is not True
    ):
        findings.append(finding("RA-HOST-012", "Accelerator workload lacks a valid externally validated HRB accelerator lease"))
        return findings
    try:
        if int(lease.get("expires_epoch", 0)) <= int(time.time()):
            findings.append(finding("RA-HOST-013", "HRB accelerator lease is expired at gate evaluation time"))
    except (TypeError, ValueError):
        findings.append(finding("RA-HOST-013", "HRB accelerator lease expiry is invalid"))

    if str(lease.get("host", "")) != str(attestation.get("host", "")) or not str(attestation.get("host", "")):
        findings.append(finding("RA-HOST-014", "HRB accelerator lease host is not bound to the live attested host"))
    if not purpose_matches_workload(lease.get("purpose"), workload_id):
        findings.append(finding("RA-HOST-015", "HRB accelerator lease purpose is not bound to the workload id"))

    accelerators = attestation.get("accelerators", [])
    if not isinstance(accelerators, list):
        accelerators = []
    uuid = lease.get("accelerator_uuid")
    bdf = normalize_bdf(lease.get("pci_bus_id"))
    matches = [
        accelerator for accelerator in accelerators
        if isinstance(accelerator, dict)
        and accelerator.get("uuid") == uuid
        and normalize_bdf(accelerator.get("pci_bdf")) == bdf
    ]
    if len(matches) != 1:
        findings.append(finding("RA-HOST-016", "HRB lease UUID/PCI BDF is not bound to exactly one live accelerator"))
        return findings

    live = matches[0]
    metrics = profile.get("metrics", {}) if isinstance(profile, dict) else {}
    physical_gib = int(live.get("memory_total_bytes", 0)) / (1024 ** 3)
    try:
        lease_memory_bytes = int(lease.get("memory_max_bytes", 0))
    except (TypeError, ValueError):
        lease_memory_bytes = 0
    lease_gib = lease_memory_bytes / (1024 ** 3)
    effective_gib = min(physical_gib, lease_gib)
    if lease_memory_bytes <= 0:
        findings.append(finding("RA-HOST-017", "HRB accelerator lease memory budget is invalid"))
    if not (
        approx_equal(metrics.get("gpu.physical_vram_gib"), physical_gib)
        and approx_equal(metrics.get("gpu.lease_memory_gib"), lease_gib)
        and approx_equal(metrics.get("gpu.vram_gib"), effective_gib)
    ):
        findings.append(finding(
            "RA-HOST-018",
            "Compute Profile accelerator memory is not bounded by the HRB lease budget",
            physical_vram_gib=physical_gib,
            lease_memory_gib=lease_gib,
            expected_effective_vram_gib=effective_gib,
            observed_effective_vram_gib=metrics.get("gpu.vram_gib"),
        ))
    if metrics.get("gpu.device_uuid") != live.get("uuid") or normalize_bdf(metrics.get("gpu.pci_bdf")) != normalize_bdf(live.get("pci_bdf")):
        findings.append(finding("RA-HOST-019", "Compute Profile accelerator identity differs from the HRB-selected live accelerator"))
    return findings


def validate_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    envelope_errors = validate_evidence_envelope(receipt)
    if envelope_errors:
        return [finding("RA-HOST-001", "Evidence Envelope validation failed", errors=envelope_errors)]

    if receipt.get("evidence_class") != "CURRENT_HOST_ADMISSION":
        findings.append(finding("RA-HOST-002", "Evidence class is not CURRENT_HOST_ADMISSION"))
    subject = receipt.get("subject", {})
    if subject.get("profile_id") != "FA3-RESOURCE-ADMISSION-CONTRACTS-001" or subject.get("gate_id") != GATE_ID:
        findings.append(finding("RA-HOST-003", "Subject profile/gate binding mismatch"))

    result = receipt.get("result", {})
    if result.get("status") != "PASS" or CLAIM not in result.get("claims", []):
        findings.append(finding("RA-HOST-004", "Current-host resource admission PASS claim missing"))
    if "GLOBAL_FA3_PROMOTION" not in result.get("non_claims", []):
        findings.append(finding("RA-HOST-005", "Receipt does not explicitly deny global promotion claim"))

    payload = receipt.get("payload", {})
    if payload.get("schema") != "fa3.resource-admission-current-host.payload.v1":
        findings.append(finding("RA-HOST-006", "Payload schema mismatch"))
    attestation = payload.get("host_attestation", {})
    if attestation.get("schema") != "fa3.host-attestation.v1" or attestation.get("secret_collection") != "PROHIBITED":
        findings.append(finding("RA-HOST-007", "Live host attestation identity/secret boundary mismatch"))

    attestation_sha = payload.get("host_attestation_sha256")
    recomputed_attestation_sha = canonical_sha256(attestation) if isinstance(attestation, dict) else None
    profile = payload.get("compute_profile", {})
    if not attestation_sha or attestation_sha != recomputed_attestation_sha or profile.get("host_attestation_sha256") != attestation_sha:
        findings.append(finding("RA-HOST-008", "Compute Profile is not cryptographically bound to the inline Host Attestation"))

    workload = payload.get("workload_resource_envelope")
    workload_id = workload.get("workload_id") if isinstance(workload, dict) else None
    requirements = workload.get("requirements", []) if isinstance(workload, dict) else []
    if not isinstance(workload, dict) or workload.get("schema") != "fa3.workload-resource-envelope.v1" or not str(workload_id or "").strip():
        findings.append(finding("RA-HOST-009", "Workload Resource Envelope identity is invalid"))
    requirement_errors = validate_workload_requirements(requirements)
    if requirement_errors:
        findings.append(finding("RA-HOST-011", "Workload requirements are invalid", errors=requirement_errors))

    requested_classes, accelerator_required = classify_requirements(requirements)
    if payload.get("requested_resource_classes") != requested_classes:
        findings.append(finding("RA-HOST-024", "Receipt requested_resource_classes does not match workload requirements", expected=requested_classes))
    if payload.get("accelerator_required") is not accelerator_required:
        findings.append(finding("RA-HOST-025", "Receipt accelerator_required does not match workload requirements", expected=accelerator_required))

    findings.extend(_validate_hrb_authorization(payload, workload_id, attestation, requested_classes, accelerator_required))
    if accelerator_required:
        findings.extend(_validate_accelerator_lease(payload, attestation, profile, workload_id))
    else:
        lease = payload.get("hrb_lease_identity")
        if isinstance(lease, dict) and any(value not in (None, "", False) for value in lease.values()):
            findings.append(finding("RA-HOST-026", "CPU-only workload unexpectedly carries accelerator lease identity"))

    admission = payload.get("admission", {})
    if admission.get("result") != "PASS" or admission.get("decision", {}).get("reason_code") != "RESOURCE_ENVELOPE_AND_HRB_PASS":
        findings.append(finding("RA-HOST-020", "Multidimensional workload/resource admission did not PASS"))
    if payload.get("errors") not in ([], None):
        findings.append(finding("RA-HOST-021", "Collector reported current-host resource admission errors", errors=payload.get("errors")))
    if payload.get("cross_metric_compensation") is not False or payload.get("cu_tu_admission_authority") is not False:
        findings.append(finding("RA-HOST-022", "Resource-admission semantics were weakened"))
    return findings


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    parent = normalization_gate(root)
    if parent.get("result") != "PASS":
        findings.append(finding("RA-HOST-000", "Parent resource/evidence normalization gate failed"))
    path = receipt_path or (root / RECEIPT)
    try:
        findings.extend(validate_receipt(loadj(path)))
    except Exception as exc:
        findings.append(finding("RA-HOST-023", "Current-host resource admission receipt missing or unreadable", error=repr(exc)))
    report = {
        "schema_id": "FA3-ENFORCEMENT-RESULT-001",
        "schema_version": "1.0.0",
        "gate": {"id": GATE_ID, "mode": "CURRENT_HOST"},
        "result": "PASS" if not findings else "BLOCKED",
        "decision": {
            "reason_code": "CURRENT_HOST_RESOURCE_ADMISSION_PASS" if not findings else "CURRENT_HOST_RESOURCE_ADMISSION_BLOCKED",
            "promotion_effect": "COMPONENT_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED",
            "exit_code": 0 if not findings else 2,
        },
        "findings": findings,
        "evidence_refs": [str(path)],
        "evidence_level": CLAIM if not findings else None,
        "global_promotion_claim": False,
    }
    out = root / "reports/resource-admission-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FA3 current-host resource admission evidence")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--receipt")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt = Path(args.receipt).resolve() if args.receipt else None
    report = gate(root, receipt)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return int(report["decision"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
