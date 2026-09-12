#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

DEFAULT_PROJECTION = "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
DEFAULT_POLICY = "canonical/enforcement-policy.json"
SNAPSHOT_SEMANTICS = "PRE_MAINTENANCE_CANONICAL_MAIN_ANCHOR"
MUTABLE_TOP_LEVEL = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache"}
MUTABLE_DIR_NAMES = {"__pycache__"}


def run(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def mutable_path(rel: str) -> bool:
    parts = Path(rel).parts
    if not parts:
        return True
    if parts[0] in MUTABLE_TOP_LEVEL:
        return True
    if any(part in MUTABLE_DIR_NAMES for part in parts):
        return True
    if rel.startswith("evidence/receipts/") and rel != "evidence/receipts/.gitkeep":
        return True
    return False


def diff_rows(root: Path, base: str, snapshot: str):
    raw = run(root, "diff", "--name-status", "--find-renames", base, snapshot)
    rows = []
    for line in raw.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        rows.append((status, path))
    return rows


def status_label(status: str) -> str:
    if status.startswith("A"):
        return "added"
    if status.startswith("M"):
        return "modified"
    if status.startswith("D"):
        return "removed"
    if status.startswith("R"):
        return "renamed"
    if status.startswith("C"):
        return "copied"
    return "other"


def reconcile(root: Path, projection_rel: str, policy_rel: str) -> dict:
    projection_path = root / projection_rel
    policy_path = root / policy_rel
    projection = loadj(projection_path)
    policy = loadj(policy_path)

    base = projection.get("base_release_commit")
    if not base:
        raise RuntimeError("projection base_release_commit is missing")
    snapshot = run(root, "rev-parse", "HEAD")
    root_tree = run(root, "rev-parse", f"{snapshot}^{{tree}}")
    canonical_tree = run(root, "rev-parse", f"{snapshot}:canonical")
    commit_count = int(run(root, "rev-list", "--count", f"{base}..{snapshot}"))
    rows = diff_rows(root, base, snapshot)
    paths = [path for _, path in rows]
    status_by_path = {path: status_label(status) for status, path in rows}

    added = sum(status.startswith("A") for status, _ in rows)
    modified = sum(status.startswith("M") for status, _ in rows)
    removed = sum(status.startswith("D") for status, _ in rows)
    other = len(rows) - added - modified - removed

    def prefixed(prefix: str):
        return sorted(path for path in paths if path.startswith(prefix))

    projection["last_reconciled_at"] = "2026-09-07"
    projection["source_snapshot"] = {
        "snapshot_semantics": SNAPSHOT_SEMANTICS,
        "baseline_commit_sha": base,
        "pre_projection_head_sha": snapshot,
        "pre_projection_root_tree_sha": root_tree,
        "pre_projection_canonical_tree_sha": canonical_tree,
        "commits_ahead_of_v3_0_11_conformance_commit": commit_count,
        "total_post_baseline_commits": commit_count,
        "delta_file_count": len(rows),
        "delta_added_files": added,
        "delta_modified_files": modified,
        "delta_removed_files": removed,
        "delta_other_files": other,
    }

    inventory = projection.setdefault("overlay_inventory", {})
    inventory.update({
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

    projection["mandatory_reference_gates"] = list(policy.get("mandatory_reference_gates", []))
    projection["inference_cache_hardening_reconciliation"] = {
        "parent_gate_id": "FA3-INFERENCE-PORTABILITY-GATESET-001",
        "subgate_id": "FA3-INFERENCE-PORTABILITY-CACHE-HARDENING-001",
        "profile_id": "FA3-INFERENCE-PORTABILITY-001",
        "contract_id": "FA3-INFERENCE-PORTABILITY-CONTRACTS-001",
        "provider_id": "FA3-PROVIDER-TENSORRT-RTX-001",
        "decision_id": "FA3-DEC-INFERENCE-CACHE-HARDENING-2026-09-07",
        "reference_id": "FA3-TENSORRT-RTX-RUNTIME-CACHE-REFERENCE-2026-09-07",
        "reference_evidence": "evidence/reference/inference-cache-hardening-ci-2026-09-07.json",
        "capability_bindings": ["CAP-005", "CAP-006", "CAP-137", "CAP-143"],
        "reconciliation_status": "GLOBAL_PROJECTION_RECONCILED_CI_REFERENCE_PASS_CURRENT_HOST_PENDING",
        "current_host_runtime_promotion_claim": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": 143,
    }

    projection["codex_reconciliation"] = {
        "provider_id": "FA3-PROVIDER-CODEX-001",
        "gate_id": "FA3-CODEX-GATESET-001",
        "capability_id": "CAP-028",
        "classification": "REMOVED_PAID_PROVIDER_TOMBSTONE",
        "reconciliation_status": "DECOMMISSIONED_FREE_ONLY_POLICY",
        "runtime_activation_status": "REMOVED_NOT_ADMITTED",
        "current_host_production_e2e": "NOT_APPLICABLE_REMOVED",
        "provider_runtime_required_for_global_promotion_when_disabled": False,
        "economics_policy": "FA3-FREE-SELF-HOSTED-ONLY-001",
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": 143,
    }
    projection["free_only_reconciliation"] = {
        "policy_id": "FA3-FREE-SELF-HOSTED-ONLY-001",
        "gate_id": "FA3-FREE-ONLY-GATESET-001",
        "status": "CANONICAL_FAIL_CLOSED",
        "paid_provider_fallback": False,
        "capability_count_after": 143,
    }

    ls = run(root, "ls-tree", "-r", "--full-tree", snapshot)
    manifest = []
    for line in ls.splitlines():
        if not line:
            continue
        meta, path = line.split("\t", 1)
        mode, obj_type, sha = meta.split()
        if obj_type != "blob" or path == projection_rel or mutable_path(path):
            continue
        manifest.append({
            "path": path,
            "git_blob_sha": sha,
            "baseline_delta_status": status_by_path.get(path, "unchanged"),
        })
    manifest.sort(key=lambda x: x["path"])
    projection["manifest"] = manifest
    projection["manifest_entry_count"] = len(manifest)
    projection["manifest_scope"] = {
        "repository_release_surface_complete": True,
        "self_excluded_path": projection_rel,
        "mutable_runtime_evidence_receipts_excluded": True,
        "mutable_runtime_paths_excluded": [
            "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache",
            "__pycache__", "evidence/receipts/* except .gitkeep",
        ],
    }
    projection["self_hash_policy"] = {
        "excluded_path": projection_rel,
        "reason": "SELF_REFERENTIAL_HASH_EXCLUSION",
    }

    writej(projection_path, projection)
    return {
        "snapshot": snapshot,
        "root_tree": root_tree,
        "canonical_tree": canonical_tree,
        "commit_count": commit_count,
        "delta_files": len(rows),
        "manifest_entries": len(manifest),
        "projection": projection_rel,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the FA3 unified release projection from an immutable Git snapshot")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--projection", default=DEFAULT_PROJECTION)
    parser.add_argument("--policy", default=DEFAULT_POLICY)
    args = parser.parse_args()
    result = reconcile(Path(args.root).resolve(), args.projection, args.policy)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
