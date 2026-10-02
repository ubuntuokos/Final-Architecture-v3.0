#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

POLICY_PATH = Path("canonical/FA3-CURRENT-HOST-STRUCTURAL-CHANGE-POLICY-001.json")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def changed_files_from_git(root: Path, base: str, head: str) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff failed: {proc.stderr.strip()}")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def is_current_host_companion(path: str, policy: dict[str, Any]) -> bool:
    lower = path.lower()
    if path.startswith("docs/") or path.startswith("tests/"):
        return False
    return any(marker in lower for marker in policy["current_host_markers"])


def is_structural(path: str, policy: dict[str, Any]) -> bool:
    if path in set(policy.get("excluded_exact_paths", [])):
        return False
    if any(path.startswith(prefix) for prefix in policy.get("excluded_path_prefixes", [])):
        return False
    if is_current_host_companion(path, policy):
        return False
    if not any(path.startswith(prefix) for prefix in policy.get("structural_path_prefixes", [])):
        return False
    lower = path.lower()
    return any(token in lower for token in policy.get("structural_tokens", []))


def _validate_impact_record(
    root: Path,
    record_path: str,
    *,
    changed_files: set[str],
    structural_changes: set[str],
    policy: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    findings: list[str] = []
    path = root / record_path
    if not path.is_file():
        return None, [f"impact record missing: {record_path}"]
    try:
        record = load_json(path)
    except Exception as exc:
        return None, [f"impact record unreadable: {record_path}: {exc}"]

    if record.get("schema") != policy.get("impact_record_schema"):
        findings.append(f"{record_path}: impact record schema mismatch")
    status = record.get("status")
    if status not in set(policy.get("accepted_impact_statuses", [])):
        findings.append(f"{record_path}: unsupported impact status")

    declared = record.get("structural_changes")
    if not isinstance(declared, list) or not declared or any(not isinstance(x, str) for x in declared):
        findings.append(f"{record_path}: structural_changes must be a non-empty string list")
        declared_set: set[str] = set()
    else:
        declared_set = set(declared)
        unknown = declared_set - structural_changes
        if unknown:
            findings.append(f"{record_path}: declares non-structural or unchanged paths: {sorted(unknown)}")

    if record.get("historical_evidence_reused") is not False:
        findings.append(f"{record_path}: historical_evidence_reused must be false")

    physical = record.get("physical_requalification_required")
    if not isinstance(physical, bool):
        findings.append(f"{record_path}: physical_requalification_required must be explicit boolean")

    companions = record.get("current_host_changes", [])
    if not isinstance(companions, list) or any(not isinstance(x, str) for x in companions):
        findings.append(f"{record_path}: current_host_changes must be a string list")
        companions = []

    if status == "RECONCILED":
        if not companions:
            findings.append(f"{record_path}: RECONCILED requires current_host_changes")
        for companion in companions:
            if companion not in changed_files:
                findings.append(f"{record_path}: current-host companion not changed in this changeset: {companion}")
            elif not is_current_host_companion(companion, policy):
                findings.append(f"{record_path}: path is not a current-host companion: {companion}")
    elif status == "NO_RUNTIME_IMPACT":
        rationale = record.get("rationale")
        if not isinstance(rationale, str) or len(rationale.strip()) < 20:
            findings.append(f"{record_path}: NO_RUNTIME_IMPACT requires a substantive rationale")
        if physical is not False:
            findings.append(f"{record_path}: NO_RUNTIME_IMPACT requires physical_requalification_required=false")

    return record, findings


def evaluate(root: Path, changed_files: list[str]) -> dict[str, Any]:
    root = root.resolve()
    policy = load_json(root / POLICY_PATH)
    changed = sorted(set(changed_files))
    changed_set = set(changed)
    structural = sorted(path for path in changed if is_structural(path, policy))
    current_host_changes = sorted(path for path in changed if is_current_host_companion(path, policy))
    impact_prefix = str(policy["impact_record_prefix"])
    impact_paths = sorted(
        path for path in changed
        if path.startswith(impact_prefix) and path.endswith(".json")
    )

    findings: list[str] = []
    records: list[dict[str, Any]] = []

    if structural:
        if not impact_paths:
            findings.append("structural FA3 changes require a current-host impact record")
        covered: set[str] = set()
        for path in impact_paths:
            record, record_findings = _validate_impact_record(
                root,
                path,
                changed_files=changed_set,
                structural_changes=set(structural),
                policy=policy,
            )
            findings.extend(record_findings)
            if record:
                records.append(record)
                declared = record.get("structural_changes", [])
                if isinstance(declared, list):
                    covered.update(x for x in declared if isinstance(x, str))
        uncovered = set(structural) - covered
        if uncovered:
            findings.append(f"structural changes missing current-host impact coverage: {sorted(uncovered)}")

    return {
        "schema": "fa3.current-host-structural-impact-gate-report.v1",
        "policy_id": policy.get("id"),
        "result": "PASS" if not findings else "FAIL",
        "fail_closed": True,
        "changed_files": changed,
        "structural_changes": structural,
        "current_host_changes": current_host_changes,
        "impact_records": impact_paths,
        "impact_record_count": len(records),
        "historical_evidence_auto_inheritance": False,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce FA3 structural-change Current Host co-development")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--output", default="reports/current-host-structural-impact-gate-report.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.changed_file:
        changed = args.changed_file
    else:
        if not args.base or not args.head:
            raise SystemExit("--base and --head are required when --changed-file is not supplied")
        changed = changed_files_from_git(root, args.base, args.head)

    report = evaluate(root, changed)
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
