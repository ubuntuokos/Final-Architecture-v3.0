#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RECEIPT_SCHEMA = "fa3.capability-current-host-evidence.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_head(root: Path) -> str | None:
    try:
        cp = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return None
    value = cp.stdout.strip()
    return value if cp.returncode == 0 and HEX40.fullmatch(value) else None


def _test_ok(test: Any, expected_id: str) -> tuple[bool, str | None]:
    if not isinstance(test, dict):
        return False, "test result missing"
    if test.get("id") != expected_id:
        return False, f"test id mismatch: expected {expected_id}"
    if test.get("status") != "PASS":
        return False, f"{expected_id} is not PASS"
    digest = test.get("artifact_sha256")
    if not isinstance(digest, str) or not HEX64.fullmatch(digest):
        return False, f"{expected_id} artifact_sha256 missing/invalid"
    return True, None


def validate_capability_receipt(
    root: Path,
    record: dict[str, Any],
    *,
    now: datetime | None = None,
    expected_source_commit: str | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    cap = record.get("subject_id")
    rel = f"evidence/receipts/capabilities/{cap}.json"
    path = root / rel
    findings: list[str] = []
    if not path.is_file():
        return {"qualified": False, "receipt": rel, "findings": ["receipt missing"]}

    try:
        receipt = load_json(path)
    except Exception as exc:
        return {"qualified": False, "receipt": rel, "findings": [f"receipt unreadable: {exc}"]}

    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("receipt schema mismatch")
    if receipt.get("subject_id") != cap:
        findings.append("receipt subject_id mismatch")
    if receipt.get("status") != "PASS":
        findings.append("receipt status is not PASS")
    if receipt.get("execution_scope") != "CURRENT_HOST":
        findings.append("execution_scope is not CURRENT_HOST")
    if receipt.get("current_host") is not True:
        findings.append("current_host flag is not true")
    if receipt.get("synthetic") is not False:
        findings.append("synthetic evidence cannot promote a capability")
    if receipt.get("ci_reference_only") is not False:
        findings.append("CI/reference-only evidence cannot promote a capability")

    source_commit = receipt.get("source_commit")
    expected_commit = expected_source_commit if expected_source_commit is not None else git_head(root)
    if not isinstance(source_commit, str) or not HEX40.fullmatch(source_commit):
        findings.append("source_commit missing/invalid")
    elif expected_commit is not None and source_commit != expected_commit:
        findings.append("source_commit does not match current repository HEAD")

    fingerprint = receipt.get("host_fingerprint_sha256")
    if not isinstance(fingerprint, str) or not HEX64.fullmatch(fingerprint):
        findings.append("host_fingerprint_sha256 missing/invalid")

    collected = parse_time(receipt.get("collected_at"))
    expires = parse_time(receipt.get("expires_at"))
    current = now or datetime.now(timezone.utc)
    if collected is None:
        findings.append("collected_at missing/invalid")
    if expires is None:
        findings.append("expires_at missing/invalid")
    elif collected is not None and expires <= collected:
        findings.append("expires_at must be after collected_at")
    elif expires <= current:
        findings.append("receipt expired")

    tests = receipt.get("tests", {})
    for key, expected in (
        ("positive", record.get("required_positive_test")),
        ("negative", record.get("required_negative_test")),
        ("rollback", record.get("rollback_requirement")),
    ):
        ok, why = _test_ok(tests.get(key), str(expected or ""))
        if not ok:
            findings.append(why or f"{key} test invalid")

    artifacts = receipt.get("evidence_artifacts")
    artifact_hashes: set[str] = set()
    artifact_paths: set[str] = set()
    if not isinstance(artifacts, list) or not artifacts:
        findings.append("evidence_artifacts must be non-empty")
    else:
        for item in artifacts:
            if not isinstance(item, dict):
                findings.append("evidence_artifact entry invalid")
                continue
            rel_path = item.get("path")
            digest = item.get("sha256")
            if not isinstance(rel_path, str) or not rel_path or Path(rel_path).is_absolute():
                findings.append("evidence_artifact path missing/absolute")
                continue
            if not isinstance(digest, str) or not HEX64.fullmatch(digest):
                findings.append("evidence_artifact sha256 invalid")
                continue
            candidate = (root / rel_path).resolve()
            if candidate == root or root not in candidate.parents:
                findings.append("evidence_artifact path escapes repository")
                continue
            if not candidate.is_file():
                findings.append(f"evidence_artifact missing: {rel_path}")
                continue
            actual = sha256_file(candidate)
            if actual != digest:
                findings.append(f"evidence_artifact digest mismatch: {rel_path}")
                continue
            artifact_hashes.add(digest)
            artifact_paths.add(rel_path)

    host_rel = receipt.get("host_fingerprint_path")
    if not isinstance(host_rel, str) or not host_rel or Path(host_rel).is_absolute():
        findings.append("host_fingerprint_path missing/absolute")
    else:
        host_path = (root / host_rel).resolve()
        if host_path == root or root not in host_path.parents or not host_path.is_file():
            findings.append("host_fingerprint_path missing or escapes repository")
        elif sha256_file(host_path) != fingerprint:
            findings.append("host fingerprint file digest mismatch")
        elif host_rel not in artifact_paths or fingerprint not in artifact_hashes:
            findings.append("host fingerprint must be a verified evidence artifact")

    for key in ("positive", "negative", "rollback"):
        test = tests.get(key)
        digest = test.get("artifact_sha256") if isinstance(test, dict) else None
        if isinstance(digest, str) and HEX64.fullmatch(digest) and digest not in artifact_hashes:
            findings.append(f"{key} test artifact hash is not bound to a verified evidence artifact")

    return {
        "qualified": not findings,
        "receipt": rel,
        "receipt_sha256": sha256_file(path),
        "expires_at": receipt.get("expires_at"),
        "source_commit": source_commit,
        "findings": findings,
    }
