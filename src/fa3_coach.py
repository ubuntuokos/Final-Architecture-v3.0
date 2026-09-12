#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

PROFILE_ID = "FA3-COACH-001"
PROVIDER_ID = "FA3-PROVIDER-COACH-LOCAL-001"
VERSION = "0.1.0"
ALLOWED_MODES = {
    "GOAL_CLARIFY",
    "PLAN",
    "COMMIT",
    "CHECKPOINT",
    "BLOCKER_REVIEW",
    "FEEDBACK",
    "ADAPT",
    "OUTCOME_REVIEW",
    "ACCOUNTABILITY",
}
COMMITMENT_MODES = {"COMMIT", "ACCOUNTABILITY"}


class CoachInputError(ValueError):
    pass


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CoachInputError(f"{field} must be a non-empty string")
    return value.strip()


def _optional_text_list(payload: dict[str, Any], field: str, limit: int = 7) -> list[str]:
    value = payload.get(field, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CoachInputError(f"{field} must be a list of strings")
    return [item.strip() for item in value if item.strip()][:limit]


def build_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a bounded Coach proposal without performing or persisting actions."""
    if not isinstance(payload, dict):
        raise CoachInputError("request must be a JSON object")

    mode = str(payload.get("mode", "PLAN")).upper()
    if mode not in ALLOWED_MODES:
        raise CoachInputError(f"unsupported mode: {mode}")

    goal = _required_text(payload, "goal")
    actions = _optional_text_list(payload, "actions")
    success_criteria = _optional_text_list(payload, "success_criteria")
    blockers = _optional_text_list(payload, "blockers")
    evidence_refs = _optional_text_list(payload, "evidence_refs")
    user_commitment = payload.get("user_commitment", False) is True
    knowledge_gap = payload.get("knowledge_gap", False) is True
    actionable_request = payload.get("actionable_request", False) is True

    if mode in COMMITMENT_MODES and not user_commitment:
        raise CoachInputError(
            f"{mode} requires explicit user_commitment=true; accountability cannot be inferred"
        )

    delegations: list[dict[str, str]] = []
    if knowledge_gap:
        delegations.append(
            {
                "kind": "MENTOR",
                "target": "FA3-MENTOR-001",
                "reason": "knowledge_or_skill_gap",
            }
        )
    if actionable_request:
        delegations.append(
            {
                "kind": "ACTION",
                "target": "FA3-AUTH-MCP-GATEWAY-001_OR_FA3-AGENT-EXEC-001",
                "reason": "typed_delegation_required",
            }
        )

    observations = []
    if blockers:
        observations.append(
            {
                "type": "USER_STATED_BLOCKERS",
                "provenance": "request.blockers",
                "value": blockers,
            }
        )
    if evidence_refs:
        observations.append(
            {
                "type": "EVIDENCE_REFERENCES",
                "provenance": "request.evidence_refs",
                "value": evidence_refs,
            }
        )

    return {
        "schema": "fa3.coach-proposal.v1",
        "profile_id": PROFILE_ID,
        "provider_id": PROVIDER_ID,
        "version": VERSION,
        "mode": mode,
        "status": "PROPOSAL_ONLY",
        "goal": {
            "owner": "USER",
            "text": goal,
            "success_criteria": success_criteria,
        },
        "plan": {
            "proposed_actions": actions,
            "user_commitment_recorded": user_commitment,
            "blockers": blockers,
        },
        "observations": observations,
        "delegations": delegations,
        "authority": {
            "direct_execution_allowed": False,
            "canonical_memory_write_allowed": False,
            "cross_workspace_persistence_allowed": False,
            "architectural_authority": False,
        },
        "boundaries": {
            "knowledge_gap_owner": "FA3-MENTOR-001",
            "action_execution": "TYPED_DELEGATION_ONLY",
            "clinical_or_therapy_authority": False,
            "identity_scoring_allowed": False,
            "coercive_accountability_allowed": False,
        },
    }


def self_check() -> None:
    proposal = build_proposal(
        {
            "mode": "PLAN",
            "goal": "Ship a verifiable FA3 change",
            "actions": ["Define acceptance criteria", "Run conformance gate"],
            "success_criteria": ["Evidence-backed result"],
            "knowledge_gap": True,
            "actionable_request": True,
        }
    )
    assert proposal["status"] == "PROPOSAL_ONLY"
    assert proposal["goal"]["owner"] == "USER"
    assert proposal["authority"]["direct_execution_allowed"] is False
    assert proposal["authority"]["architectural_authority"] is False
    assert proposal["boundaries"]["knowledge_gap_owner"] == "FA3-MENTOR-001"
    assert {item["kind"] for item in proposal["delegations"]} == {"MENTOR", "ACTION"}


def _load_input(path: str | None) -> dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.load(sys.stdin)


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Coach local reference proposal engine")
    parser.add_argument("--input", help="JSON request file; stdin is used when omitted")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_check:
            self_check()
            print("FA3 Coach self-check: PASS")
            return 0
        proposal = build_proposal(_load_input(args.input))
    except (CoachInputError, json.JSONDecodeError, OSError) as exc:
        print(f"FA3 Coach: FAIL: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(proposal, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
