#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fa3_current_host_capability_test_qualification_audit import (
    CONSTITUENT_SCHEMA,
    EVIDENCE_AUTHORITY,
    QUALIFICATION_REGISTRY,
    audit as audit_qualifications,
)

VERDICT_SCHEMA = "fa3.capability-current-host-test-verdict.v1"
QUALIFIED_ARTIFACT_SCHEMA = "fa3.capability-current-host-test-qualification.v1"
EVIDENCE_CLASS = "CAPABILITY_SPECIFIC_EXECUTABLE_TEST"
CONSTITUENT_ROOT = ".fa3-current-host/qualification-constituents"
ALLOWED_SOURCE_PREFIXES = (".fa3-current-host/", "evidence/receipts/")
FORBIDDEN_SOURCE_PREFIXES = (
    "evidence/reference/",
    "evidence/static/",
    "canonical/",
    "reports/",
    "evidence/receipts/capabilities/",
    ".fa3-current-host/qualification-constituents/",
    ".fa3-current-host/test-artifacts/",
    ".fa3-current-host/test-results/",
    ".fa3-current-host/test-bundles/",
    ".fa3-current-host/attestations/",
)


def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"JSON object required: {path}")
    return obj


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _repo_file(
    root: Path,
    rel: Any,
    *,
    allowed_prefixes: tuple[str, ...] | None = None,
) -> tuple[Path | None, str | None]:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None, "path missing or absolute"
    if allowed_prefixes is not None:
        if not rel.startswith(allowed_prefixes):
            return None, "path is outside approved current-host source evidence roots"
        if rel.startswith(FORBIDDEN_SOURCE_PREFIXES):
            return None, "static/reference/circular source is forbidden"
    unresolved = root / rel
    if unresolved.is_symlink():
        return None, "symlink paths are forbidden"
    path = unresolved.resolve()
    if path == root or root not in path.parents:
        return None, "path escapes repository"
    if not path.is_file():
        return None, f"file missing: {rel}"
    return path, None


def _parse_time(value: Any, label: str) -> tuple[datetime | None, str | None]:
    if not isinstance(value, str) or not value:
        return None, f"{label} missing"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None, f"{label} invalid"
    if parsed.tzinfo is None:
        return None, f"{label} must be timezone-aware"
    return parsed.astimezone(timezone.utc), None


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"required environment variable missing: {name}")
    return value


