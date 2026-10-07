#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

POLICY_REL = "canonical/CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-POLICY-001.json"
REGISTRY_REL = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required: " + str(path))
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_record(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, str]] = []
    policy = _load(root / POLICY_REL)
    registry_path = root / REGISTRY_REL
    registry = _load(registry_path)

    def fail(code: str, message: str) -> None:
        findings.append({"code": code, "message": message})

    if record.get("schema") != "cfa3.retroactive-redesign-record.v1":
        fail("RR-001", "record schema mismatch")
    if record.get("capability_baseline") != 175 or record.get("capability_delta") != 0:
        fail("RR-002", "capability baseline/delta mismatch")
    if record.get("architectural_authority_delta") != 0:
        fail("RR-003", "architectural authority delta must remain zero")

    component = record.get("component")
    if not isinstance(component, dict):
        fail("RR-004", "component object missing")
        component = {}
    evidence = component.get("trigger_evidence_refs")
    if not isinstance(evidence, list) or not evidence:
        fail("RR-005", "trigger evidence required")

    designed_before = component.get("designed_before_mandatory_donor_policy")
    if designed_before is not True:
        if (
            designed_before is False
            and component.get("donor_policy_applicable_at_original_design") is True
            and isinstance(evidence, list)
            and evidence
        ):
            return {
                "schema": "cfa3.retroactive-redesign-compliance-report.v1",
                "result": "PASS",
                "disposition": "NOT_APPLICABLE_NORMAL_DONOR_RULES",
                "findings": [],
                "current_host_runtime_promotion_claim": False,
            }
        fail("RR-006", "legacy pre-donor trigger not proven")

    phase = record.get("phase")
    lifecycle = policy.get("lifecycle", [])
    if phase not in lifecycle:
        fail("RR-007", "invalid lifecycle phase")
    final = phase == policy.get("finalization_gate", {}).get("final_state")

    if record.get("legacy_source_discovery_complete") is not True:
        fail("RR-008", "legacy source discovery incomplete")

    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        fail("RR-009", "canonical donor registry entries invalid")
        entries = []
    by_key = {
        row.get("source", {}).get("normalized_key"): row
        for row in entries
        if isinstance(row, dict) and isinstance(row.get("source"), dict)
    }
    allowed_states = set(policy.get("legacy_source_policy", {}).get("canonical_acceptable_states", []))
    for index, source in enumerate(record.get("legacy_sources", [])):
        if not isinstance(source, dict):
            fail("RR-010", f"legacy source {index} invalid")
            continue
        key = source.get("normalized_key")
        if not isinstance(key, str) or not key:
            fail("RR-011", f"legacy source {index} normalized key missing")
            continue
        if not isinstance(source.get("origin_refs"), list) or not source.get("origin_refs"):
            fail("RR-012", f"legacy source {key} provenance missing")
        donor = by_key.get(key)
        canonical = isinstance(donor, dict) and donor.get("status") in allowed_states
        if not canonical:
            if final:
                fail("RR-013", f"legacy source not canonical at finalization: {key}")
            elif source.get("temporary_planning_use") is not True:
                fail("RR-014", f"unregistered legacy source lacks temporary planning-use declaration: {key}")
        elif source.get("canonical_donor_id") not in (None, donor.get("donor_id")):
            fail("RR-015", f"canonical donor id mismatch: {key}")

    baseline = record.get("current_rule_baseline")
    if not isinstance(baseline, dict):
        fail("RR-016", "current rule baseline missing")
        baseline = {}
    if baseline.get("captured_from_canonical_main") is not True:
        fail("RR-017", "rule baseline must come from canonical main")
    main_sha = baseline.get("captured_main_sha")
    if not isinstance(main_sha, str) or len(main_sha) != 40 or any(ch not in "0123456789abcdef" for ch in main_sha):
        fail("RR-018", "captured main SHA invalid")
    refs = baseline.get("mandatory_rule_refs")
    if not isinstance(refs, list) or not refs:
        fail("RR-019", "mandatory rule references missing")

    required_categories = set(policy.get("current_rule_delta_review", {}).get("required_categories", []))
    deltas = record.get("rule_delta")
    if not isinstance(deltas, list):
        fail("RR-020", "rule delta list missing")
        deltas = []
    seen: set[str] = set()
    for item in deltas:
        if not isinstance(item, dict):
            fail("RR-021", "invalid rule delta entry")
            continue
        category = item.get("category")
        status = item.get("status")
        if category in seen:
            fail("RR-022", "duplicate rule delta category: " + str(category))
        seen.add(category)
        if category not in required_categories:
            fail("RR-023", "unknown rule delta category: " + str(category))
        if status not in policy.get("current_rule_delta_review", {}).get("allowed_review_statuses", []):
            fail("RR-024", "invalid rule delta status: " + str(status))
        if status == "NOT_APPLICABLE" and not str(item.get("rationale", "")).strip():
            fail("RR-025", "NOT_APPLICABLE requires rationale: " + str(category))
        if final and status not in policy.get("current_rule_delta_review", {}).get("final_resolved_statuses", []):
            fail("RR-026", "unresolved rule delta at finalization: " + str(category))
    missing_categories = sorted(required_categories - seen)
    if missing_categories:
        fail("RR-027", "missing rule delta categories: " + ",".join(missing_categories))

    checks = record.get("finalization_checks")
    if not isinstance(checks, dict):
        fail("RR-028", "finalization checks missing")
        checks = {}
    if final:
        for name in policy.get("finalization_gate", {}).get("required_checks", []):
            if checks.get(name) != "PASS":
                fail("RR-029", "finalization check not PASS: " + name)
        digest = record.get("donor_registry_sha256")
        if digest != _sha256(registry_path):
            fail("RR-030", "donor registry digest mismatch")
    return {
        "schema": "cfa3.retroactive-redesign-compliance-report.v1",
        "result": "PASS" if not findings else "FAIL",
        "disposition": "REDESIGN_FINAL" if final and not findings else "REDESIGN_ALLOWED" if not final and not findings else "BLOCKED",
        "findings": findings,
        "current_host_runtime_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one CFA3 retroactive redesign compliance record.")
    parser.add_argument("record", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    record = _load(args.record)
    report = evaluate_record(args.root, record)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
