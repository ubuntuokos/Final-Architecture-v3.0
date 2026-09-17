#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_release_projection_gate import (  # noqa: E402
    BASE_COMMIT,
    PROJECTION_PATH,
    _diff_rows,
    collect_git_snapshot_facts,
    git_blob_sha,
    is_mutable_runtime_path,
)


def _status_name(raw: str) -> str:
    if raw.startswith("A"):
        return "added"
    if raw.startswith("M"):
        return "modified"
    if raw.startswith("D"):
        return "removed"
    return "other"


def build_candidate(root: Path, snapshot_head: str) -> dict:
    root = root.resolve()
    projection_path = root / PROJECTION_PATH
    projection = json.loads(projection_path.read_text(encoding="utf-8"))

    facts = collect_git_snapshot_facts(root, snapshot_head)
    snapshot = projection.setdefault("source_snapshot", {})
    snapshot.update({
        "snapshot_semantics": "PRE_MAINTENANCE_CANONICAL_MAIN_ANCHOR",
        "baseline_commit_sha": BASE_COMMIT,
        "pre_projection_head_sha": facts["snapshot_head_sha"],
        "pre_projection_root_tree_sha": facts["root_tree_sha"],
        "pre_projection_canonical_tree_sha": facts["canonical_tree_sha"],
        "commits_ahead_of_v3_0_11_conformance_commit": facts["commit_count"],
        "total_post_baseline_commits": facts["commit_count"],
        "delta_file_count": facts["delta_file_count"],
        "delta_added_files": facts["delta_added_files"],
        "delta_modified_files": facts["delta_modified_files"],
        "delta_removed_files": facts["delta_removed_files"],
        "delta_other_files": facts["delta_other_files"],
    })

    inventory = projection.setdefault("overlay_inventory", {})
    inventory.update(facts["area_counts"])

    prior_status = {
        x.get("path"): x.get("baseline_delta_status", "other")
        for x in projection.get("manifest", [])
        if x.get("path")
    }
    delta_status = {path: _status_name(status) for status, path in _diff_rows(root, snapshot_head)}

    manifest = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == PROJECTION_PATH or is_mutable_runtime_path(rel):
            continue
        manifest.append({
            "path": rel,
            "git_blob_sha": git_blob_sha(path),
            "baseline_delta_status": delta_status.get(rel, prior_status.get(rel, "unchanged")),
        })
    manifest.sort(key=lambda x: x["path"])
    projection["manifest"] = manifest
    projection["manifest_entry_count"] = len(manifest)
    projection.setdefault("scope", {})["self_excluded_path"] = PROJECTION_PATH
    projection["scope"]["mutable_runtime_evidence_receipts_excluded"] = True
    return projection


def main() -> int:
    ap = argparse.ArgumentParser(description="Materialize a deterministic FA3 release-projection candidate without mutating canonical state")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--snapshot-head", required=True)
    ap.add_argument("--output", default="reports/release-projection-candidate.json")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    candidate = build_candidate(root, args.snapshot_head)
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "MATERIALIZED_CANDIDATE",
        "output": out.relative_to(root).as_posix(),
        "snapshot_head": candidate["source_snapshot"]["pre_projection_head_sha"],
        "manifest_entry_count": candidate["manifest_entry_count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