def qualify(root: Path, qualification_id: str) -> tuple[dict[str, Any] | None, list[str]]:
    root = Path(root).resolve()
    findings: list[str] = []

    qualification_report = audit_qualifications(root)
    if qualification_report.get("audit_integrity") != "PASS":
        return None, ["capability qualification registry audit failed"]
    accepted = [
        item
        for item in qualification_report.get("accepted_qualifications", [])
        if item.get("qualification_id") == qualification_id
    ]
    if len(accepted) != 1:
        return None, ["qualification_id is not exactly one accepted canonical qualification"]

    registry = _load(root / QUALIFICATION_REGISTRY)
    definitions = [
        item for item in registry.get("entries", [])
        if isinstance(item, dict) and item.get("qualification_id") == qualification_id
    ]
    if len(definitions) != 1:
        return None, ["canonical qualification definition missing or ambiguous"]
    definition = definitions[0]

    subject_id = _env("FA3_CAPABILITY_ID")
    test_kind = _env("FA3_TEST_KIND")
    test_id = _env("FA3_TEST_ID")
    host_rel = _env("FA3_HOST_FINGERPRINT_PATH")
    host_digest = _env("FA3_HOST_FINGERPRINT_SHA256")
    artifact_dir_env = _env("FA3_TEST_ARTIFACT_DIR")

    for key, actual in (
        ("subject_id", subject_id),
        ("test_kind", test_kind),
        ("test_id", test_id),
    ):
        if definition.get(key) != actual:
            findings.append(f"{key} mismatch against canonical qualification")

    expected_scope = (
        root / f".fa3-current-host/test-artifacts/capabilities/{subject_id}/{test_kind}"
    ).resolve()
    actual_scope = Path(artifact_dir_env).resolve()
    if actual_scope != expected_scope:
        findings.append("artifact directory is not the exact obligation-scoped directory")
    if root not in actual_scope.parents:
        findings.append("artifact directory escapes repository")

    host_path, host_error = _repo_file(root, host_rel)
    if host_error or host_path is None:
        findings.append(f"host fingerprint {host_error or 'missing'}")
    elif _sha256(host_path) != host_digest:
        findings.append("host fingerprint digest mismatch")

    ttl_limit = definition.get("max_constituent_ttl_seconds")
    if not isinstance(ttl_limit, int):
        findings.append("canonical qualification TTL limit invalid")
        ttl_limit = 0

    now = datetime.now(timezone.utc)
    accepted_constituents: list[dict[str, Any]] = []
    expected_constituents = definition.get("required_constituents", [])
    if not isinstance(expected_constituents, list):
        findings.append("canonical constituent set invalid")
        expected_constituents = []

    for expected in expected_constituents:
        if not isinstance(expected, dict):
            findings.append("canonical constituent entry invalid")
            continue
        constituent_id = expected.get("constituent_id")
        if not isinstance(constituent_id, str) or not constituent_id:
            findings.append("canonical constituent_id invalid")
            continue
        manifest_rel = f"{CONSTITUENT_ROOT}/{qualification_id}/{constituent_id}.json"
        manifest_path, manifest_error = _repo_file(root, manifest_rel)
        if manifest_error or manifest_path is None:
            findings.append(f"{constituent_id}: constituent manifest {manifest_error or 'missing'}")
            continue
        try:
            manifest = _load(manifest_path)
        except Exception as exc:
            findings.append(f"{constituent_id}: constituent manifest invalid JSON: {exc}")
            continue

        exact_fields = (
            ("schema", CONSTITUENT_SCHEMA),
            ("qualification_id", qualification_id),
            ("constituent_id", constituent_id),
            ("subject_id", subject_id),
            ("test_kind", test_kind),
            ("test_id", test_id),
            ("status", "PASS"),
            ("execution_scope", "CURRENT_HOST"),
            ("current_host", True),
            ("synthetic", False),
            ("ci_reference_only", False),
            ("provider_receipt_only", False),
            ("generic_host_collection_only", False),
            ("global_promotion_claim", False),
            ("evidence_authority_id", EVIDENCE_AUTHORITY),
            ("source_evidence_class", expected.get("source_evidence_class")),
            ("covers_source_decision_ids", expected.get("covers_source_decision_ids")),
            ("host_fingerprint_path", host_rel),
            ("host_fingerprint_sha256", host_digest),
        )
        local_findings: list[str] = []
        for key, expected_value in exact_fields:
            if manifest.get(key) != expected_value:
                local_findings.append(f"{key} mismatch")

        collected_at, collected_error = _parse_time(manifest.get("collected_at"), "collected_at")
        expires_at, expires_error = _parse_time(manifest.get("expires_at"), "expires_at")
        if collected_error:
            local_findings.append(collected_error)
        if expires_error:
            local_findings.append(expires_error)
        if collected_at is not None and expires_at is not None:
            if collected_at > now:
                local_findings.append("collected_at is in the future")
            if expires_at <= now:
                local_findings.append("constituent evidence expired")
            ttl_seconds = (expires_at - collected_at).total_seconds()
            if ttl_seconds <= 0:
                local_findings.append("constituent TTL is non-positive")
            if ttl_limit and ttl_seconds > ttl_limit:
                local_findings.append("constituent TTL exceeds canonical maximum")

        source_rel = manifest.get("source_artifact_path")
        source_digest = manifest.get("source_artifact_sha256")
        source_path, source_error = _repo_file(
            root,
            source_rel,
            allowed_prefixes=ALLOWED_SOURCE_PREFIXES,
        )
        if source_error or source_path is None:
            local_findings.append(f"source artifact {source_error or 'missing'}")
        elif not isinstance(source_digest, str) or _sha256(source_path) != source_digest:
            local_findings.append("source artifact digest mismatch")

        if local_findings:
            findings.extend(f"{constituent_id}: {item}" for item in local_findings)
            continue
        accepted_constituents.append({
            "constituent_id": constituent_id,
            "manifest_path": manifest_rel,
            "manifest_sha256": _sha256(manifest_path),
            "source_evidence_class": manifest["source_evidence_class"],
            "covers_source_decision_ids": manifest["covers_source_decision_ids"],
            "source_artifact_path": source_rel,
            "source_artifact_sha256": source_digest,
            "collected_at": manifest["collected_at"],
            "expires_at": manifest["expires_at"],
        })

    if len(accepted_constituents) != len(expected_constituents):
        findings.append("not all canonical qualification constituents were accepted")
    if findings:
        return None, findings

    artifact = {
        "schema": QUALIFIED_ARTIFACT_SCHEMA,
        "qualification_id": qualification_id,
        "subject_id": subject_id,
        "test_kind": test_kind,
        "test_id": test_id,
        "status": "PASS",
        "execution_scope": "CURRENT_HOST",
        "current_host": True,
        "synthetic": False,
        "ci_reference_only": False,
        "provider_receipt_only": False,
        "component_receipt_only": False,
        "generic_host_collection_only": False,
        "global_promotion_claim": False,
        "evidence_authority_id": EVIDENCE_AUTHORITY,
        "coverage_semantics": "COMPLETE_CAPABILITY_OBLIGATION",
        "completeness_basis": definition.get("completeness_basis"),
        "host_fingerprint_path": host_rel,
        "host_fingerprint_sha256": host_digest,
        "constituents": accepted_constituents,
    }
    output = actual_scope / "capability-obligation-qualification.json"
    _write(output, artifact)
    artifact_rel = output.relative_to(root).as_posix()
    return {
        "schema": VERDICT_SCHEMA,
        "qualification_id": qualification_id,
        "subject_id": subject_id,
        "test_kind": test_kind,
        "test_id": test_id,
        "status": "PASS",
        "execution_scope": "CURRENT_HOST",
        "current_host": True,
        "synthetic": False,
        "ci_reference_only": False,
        "global_promotion_claim": False,
        "evidence_class": EVIDENCE_CLASS,
        "artifact_path": artifact_rel,
        "artifact_sha256": _sha256(output),
    }, []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Qualify one FA3 capability test obligation from explicit current-host constituent evidence"
    )
    parser.add_argument("--qualification-id", required=True)
    args = parser.parse_args()
    try:
        root = Path(_env("FA3_REPOSITORY_ROOT"))
        verdict, findings = qualify(root, args.qualification_id)
    except Exception as exc:
        print(json.dumps({"status": "REJECTED", "findings": [str(exc)]}), file=sys.stderr)
        return 2
    if findings or verdict is None:
        print(json.dumps({"status": "REJECTED", "findings": findings}), file=sys.stderr)
        return 2
    print(json.dumps(verdict, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
