#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import venv
from pathlib import Path
from typing import Any

PROJECTION = Path("canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json")
TEST_REQUIREMENTS = Path("requirements/test.txt")


class PreparationError(RuntimeError):
    pass


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)
    if check and cp.returncode != 0:
        raise PreparationError(cp.stderr.strip() or f"git {' '.join(args)} failed")
    return cp


def _object_exists(root: Path, spec: str) -> bool:
    return _git(root, "cat-file", "-e", spec, check=False).returncode == 0


def required_git_objects(root: Path) -> list[dict[str, str]]:
    projection = json.loads((root / PROJECTION).read_text(encoding="utf-8"))
    snapshot = projection.get("source_snapshot", {})
    values = [
        ("baseline_commit", snapshot.get("baseline_commit_sha")),
        ("pre_projection_head", snapshot.get("pre_projection_head_sha")),
    ]
    out = []
    for kind, value in values:
        if not isinstance(value, str) or len(value) != 40:
            raise PreparationError(f"{kind} missing/invalid in release projection")
        out.append({"kind": kind, "sha": value})
    return out


def _is_shallow(root: Path) -> bool:
    cp = _git(root, "rev-parse", "--is-shallow-repository", check=False)
    return cp.returncode == 0 and cp.stdout.strip() == "true"


def recover_git_objects(root: Path, missing: list[str], remote: str) -> list[str]:
    commands: list[str] = []
    if not missing:
        return commands
    if _is_shallow(root):
        argv = ["fetch", "--no-tags", "--unshallow", remote]
        cp = _git(root, *argv, check=False)
        commands.append("git " + " ".join(argv))
        if cp.returncode != 0:
            argv = ["fetch", "--no-tags", "--deepen=1000000", remote]
            cp = _git(root, *argv, check=False)
            commands.append("git " + " ".join(argv))
    else:
        argv = ["fetch", "--no-tags", remote, "main"]
        _git(root, *argv, check=False)
        commands.append("git " + " ".join(argv))
    for sha in missing:
        if _object_exists(root, f"{sha}^{{commit}}"):
            continue
        argv = ["fetch", "--no-tags", remote, sha]
        _git(root, *argv, check=False)
        commands.append("git " + " ".join(argv))
    return commands


def inspect(root: Path) -> dict[str, Any]:
    required = required_git_objects(root)
    rows = []
    for item in required:
        sha = item["sha"]
        commit_ok = _object_exists(root, f"{sha}^{{commit}}")
        tree_ok = commit_ok and _object_exists(root, f"{sha}^{{tree}}")
        rows.append({**item, "commit_available": commit_ok, "tree_available": tree_ok})
    return {
        "schema": "fa3.repository-preparation-report.v1",
        "result": "PASS" if all(x["commit_available"] and x["tree_available"] for x in rows) else "FAIL",
        "repository": str(root),
        "is_shallow": _is_shallow(root),
        "required_objects": rows,
        "recovery_hint": "bash bin/fa3-prepare-repository --fetch" if any(not x["commit_available"] for x in rows) else None,
    }


def ensure_venv(root: Path, target: Path) -> dict[str, Any]:
    target = target if target.is_absolute() else root / target
    if not (target / "bin/python").exists():
        venv.EnvBuilder(with_pip=True, clear=False, symlinks=True).create(target)
    python = target / "bin/python"
    cp = subprocess.run(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(root / TEST_REQUIREMENTS)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if cp.returncode != 0:
        raise PreparationError("test dependency installation failed: " + cp.stderr.strip())
    return {"venv": str(target), "python": str(python), "requirements": str(TEST_REQUIREMENTS)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare an FA3 clone for reproducible local/CI gates")
    parser.add_argument("--root", default=".")
    parser.add_argument("--fetch", action="store_true", help="recover required historical Git objects from the remote")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--venv", help="create/update an isolated test venv and install pinned test requirements")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not (root / ".git").exists():
        print(json.dumps({"result": "FAIL", "error": "not a Git working tree"}, indent=2))
        return 2

    before = inspect(root)
    recovery_commands: list[str] = []
    if before["result"] != "PASS" and args.fetch:
        missing = [x["sha"] for x in before["required_objects"] if not x["commit_available"] or not x["tree_available"]]
        recovery_commands = recover_git_objects(root, missing, args.remote)
    after = inspect(root)
    venv_report = None
    if args.venv and after["result"] == "PASS":
        try:
            venv_report = ensure_venv(root, Path(args.venv))
        except PreparationError as exc:
            after["result"] = "FAIL"
            after["venv_error"] = str(exc)

    after["recovery_commands"] = recovery_commands
    after["test_environment"] = venv_report
    print(json.dumps(after, indent=2))
    return 0 if after["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
