#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"object required: {path}")
    return data


def assessments(root: Path) -> list[dict[str, Any]]:
    out = []
    directory = root / "canonical" / "assessments"
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.json")):
        data = load(path)
        if data.get("schema") == "fa3.decision-fabric-assessment.v1":
            data["_path"] = path.relative_to(root).as_posix()
            out.append(data)
    return out


def validate_assessment(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if row.get("assessment") not in {"REQUIRED", "RECOMMENDED", "OPTIONAL", "NOT_APPLICABLE", "PROHIBITED"}:
        errors.append("invalid assessment")
    if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
        errors.append("rationale required")
    if row.get("project_radar_checked") is not True:
        errors.append("Project Radar review required")
    hardware = row.get("hardware_audit", {})
    if hardware.get("vendor_neutral") is not True or hardware.get("cpu_only_viable") is not True or hardware.get("global_accelerator_requirement") is not False:
        errors.append("hardware-audit neutrality/cpu-only invariant failed")
    security = row.get("security_boundary", {})
    for field in ("may_grant_permission", "may_expand_candidate_set", "may_create_agent", "may_admit_model", "may_admit_provider"):
        if security.get(field) is not False:
            errors.append(f"security boundary must deny {field}")
    if row.get("assessment") in {"REQUIRED", "RECOMMENDED", "OPTIONAL"} and not isinstance(row.get("decision_points"), list):
        errors.append("decision_points list required")
    return errors


def added_ids(root: Path, base_ref: str) -> dict[str, str]:
    proc = subprocess.run(
        ["git", "diff", "--name-status", f"{base_ref}...HEAD", "--", "canonical/profiles", "canonical/providers"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 2 or parts[0] != "A" or not parts[1].endswith(".json"):
            continue
        path = root / parts[1]
        try:
            data = load(path)
        except Exception:
            continue
        item_id = data.get("id")
        if isinstance(item_id, str) and item_id:
            out[item_id] = parts[1]
    return out


def gate(root: Path, base_ref: str | None = None) -> dict[str, Any]:
    rows = assessments(root)
    findings: list[dict[str, Any]] = []
    covered: set[str] = set()
    for row in rows:
        errors = validate_assessment(row)
        if errors:
            findings.append({"code": "ADOPTION-INVALID", "path": row.get("_path"), "errors": errors})
        project_id = row.get("project_id")
        if isinstance(project_id, str):
            covered.add(project_id)
        for item in row.get("covered_ids", []):
            if isinstance(item, str):
                covered.add(item)

    if base_ref:
        for item_id, path in added_ids(root, base_ref).items():
            if item_id not in covered:
                findings.append({
                    "code": "ADOPTION-MISSING",
                    "id": item_id,
                    "path": path,
                    "message": "new profile/provider requires Decision Fabric applicability assessment",
                })

    return {
        "schema": "fa3.decision-fabric-adoption-gate-report.v1",
        "gate_id": "FA3-GATE-JEV-ADOPTION-001",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "assessment_count": len(rows),
        "covered_id_count": len(covered),
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--base-ref")
    parser.add_argument("--report", default="reports/decision-fabric-adoption-gate-report.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = gate(root, args.base_ref)
    out = root / args.report
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
