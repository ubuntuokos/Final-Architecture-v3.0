#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fa3_release_baseline import BaselineError, load_active_release_baseline

MIGRATION_ID = "FA3-CAPABILITY-COUNT-DEHARDCODE-001"
GATESET_ID = "FA3-CAPABILITY-COUNT-DEHARDCODE-GATESET-001"
DECISION_PATH = "canonical/decisions/FA3-DEC-CAPABILITY-COUNT-DEHARDCODE-2026-09-13.json"

ACTIVE_SCAN_ROOTS = ("src", "scripts")
ACTIVE_SCAN_EXCLUDES = {
    "scripts/fa3_apply_capability_count_dehardcode.py",
}
FORBIDDEN_PATTERNS = (
    re.compile(r"\b(?:CAPS|CAPABILITY_COUNT|EXPECTED_CAPABILITY_COUNT|CURRENT_RELEASE_COUNT)\s*=\s*(?:143|175)\b"),
    re.compile(r"range\(\s*1\s*,\s*(?:144|176)\s*\)"),
)


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def scan_active_python(root: Path) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for rel_root in ACTIVE_SCAN_ROOTS:
        base = root / rel_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            if rel in ACTIVE_SCAN_EXCLUDES:
                continue
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern.search(line):
                        hits.append({"path": rel, "line": lineno, "text": line.strip(), "pattern": pattern.pattern})
    return hits


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []

    required = [
        "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json",
        "canonical/enforcement-policy.json",
        "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
        "canonical/FA3-GOVERNANCE-TIERING-001.json",
        "evidence/evidence-registry.json",
        DECISION_PATH,
        "src/fa3_release_baseline.py",
        "src/fa3_enforce.py",
        "src/fa3_governance_tiering_gate.py",
        "src/fa3_release_projection_gate.py",
        "src/fa3_release_evidence_scope_gate.py",
        "scripts/fa3_reconcile_release_projection.py",
    ]
    missing = [p for p in required if not (root / p).is_file()]
    if missing:
        return {
            "schema": "fa3.capability-count-dehardcode-gate-report.v1",
            "gate_set_id": GATESET_ID,
            "migration_id": MIGRATION_ID,
            "result": "FAIL",
            "blocking_findings": len(missing),
            "checks_passed": 0,
            "checks_total": 12,
            "findings": [finding("DEHC-000", f"missing {p}") for p in missing],
        }

    try:
        baseline = load_active_release_baseline(root)
    except BaselineError as exc:
        return {
            "schema": "fa3.capability-count-dehardcode-gate-report.v1",
            "gate_set_id": GATESET_ID,
            "migration_id": MIGRATION_ID,
            "result": "FAIL",
            "blocking_findings": 1,
            "checks_passed": 0,
            "checks_total": 12,
            "findings": [finding("DEHC-001", str(exc))],
        }

    policy = loadj(root / "canonical/enforcement-policy.json")
    projection = loadj(root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json")
    governance = loadj(root / "canonical/FA3-GOVERNANCE-TIERING-001.json")
    registry = loadj(root / "evidence/evidence-registry.json")
    decision = loadj(root / DECISION_PATH)
    count = baseline.capability_count
    release = baseline.release
    records = registry.get("records", [])
    expected_ids = [f"CAP-{i:03d}" for i in range(1, count + 1)]
    hardcodes = scan_active_python(root)

    module_text = {
        p: (root / p).read_text(encoding="utf-8")
        for p in [
            "src/fa3_enforce.py",
            "src/fa3_governance_tiering_gate.py",
            "src/fa3_release_projection_gate.py",
            "src/fa3_release_evidence_scope_gate.py",
            "scripts/fa3_reconcile_release_projection.py",
        ]
    }

    checks: list[tuple[str, bool, str, dict[str, Any]]] = [
        ("DEHC-001", count > 0 and baseline.document.get("baseline_semantics") == "RELEASE_SCOPED", "active release baseline invalid", {}),
        ("DEHC-002", policy.get("architecture_release") == release and policy.get("canonical_capability_count") == count, "enforcement policy mirror differs from active release baseline", {}),
        ("DEHC-003", projection.get("base_release") == release and projection.get("invariants", {}).get("canonical_capability_count") == count, "release projection mirror differs from active release baseline", {}),
        ("DEHC-004", registry.get("architecture_release") == release and registry.get("canonical_capability_count") == count and registry.get("record_count") == count and len(records) == count and [r.get("subject_id") for r in records] == expected_ids, "Evidence Registry cardinality differs from active release baseline", {}),
        ("DEHC-005", governance.get("canonical_capability_count_after") == count and isinstance(governance.get("canonical_capability_count_before"), int) and governance.get("capability_delta") == count - governance.get("canonical_capability_count_before"), "governance projection baseline mirror drift", {}),
        ("DEHC-006", not hardcodes, "active executable Python still contains forbidden capability-count hardcodes", {"hardcodes": hardcodes[:100]}),
        ("DEHC-007", all("fa3_release_baseline" in text and "load_active_release_baseline" in text for text in module_text.values()), "one or more central executable paths do not consume the shared release baseline loader", {}),
        ("DEHC-008", "range(1,CAPS+1)" in module_text["src/fa3_enforce.py"].replace(" ", ""), "global enforcement catalog range is not derived from the active baseline", {}),
        ("DEHC-009", '"capability_count_after": capability_count' in module_text["scripts/fa3_reconcile_release_projection.py"], "release reconciler does not write the baseline-derived capability count", {}),
        ("DEHC-010", decision.get("id") == "FA3-DEC-CAPABILITY-COUNT-DEHARDCODE-2026-09-13" and decision.get("status") == "CANONICAL_CLOSED" and decision.get("authority_delta") == 0 and decision.get("capability_delta") == 0, "migration decision missing or gained authority/capability delta", {}),
        ("DEHC-011", decision.get("capability_count_at_migration") in [r.get("capability_count") for r in baseline.document.get("release_baselines", [])] and decision.get("semantic_effect") == "NO_CAPABILITY_COUNT_CHANGE", "historical de-hardcode migration decision is not represented by a declared release baseline", {}),
        ("DEHC-012", policy.get("runtime_promotion_requires_current_host_evidence") is True and policy.get("document_only_promotion_forbidden") is True, "promotion/current-host fail-closed boundary weakened", {}),
    ]

    for code, ok, message, extra in checks:
        if not ok:
            findings.append(finding(code, message, **extra))

    return {
        "schema": "fa3.capability-count-dehardcode-gate-report.v1",
        "gate_set_id": GATESET_ID,
        "migration_id": MIGRATION_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "checks_passed": sum(1 for _, ok, _, _ in checks if ok),
        "checks_total": len(checks),
        "active_release": release,
        "active_release_capability_count": count,
        "authority_delta": decision.get("authority_delta"),
        "capability_delta": decision.get("capability_delta"),
        "active_hardcode_hits": len(hardcodes),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FA3 capability-count de-hardcode migration")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default="reports/capability-count-dehardcode-gate-report.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    result = gate(root)
    report = root / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
