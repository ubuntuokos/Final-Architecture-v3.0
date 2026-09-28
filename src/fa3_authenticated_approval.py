#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

RECEIPT_SCHEMA = "fa3.authenticated-approval-receipt.v2"
GRANT_SCHEMA = "fa3.authorization-role-grant.v1"
SECURITY_AUTHORITY = "FA3-AUTH-SECURITY-GOV-001"
TRUST_PROFILE = "FA3-TRUST-PKI-001"
DEFAULT_ROOT_CA = Path("/var/lib/fa3-step-ca/certs/root_ca.crt")
DEFAULT_SECURITY_APPROVAL_KEY = Path("/etc/fa3/trust/security-governance-approval.pub")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
NONCE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")

REQUIREMENTS: dict[str, dict[str, Any]] = {
    "host-fingerprint.json": {
        "receipt_type": "CURRENT_HOST_EVIDENCE_SIGNING",
        "role": "CURRENT_HOST_EVIDENCE_SIGNER",
    },
    "source-exclusion-receipt.json": {
        "receipt_type": "SOURCE_EXCLUSION_SIGNING",
        "role": "CURRENT_HOST_EVIDENCE_SIGNER",
    },
    "release-integrity.json": {
        "receipt_type": "RELEASE_INTEGRITY",
        "role": "RELEASE_INTEGRITY_SIGNER",
    },
    "independent-review.json": {
        "receipt_type": "INDEPENDENT_REVIEW",
        "role": "INDEPENDENT_REVIEWER",
        "independent": True,
    },
    "human-promotion-receipt.json": {
        "receipt_type": "HUMAN_PROMOTION",
        "role": "RELEASE_PROMOTER",
        "human": True,
    },
}


class ApprovalVerificationError(ValueError):
    pass


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _run(argv: list[str], *, input_bytes: bytes | None = None, timeout: int = 15) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            argv,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ApprovalVerificationError(f"verification command failed: {type(exc).__name__}") from exc


def _require_openssl() -> str:
    path = shutil.which("openssl")
    if not path:
        raise ApprovalVerificationError("openssl verifier unavailable")
    return path


def _write(path: Path, data: str | bytes) -> None:
    path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)


def certificate_fingerprint(pem: str) -> str:
    openssl = _require_openssl()
    cp = _run([openssl, "x509", "-outform", "DER"], input_bytes=pem.encode("utf-8"))
    if cp.returncode != 0 or not cp.stdout:
        raise ApprovalVerificationError("signer certificate is not valid X.509 PEM")
    return sha256_bytes(cp.stdout)


def _verify_certificate(
    leaf_pem: str,
    intermediates: list[str],
    identity: str,
    root_ca: Path,
) -> str:
    openssl = _require_openssl()
    if not root_ca.is_file():
        raise ApprovalVerificationError("FA3 trust root unavailable")
    with tempfile.TemporaryDirectory(prefix="fa3-approval-cert-") as td:
        temp = Path(td)
        leaf = temp / "leaf.pem"
        _write(leaf, leaf_pem)
        argv = [openssl, "verify", "-CAfile", str(root_ca)]
        if intermediates:
            chain = temp / "intermediates.pem"
            _write(chain, "\n".join(intermediates) + "\n")
            argv.extend(["-untrusted", str(chain)])
        argv.append(str(leaf))
        cp = _run(argv)
        if cp.returncode != 0:
            raise ApprovalVerificationError("signer certificate chain verification failed")
        san = _run([openssl, "x509", "-in", str(leaf), "-noout", "-ext", "subjectAltName"])
        if san.returncode != 0:
            raise ApprovalVerificationError("signer certificate SAN unavailable")
        text = san.stdout.decode("utf-8", "replace")
        if f"URI:{identity}" not in text:
            raise ApprovalVerificationError("signer identity is not bound by certificate URI SAN")
    return certificate_fingerprint(leaf_pem)


def _verify_signature_with_certificate(
    leaf_pem: str,
    payload: bytes,
    signature_b64: str,
) -> None:
    openssl = _require_openssl()
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except Exception as exc:
        raise ApprovalVerificationError("receipt signature is not valid base64") from exc
    if not signature:
        raise ApprovalVerificationError("receipt signature is empty")
    with tempfile.TemporaryDirectory(prefix="fa3-approval-signature-") as td:
        temp = Path(td)
        leaf = temp / "leaf.pem"
        public = temp / "public.pem"
        data = temp / "payload.bin"
        sig = temp / "signature.bin"
        _write(leaf, leaf_pem)
        _write(data, payload)
        _write(sig, signature)
        pub = _run([openssl, "x509", "-in", str(leaf), "-pubkey", "-noout"])
        if pub.returncode != 0 or b"BEGIN PUBLIC KEY" not in pub.stdout:
            raise ApprovalVerificationError("unable to extract signer public key")
        _write(public, pub.stdout)
        cp = _run([openssl, "dgst", "-sha256", "-verify", str(public), "-signature", str(sig), str(data)])
        if cp.returncode != 0:
            raise ApprovalVerificationError("receipt cryptographic signature invalid")


