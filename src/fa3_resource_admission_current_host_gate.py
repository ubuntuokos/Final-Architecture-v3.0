#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_resource_evidence_normalization_gate import gate as normalization_gate, validate_evidence_envelope

GATE_ID = "FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001"
RECEIPT = Path("evidence/receipts/resource-admission-current-host.json")
CLAIM = "CURRENT_HOST_RESOURCE_ADMISSION_PASS"
FORBIDDEN_METRICS = {"cu", "tu", "compute_unit", "tensor_unit", "aggregate.cu", "aggregate.tu"}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def validate_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    envelope_errors = validate_evidence_envelope(receipt)
    if envelope_errors:
        findings.append(finding("RA-HOST-001", "Evidence Envelope validation failed", errors=envelope_errors))
        return findings

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
    if not payload.get("host_attestation_sha256") or payload.get("compute_profile", {}).get("host_attestation_sha256") != payload.get("host_attestation_sha256"):
        findings.append(finding("RA-HOST-008", "Compute Profile is not bound to Host Attestation SHA-256"))

    workload = payload.get("workload_resource_envelope")
    requirements = workload.get("requirements", []) if isinstance(workload, dict) else []
    if not isinstance(requirements, list) or not requirements:
        findings.append(finding("RA-HOST-009", "Workload Resource Envelope has no requirements"))
    else:
        forbidden = sorted({item.get("metric") for item in requirements if isinstance(item, dict)} & FORBIDDEN_METRICS)
        if forbidden:
            findings.append(finding("RA-HOST-010", "CU/TU scalar diagnostics used as admission requirements", metrics=forbidden))

    lease = payload.get("hrb_lease_identity", {})
    if lease.get("schema") != "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1" or lease.get("issuer") != "FA3-HOST-RESOURCE-BROKER-001" or lease.get("broker_validation") is not True:
        findings.append(finding("RA-HOST-011", "HRB lease identity/external broker validation mismatch"))
    accelerators = attestation.get("accelerators", [])
    uuid = lease.get("accelerator_uuid")
    bdf = str(lease.get("pci_bus_id", "")).lower()
    if bdf.startswith("00000000:"):
        bdf = bdf[5:]
    matches = [a for a in accelerators if a.get("uuid") == uuid and str(a.get("pci_bdf", "")).lower() == bdf]
    if len(matches) != 1:
        findings.append(finding("RA-HOST-012", "HRB lease UUID/PCI BDF is not bound to exactly one live accelerator"))

    admission = payload.get("admission", {})
    if admission.get("result") != "PASS" or admission.get("decision", {}).get("reason_code") != "RESOURCE_ENVELOPE_AND_HRB_PASS":
        findings.append(finding("RA-HOST-013", "Multidimensional workload/resource admission did not PASS"))
    if payload.get("cross_metric_compensation") is not False or payload.get("cu_tu_admission_authority") is not False:
        findings.append(finding("RA-HOST-014", "Resource-admission semantics were weakened"))

    return findings


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    parent = normalization_gate(root)
    if parent.get("result") != "PASS":
        findings.append(finding("RA-HOST-000", "Parent resource/evidence normalization gate failed"))
    path = receipt_path or (root / RECEIPT)
    try:
        receipt = loadj(path)
        findings.extend(validate_receipt(receipt))
    except Exception as exc:
        receipt = {}
        findings.append(finding("RA-HOST-015", "Current-host resource admission receipt missing or unreadable", error=repr(exc)))
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
