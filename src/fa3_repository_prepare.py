#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

PROJECTION = Path("canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json")


class RepositoryPrepareError(RuntimeError):
    pass


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if check and cp.returncode != 0:
        raise RepositoryPrepareError(
            f"git {' '.join(args)} failed with rc={cp.returncode}: {cp.stderr.strip()}"
        )
    return cp


def _commit_exists(root: Path, sha: str) -> bool:
    return _git(root, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0


def required_commits(root: Path) -> list[str]:
    path = root / PROJECTION
    data = json.loads(path.read_text(encoding="utf-8"))
    snapshot = data.get("source_snapshot", {})
    values = [
        data.get("base_release_commit"),
        snapshot.get("baseline_commit_sha"),
        snapshot.get("pre_projection_head_sha"),
    ]
    out: list[str] = []
    for value in values:
        if isinstance(value, str) and value and value not in out:
            out.append(value)
    if not out:
        raise RepositoryPrepareError("release projection declares no required Git commit anchors")
    return out


def _fetch_exact(root: Path, remote: str, sha: str) -> None:
    attempts = [
        ["fetch", "--no-tags", "--filter=blob:none", remote, sha],
        ["fetch", "--no-tags", remote, sha],
    ]
    errors: list[str] = []
    for argv in attempts:
        cp = _git(root, *argv, check=False)
        if cp.returncode == 0 and _commit_exists(root, sha):
            return
        errors.append(cp.stderr.strip() or f"rc={cp.returncode}")
    raise RepositoryPrepareError(
        f"required Git object {sha} is unavailable. Recovery: git -C {root} fetch --no-tags {remote} {sha}. "
        f"Fetch attempts: {' | '.join(errors)}"
    )


def _verify_snapshot_identity(root: Path) -> dict[str, Any]:
    data = json.loads((root / PROJECTION).read_text(encoding="utf-8"))
    snapshot = data["source_snapshot"]
    head = snapshot["pre_projection_head_sha"]
    root_tree = _git(root, "rev-parse", f"{head}^{{tree}}").stdout.strip()
    canonical_tree = _git(root, "rev-parse", f"{head}:canonical").stdout.strip()
    baseline = snapshot["baseline_commit_sha"]
    ancestor = _git(root, "merge-base", "--is-ancestor", baseline, head, check=False).returncode == 0
    findings: list[str] = []
    if root_tree != snapshot.get("pre_projection_root_tree_sha"):
        findings.append("pre_projection_root_tree_sha mismatch")
    if canonical_tree != snapshot.get("pre_projection_canonical_tree_sha"):
        findings.append("pre_projection_canonical_tree_sha mismatch")
    if not ancestor:
        findings.append("baseline commit is not an ancestor of projection snapshot")
    return {
        "snapshot_head": head,
        "root_tree_sha": root_tree,
        "canonical_tree_sha": canonical_tree,
        "baseline_is_ancestor": ancestor,
        "findings": findings,
    }


def prepare_repository(root: Path, *, remote: str = "origin", check_only: bool = False) -> dict[str, Any]:
    root = root.resolve()
    required = required_commits(root)
    missing = [sha for sha in required if not _commit_exists(root, sha)]
    fetched: list[str] = []
    if missing and not check_only:
        for sha in missing:
            _fetch_exact(root, remote, sha)
            fetched.append(sha)
    remaining = [sha for sha in required if not _commit_exists(root, sha)]
    identity: dict[str, Any] | None = None
    findings: list[str] = []
    if remaining:
        findings.extend([f"missing Git object: {sha}" for sha in remaining])
    else:
        try:
            identity = _verify_snapshot_identity(root)
            findings.extend(identity["findings"])
        except Exception as exc:
            findings.append(f"snapshot identity verification failed: {exc}")
    return {
        "schema": "fa3.repository-prepare.v1",
        "result": "PASS" if not findings else "FAIL",
        "check_only": check_only,
        "remote": remote,
        "required_commits": required,
        "initially_missing": missing,
        "fetched": fetched,
        "remaining_missing": remaining,
        "snapshot_identity": identity,
        "working_tree_mutated": False,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Git history required by FA3 canonical gates")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    result = prepare_repository(Path(args.root), remote=args.remote, check_only=args.check_only)
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
