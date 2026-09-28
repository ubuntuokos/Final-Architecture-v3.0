#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_authenticated_approval import (
    GRANT_SCHEMA,
    RECEIPT_SCHEMA,
    SECURITY_AUTHORITY,
    TRUST_PROFILE,
    canonical_bytes,
    certificate_fingerprint,
    sha256_bytes,
)


def _run(argv: list[str]) -> bytes:
    cp = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if cp.returncode != 0:
        raise SystemExit(cp.stderr.decode("utf-8", "replace") or f"command failed: {argv[0]}")
    return cp.stdout


def _sign(private_key: Path, payload: bytes) -> str:
    openssl = shutil.which("openssl")
    if not openssl:
        raise SystemExit("openssl is required")
    cp = subprocess.run(
        [openssl, "dgst", "-sha256", "-sign", str(private_key)],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        raise SystemExit(cp.stderr.decode("utf-8", "replace"))
    return base64.b64encode(cp.stdout).decode("ascii")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def cmd_grant(args: argparse.Namespace) -> int:
    cert_pem = Path(args.certificate).read_text(encoding="utf-8")
    issued = _utcnow()
    grant = {
        "schema": GRANT_SCHEMA,
        "authority": SECURITY_AUTHORITY,
        "identity": args.identity,
        "identity_class": args.identity_class,
        "certificate_sha256": certificate_fingerprint(cert_pem),
        "roles": sorted(set(args.role)),
        "receipt_types": sorted(set(args.receipt_type)),
        "scope": args.scope,
        "issued_at": issued.isoformat(),
        "expires_at": (issued + timedelta(seconds=args.ttl_seconds)).isoformat(),
    }
    signature = _sign(Path(args.security_governance_private_key), canonical_bytes(grant))
    out = {
        "schema": "fa3.signed-authorization-role-grant.v1",
        "authority": SECURITY_AUTHORITY,
        "trust_profile": TRUST_PROFILE,
        "algorithm": "RSA-SHA256",
        "grant": grant,
        "value_b64": signature,
    }
    Path(args.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def cmd_receipt(args: argparse.Namespace) -> int:
    grant_wrapper = json.loads(Path(args.signed_grant).read_text(encoding="utf-8"))
    cert_pem = Path(args.certificate).read_text(encoding="utf-8")
    cert_fp = certificate_fingerprint(cert_pem)
    grant = grant_wrapper.get("grant", {})
    if grant.get("identity") != args.identity:
        raise SystemExit("signed grant identity does not match receipt signer")
    if grant.get("certificate_sha256") != cert_fp:
        raise SystemExit("signed grant certificate fingerprint does not match signer certificate")
    if args.receipt_type not in grant.get("receipt_types", []):
        raise SystemExit("role grant does not cover requested receipt type")
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("approval payload must be a JSON object")
    from fa3_skill_signed_authority import KIND_POLICY
    skill_types = {item[0] for item in KIND_POLICY.values()}
    if args.receipt_type in skill_types:
        if grant.get("scope") != "FA3_SKILL_RUNTIME":
            raise SystemExit("skill receipt requires an FA3_SKILL_RUNTIME grant")
        if (payload.get("schema") != "fa3.skill-authority-binding.v1"
                or payload.get("kind") not in KIND_POLICY
                or KIND_POLICY[payload["kind"]][0] != args.receipt_type
                or not isinstance(payload.get("task_id"), str) or not payload["task_id"]
                or not isinstance(payload.get("claim"), dict)):
            raise SystemExit("skill receipt requires an exact typed task-bound claim")
    issued = _utcnow()
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS",
        "receipt_id": args.receipt_id,
        "receipt_type": args.receipt_type,
        "source_commit": args.source_commit,
        "issued_at": issued.isoformat(),
        "expires_at": (issued + timedelta(seconds=args.ttl_seconds)).isoformat(),
        "nonce": args.nonce,
        "single_use": True,
        "content_sha256": sha256_bytes(canonical_bytes(payload)),
        "payload": payload,
        "signer": {
            "identity": args.identity,
            "certificate_sha256": cert_fp,
            "certificate_pem": cert_pem,
            "intermediate_certificates_pem": [
                Path(path).read_text(encoding="utf-8") for path in args.intermediate
            ],
        },
        "signature": {"algorithm": "RSA-SHA256", "value_b64": ""},
        "authorization": grant_wrapper,
    }
    signed = {
        "schema": receipt["schema"],
        "status": receipt["status"],
        "receipt_id": receipt["receipt_id"],
        "receipt_type": receipt["receipt_type"],
        "source_commit": receipt["source_commit"],
        "issued_at": receipt["issued_at"],
        "expires_at": receipt["expires_at"],
        "nonce": receipt["nonce"],
        "single_use": receipt["single_use"],
        "content_sha256": receipt["content_sha256"],
        "payload": receipt["payload"],
        "signer_identity": receipt["signer"]["identity"],
        "signer_certificate_sha256": receipt["signer"]["certificate_sha256"],
    }
    receipt["signature"]["value_b64"] = _sign(Path(args.private_key), canonical_bytes(signed))
    Path(args.output).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue FA3 authenticated approval grants/receipts")
    sub = parser.add_subparsers(dest="command", required=True)

    grant = sub.add_parser("grant", help="Create Security Governance signed role grant")
    grant.add_argument("--identity", required=True)
    grant.add_argument("--identity-class", choices=["HUMAN", "WORKLOAD"], required=True)
    grant.add_argument("--scope", choices=["FA3_RELEASE_ACCEPTANCE", "FA3_SKILL_RUNTIME"], default="FA3_RELEASE_ACCEPTANCE")
    grant.add_argument("--certificate", required=True)
    grant.add_argument("--role", action="append", required=True)
    grant.add_argument("--receipt-type", action="append", required=True)
    grant.add_argument("--ttl-seconds", type=int, default=3600)
    grant.add_argument("--security-governance-private-key", required=True)
    grant.add_argument("--output", required=True)
    grant.set_defaults(func=cmd_grant)

    receipt = sub.add_parser("receipt", help="Create signer-authenticated approval receipt")
    receipt.add_argument("--identity", required=True)
    receipt.add_argument("--certificate", required=True)
    receipt.add_argument("--private-key", required=True)
    receipt.add_argument("--intermediate", action="append", default=[])
    receipt.add_argument("--signed-grant", required=True)
    receipt.add_argument("--receipt-type", required=True)
    receipt.add_argument("--receipt-id", required=True)
    receipt.add_argument("--source-commit", required=True)
    receipt.add_argument("--nonce", required=True)
    receipt.add_argument("--payload", required=True)
    receipt.add_argument("--ttl-seconds", type=int, default=1800)
    receipt.add_argument("--output", required=True)
    receipt.set_defaults(func=cmd_receipt)

    args = parser.parse_args()
    if args.ttl_seconds <= 0:
        raise SystemExit("ttl-seconds must be positive")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
