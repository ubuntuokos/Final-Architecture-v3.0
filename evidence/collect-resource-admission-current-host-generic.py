#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEGACY_COLLECTOR = ROOT / "evidence/collect-resource-admission-current-host.py"
RECEIPT_DEFAULT = ROOT / "evidence/receipts/resource-admission-current-host-cpu.json"
BROKER_DEFAULT = "/usr/local/bin/fa3-host-resource-broker-validator"
AUTHORIZER_DEFAULT = "/usr/local/bin/fa3-host-resource-broker-authorizer"
AUTH_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/ResourceAdmissionAuthorization@1"
HRB_AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
HRB_ISSUER = "FA3-HOST-RESOURCE-BROKER-001"
COLLECTOR_ID = "FA3-RESOURCE-ADMISSION-CURRENT-HOST-GENERIC-COLLECTOR-001"
COLLECTOR_VERSION = "1.0.0"


def _load_legacy():
    spec = importlib.util.spec_from_file_location("fa3_resource_admission_legacy_collector", LEGACY_COLLECTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("legacy collector module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(command: list[str], timeout: int = 20) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", repr(exc)


def _purpose_matches(left: Any, right: Any) -> bool:
    return bool(str(right or "").strip()) and str(left or "").strip().lower() == str(right or "").strip().lower()


def validate_authorization(
    path: Path,
    broker: str,
    workload: dict[str, Any],
    requested_classes: list[str],
    *,
    host: str | None = None,
    now_epoch: int | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    try:
        authorization = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"AUTHORIZATION_UNREADABLE:{exc!r}"]
    if not isinstance(authorization, dict):
        return None, ["AUTHORIZATION_NOT_OBJECT"]
    required = [
        "schema", "authorization_id", "issuer", "authority", "status", "host",
        "workload_id", "requested_resource_classes", "issued_epoch", "expires_epoch",
        "nonce", "resource_decisions", "signature",
    ]
    missing = [key for key in required if key not in authorization]
    if missing:
        errors.append("AUTHORIZATION_MISSING_FIELDS:" + ",".join(missing))
    if authorization.get("schema") != AUTH_SCHEMA:
        errors.append("AUTHORIZATION_SCHEMA_MISMATCH")
    if authorization.get("issuer") != HRB_ISSUER or authorization.get("authority") != HRB_AUTHORITY:
        errors.append("AUTHORIZATION_AUTHORITY_MISMATCH")
    if authorization.get("status") != "ACTIVE":
        errors.append("AUTHORIZATION_NOT_ACTIVE")
    expected_host = socket.gethostname() if host is None else host
    if str(authorization.get("host", "")) != expected_host:
        errors.append("AUTHORIZATION_HOST_MISMATCH")
    if not _purpose_matches(authorization.get("workload_id"), workload.get("workload_id")):
        errors.append("AUTHORIZATION_WORKLOAD_SCOPE_MISMATCH")
    classes = authorization.get("requested_resource_classes")
    if classes != requested_classes or any(item not in {"cpu", "memory"} for item in (classes if isinstance(classes, list) else [])):
        errors.append("AUTHORIZATION_RESOURCE_CLASS_MISMATCH")
    current = int(time.time()) if now_epoch is None else int(now_epoch)
    try:
        issued = int(authorization.get("issued_epoch", 0))
        expires = int(authorization.get("expires_epoch", 0))
        if issued <= 0 or issued > current + 30:
            errors.append("AUTHORIZATION_ISSUED_TIME_INVALID")
        if expires <= current or expires <= issued:
            errors.append("AUTHORIZATION_EXPIRED")
    except (TypeError, ValueError):
        errors.append("AUTHORIZATION_TIME_INVALID")
    signature = authorization.get("signature")
    if not isinstance(signature, dict) or signature.get("alg") != "HMAC-SHA256" or signature.get("key_id") != "host-local-v1" or not re.fullmatch(r"[0-9a-f]{64}", str(signature.get("value", ""))):
        errors.append("AUTHORIZATION_SIGNATURE_DESCRIPTOR_INVALID")
    broker_path = shutil.which(broker) if "/" not in broker else broker
    if not broker_path or not Path(broker_path).is_file():
        errors.append("HRB_BROKER_UNAVAILABLE")
    else:
        rc, stdout, _ = _run([str(broker_path), "validate-authorization", str(path.resolve())], timeout=20)
        if rc != 0 or stdout.strip().splitlines()[-1:] != ["VALID"]:
            errors.append("HRB_BROKER_VALIDATION_FAILED")
    return authorization, errors


def authorize(workload_path: Path, authorization_path: Path, authorizer: str) -> list[str]:
    executable = shutil.which(authorizer) if "/" not in authorizer else authorizer
    if not executable or not Path(executable).is_file():
        return ["HRB_AUTHORIZER_UNAVAILABLE"]
    authorization_path.parent.mkdir(parents=True, exist_ok=True)
    rc, stdout, _ = _run([
        str(executable), "authorize-resource", str(workload_path.resolve()), str(authorization_path.resolve()), "300"
    ], timeout=30)
    if rc != 0 or not authorization_path.is_file():
        return ["HRB_AUTHORIZATION_ACQUIRE_FAILED"]
    if stdout.strip().splitlines()[-1:] not in ([str(authorization_path.resolve())], []):
        return ["HRB_AUTHORIZER_OUTPUT_INVALID"]
    return []


def collect(
    root: Path,
    workload_path: Path,
    authorization_path: Path,
    receipt_path: Path,
    broker: str,
    authorizer: str,
    *,
    acquire: bool,
) -> dict[str, Any]:
    legacy = _load_legacy()
    sys_path = str(root / "src")
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    from fa3_resource_evidence_normalization_gate import _canonical_payload_hash, evaluate_resource_admission

    workload, workload_errors, requested_classes, accelerator_required = legacy.load_workload(workload_path)
    errors = list(workload_errors)
    if accelerator_required:
        errors.append("GENERIC_AUTHORIZATION_CANNOT_AUTHORIZE_ACCELERATOR")
    if any(item not in {"cpu", "memory"} for item in requested_classes):
        errors.append("GENERIC_AUTHORIZATION_RESOURCE_CLASS_UNSUPPORTED")

    if acquire and not errors:
        errors.extend(authorize(workload_path, authorization_path, authorizer))

    attestation, attestation_sha = legacy.collect_host_attestation(collect_accelerators=False)
    authorization: dict[str, Any] | None = None
    auth_errors: list[str] = []
    if not errors and workload is not None:
        authorization, auth_errors = validate_authorization(authorization_path, broker, workload, requested_classes)
        errors.extend(auth_errors)

    profile = legacy.build_compute_profile(attestation, attestation_sha, None)
    admission = None
    if not errors and workload is not None and authorization is not None:
        admission = evaluate_resource_admission(
            profile["metrics"], workload["requirements"],
            {"status": "VALID", "authorization_id": authorization.get("authorization_id")},
        )
        if admission.get("result") != "PASS":
            errors.append("RESOURCE_REQUIREMENTS_BLOCKED")

    hrb_authorization: dict[str, Any] = {}
    if authorization is not None:
        hrb_authorization = {
            "authority": HRB_AUTHORITY,
            "authorization_id": authorization.get("authorization_id"),
            "authorization_schema": authorization.get("schema"),
            "issuer": authorization.get("issuer"),
            "status": "VALID" if not auth_errors else "INVALID",
            "record_status": authorization.get("status"),
            "host": authorization.get("host"),
            "workload_id": authorization.get("workload_id"),
            "requested_resource_classes": authorization.get("requested_resource_classes"),
            "issued_epoch": authorization.get("issued_epoch"),
            "expires_epoch": authorization.get("expires_epoch"),
            "broker_validation": not auth_errors,
            "source": "RESOURCE_ADMISSION_AUTHORIZATION",
            "authorization_file_sha256": legacy.sha256_file(authorization_path) if authorization_path.is_file() else None,
        }

    payload = {
        "schema": "fa3.resource-admission-current-host.payload.v1",
        "host_attestation": attestation,
        "host_attestation_sha256": attestation_sha,
        "compute_profile": profile,
        "workload_resource_envelope": workload,
        "workload_resource_envelope_sha256": legacy.sha256_file(workload_path) if workload_path.is_file() else None,
        "requested_resource_classes": requested_classes,
        "accelerator_required": False,
        "hrb_authorization": hrb_authorization,
        "hrb_lease_identity": {},
        "admission": admission,
        "errors": errors,
        "cross_metric_compensation": False,
        "cu_tu_admission_authority": False,
    }
    passed = not errors and admission is not None and admission.get("result") == "PASS"
    artifact_digests = [
        {"kind": "host_attestation", "sha256": attestation_sha},
        {"kind": "workload_resource_envelope", "sha256": legacy.sha256_file(workload_path) if workload_path.is_file() else None},
    ]
    if authorization_path.is_file():
        artifact_digests.append({"kind": "hrb_resource_authorization", "sha256": legacy.sha256_file(authorization_path)})
    envelope = {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": f"FA3-RESOURCE-ADMISSION-CURRENT-HOST-CPU-{int(time.time())}",
        "evidence_class": "CURRENT_HOST_ADMISSION",
        "subject": {"profile_id": "FA3-RESOURCE-ADMISSION-CONTRACTS-001", "provider_id": None, "gate_id": "FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001"},
        "canonical_context": {
            "architecture_release": "2026-08-23/v3.0.11",
            "release_baseline_id": "FA3-RELEASE-CAPABILITY-BASELINE-001",
            "release_manifest_digest": legacy.release_manifest_digest(root),
        },
        "execution_context": {
            "host_attestation_ref": attestation["host_attestation_id"],
            "compute_profile_ref": "INLINE_SHA256:" + legacy.sha256_obj(profile),
            "workload_resource_envelope_ref": str(workload_path.resolve()),
            "hrb_authorization_ref": str(authorization_path.resolve()),
            "hrb_lease_ref": None,
            "diagnostics": {},
        },
        "provenance": {"collector_id": COLLECTOR_ID, "collector_revision": COLLECTOR_VERSION, "generated_at": legacy.now(), "artifact_digests": artifact_digests},
        "integrity": {"payload_sha256": _canonical_payload_hash(payload)},
        "result": {
            "status": "PASS" if passed else "BLOCKED",
            "scope": "COMPONENT_CURRENT_HOST_RESOURCE_ADMISSION",
            "claims": ["CURRENT_HOST_RESOURCE_ADMISSION_PASS"] if passed else [],
            "non_claims": ["GLOBAL_FA3_PROMOTION", "PROVIDER_RUNTIME_E2E", "END_TO_END_ZERO_COPY"],
        },
        "payload_schema_id": "fa3.resource-admission-current-host.payload.v1",
        "payload": payload,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return envelope


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect CPU/memory current-host resource admission using HRB ResourceAdmissionAuthorization@1")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--workload-envelope", required=True)
    parser.add_argument("--hrb-authorization", required=True)
    parser.add_argument("--receipt", default=str(RECEIPT_DEFAULT))
    parser.add_argument("--broker", default=BROKER_DEFAULT)
    parser.add_argument("--authorizer", default=AUTHORIZER_DEFAULT)
    parser.add_argument("--acquire", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    envelope = collect(
        root,
        Path(args.workload_envelope),
        Path(args.hrb_authorization),
        Path(args.receipt),
        args.broker,
        args.authorizer,
        acquire=args.acquire,
    )
    print(json.dumps({
        "evidence_id": envelope["evidence_id"],
        "status": envelope["result"]["status"],
        "requested_resource_classes": envelope["payload"]["requested_resource_classes"],
        "accelerator_required": envelope["payload"]["accelerator_required"],
        "receipt": str(Path(args.receipt).resolve()),
    }, indent=2))
    return 0 if envelope["result"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
