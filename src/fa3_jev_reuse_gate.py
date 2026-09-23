#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PREFERRED = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD"}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def gate(root: Path) -> dict[str, Any]:
    path = root / "canonical/third-party/FA3-JEV-CODE-REUSE-001.json"
    findings: list[dict[str, Any]] = []
    try:
        data = load(path)
    except Exception as exc:
        return {
            "schema": "fa3.jev-code-reuse-gate-report.v1",
            "result": "FAIL",
            "findings": [{"code": "JEV-REUSE-000", "message": "reuse registry unreadable", "error": repr(exc)}],
        }

    policy = data.get("policy", {})
    required_policy = {
        "source_commit_pin": "REQUIRED",
        "source_paths": "REQUIRED",
        "license_identifier": "REQUIRED",
        "spdx_attribution": "REQUIRED",
        "local_modifications": "REQUIRED",
        "security_review": "REQUIRED",
        "distribution_impact_review": "REQUIRED",
        "foreign_authority_import": "DENY",
        "unknown_license_source_copy": "DENY",
        "automatic_external_install": "DENY",
    }
    for key, expected in required_policy.items():
        if policy.get(key) != expected:
            findings.append({"code": "JEV-REUSE-001", "field": key, "expected": expected, "actual": policy.get(key)})

    seen: set[tuple[str, str]] = set()
    for index, entry in enumerate(data.get("entries", [])):
        if not isinstance(entry, dict):
            findings.append({"code": "JEV-REUSE-002", "index": index, "message": "entry must be object"})
            continue
        repo = entry.get("source_repository")
        commit = entry.get("source_commit")
        license_id = entry.get("license")
        paths = entry.get("source_paths")
        local_paths = entry.get("local_paths")
        if not isinstance(repo, str) or not repo:
            findings.append({"code": "JEV-REUSE-003", "index": index, "message": "source_repository required"})
        if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
            findings.append({"code": "JEV-REUSE-004", "index": index, "message": "immutable source commit required"})
        if not isinstance(license_id, str) or not license_id:
            findings.append({"code": "JEV-REUSE-005", "index": index, "message": "license required"})
        if not isinstance(paths, list) or not paths or any(not isinstance(x, str) or not x for x in paths):
            findings.append({"code": "JEV-REUSE-006", "index": index, "message": "source_paths required"})
        if not isinstance(local_paths, list) or not local_paths or any(not isinstance(x, str) or not x for x in local_paths):
            findings.append({"code": "JEV-REUSE-007", "index": index, "message": "local_paths required"})
        if entry.get("security_review") != "PASS" or entry.get("distribution_impact_review") != "PASS":
            findings.append({"code": "JEV-REUSE-008", "index": index, "message": "security/distribution review must PASS"})
        if not isinstance(entry.get("spdx_attribution"), str) or not entry.get("spdx_attribution"):
            findings.append({"code": "JEV-REUSE-009", "index": index, "message": "SPDX attribution required"})
        if not isinstance(entry.get("local_modifications"), list):
            findings.append({"code": "JEV-REUSE-010", "index": index, "message": "local_modifications list required"})
        if entry.get("imports_architectural_authority") is not False:
            findings.append({"code": "JEV-REUSE-011", "index": index, "message": "foreign authority import forbidden"})
        key = (str(repo), str(commit))
        if key in seen:
            findings.append({"code": "JEV-REUSE-012", "index": index, "message": "duplicate source pin"})
        seen.add(key)

    return {
        "schema": "fa3.jev-code-reuse-gate-report.v1",
        "gate_id": "FA3-GATE-JEV-CODE-REUSE-001",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "entry_count": len(data.get("entries", [])),
        "preferred_permissive_licenses": sorted(PREFERRED),
        "global_promotion_claim": False,
    }


def notices(root: Path) -> str:
    data = load(root / "canonical/third-party/FA3-JEV-CODE-REUSE-001.json")
    chunks = ["# FA3 Jev-derived third-party notices", ""]
    entries = data.get("entries", [])
    if not entries:
        chunks += ["No third-party runtime source is currently copied under this registry.", ""]
    for entry in entries:
        chunks += [
            f"## {entry['source_repository']} @ {entry['source_commit']}",
            f"License: {entry['license']}",
            f"SPDX: {entry['spdx_attribution']}",
            "Source paths: " + ", ".join(entry["source_paths"]),
            "Local paths: " + ", ".join(entry["local_paths"]),
            "Modifications: " + ("; ".join(entry["local_modifications"]) or "none"),
            "",
        ]
    return "\n".join(chunks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report", default="reports/jev-code-reuse-gate-report.json")
    parser.add_argument("--notices", default="reports/THIRD_PARTY_NOTICES_JEV.md")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = gate(root)
    report_path = root / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    notice_path = root / args.notices
    notice_path.parent.mkdir(parents=True, exist_ok=True)
    notice_path.write_text(notices(root), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
