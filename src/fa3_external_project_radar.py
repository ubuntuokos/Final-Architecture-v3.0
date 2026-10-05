#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

DISPOSITIONS = {
    "IMPLEMENTED",
    "CODE_CANDIDATE",
    "PATTERN_SOURCE",
    "REFERENCE",
    "BLOCKED_LICENSE",
    "BLOCKED_SECURITY",
    "SUPERSEDED",
}
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD"}
COPY_BLOCKED = {"UNKNOWN", "UNDECLARED", "CUSTOM", "GPL", "AGPL", "FSL"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema") != "fa3.external-project-radar.snapshot.v1":
        raise ValueError("invalid radar snapshot schema")
    commit = data.get("source_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("snapshot requires immutable 40-char commit")
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("snapshot file inventory required")
    for row in files:
        if not isinstance(row, dict):
            raise ValueError("snapshot file row must be object")
        if not re.fullmatch(r"[0-9a-f]{40}", str(row.get("blob_sha", ""))):
            raise ValueError("snapshot row requires blob sha")
        if row.get("copy_policy") not in {"LOCAL_COPY", "IMMUTABLE_UPSTREAM_BLOB_REFERENCE"}:
            raise ValueError("invalid copy policy")
    return data


def verify_local_copies(snapshot_dir: Path) -> list[dict[str, Any]]:
    manifest = validate_manifest(snapshot_dir / "manifest.json")
    findings: list[dict[str, Any]] = []
    for row in manifest["files"]:
        if row["copy_policy"] != "LOCAL_COPY":
            continue
        path = snapshot_dir / row["path"]
        if not path.is_file():
            findings.append({"code": "RADAR_COPY_MISSING", "path": row["path"]})
            continue
        if path.stat().st_size != int(row["size"]):
            findings.append({
                "code": "RADAR_COPY_SIZE_DRIFT",
                "path": row["path"],
                "expected": row["size"],
                "actual": path.stat().st_size,
            })
    return findings


_PROJECT_LINE = re.compile(
    r"^- \[\*\*(?P<name>.+?)\*\*\]\((?P<url>https://github\.com/[^)]+)\).*?"
)
_LICENSE = re.compile(r"License:\s*([^\n·]+)", re.IGNORECASE)


def normalize_readme(snapshot_dir: Path) -> list[dict[str, Any]]:
    readme = snapshot_dir / "README.md"
    if not readme.is_file():
        raise FileNotFoundError(readme)
    lines = readme.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    category = "UNCLASSIFIED"
    current: dict[str, Any] | None = None
    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            title = re.sub(r"^##\s+", "", line).strip()
            if title and title not in {"Categories"}:
                category = re.sub(r"^[^A-Za-z0-9]+", "", title).strip()
        match = _PROJECT_LINE.match(line)
        if match:
            current = {
                "name": match.group("name"),
                "repository": match.group("url").removesuffix("/"),
                "category": category,
                "upstream_listed": True,
                "upstream_source_reviewed": False,
                "fa3_source_reviewed": False,
                "fa3_license_reviewed": False,
                "fa3_security_reviewed": False,
                "fa3_runtime_verified": False,
                "disposition": "REFERENCE",
            }
            rows.append(current)
            continue
        if current and "Where Jev makes a decision" in line:
            current["decision_point"] = line.split(":", 1)[-1].strip()
        if current and "What this project offers" in line:
            current["offering"] = line.split(":", 1)[-1].strip()
        if current and "License:" in line:
            m = _LICENSE.search(line)
            if m:
                current["declared_license"] = m.group(1).strip()
    return rows


def license_reuse_mode(license_name: str | None) -> str:
    if not license_name:
        return "PATTERN_ONLY_PENDING_LICENSE"
    normalized = license_name.strip()
    if normalized in PERMISSIVE:
        return "CODE_CANDIDATE_AFTER_FA3_REVIEW"
    upper = normalized.upper()
    if upper in COPY_BLOCKED or any(token in upper for token in ("GPL", "AGPL", "FAIR SOURCE", "FSL")):
        return "PATTERN_ONLY"
    return "MANUAL_LICENSE_REVIEW_REQUIRED"


def reuse_hints(row: dict[str, Any]) -> dict[str, Any]:
    hay = " ".join(str(row.get(k, "")) for k in ("name", "category", "offering", "decision_point")).lower()
    capabilities: list[str] = []
    patterns: list[str] = []
    consumers: list[str] = []
    collisions: list[str] = []
    if "browser" in hay:
        capabilities.append("fa3.browser.navigate")
        consumers.append("FA3-WEB-AI-001")
    if any(token in hay for token in ("memory", "knowledge", "rag", "retrieval")):
        capabilities.extend(["fa3.memory.retrieve", "fa3.document.retrieve"])
        consumers.append("FA3-KNOWLEDGE-001")
    if any(token in hay for token in ("model", "inference", "embedding", "llm")):
        consumers.extend(["FA3-MODEL-MANAGER-001", "FA3-INFERENCE-PORTABILITY-001"])
        patterns.append("FA3-PATTERN-PROVIDER-NEUTRAL-ADAPTER-001")
    if any(token in hay for token in ("migration", "version", "upgrade")):
        patterns.append("FA3-PATTERN-SHADOW-MIGRATION-001")
    if any(token in hay for token in ("router", "scheduler", "registry", "authority")):
        collisions.extend(["MODEL_ROUTING_OR_RESOURCE_OR_REGISTRY_AUTHORITY_REVIEW_REQUIRED"])
    return {
        "problem_classes": sorted(set(re.findall(r"[a-z0-9-]+", str(row.get("category", "")).lower()))),
        "potential_capability_bindings": sorted(set(capabilities)),
        "reusable_patterns": sorted(set(patterns)),
        "possible_existing_fa3_consumers": sorted(set(consumers)),
        "authority_collision_candidates": sorted(set(collisions)),
    }


def build_normalized(snapshot_dir: Path) -> dict[str, Any]:
    manifest = validate_manifest(snapshot_dir / "manifest.json")
    rows = normalize_readme(snapshot_dir)
    for row in rows:
        row["reuse_mode"] = license_reuse_mode(row.get("declared_license"))
        row.update(reuse_hints(row))
    return {
        "schema": "fa3.external-project-radar.normalized.v1",
        "source_repository": manifest["source_repository"],
        "source_commit": manifest["source_commit"],
        "project_count": len(rows),
        "projects": rows,
        "fa3_verification_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-dir", required=True)
    parser.add_argument("--output")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    snapshot_dir = Path(args.snapshot_dir)
    findings = verify_local_copies(snapshot_dir)
    normalized = build_normalized(snapshot_dir)
    report = {
        "schema": "fa3.external-project-radar-report.v1",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "snapshot": normalized,
    }
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
