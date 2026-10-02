#!/usr/bin/env python3
"""P0 fail-closed static gate for FA3 Change-History Intelligence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROFILE = "canonical/profiles/FA3-CHANGE-HISTORY-INTELLIGENCE-001.json"
CONTRACT = "canonical/contracts/FA3-CHANGE-HISTORY-INTELLIGENCE-CONTRACTS-001.json"
ASSESSMENT = "canonical/assessments/FA3-CHANGE-HISTORY-INTELLIGENCE-REUSE-ASSESSMENT-001.json"
DECISION_ASSESSMENT = "canonical/assessments/FA3-CHANGE-HISTORY-INTELLIGENCE-DECISION-ASSESSMENT-001.json"
DECISION = "canonical/decisions/FA3-DEC-CHANGE-HISTORY-INTELLIGENCE-2026-10-02.json"
HOST = "canonical/FA3-CHANGE-HISTORY-CURRENT-HOST-IMPACT-001.json"
ENFORCEMENT = "canonical/change-history-intelligence-enforcement.json"
GATE_RECORD = "canonical/FA3-GATE-CHANGE-HISTORY-INTELLIGENCE-001.json"
LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
REGISTRY = "canonical/FA3-GATE-REGISTRY-001.json"
POLICY = "canonical/enforcement-policy.json"
GATESET = "FA3-CHANGE-HISTORY-GATESET-001"
DONORS = {
    "FA3-DONOR-SLSA-BUILD-PROVENANCE-001",
    "FA3-DONOR-IN-TOTO-SPECIFICATIONS-001",
    "FA3-DONOR-OPENTELEMETRY-EVENT-CONVENTIONS-001",
    "FA3-DONOR-OPENLINEAGE-LINEAGE-FACET-001",
}


def load(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {rel}")
    return value


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, str]] = []

    def require(ok: bool, code: str, message: str) -> None:
        if not ok:
            findings.append({"code": code, "severity": "P0", "message": message})

    required_paths = [PROFILE, CONTRACT, ASSESSMENT, DECISION_ASSESSMENT, DECISION,
                      HOST, ENFORCEMENT, GATE_RECORD, LINKS, REGISTRY, POLICY]
    missing = [rel for rel in required_paths if not (root / rel).is_file()]
    if missing:
        return {
            "schema": "fa3.change-history-gate-report.v1",
            "gate_id": GATESET, "result": "FAIL",
            "findings": [{"code": "CHIF-001", "severity": "P0",
                          "message": "required materialization files missing: " + ",".join(missing)}],
        }

    profile = load(root, PROFILE)
    contract = load(root, CONTRACT)
    assessment = load(root, ASSESSMENT)
    decision = load(root, DECISION)
    host = load(root, HOST)
    enforcement = load(root, ENFORCEMENT)
    links = load(root, LINKS)
    registry = load(root, REGISTRY)
    policy = load(root, POLICY)

    require(profile.get("id") == "FA3-CHANGE-HISTORY-INTELLIGENCE-001", "CHIF-002", "profile identity drift")
    require(profile.get("parent_profile_id") == "FA3-JOURNAL-001", "CHIF-003", "Journal must remain parent history authority")
    require(profile.get("new_capability") is False and profile.get("new_architectural_authority") is False,
            "CHIF-004", "CHIF may add no capability or authority")
    require(profile.get("capability_count") == 175 and contract.get("capability_count") == 175,
            "CHIF-005", "capability baseline must remain 175")
    storage = profile.get("storage", {})
    require(storage.get("source_of_truth") is False and storage.get("rebuildable") is True
            and storage.get("source_mutation_forbidden") is True,
            "CHIF-006", "derived index boundary is incomplete")
    require(set(profile.get("truth_classes", [])) ==
            {"FACT", "DERIVED_FACT", "INFERENCE", "USER_NOTE", "AI_INFERENCE"},
            "CHIF-007", "truth-class separation drift")
    require(contract.get("contracts", {}).get("lineage_pattern", {}).get("all_to_all_inference_forbidden") is True,
            "CHIF-008", "implicit cartesian lineage must be forbidden")
    ai = contract.get("contracts", {}).get("ai_boundary", {})
    require(ai.get("router") == "FA3-AUTH-MODEL-ROUTER-001"
            and ai.get("direct_provider_execution") is False
            and ai.get("may_create_fact") is False,
            "CHIF-009", "AI boundary must preserve Model Router and non-authority")
    require(assessment.get("donor_planning_snapshot", {}).get("donor_registry_entry_count") == 1344,
            "CHIF-010", "reuse assessment is not bound to the published 1344-donor snapshot")
    selected = set(assessment.get("selected_existing_donor_ids", []))
    require(selected == DONORS and assessment.get("donor_adoption_authorized") is True,
            "CHIF-011", "approved donor pattern set drift")
    active_edges = {
        row.get("donor_id") for row in links.get("donor_usage_records", [])
        if isinstance(row, dict) and row.get("status") != "REMOVED"
    }
    require(DONORS <= active_edges, "CHIF-012", "canonical donor usage edges are incomplete")
    require(enforcement.get("mandatory_rule_count") == len(enforcement.get("rules", [])) == 25,
            "CHIF-013", "P0 enforcement rule count drift")
    require(GATESET in registry.get("mandatory_reference_gates", [])
            and registry.get("mandatory_reference_gates") == policy.get("mandatory_reference_gates"),
            "CHIF-014", "global gate registry/policy binding missing or divergent")
    require(GATESET in policy.get("mandatory_reference_gates", []),
            "CHIF-015", "CHIF gate is not permanent mandatory enforcement")
    require(host.get("physical_pass_claimed") is False
            and host.get("result") == "PENDING_PHYSICAL_CURRENT_HOST_REQUALIFICATION",
            "CHIF-016", "static materialization may not claim Current Host PASS")
    require(decision.get("invariants", {}).get("current_host_pass_claimed") is False
            and decision.get("invariants", {}).get("global_promotion_claim") is False,
            "CHIF-017", "decision overclaims runtime/current-host promotion")

    report = {
        "schema": "fa3.change-history-gate-report.v1",
        "gate_id": GATESET,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "capability_count": 175,
        "capability_delta": 0,
        "authority_delta": 0,
        "current_host_runtime_claim": False,
        "donor_usage_edges_verified": sorted(DONORS),
    }
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "change-history-intelligence-gate-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
