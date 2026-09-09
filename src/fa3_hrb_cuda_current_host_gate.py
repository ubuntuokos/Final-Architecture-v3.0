#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

GATE_ID = "FA3-GATE-HRB-CUDA-CURRENT-HOST-001"
EVIDENCE_LEVEL = "SCOPED_CURRENT_HOST_HRB_V1_0_AUTHENTICATED_CUDA_V1_2_PRODUCTION_E2E_PASS"
ATTESTATION = "evidence/reference/hrb-cuda-current-host-digest-attestation-2026-09-09.json"
RECEIPT = "evidence/receipts/hrb-cuda-current-host.json"
EXPECTED_HOST = "horvath-precisiontower7910"
EXPECTED = {
    "HRB-CONFORMANCE": {
        "sha256": "4249bde6a6312f5264d308ec222c72e9847fdf90dcf04be5392ab555d6ddf3f4",
        "profile": "FA3-HOST-RESOURCE-BROKER-001",
        "version": "1.0.0",
    },
    "CUDA-BROKER-REGRESSION": {
        "sha256": "b94a1c083f8bd0f25fae358a8be84515a6c04e1f8a6f03152af4bef399ad4f5b",
        "profile": "FA3-CUDA-PY-001",
        "version": "1.2.0",
    },
    "CUDA-AUTH-E2E": {
        "sha256": "c98a44673507f52d1c92dfff91e673fc84bb8963fef87c34c5cdc9105688f57c",
        "profile": "FA3-CUDA-PY-001",
        "version": "1.2.0",
    },
    "HRB-CUDA-EVIDENCE-INTEGRATION-GATE": {
        "sha256": "5d42396b229cea0a371289a09f7a856955c961894666fadcb5aeb9457325cfee",
        "profile": None,
        "version": None,
    },
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _artifact_map(value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("id"): item for item in value.get("artifacts", []) if isinstance(item, dict) and item.get("id")}


def validate_attestation(attestation: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str) -> None:
        findings.append({"code": code, "severity": "P0", "message": message})

    if not (
        attestation.get("schema") == "fa3.external-current-host-digest-attestation.v1"
        and attestation.get("status") == "PASS"
        and attestation.get("host") == EXPECTED_HOST
        and attestation.get("raw_artifacts_committed") is False
        and attestation.get("scope") == "HRB_V1_0_LEASE_AUTH_AND_CUDA_V1_2_EXECUTION_ONLY"
    ):
        fail("HRB-CUDA-HOST-001", "digest attestation identity/scope mismatch")

    artifacts = _artifact_map(attestation)
    if set(artifacts) != set(EXPECTED):
        fail("HRB-CUDA-HOST-002", "digest attestation artifact set mismatch")
    else:
        for evidence_id, expected in EXPECTED.items():
            item = artifacts[evidence_id]
            if item.get("sha256") != expected["sha256"] or item.get("status") != "PASS" or not _digest(item.get("sha256")):
                fail("HRB-CUDA-HOST-003", f"{evidence_id} immutable digest/status mismatch")
            if expected["profile"] is not None and (
                item.get("profile") != expected["profile"] or item.get("version") != expected["version"]
            ):
                fail("HRB-CUDA-HOST-004", f"{evidence_id} profile/version mismatch")

    reconciliation = attestation.get("canonical_reconciliation", {})
    if not (
        reconciliation.get("hrb_profile_current_version") == "1.4.0"
        and reconciliation.get("hrb_v1_4_full_runtime_promoted") is False
        and reconciliation.get("cuda_profile_current_version") == "1.2.0"
        and reconciliation.get("cuda_scoped_component_promotion_eligible") is True
        and reconciliation.get("capability_count") == 143
        and reconciliation.get("global_promotion_claim") is False
    ):
        fail("HRB-CUDA-HOST-005", "canonical version/promotion reconciliation drift")
    return findings


def validate_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str) -> None:
        findings.append({"code": code, "severity": "P0", "message": message})

    if not (
        receipt.get("schema") == "fa3.hrb-cuda-current-host-receipt.v1"
        and receipt.get("status") == "PASS"
        and receipt.get("evidence_level") == EVIDENCE_LEVEL
        and receipt.get("host") == EXPECTED_HOST
        and receipt.get("live_source_reverified") is True
    ):
        fail("HRB-CUDA-HOST-006", "live current-host receipt identity/status mismatch")

    scope = receipt.get("scope", {})
    if not (
        scope.get("hrb_implementation_version") == "1.0.0"
        and scope.get("cuda_python_version") == "1.2.0"
        and scope.get("canonical_hrb_profile_version") == "1.4.0"
        and scope.get("hrb_v1_4_full_runtime_claim") is False
        and scope.get("cuda_component_promotion_eligible") is True
        and scope.get("global_promotion_claim") is False
    ):
        fail("HRB-CUDA-HOST-007", "component/current-canonical scope boundary mismatch")

    artifacts = _artifact_map(receipt)
    if set(artifacts) != set(EXPECTED):
        fail("HRB-CUDA-HOST-008", "live receipt artifact set mismatch")
    else:
        for evidence_id, expected in EXPECTED.items():
            item = artifacts[evidence_id]
            if not (
                item.get("sha256") == expected["sha256"]
                and item.get("status") == "PASS"
                and item.get("byte_reverified") is True
            ):
                fail("HRB-CUDA-HOST-008", f"{evidence_id} live byte verification mismatch")

    registry = {item.get("id"): item for item in receipt.get("external_registry_records", []) if isinstance(item, dict)}
    required_registry = {"HRB-CONFORMANCE", "CUDA-BROKER-REGRESSION", "CUDA-AUTH-E2E"}
    if set(registry) != required_registry:
        fail("HRB-CUDA-HOST-009", "external current-host Evidence Registry record set mismatch")
    else:
        for evidence_id in required_registry:
            expected = EXPECTED[evidence_id]
            item = registry[evidence_id]
            if not (
                item.get("status") == "PASS"
                and item.get("host") == EXPECTED_HOST
                and item.get("sha256") == expected["sha256"]
                and item.get("profile") == expected["profile"]
                and item.get("version") == expected["version"]
            ):
                fail("HRB-CUDA-HOST-009", f"{evidence_id} external registry projection mismatch")

    if not (
        receipt.get("authority_boundary") == {
            "hrb": "ADMISSION_PLACEMENT_RESERVATION_LEASE_AUTHORITY",
            "cuda_python": "EXECUTION_PROVIDER_NOT_AUTHORITY",
        }
        and receipt.get("capability_count_after") == 143
        and receipt.get("new_capabilities") == 0
        and receipt.get("new_architectural_authorities") == 0
        and receipt.get("global_promotion_claim") is False
    ):
        fail("HRB-CUDA-HOST-010", "authority/capability/global-promotion invariant drift")
    return findings


