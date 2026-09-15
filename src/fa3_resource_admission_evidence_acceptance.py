#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA_ID = "FA3-EVIDENCE-ENVELOPE-001"
EXPECTED_EVIDENCE_CLASS = "CURRENT_HOST_ADMISSION"
EXPECTED_GATE_ID = "FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001"
EXPECTED_CLAIM = "CURRENT_HOST_RESOURCE_ADMISSION_PASS"
REQUIRED_NON_CLAIMS = {"GLOBAL_FA3_PROMOTION", "PROVIDER_RUNTIME_E2E"}
ACCEPTANCE_SCHEMA = "fa3.resource-admission-current-host.production-evidence-acceptance.v1"
CAPABILITY_ID = "CAP-006"


class AcceptanceError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AcceptanceError(f"JSON root must be object: {path}")
    return data


def _canonical_payload_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_receipt(receipt: dict[str, Any], *, now_epoch: int | None = None) -> list[str]:
    errors: list[str] = []
    if receipt.get("schema_id") != EXPECTED_SCHEMA_ID:
        errors.append("RECEIPT_SCHEMA_ID_MISMATCH")
    if receipt.get("evidence_class") != EXPECTED_EVIDENCE_CLASS:
        errors.append("RECEIPT_EVIDENCE_CLASS_MISMATCH")
    subject = receipt.get("subject")
    if not isinstance(subject, dict) or subject.get("gate_id") != EXPECTED_GATE_ID:
        errors.append("RECEIPT_GATE_ID_MISMATCH")

    result = receipt.get("result")
    if not isinstance(result, dict):
        errors.append("RECEIPT_RESULT_MISSING")
    else:
        if result.get("status") != "PASS":
            errors.append("RECEIPT_NOT_PASS")
        claims = result.get("claims")
        non_claims = result.get("non_claims")
        if not isinstance(claims, list) or EXPECTED_CLAIM not in claims:
            errors.append("CURRENT_HOST_RESOURCE_ADMISSION_PASS_CLAIM_MISSING")
        if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
            errors.append("REQUIRED_NON_CLAIMS_MISSING")

    payload = receipt.get("payload")
    if not isinstance(payload, dict):
        errors.append("RECEIPT_PAYLOAD_MISSING")
        return errors
    expected_payload_hash = (receipt.get("integrity") or {}).get("payload_sha256")
    if expected_payload_hash != _canonical_payload_hash(payload):
        errors.append("RECEIPT_PAYLOAD_SHA256_MISMATCH")
    if payload.get("errors") not in ([], None):
        errors.append("RECEIPT_PAYLOAD_ERRORS_NOT_EMPTY")

    admission = payload.get("admission")
    if not isinstance(admission, dict) or admission.get("result") != "PASS":
        errors.append("RESOURCE_ADMISSION_RESULT_NOT_PASS")

    attestation = payload.get("host_attestation")
    attestation_sha = payload.get("host_attestation_sha256")
    if not isinstance(attestation, dict) or not isinstance(attestation_sha, str):
        errors.append("HOST_ATTESTATION_BINDING_MISSING")
    else:
        actual = hashlib.sha256(
            json.dumps(attestation, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        if actual != attestation_sha:
            errors.append("HOST_ATTESTATION_SHA256_MISMATCH")

    lease = payload.get("hrb_lease_identity")
    if not isinstance(lease, dict):
        errors.append("HRB_LEASE_IDENTITY_MISSING")
    else:
        if lease.get("status") != "ACTIVE":
            errors.append("HRB_LEASE_NOT_ACTIVE_AT_CAPTURE")
        if lease.get("broker_validation") is not True:
            errors.append("HRB_EXTERNAL_VALIDATION_NOT_PROVEN")
        try:
            expiry = int(lease.get("expires_epoch", 0))
        except (TypeError, ValueError):
            expiry = 0
        check_now = int(time.time()) if now_epoch is None else int(now_epoch)
        if expiry <= check_now:
            errors.append("HRB_LEASE_EXPIRED_BEFORE_ACCEPTANCE_CAPTURE")

    workload = payload.get("workload_resource_envelope")
    if not isinstance(workload, dict) or not str(workload.get("workload_id", "")).strip():
        errors.append("WORKLOAD_ID_MISSING")
    if payload.get("cu_tu_admission_authority") is not False:
        errors.append("CU_TU_AUTHORITY_INVARIANT_VIOLATED")
    if payload.get("cross_metric_compensation") is not False:
        errors.append("CROSS_METRIC_COMPENSATION_INVARIANT_VIOLATED")
    return errors


def build_acceptance(
    receipt_path: Path,
    *,
    now_epoch: int | None = None,
    workflow_run_id: str | None = None,
    workflow_run_url: str | None = None,
    git_sha: str | None = None,
) -> dict[str, Any]:
    receipt_path = receipt_path.resolve()
    receipt = _load(receipt_path)
    errors = validate_receipt(receipt, now_epoch=now_epoch)
    if errors:
        raise AcceptanceError(";".join(errors))

    payload = receipt["payload"]
    workload = payload["workload_resource_envelope"]
    lease = payload["hrb_lease_identity"]
    result = receipt["result"]
    provenance = receipt.get("provenance") or {}

    return {
        "schema": ACCEPTANCE_SCHEMA,
        "id": f"FA3-EVID-RESOURCE-ADMISSION-CURRENT-HOST-{receipt.get('evidence_id', 'UNKNOWN')}",
        "status": "REAL_EXECUTION_PASS_CAPTURED_PER_WORKLOAD_READMISSION_REQUIRED",
        "captured_at": _utc_now(),
        "subject": {
            "capability_id": CAPABILITY_ID,
            "capability": "Resource Fabric",
            "gate_id": EXPECTED_GATE_ID,
            "evidence_level": "CURRENT_HOST_RESOURCE_ADMISSION_PASS",
        },
        "source_evidence": {
            "raw_receipt_committed": False,
            "raw_receipt_location": "GITHUB_ACTIONS_ARTIFACT_OR_LOCAL_RUNTIME_ONLY",
            "receipt_sha256": _sha256_file(receipt_path),
            "receipt_evidence_id": receipt.get("evidence_id"),
            "receipt_generated_at": provenance.get("generated_at"),
            "workload_id": workload.get("workload_id"),
            "lease_expires_epoch": lease.get("expires_epoch"),
            "lease_validated_by_hrb": lease.get("broker_validation") is True,
        },
        "workflow_provenance": {
            "run_id": workflow_run_id,
            "run_url": workflow_run_url,
            "git_sha": git_sha,
            "runner_label_class": "fa3-current-host" if workflow_run_id else None,
        },
        "claims": [EXPECTED_CLAIM],
        "non_claims": sorted(REQUIRED_NON_CLAIMS),
        "archival_semantics": {
            "historical_execution_pass": True,
            "current_or_future_workload_authorization": False,
            "future_workloads_require_fresh_hrb_lease": True,
            "future_workloads_require_fresh_resource_admission": True,
            "expired_source_lease_does_not_invalidate_historical_execution_evidence": True,
        },
        "projection_semantics": {
            "component_pass_claim": True,
            "capability_top_level_status_changed": False,
            "global_promotion_claim": False,
            "provider_runtime_e2e_claim": False,
            "capability_delta": 0,
            "authority_delta": 0,
        },
        "receipt_result_scope": result.get("scope"),
    }


def verify_acceptance(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema") != ACCEPTANCE_SCHEMA:
        errors.append("ACCEPTANCE_SCHEMA_MISMATCH")
    if record.get("status") != "REAL_EXECUTION_PASS_CAPTURED_PER_WORKLOAD_READMISSION_REQUIRED":
        errors.append("ACCEPTANCE_STATUS_MISMATCH")
    subject = record.get("subject")
    if not isinstance(subject, dict) or subject.get("capability_id") != CAPABILITY_ID:
        errors.append("ACCEPTANCE_CAPABILITY_MISMATCH")
    if not isinstance(subject, dict) or subject.get("gate_id") != EXPECTED_GATE_ID:
        errors.append("ACCEPTANCE_GATE_MISMATCH")
    source = record.get("source_evidence")
    if not isinstance(source, dict) or not isinstance(source.get("receipt_sha256"), str):
        errors.append("ACCEPTANCE_RECEIPT_DIGEST_MISSING")
    elif len(source["receipt_sha256"]) != 64:
        errors.append("ACCEPTANCE_RECEIPT_DIGEST_INVALID")
    claims = record.get("claims")
    non_claims = record.get("non_claims")
    if claims != [EXPECTED_CLAIM]:
        errors.append("ACCEPTANCE_CLAIMS_INVALID")
    if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
        errors.append("ACCEPTANCE_NON_CLAIMS_INVALID")
    archival = record.get("archival_semantics")
    if not isinstance(archival, dict) or archival.get("future_workloads_require_fresh_hrb_lease") is not True:
        errors.append("FRESH_HRB_LEASE_REQUIREMENT_MISSING")
    if not isinstance(archival, dict) or archival.get("current_or_future_workload_authorization") is not False:
        errors.append("ARCHIVAL_RECORD_MUST_NOT_AUTHORIZE_FUTURE_WORKLOADS")
    projection = record.get("projection_semantics")
    if not isinstance(projection, dict) or projection.get("global_promotion_claim") is not False:
        errors.append("GLOBAL_PROMOTION_NONCLAIM_MISSING")
    if not isinstance(projection, dict) or projection.get("capability_delta") != 0 or projection.get("authority_delta") != 0:
        errors.append("CAPABILITY_AUTHORITY_DELTA_MUST_BE_ZERO")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture/verify sanitized FA3 current-host resource admission acceptance metadata.")
    parser.add_argument("--receipt")
    parser.add_argument("--acceptance")
    parser.add_argument("--output")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.verify:
        if not args.acceptance:
            parser.error("--verify requires --acceptance")
        record = _load(Path(args.acceptance))
        errors = verify_acceptance(record)
        if errors:
            print(json.dumps({"status": "BLOCKED", "errors": errors}, indent=2))
            return 2
        print(json.dumps({"status": "PASS", "acceptance": str(Path(args.acceptance).resolve())}, indent=2))
        return 0

    if not args.receipt or not args.output:
        parser.error("capture requires --receipt and --output")
    try:
        record = build_acceptance(
            Path(args.receipt),
            workflow_run_id=os.environ.get("GITHUB_RUN_ID"),
            workflow_run_url=(
                f"{os.environ.get('GITHUB_SERVER_URL')}/{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/{os.environ.get('GITHUB_RUN_ID')}"
                if os.environ.get("GITHUB_SERVER_URL")
                and os.environ.get("GITHUB_REPOSITORY")
                and os.environ.get("GITHUB_RUN_ID")
                else None
            ),
            git_sha=os.environ.get("GITHUB_SHA"),
        )
    except (OSError, json.JSONDecodeError, AcceptanceError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "acceptance": str(output.resolve()), "receipt_sha256": record["source_evidence"]["receipt_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