def _secure_host_public_key(path: Path, *, strict_permissions: bool) -> None:
    if not path.is_file():
        raise ApprovalVerificationError("Security Governance approval verification key unavailable")
    if strict_permissions:
        st = path.stat()
        if st.st_uid != 0:
            raise ApprovalVerificationError("Security Governance approval verification key is not root-owned")
        if st.st_mode & 0o022:
            raise ApprovalVerificationError("Security Governance approval verification key is writable by group/other")


def _verify_security_grant(
    grant: Mapping[str, Any],
    signature_b64: str,
    security_public_key: Path,
    *,
    strict_permissions: bool,
) -> None:
    openssl = _require_openssl()
    _secure_host_public_key(security_public_key, strict_permissions=strict_permissions)
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except Exception as exc:
        raise ApprovalVerificationError("role-grant signature is not valid base64") from exc
    with tempfile.TemporaryDirectory(prefix="fa3-role-grant-") as td:
        temp = Path(td)
        data = temp / "grant.bin"
        sig = temp / "grant.sig"
        _write(data, canonical_bytes(grant))
        _write(sig, signature)
        cp = _run([
            openssl,
            "dgst",
            "-sha256",
            "-verify",
            str(security_public_key),
            "-signature",
            str(sig),
            str(data),
        ])
        if cp.returncode != 0:
            raise ApprovalVerificationError("Security Governance role-grant signature invalid")


def _signed_receipt_content(receipt: Mapping[str, Any]) -> dict[str, Any]:
    signer = receipt.get("signer", {})
    return {
        "schema": receipt.get("schema"),
        "status": receipt.get("status"),
        "receipt_id": receipt.get("receipt_id"),
        "receipt_type": receipt.get("receipt_type"),
        "source_commit": receipt.get("source_commit"),
        "issued_at": receipt.get("issued_at"),
        "expires_at": receipt.get("expires_at"),
        "nonce": receipt.get("nonce"),
        "single_use": receipt.get("single_use"),
        "content_sha256": receipt.get("content_sha256"),
        "payload": receipt.get("payload"),
        "signer_identity": signer.get("identity"),
        "signer_certificate_sha256": signer.get("certificate_sha256"),
    }


