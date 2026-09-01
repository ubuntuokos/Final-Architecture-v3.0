#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

from fa3_release_projection_gate import (
    PROJECTION_PATH,
    collect_git_snapshot_facts,
    git_blob_sha,
    is_mutable_runtime_path,
)


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git command failed")
    return proc.stdout.strip()


def regenerate(root: Path, snapshot_head: str | None = None):
    root = Path(root).resolve()
    projection_path = root / PROJECTION_PATH
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    policy = json.loads((root / "canonical/enforcement-policy.json").read_text(encoding="utf-8"))
    snapshot_head = snapshot_head or _git(root, "rev-parse", "HEAD")
    facts = collect_git_snapshot_facts(root, snapshot_head)

    snapshot = projection["source_snapshot"]
    snapshot.update({
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

    inventory = projection["overlay_inventory"]
    inventory.update(facts["area_counts"])
    inventory.update(facts["record_lists"])
    projection["mandatory_reference_gates"] = policy["mandatory_reference_gates"]

    manifest = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == PROJECTION_PATH or is_mutable_runtime_path(rel):
            continue
        manifest.append({"path": rel, "git_blob_sha": git_blob_sha(path)})
    projection["manifest"] = manifest
    projection["manifest_entry_count"] = len(manifest)
    projection["last_reconciled_at"] = date.today().isoformat()
    projection["last_regenerated_at"] = date.today().isoformat()
    projection_path.write_text(
        json.dumps(projection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "projection": PROJECTION_PATH,
        "snapshot_head": snapshot_head,
        "manifest_entries": len(manifest),
        "delta_files": facts["delta_file_count"],
    }


def main():
    parser = argparse.ArgumentParser(description="Regenerate the unified FA3 release projection")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--snapshot-head")
    args = parser.parse_args()
    result = regenerate(Path(args.root), args.snapshot_head)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
