#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "1d8a3ffaa2b4d11abcc6003250ff66b4798eef60"
PROJECTION_PATH = "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
TEMP_PATHS = {
    ".github/workflows/fa3-openhero-snapshot-reconcile.yml",
    "tools/reconcile_openhero_snapshot.py",
}
MUTABLE_TOP_LEVEL = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache", ".fa3-current-host"}


def run(*args: str) -> str:
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"{' '.join(args)}\n{p.stdout}\n{p.stderr}")
    return p.stdout.strip()


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def mutable(rel: str) -> bool:
    parts = Path(rel).parts
    if not parts or parts[0] in MUTABLE_TOP_LEVEL or "__pycache__" in parts:
        return True
    return rel.startswith("evidence/receipts/") and rel != "evidence/receipts/.gitkeep"


def diff_rows(snapshot: str):
    raw = run("git", "diff", "--name-status", "--find-renames", BASE, snapshot)
    rows = []
    for line in raw.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1] if status.startswith(("R", "C")) else parts[1]
        rows.append((status, path))
    return rows


def main() -> None:
    # The workflow and this helper are the only two commits after the real
    # merged pre-projection release surface. Anchor to that immutable state.
    snapshot = run("git", "rev-parse", "HEAD~2")
    rows = diff_rows(snapshot)
    paths = [p for _, p in rows]
    added = sum(s.startswith("A") for s, _ in rows)
    modified = sum(s.startswith("M") for s, _ in rows)
    removed = sum(s.startswith("D") for s, _ in rows)
    other = len(rows) - added - modified - removed
    prefixed = lambda prefix: sorted(p for p in paths if p.startswith(prefix))

    projection_file = ROOT / PROJECTION_PATH
    projection = json.loads(projection_file.read_text(encoding="utf-8"))
    ss = projection.setdefault("source_snapshot", {})
    ss.update({
        "snapshot_semantics": "PRE_MAINTENANCE_CANONICAL_MAIN_ANCHOR",
        "baseline_commit_sha": BASE,
        "pre_projection_head_sha": snapshot,
        "pre_projection_root_tree_sha": run("git", "rev-parse", f"{snapshot}^{{tree}}"),
        "pre_projection_canonical_tree_sha": run("git", "rev-parse", f"{snapshot}:canonical"),
        "commits_ahead_of_v3_0_11_conformance_commit": int(run("git", "rev-list", "--count", f"{BASE}..{snapshot}")),
        "total_post_baseline_commits": int(run("git", "rev-list", "--count", f"{BASE}..{snapshot}")),
        "delta_file_count": len(rows),
        "delta_added_files": added,
        "delta_modified_files": modified,
        "delta_removed_files": removed,
        "delta_other_files": other,
    })

    inv = projection.setdefault("overlay_inventory", {})
    inv.update({
        "canonical_files_in_post_baseline_delta": len(prefixed("canonical/")),
        "evidence_files_in_post_baseline_delta": len(prefixed("evidence/")),
        "source_files_in_post_baseline_delta": len(prefixed("src/")),
        "test_files_in_post_baseline_delta": len(prefixed("tests/")),
        "workflow_files_in_post_baseline_delta": len(prefixed(".github/workflows/")),
        "provider_records": prefixed("canonical/providers/"),
        "profile_records": prefixed("canonical/profiles/"),
        "contract_records": prefixed("canonical/contracts/"),
        "decision_records": prefixed("canonical/decisions/"),
        "upstream_reference_records": prefixed("canonical/references/"),
        "reference_evidence_records": prefixed("evidence/reference/"),
    })

    files = []
    for item in ROOT.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(ROOT).as_posix()
        if rel == PROJECTION_PATH or rel in TEMP_PATHS or mutable(rel):
            continue
        files.append(rel)
    files.sort()
    projection["manifest"] = [{"path": rel, "git_blob_sha": blob_sha(ROOT / rel)} for rel in files]
    projection["manifest_entry_count"] = len(files)
    projection_file.write_text(json.dumps(projection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", PROJECTION_PATH)
    run("git", "commit", "-m", "FA3: reconcile merged OpenHero release snapshot lineage")
    branch = os.environ.get("GITHUB_REF_NAME") or run("git", "branch", "--show-current")
    run("git", "push", "origin", f"HEAD:{branch}")
    print(json.dumps({
        "status": "PASS",
        "snapshot": snapshot,
        "manifest_entry_count": len(files),
        "delta_file_count": len(rows),
        "commit_count": ss["total_post_baseline_commits"],
        "head": run("git", "rev-parse", "HEAD"),
    }, indent=2))


if __name__ == "__main__":
    main()