def verify_authenticated_receipt(
    receipt: Mapping[str, Any],
    *,
    expected_receipt_type: str,
    required_role: str,
    expected_source_commit: str,
    root_ca: Path = DEFAULT_ROOT_CA,
    security_public_key: Path = DEFAULT_SECURITY_APPROVAL_KEY,
    require_human: bool = False,
    require_independent: bool = False,
    now: datetime | None = None,
    strict_host_permissions: bool = True,
    expected_grant_scope: str = "FA3_RELEASE_ACCEPTANCE",
) -> dict[str, Any]:
    findings: list[str] = []
    current = now or datetime.now(timezone.utc)

    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("authenticated approval receipt schema mismatch")
    if receipt.get("status") != "PASS":
        findings.append("authenticated approval receipt is not PASS")
    rid = receipt.get("receipt_id")
    if not isinstance(rid, str) or not rid.strip():
        findings.append("receipt_id missing")
    if receipt.get("receipt_type") != expected_receipt_type:
        findings.append("receipt_type mismatch")
    if receipt.get("source_commit") != expected_source_commit or not HEX40.fullmatch(str(receipt.get("source_commit", ""))):
        findings.append("approval receipt source_commit mismatch")
    if receipt.get("single_use") is not True:
        findings.append("approval receipt must be single-use")
    if not NONCE.fullmatch(str(receipt.get("nonce", ""))):
        findings.append("approval receipt nonce missing/invalid")

    issued = parse_time(receipt.get("issued_at"))
    expires = parse_time(receipt.get("expires_at"))
    if issued is None:
        findings.append("approval issued_at missing/invalid")
    if expires is None:
        findings.append("approval expires_at missing/invalid")
    elif issued is not None and expires <= issued:
        findings.append("approval expiry must be after issuance")
    elif expires <= current:
        findings.append("approval receipt expired")
    if issued is not None and issued > current:
        findings.append("approval issued_at is in the future")

    payload = receipt.get("payload")
    if not isinstance(payload, dict):
        findings.append("approval payload missing")
        payload = {}
    digest = sha256_bytes(canonical_bytes(payload))
    if receipt.get("content_sha256") != digest:
        findings.append("approval payload content digest mismatch")

    signer = receipt.get("signer")
    cert_fingerprint: str | None = None
    if not isinstance(signer, dict):
        findings.append("signer metadata missing")
        signer = {}
    identity = signer.get("identity")
    cert_pem = signer.get("certificate_pem")
    intermediates = signer.get("intermediate_certificates_pem", [])
    if not isinstance(identity, str) or not identity:
        findings.append("signer identity missing")
    if not isinstance(cert_pem, str) or "BEGIN CERTIFICATE" not in cert_pem:
        findings.append("signer certificate missing")
    if not isinstance(intermediates, list) or any(not isinstance(x, str) for x in intermediates):
        findings.append("intermediate certificate list invalid")
        intermediates = []

    if not findings:
        try:
            cert_fingerprint = _verify_certificate(cert_pem, intermediates, identity, Path(root_ca))
        except ApprovalVerificationError as exc:
            findings.append(str(exc))
    claimed_fp = signer.get("certificate_sha256")
    if cert_fingerprint is not None:
        if claimed_fp != cert_fingerprint or not HEX64.fullmatch(str(claimed_fp or "")):
            findings.append("signer certificate fingerprint mismatch")

    signature = receipt.get("signature")
    if not isinstance(signature, dict):
        findings.append("receipt signature metadata missing")
        signature = {}
    if signature.get("algorithm") not in {"RSA-SHA256", "ECDSA-SHA256"}:
        findings.append("receipt signature algorithm unsupported")
    if not findings:
        try:
            _verify_signature_with_certificate(
                cert_pem,
                canonical_bytes(_signed_receipt_content(receipt)),
                str(signature.get("value_b64", "")),
            )
        except ApprovalVerificationError as exc:
            findings.append(str(exc))

    auth = receipt.get("authorization")
    if not isinstance(auth, dict):
        findings.append("authorization role-grant missing")
        auth = {}
    grant = auth.get("grant")
    if not isinstance(grant, dict):
        findings.append("authorization grant missing")
        grant = {}
    if auth.get("authority") != SECURITY_AUTHORITY:
        findings.append("authorization authority drift")
    if auth.get("trust_profile") != TRUST_PROFILE:
        findings.append("authorization trust profile drift")
    if auth.get("algorithm") not in {"RSA-SHA256", "ECDSA-SHA256"}:
        findings.append("authorization signature algorithm unsupported")

    if grant.get("schema") != GRANT_SCHEMA:
        findings.append("authorization grant schema mismatch")
    if grant.get("authority") != SECURITY_AUTHORITY:
        findings.append("authorization grant authority drift")
    if grant.get("identity") != identity:
        findings.append("authorization grant identity mismatch")
    if cert_fingerprint is not None and grant.get("certificate_sha256") != cert_fingerprint:
        findings.append("authorization grant certificate mismatch")
    roles = grant.get("roles")
    if not isinstance(roles, list) or required_role not in roles:
        findings.append("required authorization role missing")
    types = grant.get("receipt_types")
    if not isinstance(types, list) or expected_receipt_type not in types:
        findings.append("authorization grant does not cover receipt type")
    if (grant.get("scope") != expected_grant_scope
            or expected_grant_scope not in {"FA3_RELEASE_ACCEPTANCE", "FA3_SKILL_RUNTIME"}):
        findings.append("authorization grant scope mismatch")
    grant_issued = parse_time(grant.get("issued_at"))
    grant_expires = parse_time(grant.get("expires_at"))
    if grant_issued is None or grant_expires is None:
        findings.append("authorization grant validity interval missing/invalid")
    elif grant_expires <= grant_issued or grant_expires <= current:
        findings.append("authorization grant expired/invalid")
    elif grant_issued > current:
        findings.append("authorization grant issued_at is in the future")
    identity_class = grant.get("identity_class")
    if require_human and identity_class != "HUMAN":
        findings.append("human promotion requires HUMAN identity class")

    if grant and auth.get("value_b64"):
        try:
            _verify_security_grant(
                grant,
                str(auth.get("value_b64")),
                Path(security_public_key),
                strict_permissions=strict_host_permissions,
            )
        except ApprovalVerificationError as exc:
            findings.append(str(exc))
    else:
        findings.append("authorization role-grant signature missing")

    if require_independent:
        producer = payload.get("producer_identity")
        if not isinstance(producer, str) or not producer:
            findings.append("independent review producer identity missing")
        elif producer == identity:
            findings.append("reviewer identity is not independent from producer")

    return {
        "qualified": not findings,
        "receipt_id": rid,
        "receipt_type": expected_receipt_type,
        "identity": identity,
        "role": required_role,
        "certificate_sha256": cert_fingerprint,
        "content_sha256": digest,
        "source_commit": receipt.get("source_commit"),
        "findings": findings,
    }