def reference_gate(root: Path) -> dict[str, Any]:
    try:
        attestation = _load(root / ATTESTATION)
        findings = validate_attestation(attestation)
    except Exception as exc:
        findings = [{"code": "HRB-CUDA-HOST-000", "severity": "P0", "message": "digest attestation missing or unreadable", "error": repr(exc)}]
    return {
        "schema": "fa3.hrb-cuda-current-host-reference-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "promotion_effect": "REFERENCE_DIGEST_ATTESTATION_ONLY_GLOBAL_PROMOTION_UNCHANGED",
    }


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    path = receipt_path or (root / RECEIPT)
    try:
        receipt = _load(path)
        findings = validate_receipt(receipt)
    except Exception as exc:
        receipt = {}
        findings = [{"code": "HRB-CUDA-HOST-000", "severity": "P0", "message": "live current-host HRB/CUDA receipt missing or unreadable", "error": repr(exc)}]
    report = {
        "schema": "fa3.hrb-cuda-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "evidence_level": receipt.get("evidence_level"),
        "scope": "HRB_V1_0_LEASE_AUTH_AND_CUDA_V1_2_EXECUTION_ONLY",
        "canonical_hrb_v1_4_full_runtime_promotion_claim": False,
        "promotion_effect": "COMPONENT_SCOPED_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED",
    }
    _write(root / "reports/hrb-cuda-current-host-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate scoped FA3 HRB/CUDA current-host evidence")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--receipt")
    parser.add_argument("--reference-only", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.reference_only:
        report = reference_gate(root)
    else:
        receipt_path = Path(args.receipt).resolve() if args.receipt else None
        report = gate(root, receipt_path)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
