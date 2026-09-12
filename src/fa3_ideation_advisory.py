#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

PROFILE_ID = "FA3-IDEATION-ADVISORY-001"
PROVIDER_ID = "FA3-PROVIDER-IDEATION-ADVISORY-LOCAL-001"
VERSION = "0.1.0"
ALLOWED_MODES = {
    "IDEATE", "CONSTRAINED_IDEATION", "CONTRARIAN", "COMBINE", "GAP_DISCOVERY", "SIMPLIFY",
    "COMPARE", "TRADEOFF_ANALYSIS", "RISK_ASSESSMENT", "RECOMMEND",
}
IDEATION_MODES = {
    "IDEATE", "CONSTRAINED_IDEATION", "CONTRARIAN", "COMBINE", "GAP_DISCOVERY", "SIMPLIFY",
}
ADVISORY_MODES = ALLOWED_MODES - IDEATION_MODES
ALLOWED_EVIDENCE_STATUS = {"VERIFIED", "UNVERIFIED", "CONFLICTED"}


class IdeationAdvisoryInputError(ValueError):
    pass


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise IdeationAdvisoryInputError(f"{field} must be a non-empty string")
    return value.strip()


def _text_list(payload: dict[str, Any], field: str, limit: int = 20) -> list[str]:
    value = payload.get(field, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise IdeationAdvisoryInputError(f"{field} must be a list of strings")
    return [item.strip() for item in value if item.strip()][:limit]


def _candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("candidates", [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise IdeationAdvisoryInputError("candidates must be a list")
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(raw[:20], start=1):
        if isinstance(item, str):
            text = item.strip()
            if text:
                out.append({"id": f"C{idx:02d}", "text": text, "semantic_status": "HYPOTHESIS"})
            continue
        if not isinstance(item, dict):
            raise IdeationAdvisoryInputError("candidate items must be strings or objects")
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise IdeationAdvisoryInputError("candidate.text must be a non-empty string")
        cid = item.get("id", f"C{idx:02d}")
        if not isinstance(cid, str) or not cid.strip():
            raise IdeationAdvisoryInputError("candidate.id must be a non-empty string")
        out.append({"id": cid.strip(), "text": text.strip(), "semantic_status": "HYPOTHESIS"})
    return out


def _evidence(payload: dict[str, Any]) -> list[dict[str, str]]:
    raw = payload.get("evidence", [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise IdeationAdvisoryInputError("evidence must be a list")
    out: list[dict[str, str]] = []
    for item in raw[:50]:
        if not isinstance(item, dict):
            raise IdeationAdvisoryInputError("evidence items must be objects")
        ref = item.get("ref")
        claim = item.get("claim")
        status = str(item.get("status", "UNVERIFIED")).upper()
        if not isinstance(ref, str) or not ref.strip():
            raise IdeationAdvisoryInputError("evidence.ref must be a non-empty string")
        if not isinstance(claim, str) or not claim.strip():
            raise IdeationAdvisoryInputError("evidence.claim must be a non-empty string")
        if status not in ALLOWED_EVIDENCE_STATUS:
            raise IdeationAdvisoryInputError(f"unsupported evidence status: {status}")
        out.append({"ref": ref.strip(), "claim": claim.strip(), "status": status})
    return out


def build_projection(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a bounded ideation/advisory projection without deciding or executing."""
    if not isinstance(payload, dict):
        raise IdeationAdvisoryInputError("request must be a JSON object")

    mode = str(payload.get("mode", "IDEATE")).upper()
    if mode not in ALLOWED_MODES:
        raise IdeationAdvisoryInputError(f"unsupported mode: {mode}")

    problem = _required_text(payload, "problem")
    constraints = _text_list(payload, "constraints")
    criteria = _text_list(payload, "criteria")
    candidates = _candidates(payload)
    evidence = _evidence(payload)
    requested_recommendation = payload.get("requested_recommendation")
    high_impact = payload.get("high_impact", False) is True
    actionable_request = payload.get("actionable_request", False) is True

    verified_refs = [item["ref"] for item in evidence if item["status"] == "VERIFIED"]
    conflicted_refs = [item["ref"] for item in evidence if item["status"] == "CONFLICTED"]
    unverified_refs = [item["ref"] for item in evidence if item["status"] == "UNVERIFIED"]

    recommendation: dict[str, Any] | None = None
    if mode in ADVISORY_MODES:
        if requested_recommendation is not None and not isinstance(requested_recommendation, str):
            raise IdeationAdvisoryInputError("requested_recommendation must be a string when provided")
        evidence_state = (
            "CONFLICTED" if conflicted_refs else "VERIFIED" if verified_refs and not unverified_refs else "UNVERIFIED"
        )
        confidence = "LOW" if evidence_state in {"UNVERIFIED", "CONFLICTED"} else "MEDIUM" if len(verified_refs) < 3 else "HIGH"
        recommendation = {
            "text": (requested_recommendation or "No preferred candidate supplied; assessment only.").strip(),
            "semantic_status": "RECOMMENDATION_NOT_DECISION",
            "evidence_status": evidence_state,
            "evidence_refs": [item["ref"] for item in evidence],
            "conflict_refs": conflicted_refs,
            "confidence": confidence,
            "uncertainty": (
                "EVIDENCE_CONFLICT_PRESENT" if conflicted_refs else
                "MISSING_OR_UNVERIFIED_EVIDENCE" if evidence_state == "UNVERIFIED" else
                "RESIDUAL_MODEL_AND_ASSUMPTION_UNCERTAINTY"
            ),
            "decision_required": True,
        }

    delegations: list[dict[str, str]] = []
    if actionable_request:
        delegations.append({
            "kind": "ACTION",
            "target": "FA3-AUTH-MCP-GATEWAY-001_OR_FA3-AGENT-EXEC-001",
            "reason": "typed_delegation_required",
        })
    if high_impact:
        delegations.append({
            "kind": "VERIFICATION",
            "target": "FA3-INSPECTOR-001",
            "reason": "independent_verification_required_before_high_impact_or_promotion_claim",
        })

    return {
        "schema": "fa3.ideation-advisory-projection.v1",
        "profile_id": PROFILE_ID,
        "provider_id": PROVIDER_ID,
        "version": VERSION,
        "mode": mode,
        "phase": "IDEATION" if mode in IDEATION_MODES else "ADVISORY",
        "status": "PROPOSAL_ONLY",
        "problem": problem,
        "constraints": constraints,
        "criteria": criteria,
        "candidates": candidates,
        "evidence": evidence,
        "recommendation": recommendation,
        "delegations": delegations,
        "semantic_boundaries": {
            "idea_is_fact": False,
            "hypothesis_is_evidence": False,
            "recommendation_is_decision": False,
            "decision_is_authorization": False,
            "authorization_is_execution": False,
            "execution_is_verified_result": False,
        },
        "authority": {
            "decision_authority": False,
            "direct_tool_execution_allowed": False,
            "direct_agent_execution_allowed": False,
            "direct_repository_write_allowed": False,
            "direct_production_mutation_allowed": False,
            "canonical_memory_write_allowed": False,
            "architectural_authority": False,
        },
        "trace": {
            "candidate_ids": [item["id"] for item in candidates],
            "evidence_refs": [item["ref"] for item in evidence],
            "decision_handoff_required": recommendation is not None,
        },
    }


def self_check() -> None:
    ideation = build_projection({
        "mode": "IDEATE", "problem": "Find multiple safe implementation options", "candidates": ["Option A", "Option B"],
    })
    assert ideation["phase"] == "IDEATION"
    assert all(c["semantic_status"] == "HYPOTHESIS" for c in ideation["candidates"])
    assert ideation["semantic_boundaries"]["idea_is_fact"] is False
    assert ideation["authority"]["direct_repository_write_allowed"] is False

    advice = build_projection({
        "mode": "RECOMMEND", "problem": "Select an option",
        "candidates": [{"id": "A", "text": "Option A"}],
        "evidence": [{"ref": "E1", "claim": "Measured result", "status": "VERIFIED"}],
        "requested_recommendation": "Option A", "high_impact": True, "actionable_request": True,
    })
    assert advice["recommendation"]["semantic_status"] == "RECOMMENDATION_NOT_DECISION"
    assert advice["recommendation"]["evidence_status"] == "VERIFIED"
    assert advice["recommendation"]["decision_required"] is True
    assert {d["kind"] for d in advice["delegations"]} == {"ACTION", "VERIFICATION"}

    unverified = build_projection({
        "mode": "RECOMMEND", "problem": "Select without evidence", "requested_recommendation": "Option X",
    })
    assert unverified["recommendation"]["evidence_status"] == "UNVERIFIED"
    assert unverified["recommendation"]["confidence"] == "LOW"

    conflicted = build_projection({
        "mode": "RISK_ASSESSMENT", "problem": "Assess conflicting evidence",
        "evidence": [{"ref": "E2", "claim": "Conflicting result", "status": "CONFLICTED"}],
    })
    assert conflicted["recommendation"]["evidence_status"] == "CONFLICTED"
    assert conflicted["recommendation"]["conflict_refs"] == ["E2"]


def _load_input(path: str | None) -> dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.load(sys.stdin)


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Ideation-Advisory reference projection engine")
    parser.add_argument("--input", help="JSON request file; stdin is used when omitted")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_check:
            self_check()
            print("FA3 Ideation-Advisory self-check: PASS")
            return 0
        projection = build_projection(_load_input(args.input))
    except (IdeationAdvisoryInputError, json.JSONDecodeError, OSError) as exc:
        print(f"FA3 Ideation-Advisory: FAIL: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
