#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

from fa3_api_mega_list_adapter import SOURCE_ID, SOURCE_REPOSITORY, parse_api_mega_list_markdown
from fa3_external_discovery_store import build_candidate_store, validate_candidate_store, volume_action

SNAPSHOT_SCHEMA = "fa3.external-api-discovery.snapshot.v1"
INGEST_RECEIPT_SCHEMA = "fa3.external-api-discovery.ingest-receipt.v1"
DRIFT_SCHEMA = "fa3.external-api-discovery.drift-report.v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_relpath(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe snapshot path: {value}")
    return path.as_posix()


def create_snapshot_manifest(snapshot_dir: Path, *, source_commit: str) -> dict[str, Any]:
    snapshot_dir = Path(snapshot_dir).resolve()
    if not SHA40.fullmatch(source_commit):
        raise ValueError("immutable 40-character source commit required")
    files: list[dict[str, Any]] = []
    for path in sorted(snapshot_dir.rglob("README.md")):
        if not path.is_file():
            continue
        rel = path.relative_to(snapshot_dir).as_posix()
        data = path.read_bytes()
        files.append(
            {
                "path": rel,
                "sha256": _sha256_bytes(data),
                "size": len(data),
                "copy_policy": "LOCAL_DISCOVERY_METADATA_SNAPSHOT",
            }
        )
    if not files:
        raise ValueError("snapshot requires at least one README.md surface")
    manifest = {
        "schema": SNAPSHOT_SCHEMA,
        "source_id": SOURCE_ID,
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "immutable": True,
        "network_fetch_performed": False,
        "files": files,
    }
    manifest["manifest_digest"] = _stable_digest({k: v for k, v in manifest.items() if k != "manifest_digest"})
    return manifest


