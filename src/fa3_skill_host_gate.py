#!/usr/bin/env python3
"""Verify a real Codex skill observation signed by existing FA3 Evidence authority.

A local OBSERVED_PASS report is NOT production admission. Only the existing
PKI/Security Governance role, signed receipt and matching artifact digest
allow this specific current-host evidence gate to pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from fa3_authenticated_approval import (
    DEFAULT_ROOT_CA, DEFAULT_SECURITY_APPROVAL_KEY,
    verify_authenticated_receipt,
)
from fa3_codex_adapter import ADAPTER_ID, ARCHIVE_SHA256, CODEX_VERSION, PROVIDER_ID
from fa3_skill_codex_current_host import REPORT, SCHEMA

RECEIPT_PATH = "evidence/receipts/skill-codex-current-host.json"
EVIDENCE_SCHEMA = "fa3.skill-codex-current-host-evidence-binding.v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def verify_signed_host_evidence(
    root: Path, *,
    expected_source_commit: str,
    root_ca: Path = DEFAULT_ROOT_CA,
    security_public_key: Path = DEFAULT_SECURITY_APPROVAL_KEY,
    strict_host_permissions: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    artifact = Path(root) / REPORT
    receipt_path = Path(root) / RECEIPT_PATH
    if not artifact.is_file() or not receipt_path.is_file():
        return {"result": "FAIL", "errors": ["host observation or signed evidence receipt missing"],
                "current_host_promotion_claim": False}
    try:
        raw = artifact.read_bytes()
        observation = json.loads(raw)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"result": "FAIL", "errors": [f"host evidence malformed: {type(exc).__name__}"],
                "current_host_promotion_claim": False}
    if (not isinstance(observation, dict)
            or observation.get("schema") != SCHEMA
            or observation.get("result") != "OBSERVED_PASS"
            or observation.get("evidence_level") !=
               "UNSIGNED_HOST_OBSERVATION_AWAITING_EXISTING_EVIDENCE_AUTHORITY"
            or observation.get("source_commit") != expected_source_commit
            or observation.get("provider_id") != PROVIDER_ID
            or observation.get("adapter_id") != ADAPTER_ID
            or observation.get("provider_archive_sha256") != ARCHIVE_SHA256
            or observation.get("provider_runtime_version") != CODEX_VERSION
            or observation.get("synthetic_provider") is not False
            or observation.get("global_promotion_claim") is not False
            or observation.get("cross_host_replay_claim") is not False):
        errors.append("real Codex skill observation identity, scope or provenance mismatch")
    for field in ("registry_sha256", "skill_content_sha256",
                  "worker_skill_context_sha256", "provider_binary_sha256"):
        if not SHA256.fullmatch(str(observation.get(field, ""))):
            errors.append("missing or invalid observation digest: " + field)
    registry = Path(root) / "canonical/skill-registry.json"
    if not registry.is_file() or observation.get("registry_sha256") != hashlib.sha256(registry.read_bytes()).hexdigest():
        errors.append("installed registry bytes differ from observed trusted registry digest")
    payload = receipt.get("payload") if isinstance(receipt, dict) else None
    if (not isinstance(payload, dict) or
            payload.get("schema") != EVIDENCE_SCHEMA or
            payload.get("artifact_sha256") != hashlib.sha256(raw).hexdigest() or
            payload.get("subject_id") != "CAP-080" or
            payload.get("provider_id") != PROVIDER_ID or
            payload.get("source_commit") != expected_source_commit or
            not isinstance(payload.get("qualification_id"), str) or
            not payload["qualification_id"]):
        errors.append("signed evidence payload does not bind exact CAP-080 observation")
    if not errors:
        try:
            verdict = verify_authenticated_receipt(
                receipt, expected_receipt_type="CURRENT_HOST_EVIDENCE_SIGNING",
                required_role="CURRENT_HOST_EVIDENCE_SIGNER",
                expected_source_commit=expected_source_commit,
                root_ca=root_ca, security_public_key=security_public_key,
                strict_host_permissions=strict_host_permissions,
            )
            if verdict["qualified"] is not True:
                errors.extend(verdict["findings"])
        except (OSError, ValueError) as exc:
            errors.append("existing FA3 cryptographic evidence verifier unavailable")
    return {
        "schema": "fa3.skill-codex-host-gate-report.v1",
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "source_commit": expected_source_commit,
        "evidence_class": "SIGNED_CURRENT_HOST_CODEX_SKILL_CONSUMER" if not errors else "UNVERIFIED",
        "global_promotion_claim": False,
        "current_host_promotion_claim": False,
        "cross_host_replay_claim": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify existing FA3-signed Codex skill host evidence")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    try:
        commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        report = verify_signed_host_evidence(root, expected_source_commit=commit)
    except Exception as exc:
        report = {"result": "FAIL", "errors": [str(exc)], "global_promotion_claim": False}
    output = root / "reports/skill-codex-host-gate-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
