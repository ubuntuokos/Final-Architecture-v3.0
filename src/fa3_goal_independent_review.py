"""Non-authoritative, checker-separated evidence review for existing FA3 goals.

This is a read-only projection for the existing Control Center; the existing
canonical Evidence/Gate is the only authority that can close a goal.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from fa3_goal_execution import assess_evidence, digest, validate_goal

EVIDENCE_AUTHORITY = "FA3-AUTH-OBS-EVIDENCE-001"

class IndependentReviewDenied(ValueError):
    pass

def review_goal_evidence(
    goal_value: dict[str, Any], observations: list[dict[str, Any]], *,
    verify_canonical_evidence: Callable[[dict[str, Any]], dict[str, Any]],
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Require existing external evidence checks; never infer final VERIFIED.

    The injected verifier must be a trusted binding to existing Evidence/Gate,
    not a self-reported model result or a caller-controlled 'status' field.
    """
    goal = validate_goal(goal_value)
    if not callable(verify_canonical_evidence):
        raise IndependentReviewDenied("existing canonical verifier required")
    preliminary = assess_evidence(goal, observations, plan=plan)
    by_id = {row["criterion_id"]: row for row in observations}
    by_criterion = {c["criterion_id"]: c for c in goal["acceptance_criteria"]}
    participants = set(goal["execution_policy"]["authorized_ai_participants"])
    results = []
    for entry in preliminary["criteria"]:
        cid = entry["criterion_id"]
        if entry["status"] != "READY_FOR_CANONICAL_VERIFICATION":
            results.append({**entry, "independent_confirmation": False})
            continue
        obs = by_id[cid]
        criterion = by_criterion[cid]
        expected = criterion["verification"]
        query = {
            "goal_id": goal["goal_id"], "goal_revision": goal["revision"],
            "goal_digest": digest(goal), "criterion_id": cid,
            "verifier_ref": expected["verifier_ref"],
            "expected_independent_verifier_ref": expected.get("independent_verifier_ref"),
            "artifact_digest": obs["artifact_digest"],
            "evidence_ref": obs["evidence_ref"],
            "required_evidence_kinds": expected["evidence_kinds"],
            "human_approval_ref": obs.get("human_approval_ref"),
        }
        try:
            answer = verify_canonical_evidence(query)
        except Exception as exc:
            raise IndependentReviewDenied("canonical evidence verifier unavailable") from exc
        if not isinstance(answer, dict):
            raise IndependentReviewDenied("canonical verifier returned invalid response")
        required = {
            "authority": EVIDENCE_AUTHORITY,
            "goal_digest": digest(goal),
            "criterion_id": cid,
            "artifact_digest": obs["artifact_digest"],
            "evidence_ref": obs["evidence_ref"],
            "verifier_ref": expected["verifier_ref"],
            "status": "REFERENCE_AUTHENTICATED",
        }
        if any(answer.get(key) != value for key, value in required.items()):
            results.append({"criterion_id": cid, "status": "BLOCKED",
                            "reason": "CANONICAL_EVIDENCE_AUTHENTICATION_MISMATCH",
                            "independent_confirmation": False})
            continue
        checker = answer.get("independent_checker_ref")
        if not isinstance(checker, str) or not checker or checker in participants:
            results.append({"criterion_id": cid, "status": "BLOCKED",
                            "reason": "INDEPENDENT_CHECKER_REQUIRED",
                            "independent_confirmation": False})
            continue
        if (expected["kind"] == "SEMANTIC_ADVISORY_WITH_INDEPENDENT_CHECK" and
                checker != expected["independent_verifier_ref"]):
            results.append({"criterion_id": cid, "status": "BLOCKED",
                            "reason": "INDEPENDENT_VERIFIER_MISMATCH",
                            "independent_confirmation": False})
            continue
        if (expected["kind"] == "HUMAN" and
                (answer.get("human_approval_ref") != obs.get("human_approval_ref") or
                 answer.get("human_approval_status") != "APPROVED")):
            results.append({"criterion_id": cid, "status": "BLOCKED",
                            "reason": "HUMAN_APPROVAL_NOT_AUTHENTICATED",
                            "independent_confirmation": False})
            continue
        results.append({
            "criterion_id": cid,
            "status": "REFERENCE_AUTHENTICATED_PENDING_CANONICAL_CLOSURE",
            "reason": "EXTERNAL_EVIDENCE_REFERENCE_CHECKED",
            "independent_confirmation": True,
        })
    all_checked = all(r["independent_confirmation"] for r in results)
    return {
        "schema": "fa3.goal-independent-review-projection.v1",
        "goal_id": goal["goal_id"],
        "goal_revision": goal["revision"], "goal_digest": digest(goal),
        "criteria": results,
        "status": ("ALL_REFERENCES_CHECKED_CANONICAL_CLOSURE_REQUIRED" if all_checked
                   else "MISSING_OR_BLOCKED"),
        "verification_claim": False,
        "canonical_gate_required": True,
        "authority": False, "execution_performed": False,
    }

def write_readonly_projection(value: dict[str, Any], path: Path) -> Path:
    """Atomic owner-only UI projection. Never use this file as canonical proof."""
    if (value.get("schema") != "fa3.goal-independent-review-projection.v1" or
            value.get("verification_claim") is not False or
            value.get("authority") is not False or
            value.get("canonical_gate_required") is not True):
        raise IndependentReviewDenied("untrusted goal review projection")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".goal-review-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path