def validate_snapshot_manifest(snapshot_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if manifest.get("schema") != SNAPSHOT_SCHEMA:
        findings.append({"code": "EXTDISC-SNAPSHOT-SCHEMA", "message": "invalid snapshot schema"})
    if manifest.get("source_id") != SOURCE_ID or manifest.get("source_repository") != SOURCE_REPOSITORY:
        findings.append({"code": "EXTDISC-SNAPSHOT-SOURCE", "message": "unexpected source identity"})
    if not SHA40.fullmatch(str(manifest.get("source_commit", ""))):
        findings.append({"code": "EXTDISC-SNAPSHOT-COMMIT", "message": "immutable source commit required"})
    if manifest.get("immutable") is not True or manifest.get("network_fetch_performed") is not False:
        findings.append({"code": "EXTDISC-SNAPSHOT-BOUNDARY", "message": "snapshot must be immutable and offline"})
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        findings.append({"code": "EXTDISC-SNAPSHOT-FILES", "message": "snapshot file inventory required"})
        return findings

    seen: set[str] = set()
    for row in files:
        if not isinstance(row, dict):
            findings.append({"code": "EXTDISC-SNAPSHOT-FILE", "message": "snapshot row must be object"})
            continue
        try:
            rel = _safe_relpath(str(row.get("path", "")))
        except ValueError as exc:
            findings.append({"code": "EXTDISC-SNAPSHOT-PATH", "message": str(exc)})
            continue
        if rel in seen:
            findings.append({"code": "EXTDISC-SNAPSHOT-DUPLICATE", "message": f"duplicate snapshot path: {rel}"})
            continue
        seen.add(rel)
        if not rel.endswith("README.md"):
            findings.append({"code": "EXTDISC-SNAPSHOT-SURFACE", "message": f"unsupported snapshot surface: {rel}"})
            continue
        if not SHA256.fullmatch(str(row.get("sha256", ""))):
            findings.append({"code": "EXTDISC-SNAPSHOT-HASH", "message": f"invalid sha256: {rel}"})
            continue
        path = snapshot_dir / rel
        if not path.is_file():
            findings.append({"code": "EXTDISC-SNAPSHOT-MISSING", "message": f"missing snapshot file: {rel}"})
            continue
        data = path.read_bytes()
        if len(data) != int(row.get("size", -1)):
            findings.append({"code": "EXTDISC-SNAPSHOT-SIZE", "message": f"size drift: {rel}"})
        if _sha256_bytes(data) != row["sha256"]:
            findings.append({"code": "EXTDISC-SNAPSHOT-HASH-DRIFT", "message": f"content drift: {rel}"})
    expected_manifest_digest = _stable_digest({k: v for k, v in manifest.items() if k != "manifest_digest"})
    if manifest.get("manifest_digest") != expected_manifest_digest:
        findings.append({"code": "EXTDISC-SNAPSHOT-MANIFEST-DIGEST", "message": "snapshot manifest digest drift"})
    return findings


def load_snapshot_manifest(snapshot_dir: Path) -> dict[str, Any]:
    path = Path(snapshot_dir) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def ingest_snapshot(snapshot_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot_dir = Path(snapshot_dir).resolve()
    manifest = load_snapshot_manifest(snapshot_dir)
    findings = validate_snapshot_manifest(snapshot_dir, manifest)
    if findings:
        raise ValueError(json.dumps(findings, ensure_ascii=False, sort_keys=True))

    observations: list[dict[str, Any]] = []
    for row in manifest["files"]:
        rel = _safe_relpath(row["path"])
        text = (snapshot_dir / rel).read_text(encoding="utf-8")
        observations.extend(parse_api_mega_list_markdown(text, source_path=rel))

    source_snapshot = {
        "source_id": SOURCE_ID,
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": manifest["source_commit"],
        "manifest_digest": manifest["manifest_digest"],
        "file_count": len(manifest["files"]),
        "immutable": True,
        "network_fetch_performed": False,
    }
    store = build_candidate_store(source_snapshot=source_snapshot, observations=observations)
    store_findings = validate_candidate_store(store)
    if store_findings:
        raise ValueError(json.dumps(store_findings, ensure_ascii=False, sort_keys=True))

    receipt = {
        "schema": INGEST_RECEIPT_SCHEMA,
        "result": "PASS",
        "source_snapshot": source_snapshot,
        "observation_count": len(observations),
        "candidate_count": store["candidate_count"],
        "store_digest": store["store_digest"],
        "authority": False,
        "runtime_provider": False,
        "automatic_donor_creation": False,
        "automatic_provider_admission": False,
        "automatic_mcp_registration": False,
        "automatic_activation": False,
    }
    receipt["receipt_digest"] = _stable_digest({k: v for k, v in receipt.items() if k != "receipt_digest"})
    return store, receipt


def drift_report(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    prev = {row["candidate_id"]: row for row in previous.get("candidates", []) if isinstance(row, dict) and row.get("candidate_id")}
    curr = {row["candidate_id"]: row for row in current.get("candidates", []) if isinstance(row, dict) and row.get("candidate_id")}
    added = sorted(set(curr) - set(prev))
    removed = sorted(set(prev) - set(curr))
    common = sorted(set(prev) & set(curr))
    changed = sorted(
        candidate_id
        for candidate_id in common
        if prev[candidate_id].get("candidate_digest") != curr[candidate_id].get("candidate_digest")
    )
    report = {
        "schema": DRIFT_SCHEMA,
        "authority": False,
        "canonical_state_replacement_allowed": False,
        "previous_store_digest": previous.get("store_digest"),
        "current_store_digest": current.get("store_digest"),
        "added_candidate_ids": added,
        "removed_candidate_ids": removed,
        "changed_candidate_ids": changed,
        "has_drift": bool(added or removed or changed),
    }
    report["drift_digest"] = _stable_digest({k: v for k, v in report.items() if k != "drift_digest"})
    return report


def default_state_root() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base) / "fa3" / "external-discovery" / "candidates"
    return Path.home() / ".local" / "state" / "fa3" / "external-discovery" / "candidates"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 offline external API discovery ingestion")
    sub = parser.add_subparsers(dest="command", required=True)

    p_snapshot = sub.add_parser("snapshot")
    p_snapshot.add_argument("--snapshot-dir", required=True)
    p_snapshot.add_argument("--source-commit", required=True)
    p_snapshot.add_argument("--output")

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--snapshot-dir", required=True)
    p_ingest.add_argument("--output")
    p_ingest.add_argument("--receipt")

    p_check = sub.add_parser("check")
    p_check.add_argument("--store", required=True)

    p_drift = sub.add_parser("drift")
    p_drift.add_argument("--previous", required=True)
    p_drift.add_argument("--current", required=True)
    p_drift.add_argument("--output")

    p_capacity = sub.add_parser("capacity")
    p_capacity.add_argument("--current-records", required=True, type=int)
    p_capacity.add_argument("--planned-capacity", required=True, type=int)

    args = parser.parse_args()

    if args.command == "snapshot":
        snapshot_dir = Path(args.snapshot_dir)
        manifest = create_snapshot_manifest(snapshot_dir, source_commit=args.source_commit)
        output = Path(args.output) if args.output else snapshot_dir / "manifest.json"
        _write_json(output, manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    if args.command == "ingest":
        store, receipt = ingest_snapshot(Path(args.snapshot_dir))
        output = Path(args.output) if args.output else default_state_root() / "candidate-store.json"
        receipt_path = Path(args.receipt) if args.receipt else output.with_name("ingest-receipt.json")
        _write_json(output, store)
        _write_json(receipt_path, receipt)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0

    if args.command == "check":
        store = _load_json(Path(args.store))
        findings = validate_candidate_store(store)
        report = {"result": "PASS" if not findings else "FAIL", "findings": findings}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if not findings else 2

    if args.command == "drift":
        report = drift_report(_load_json(Path(args.previous)), _load_json(Path(args.current)))
        if args.output:
            _write_json(Path(args.output), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.command == "capacity":
        report = volume_action(current_records=args.current_records, planned_capacity=args.planned_capacity)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    return 3


if __name__ == "__main__":
    raise SystemExit(main())
