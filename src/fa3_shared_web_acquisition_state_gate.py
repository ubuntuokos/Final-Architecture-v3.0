#!/usr/bin/env python3
"""Fail-closed static gate for shared web acquisition state hardening."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import active_capability_count

GATE_ID = "FA3-SHARED-WEB-ACQUISITION-STATE-GATESET-001"
PROFILE_ID = "FA3-SHARED-WEB-ACQUISITION-STATE-001"
CONTRACT_ID = "FA3-SHARED-WEB-ACQUISITION-STATE-CONTRACTS-001"
PROFILE = "canonical/profiles/FA3-SHARED-WEB-ACQUISITION-STATE-001.json"
CONTRACTS = "canonical/contracts/FA3-SHARED-WEB-ACQUISITION-STATE-CONTRACTS-001.json"
ASSESSMENT = "canonical/assessments/FA3-APIFY-WEB-ACQUISITION-HARDENING-REUSE-ASSESSMENT-001.json"
REFRESH = "research/apify-ecosystem-pattern-refresh-2026-10-02.json"
IMPACT = "canonical/reconciliations/FA3-APIFY-WEB-ACQUISITION-CONSUMER-IMPACT-2026-10-02.json"
HOST_IMPACT = "canonical/FA3-SHARED-WEB-ACQUISITION-STATE-CURRENT-HOST-IMPACT-001.json"
PLAN = "docs/FA3-APIFY-WEB-ACQUISITION-HARDENING-PLAN-2026-10-02.md"
APPROVAL = "canonical/decisions/FA3-DEC-APIFY-WEB-ACQUISITION-HARDENING-APPROVAL-2026-10-02.json"
SOURCE = "src/fa3_shared_web_acquisition_state.py"
DECISION_ASSESSMENT = "canonical/assessments/FA3-SHARED-WEB-ACQUISITION-STATE-DECISION-ASSESSMENT-2026-10-02.json"

REQUIRED = [
    PROFILE,
    CONTRACTS,
    ASSESSMENT,
    REFRESH,
    IMPACT,
    HOST_IMPACT,
    PLAN,
    APPROVAL,
    SOURCE,
    DECISION_ASSESSMENT,
    "canonical/decisions/FA3-DEC-SHARED-WEB-ACQUISITION-STATE-2026-10-02.json",
    "canonical/intents/FA3-APIFY-WEB-ACQUISITION-HARDENING-APPLICATION-INTENT-001.json",
    "canonical/FA3-GATE-SHARED-WEB-ACQUISITION-STATE-001.json",
    "canonical/shared-web-acquisition-state-enforcement.json",
    "tests/test_shared_web_acquisition_state.py",
    ".github/workflows/fa3-shared-web-acquisition-state.yml",
]


def loadj(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{rel}")
    return value


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []

    for rel in REQUIRED:
        if not (root / rel).is_file():
            findings.append({"code": "WAS-001", "message": "required artifact missing", "path": rel})
    if findings:
        return {
            "schema": "fa3.shared-web-acquisition-state-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "findings": findings,
            "current_host_runtime_promotion_claim": False,
        }

    try:
        baseline_count = active_capability_count(root)
        profile = loadj(root, PROFILE)
        contracts = loadj(root, CONTRACTS)
        assessment = loadj(root, ASSESSMENT)
        refresh = loadj(root, REFRESH)
        impact = loadj(root, IMPACT)
        host = loadj(root, HOST_IMPACT)
        approval = loadj(root, APPROVAL)
        decision_assessment = loadj(root, DECISION_ASSESSMENT)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        findings.append({"code": "WAS-002", "message": str(exc)})
        baseline_count = None
        profile = contracts = assessment = refresh = impact = host = approval = decision_assessment = {}

    if (
        profile.get("id") != PROFILE_ID
        or profile.get("parent_profile") != "FA3-WEB-AI-001"
        or profile.get("capability_count") != baseline_count
        or profile.get("new_capability") is not False
        or profile.get("new_architectural_authority") is not False
    ):
        findings.append({"code": "WAS-003", "message": "profile capability/authority/parent drift"})

    required_invariants = {
        "CLAIMS_ARE_LEASE_BOUND_AND_EXPIRE_FAIL_CLOSED",
        "EXPIRED_CLAIMS_REQUEUE_WITH_RECOVERY_RECEIPT",
        "BROWSER_MUTATION_AUTHORITY_REMAINS_BROWSER_ACTION_RUNTIME",
        "LOAD_FEEDBACK_IS_ADVISORY_ONLY_HRB_REMAINS_RESOURCE_AUTHORITY",
        "DONOR_ADOPTION_REQUIRES_REGISTERED_SOURCE_AND_CANONICAL_USAGE_EDGE",
    }
    if not required_invariants.issubset(set(profile.get("invariants", []))):
        findings.append({"code": "WAS-004", "message": "mandatory profile invariants missing"})

    if (
        contracts.get("id") != CONTRACT_ID
        or contracts.get("capability_count") != baseline_count
        or contracts.get("profile_id") != PROFILE_ID
    ):
        findings.append({"code": "WAS-005", "message": "contract identity or baseline drift"})
    if (
        decision_assessment.get("assessment") != "NOT_APPLICABLE"
        or PROFILE_ID not in decision_assessment.get("covered_ids", [])
        or decision_assessment.get("project_radar_checked") is not True
    ):
        findings.append({"code": "WAS-005A", "message": "Decision Fabric applicability assessment missing or drifted"})

    donor_boundary = contracts.get("donor_boundary", {})
    if (
        donor_boundary.get("child_repository_adoption") is not False
        or donor_boundary.get("child_usage_edge_created") is not False
        or donor_boundary.get("usage_edge_required_for_future_material_adoption") is not True
    ):
        findings.append({"code": "WAS-006", "message": "donor adoption boundary weakened"})

    snapshot = assessment.get("donor_planning_snapshot", {})
    if (
        assessment.get("donor_review") != "REVIEWED_MATCH"
        or assessment.get("adopted_donors") != []
        or assessment.get("donor_adoption_authorized") is not False
        or assessment.get("code_import_authorized") is not False
        or snapshot.get("published_main_commit") != "eaf6ea69897db229e6e6973bb57f2182f153ec3c"
        or snapshot.get("donor_registry_blob_sha") != "7059b3a8c816400f4dee221744be2d13038c48f8"
        or snapshot.get("donor_registry_sha256") != "3e97b1a1ee56dd81c224c3601cb2ebc088e92af0c56d7008bf84b6c45e5cbbd0"
        or snapshot.get("donor_registry_entry_count") != 1339
    ):
        findings.append({"code": "WAS-007", "message": "published donor planning snapshot/adoption boundary drift"})

    if (
        refresh.get("child_repository_registration") is not False
        or refresh.get("material_adoption_authorized") is not False
        or refresh.get("usage_edges_created") is not False
    ):
        findings.append({"code": "WAS-008", "message": "analysis-only Apify boundary drift"})

    if (
        impact.get("shared_first") is not True
        or impact.get("direct_consumer_mutation") is not False
        or impact.get("capability_delta") != 0
        or impact.get("authority_delta") != 0
    ):
        findings.append({"code": "WAS-009", "message": "shared-first consumer impact drift"})

    if (
        host.get("runtime_service_created") is not False
        or host.get("external_runtime_installed") is not False
        or host.get("hardware_mutation") is not False
        or host.get("physical_current_host_pass_claim") is not False
        or host.get("runtime_promotion_claim") is not False
    ):
        findings.append({"code": "WAS-010", "message": "Current Host/runtime boundary drift"})

    try:
        plan_raw = (root / PLAN).read_bytes()
        plan_sha = hashlib.sha256(plan_raw).hexdigest()
    except OSError:
        plan_sha = None
    if (
        approval.get("status") != "APPROVED"
        or approval.get("explicit_user_approval") is not True
        or approval.get("approved_plan_path") != PLAN
        or approval.get("approved_plan_sha256") != plan_sha
        or approval.get("donor_registry_mutation_authorized") is not False
        or approval.get("child_donor_adoption_authorized") is not False
    ):
        findings.append({"code": "WAS-011", "message": "immutable approved plan proof invalid"})

    try:
        source = (root / SOURCE).read_text(encoding="utf-8")
    except OSError:
        source = ""
    for literal in (
        '"advisory_only": True',
        '"may_change_concurrency": False',
        '"resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001"',
        "DEDUPE_KEY_IDENTITY_CONFLICT",
        "LEASE_EXPIRED_REQUEUED",
        "ROBOTS_POLICY_DENIED",
    ):
        if literal not in source:
            findings.append({"code": "WAS-012", "message": "reference core invariant missing", "literal": literal})

    return {
        "schema": "fa3.shared-web-acquisition-state-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "capability_baseline": baseline_count,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "donor_adoption": False,
        "usage_edge_created": False,
        "runtime_promotion_claim": False,
        "current_host_runtime_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
