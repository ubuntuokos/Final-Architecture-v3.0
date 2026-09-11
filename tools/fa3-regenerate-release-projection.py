#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

PROJECTION_REL = Path("canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json")


def run(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def excluded(path: str) -> bool:
    return (
        path == PROJECTION_REL.as_posix()
        or path.startswith("reports/")
        or path.startswith("acceptance/")
        or path.startswith("promotion/")
        or path.startswith(".fa3-current-host/")
        or "/__pycache__/" in path
        or path.startswith(".pytest_cache/")
        or path.startswith(".mypy_cache/")
        or (path.startswith("evidence/receipts/") and path != "evidence/receipts/.gitkeep")
    )


def tree_entries(root: Path, ref: str) -> list[dict[str, str]]:
    out = run(root, "ls-tree", "-r", ref)
    rows: list[dict[str, str]] = []
    for line in out.splitlines():
        if not line:
            continue
        meta, path = line.split("\t", 1)
        mode, typ, sha = meta.split()
        if typ == "blob":
            rows.append({"path": path, "mode": mode, "sha": sha})
    return rows


def diff_rows(root: Path, baseline: str, ref: str) -> list[tuple[str, str]]:
    out = run(root, "diff", "--name-status", f"{baseline}..{ref}")
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0][0]
        path = parts[-1]
        rows.append((status, path))
    return rows


def changed_paths(rows: list[tuple[str, str]], prefix: str) -> list[str]:
    return sorted(path for status, path in rows if status != "D" and path.startswith(prefix))


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate the FA3 unified post-v3.0.11 release projection from Git objects")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--snapshot-ref", default="HEAD", help="Git ref/commit whose release surface is projected")
    ap.add_argument("--output", help="Optional output path; defaults to canonical projection path")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    projection_path = root / PROJECTION_REL
    projection: dict[str, Any] = json.loads(projection_path.read_text(encoding="utf-8"))
    baseline = projection.get("source_snapshot", {}).get("baseline_commit_sha") or projection.get("base_release_commit")
    if not baseline:
        raise RuntimeError("projection has no baseline commit")

    snapshot = run(root, "rev-parse", args.snapshot_ref)
    root_tree = run(root, "rev-parse", f"{snapshot}^{{tree}}")
    canonical_tree = run(root, "rev-parse", f"{snapshot}:canonical")
    commit_count = int(run(root, "rev-list", "--count", f"{baseline}..{snapshot}"))
    rows = diff_rows(root, baseline, snapshot)
    added = sum(status == "A" for status, _ in rows)
    modified = sum(status == "M" for status, _ in rows)
    removed = sum(status == "D" for status, _ in rows)

    projection["source_snapshot"] = {
        **projection.get("source_snapshot", {}),
        "snapshot_semantics": "PRE_MAINTENANCE_CANONICAL_MAIN_ANCHOR",
        "baseline_commit_sha": baseline,
        "pre_projection_head_sha": snapshot,
        "pre_projection_root_tree_sha": root_tree,
        "pre_projection_canonical_tree_sha": canonical_tree,
        "commits_ahead_of_v3_0_11_conformance_commit": commit_count,
        "total_post_baseline_commits": commit_count,
        "delta_file_count": len(rows),
        "delta_added_files": added,
        "delta_modified_files": modified,
        "delta_removed_files": removed,
        "delta_other_files": len(rows) - added - modified - removed,
    }

    inventory = projection.setdefault("overlay_inventory", {})
    inventory.update({
        "canonical_files_in_post_baseline_delta": len(changed_paths(rows, "canonical/")),
        "evidence_files_in_post_baseline_delta": len(changed_paths(rows, "evidence/")),
        "source_files_in_post_baseline_delta": len(changed_paths(rows, "src/")),
        "test_files_in_post_baseline_delta": len(changed_paths(rows, "tests/")),
        "workflow_files_in_post_baseline_delta": len(changed_paths(rows, ".github/workflows/")),
        "provider_records": changed_paths(rows, "canonical/providers/"),
        "profile_records": changed_paths(rows, "canonical/profiles/"),
        "contract_records": changed_paths(rows, "canonical/contracts/"),
        "decision_records": changed_paths(rows, "canonical/decisions/"),
        "upstream_reference_records": changed_paths(rows, "canonical/references/"),
        "reference_evidence_records": changed_paths(rows, "evidence/reference/"),
    })

    ff = projection.setdefault("ffmpeg_ai_reconciliation", {})
    ff.update({
        "current_host_conformance_id": "FA3-FFMPEG-AI-RUNTIME-CONFORMANCE-001",
        "current_host_executable_gate_id": "FA3-GATE-FFMPEG-AI-CURRENT-HOST-001",
        "current_host_decision_id": "FA3-DEC-FFMPEG-AI-CURRENT-HOST-2026-09-03",
        "current_host_correction_decision_id": "FA3-DEC-FFMPEG-AI-CURRENT-HOST-PORTABILITY-2026-09-04",
        "current_host_workflow": ".github/workflows/fa3-ffmpeg-ai-current-host.yml",
        "current_host_closure_status": "EXECUTABLE_CLOSURE_MATERIALIZED_REAL_HOST_EXECUTION_PENDING",
        "current_host_required_evidence_level": "CURRENT_HOST_FFMPEG_NEURAL_MEDIA_PRODUCTION_E2E_PASS",
        "current_host_receipt_schema": "fa3.ffmpeg-ai-current-host-receipt.v2",
        "current_host_runtime_evidence": "PENDING_REAL_CURRENT_HOST_EXECUTION",
        "current_host_runtime_promotion_claim": False,
        "hardware_baseline_id": "FA3-HARDWARE-BASELINE-001",
        "reference_host_match_required": False,
        "current_host_facts_are_evidence_only": True,
        "hrb_lease_schema": "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1",
        "production_real_media_provenance_required": True,
        "synthetic_media_can_satisfy_production_pass": False,
    })

    manifest = [
        {"path": row["path"], "git_blob_sha": row["sha"]}
        for row in tree_entries(root, snapshot)
        if not excluded(row["path"])
    ]
    manifest.sort(key=lambda item: item["path"])
    projection["manifest"] = manifest
    projection["manifest_entry_count"] = len(manifest)
    projection["last_reconciled_at"] = "2026-09-04"
    projection["last_regenerated_at"] = "2026-09-04"

    output = Path(args.output).resolve() if args.output else projection_path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(projection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "snapshot": snapshot,
        "root_tree": root_tree,
        "canonical_tree": canonical_tree,
        "commits": commit_count,
        "delta_files": len(rows),
        "added": added,
        "modified": modified,
        "removed": removed,
        "manifest_entries": len(manifest),
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