def requirement_for_filename(filename: str) -> dict[str, Any] | None:
    value = REQUIREMENTS.get(filename)
    return dict(value) if value is not None else None


def verify_receipt_file(
    path: Path,
    *,
    expected_source_commit: str,
    root_ca: Path = DEFAULT_ROOT_CA,
    security_public_key: Path = DEFAULT_SECURITY_APPROVAL_KEY,
    strict_host_permissions: bool = True,
) -> dict[str, Any]:
    requirement = requirement_for_filename(path.name)
    if requirement is None:
        raise ApprovalVerificationError(f"{path.name} has no authenticated approval requirement")
    if not path.is_file():
        return {"qualified": False, "receipt_id": None, "findings": ["missing"]}
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"qualified": False, "receipt_id": None, "findings": ["unreadable"]}
    if not isinstance(receipt, dict):
        return {"qualified": False, "receipt_id": None, "findings": ["receipt is not an object"]}
    return verify_authenticated_receipt(
        receipt,
        expected_receipt_type=requirement["receipt_type"],
        required_role=requirement["role"],
        expected_source_commit=expected_source_commit,
        root_ca=root_ca,
        security_public_key=security_public_key,
        require_human=requirement.get("human", False),
        require_independent=requirement.get("independent", False),
        strict_host_permissions=strict_host_permissions,
    )


def receipt_digest(path: Path) -> str:
    return sha256_file(path)


PROMOTION_CONSUMPTION_LEDGER = Path("promotion/approval-consumption-ledger.json")
PROMOTION_RECEIPT_FILENAMES = (
    "release-integrity.json",
    "independent-review.json",
    "human-promotion-receipt.json",
)


def load_consumption_ledger(root: Path) -> dict[str, Any]:
    path = Path(root) / PROMOTION_CONSUMPTION_LEDGER
    if not path.is_file():
        return {
            "schema": "fa3.approval-consumption-ledger.v1",
            "authority": SECURITY_AUTHORITY,
            "consumed": [],
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "fa3.approval-consumption-ledger.v1":
        raise ApprovalVerificationError("approval consumption ledger schema mismatch")
    if data.get("authority") != SECURITY_AUTHORITY:
        raise ApprovalVerificationError("approval consumption ledger authority mismatch")
    if not isinstance(data.get("consumed"), list):
        raise ApprovalVerificationError("approval consumption ledger consumed list invalid")
    return data


def ensure_promotion_receipts_unconsumed(root: Path, receipt_paths: list[Path]) -> dict[str, Any]:
    ledger = load_consumption_ledger(root)
    consumed = {
        item.get("receipt_id")
        for item in ledger.get("consumed", [])
        if isinstance(item, dict)
    }
    reused: list[str] = []
    receipts: list[dict[str, str]] = []
    for path in receipt_paths:
        if not path.is_file():
            reused.append(f"missing:{path.name}")
            continue
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            reused.append(f"unreadable:{path.name}")
            continue
        rid = receipt.get("receipt_id")
        if not isinstance(rid, str) or not rid:
            reused.append(f"missing-id:{path.name}")
            continue
        if rid in consumed:
            reused.append(rid)
        receipts.append({
            "receipt_id": rid,
            "filename": path.name,
            "receipt_sha256": sha256_file(path),
        })
    return {
        "available": not reused,
        "reused_or_invalid": reused,
        "receipts": receipts,
    }


def consume_promotion_receipts(
    root: Path,
    receipt_paths: list[Path],
    *,
    source_commit: str,
    acceptance_report_sha256: str,
) -> dict[str, Any]:
    root = Path(root)
    state = ensure_promotion_receipts_unconsumed(root, receipt_paths)
    if not state["available"]:
        raise ApprovalVerificationError(
            "promotion approval receipt already consumed or invalid: "
            + ",".join(state["reused_or_invalid"])
        )
    ledger = load_consumption_ledger(root)
    now = datetime.now(timezone.utc).isoformat()
    for item in state["receipts"]:
        ledger["consumed"].append({
            **item,
            "source_commit": source_commit,
            "acceptance_report_sha256": acceptance_report_sha256,
            "consumed_at": now,
        })
    ledger_path = root / PROMOTION_CONSUMPTION_LEDGER
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = ledger_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(ledger_path)
    return {
        "status": "CONSUMED",
        "receipt_ids": [item["receipt_id"] for item in state["receipts"]],
        "ledger": str(PROMOTION_CONSUMPTION_LEDGER),
    }
