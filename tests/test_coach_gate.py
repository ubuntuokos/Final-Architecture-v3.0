from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_coach import CoachInputError, build_proposal  # noqa: E402
from fa3_coach_gate import validate  # noqa: E402


def test_coach_gate_passes_reference_materialization() -> None:
    assert validate() == []


def test_coach_is_proposal_only_and_user_goal_owned() -> None:
    proposal = build_proposal(
        {
            "mode": "PLAN",
            "goal": "Complete a verifiable milestone",
            "actions": ["Define evidence", "Execute through authorized boundary"],
        }
    )
    assert proposal["status"] == "PROPOSAL_ONLY"
    assert proposal["goal"]["owner"] == "USER"
    assert proposal["authority"]["direct_execution_allowed"] is False
    assert proposal["authority"]["architectural_authority"] is False
    assert proposal["authority"]["canonical_memory_write_allowed"] is False
    assert proposal["authority"]["cross_workspace_persistence_allowed"] is False


def test_knowledge_gap_and_action_request_create_typed_delegations() -> None:
    proposal = build_proposal(
        {
            "mode": "BLOCKER_REVIEW",
            "goal": "Resolve a technical blocker",
            "knowledge_gap": True,
            "actionable_request": True,
        }
    )
    delegations = {item["kind"]: item["target"] for item in proposal["delegations"]}
    assert delegations["MENTOR"] == "FA3-MENTOR-001"
    assert "FA3-AUTH-MCP-GATEWAY-001" in delegations["ACTION"]


def test_accountability_requires_explicit_commitment() -> None:
    with pytest.raises(CoachInputError):
        build_proposal({"mode": "ACCOUNTABILITY", "goal": "Finish task"})

    proposal = build_proposal(
        {
            "mode": "ACCOUNTABILITY",
            "goal": "Finish task",
            "user_commitment": True,
        }
    )
    assert proposal["plan"]["user_commitment_recorded"] is True


def test_invalid_or_empty_goal_fails_closed() -> None:
    with pytest.raises(CoachInputError):
        build_proposal({"mode": "PLAN", "goal": ""})
