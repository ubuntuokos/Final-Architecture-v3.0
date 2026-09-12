#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import shutil
from pathlib import Path

PROVIDER_ID = "FA3-PROVIDER-PYRIT-001"
ADMISSION_ID = "FA3-PYRIT-RUNTIME-ADMISSION-001"
RELEASE = "v1.1.0"
VERSION = "1.1.0"
COMMIT = "d0524f0714840519b826eb770687ca1d4f46a761"


def loadj(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def localhost_url(value: str) -> bool:
    return value.startswith("http://127.0.0.1:") or value.startswith("http://localhost:")


def validate_real_scan(ev: dict) -> list[str]:
    errors = []
    isolation = ev.get("isolation", {})
    if ev.get("schema") != "fa3.pyrit-real-scan-evidence.v1":
        errors.append("schema")
    if ev.get("provider_id") != PROVIDER_ID:
        errors.append("provider_id")
    if ev.get("release") != RELEASE or ev.get("release_commit") != COMMIT:
        errors.append("immutable_runtime_pin")
    if ev.get("synthetic") is not False:
        errors.append("synthetic")
    if not localhost_url(str(ev.get("target_url", ""))):
        errors.append("target_url")
    if ev.get("target_allowlisted") is not True:
        errors.append("target_allowlisted")
    if isolation.get("egress_policy") != "DENY_BY_DEFAULT_ALLOWLIST_ONLY":
        errors.append("egress_policy")
    for field in (
        "secret_environment_passthrough",
        "arbitrary_host_shell",
        "arbitrary_mcp_access",
        "canonical_memory_write",
        "direct_gpu_device_placement",
    ):
        if isolation.get(field) is not False:
            errors.append(field)
    if isolation.get("model_routing_authority") != "FA3-AUTH-MODEL-ROUTER-001":
        errors.append("model_routing_authority")
    score = ev.get("score", {})
    if score.get("security_pass") is True and score.get("status") == "UNDETERMINED":
        errors.append("undetermined_score_pass")
    digest = str(ev.get("output_sha256", ""))
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
        errors.append("output_sha256")
    if ev.get("run_id") in {None, ""}:
        errors.append("run_id")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-evidence", required=True)
    parser.add_argument("--out", default="evidence/receipts/pyrit-current-host.json")
    args = parser.parse_args()

    path = Path(args.scan_evidence).resolve()
    evidence = loadj(path)
    errors = validate_real_scan(evidence)

    installed = None
    try:
        installed = importlib.metadata.version("pyrit")
    except importlib.metadata.PackageNotFoundError:
        errors.append("pyrit_not_installed")
    if installed != VERSION:
        errors.append("pyrit_version")
    if shutil.which("pyrit_scan") is None:
        errors.append("pyrit_scan_missing")

    receipt = {
        "schema": "fa3.pyrit-current-host-receipt.v1",
        "provider_id": PROVIDER_ID,
        "admission_id": ADMISSION_ID,
        "status": "PASS" if not errors else "FAIL",
        "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS" if not errors else "CURRENT_HOST_REJECTED",
        "synthetic": False,
        "installed_pyrit_version": installed,
        "release": RELEASE,
        "release_commit": COMMIT,
        "source_scan_evidence": str(path),
        "source_scan_evidence_sha256": sha256_file(path),
        "run_id": evidence.get("run_id"),
        "target_url": evidence.get("target_url"),
        "target_allowlisted": evidence.get("target_allowlisted"),
        "score": evidence.get("score"),
        "isolation": evidence.get("isolation"),
        "output_sha256": evidence.get("output_sha256"),
        "validation_errors": errors,
        "runtime_admission_eligible": not errors,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": 143,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
