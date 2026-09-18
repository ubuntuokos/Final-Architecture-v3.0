#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GATE_ID = "FA3-PODMAN-SECRET-ISOLATION-CURRENT-HOST-GATESET-001"
RECEIPT_SCHEMA = "fa3.podman-secret-isolation-current-host-receipt.v1"
RUNNER_LABELS = {"self-hosted", "linux", "x64", "fa3-current-host"}


def _run(argv: list[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(argv, input=input_text, text=True, capture_output=True, check=False)
    if check and cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout or f"exit={cp.returncode}").strip()[:2000])
    return cp


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _podman_info() -> dict[str, Any]:
    return json.loads(_run(["podman", "info", "--format", "json"]).stdout)


def _rootless(info: dict[str, Any]) -> bool:
    host = info.get("host") or info.get("Host") or {}
    security = host.get("security") or host.get("Security") or {}
    value = security.get("rootless")
    if value is None:
        value = host.get("rootless")
    return value is True


def collect_current_host(root: Path, image: str) -> dict[str, Any]:
    if not shutil.which("podman"):
        raise RuntimeError("podman is required for current-host secret isolation evidence")
    if not image or image.endswith(":latest"):
        raise RuntimeError("a preloaded immutable/non-latest OCI image reference is required")
    if _run(["podman", "image", "exists", image], check=False).returncode != 0:
        raise RuntimeError("test image must already exist locally; network pulling is forbidden")

    info = _podman_info()
    if not _rootless(info):
        raise RuntimeError("rootless Podman is required for this current-host security proof")

    canary = "FA3_SECRET_NEG_CANARY_" + secrets.token_hex(32)
    canary_sha = hashlib.sha256(canary.encode("utf-8")).hexdigest()
    secret_name = "fa3-neg-" + uuid.uuid4().hex
    inspect_name = "fa3-neg-inspect-" + uuid.uuid4().hex[:12]
    secret_created = False
    container_created = False
    checks: dict[str, bool] = {}

    try:
        _run(["podman", "secret", "create", secret_name, "-"], input_text=canary)
        secret_created = True

        neg = _run(
            [
                "podman", "run", "--rm", "--pull=never", "--network=none", "--read-only",
                "--cap-drop=all", "--security-opt=no-new-privileges",
                image, "sh", "-c",
                "test ! -e /run/secrets/canary && ! env | grep -q '^FA3_SECRET_CANARY='",
            ],
            check=False,
        )
        checks["unauthorized_mount_absent"] = neg.returncode == 0
        checks["unauthorized_env_absent"] = neg.returncode == 0

        pos = _run(
            [
                "podman", "run", "--rm", "--pull=never", "--network=none", "--read-only",
                "--cap-drop=all", "--security-opt=no-new-privileges",
                "--secret", f"{secret_name},target=canary",
                image, "sh", "-c", "sha256sum /run/secrets/canary | cut -d' ' -f1",
            ],
            check=False,
        )
        checks["explicit_secret_control_works"] = (
            pos.returncode == 0 and pos.stdout.strip() == canary_sha
        )
        checks["control_output_contains_no_raw_secret"] = canary not in (pos.stdout + pos.stderr)

        create = _run(
            [
                "podman", "create", "--pull=never", "--name", inspect_name, "--network=none",
                "--cap-drop=all", "--security-opt=no-new-privileges",
                "--secret", f"{secret_name},target=canary",
                image, "sh", "-c", "sleep 30",
            ],
            check=False,
        )
        container_created = create.returncode == 0
        if container_created:
            inspected = _run(["podman", "inspect", inspect_name], check=False)
            inspect_blob = inspected.stdout + inspected.stderr
            checks["inspect_contains_no_raw_secret"] = (
                inspected.returncode == 0 and canary not in inspect_blob
            )
        else:
            checks["inspect_contains_no_raw_secret"] = False

        image_id = _run(["podman", "image", "inspect", "--format", "{{.Id}}", image]).stdout.strip()
        checks["image_resolved_to_content_id"] = bool(re.fullmatch(r"sha256:[0-9a-f]{64}", image_id))
        checks["secret_store_entry_exists_during_probe"] = (
            _run(["podman", "secret", "exists", secret_name], check=False).returncode == 0
        )

        if container_created:
            _run(["podman", "rm", "-f", inspect_name])
            container_created = False
        checks["container_removed_after_probe"] = (
            _run(["podman", "container", "exists", inspect_name], check=False).returncode != 0
        )

        if secret_created:
            _run(["podman", "secret", "rm", secret_name])
            secret_created = False
        checks["secret_removed_after_probe"] = (
            _run(["podman", "secret", "exists", secret_name], check=False).returncode != 0
        )

        status = "PASS" if all(checks.values()) else "FAIL"
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "gate_id": GATE_ID,
            "status": status,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "execution_context": "REAL_CURRENT_HOST",
            "required_runner_labels": sorted(RUNNER_LABELS),
            "rootless_podman": True,
            "image_reference": image,
            "image_id": image_id,
            "canary_sha256": canary_sha,
            "raw_secret_value_persisted": False,
            "synthetic": False,
            "checks": checks,
            "current_host_runtime_promotion_claim": False,
            "global_promotion_claim": False,
        }
        _write(root / "evidence/receipts/podman-secret-isolation-current-host.json", receipt)
        return receipt
    finally:
        if container_created:
            _run(["podman", "rm", "-f", inspect_name], check=False)
        if secret_created:
            _run(["podman", "secret", "rm", secret_name], check=False)


def validate_receipt(receipt: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if receipt.get("schema") != RECEIPT_SCHEMA:
        errors.append("schema")
    if receipt.get("gate_id") != GATE_ID:
        errors.append("gate_id")
    if receipt.get("status") != "PASS":
        errors.append("status")
    if receipt.get("execution_context") != "REAL_CURRENT_HOST":
        errors.append("execution_context")
    if receipt.get("rootless_podman") is not True:
        errors.append("rootless_podman")
    if receipt.get("synthetic") is not False:
        errors.append("synthetic")
    if receipt.get("raw_secret_value_persisted") is not False:
        errors.append("raw_secret_value_persisted")
    if receipt.get("current_host_runtime_promotion_claim") is not False:
        errors.append("current_host_runtime_promotion_claim")
    if receipt.get("global_promotion_claim") is not False:
        errors.append("global_promotion_claim")
    if set(receipt.get("required_runner_labels") or []) != RUNNER_LABELS:
        errors.append("runner_labels")
    if not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("canary_sha256", ""))):
        errors.append("canary_sha256")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(receipt.get("image_id", ""))):
        errors.append("image_id")
    checks = receipt.get("checks")
    required_checks = {
        "unauthorized_mount_absent",
        "unauthorized_env_absent",
        "explicit_secret_control_works",
        "control_output_contains_no_raw_secret",
        "inspect_contains_no_raw_secret",
        "image_resolved_to_content_id",
        "secret_store_entry_exists_during_probe",
        "container_removed_after_probe",
        "secret_removed_after_probe",
    }
    if not isinstance(checks, dict) or set(checks) != required_checks or not all(checks.values()):
        errors.append("checks")
    return not errors, errors


def gate(root: Path, require_evidence: bool = False) -> dict[str, Any]:
    receipt_path = root / "evidence/receipts/podman-secret-isolation-current-host.json"
    if not receipt_path.exists():
        report = {
            "schema": "fa3.podman-secret-isolation-current-host-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL" if require_evidence else "PASS",
            "status": "BLOCKED_CURRENT_HOST_EVIDENCE_REQUIRED" if require_evidence else "PENDING_CURRENT_HOST",
            "receipt_present": False,
            "current_host_runtime_promotion_claim": False,
            "global_promotion_claim": False,
        }
    else:
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            ok, errors = validate_receipt(receipt)
        except Exception as exc:
            ok, errors = False, [f"receipt_parse:{type(exc).__name__}"]
        report = {
            "schema": "fa3.podman-secret-isolation-current-host-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "PASS" if ok else "FAIL",
            "status": "CURRENT_HOST_PASS" if ok else "BLOCKED_INVALID_CURRENT_HOST_EVIDENCE",
            "receipt_present": True,
            "errors": errors,
            "current_host_runtime_promotion_claim": False,
            "global_promotion_claim": False,
        }
    _write(root / "reports/podman-secret-isolation-current-host-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--image", default="")
    ap.add_argument("--require-evidence", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if args.collect:
        try:
            collect_current_host(root, args.image)
        except Exception as exc:
            report = {
                "schema": "fa3.podman-secret-isolation-current-host-gate-report.v1",
                "gate_id": GATE_ID,
                "result": "FAIL",
                "status": "BLOCKED_CURRENT_HOST_PROBE_FAILED",
                "error": str(exc)[:2000],
                "current_host_runtime_promotion_claim": False,
                "global_promotion_claim": False,
            }
            _write(root / "reports/podman-secret-isolation-current-host-gate-report.json", report)
            print(json.dumps(report, indent=2))
            return 2
    report = gate(root, require_evidence=args.require_evidence)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
