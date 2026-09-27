#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

PROFILE_ID = "FA3-AGENT-COLLABORATION-DELIBERATION-001"
AI_COMMS_ID = "FA3-AI-COMMS-001"
MODEL_ROUTER = "FA3-AUTH-MODEL-ROUTER-001"

MODES = {
    "OPEN", "DIRECTED", "ROUND_ROBIN", "MODERATOR", "CHALLENGE",
    "INDEPENDENT", "CONSENSUS_CHECK", "HUMAN_ONLY", "CLOSED",
}
PHASES = {
    "EVIDENCE_COLLECTION", "INDEPENDENT_POSITIONS", "CHALLENGE",
    "CONTRADICTION_RESOLUTION", "PROPOSED_DECISION", "OBJECTION_WINDOW",
    "HUMAN_APPROVAL", "CLOSED",
}
ARTIFACT_KINDS = {"DECISION", "TODO", "STATUS", "RESULT", "BLOCKER", "EVIDENCE"}


class DeliberationContractError(ValueError):
    pass


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_participant(participant: dict[str, Any]) -> None:
    for field in ("participant_id", "role", "identity_receipt_ref"):
        if not _nonempty(participant.get(field)):
            raise DeliberationContractError(f"participant {field} required")
    if participant.get("role") not in {"AGENT", "HUMAN"}:
        raise DeliberationContractError("participant role invalid")
    if participant.get("authorized") is not True:
        raise DeliberationContractError("participant must already be authorized")
    if participant.get("authority_grants") != [] or participant.get("capability_grants") != []:
        raise DeliberationContractError("room participant cannot gain authority or capability grants")
    if participant.get("role") == "AGENT":
        binding = participant.get("model_binding")
        if not isinstance(binding, dict):
            raise DeliberationContractError("agent model binding required")
        for field in ("route_id", "provider_id", "model_id", "receipt_ref"):
            if not _nonempty(binding.get(field)):
                raise DeliberationContractError(f"model binding {field} required")
        if binding.get("router_authority") != MODEL_ROUTER:
            raise DeliberationContractError("model routing authority bypass")
        if binding.get("binding_source") != "MODEL_ROUTER_RECEIPT":
            raise DeliberationContractError("self-asserted model/provider binding denied")


def new_session(
    session_id: str,
    objective: str,
    participants: list[dict[str, Any]],
    *,
    mode: str = "OPEN",
    moderator_id: str | None = None,
    human_approval_required: bool = False,
) -> dict[str, Any]:
    if not _nonempty(session_id) or not _nonempty(objective):
        raise DeliberationContractError("session id and objective required")
    if mode not in MODES or mode == "CLOSED":
        raise DeliberationContractError("initial room mode invalid")
    if len(participants) < 2:
        raise DeliberationContractError("collaboration session requires at least two participants")
    checked = []
    ids: set[str] = set()
    for participant in participants:
        validate_participant(participant)
        pid = participant["participant_id"]
        if pid in ids:
            raise DeliberationContractError("duplicate participant id")
        ids.add(pid)
        checked.append(deepcopy(participant))
    if moderator_id is not None and moderator_id not in ids:
        raise DeliberationContractError("moderator must be an authorized participant")
    required = [p["participant_id"] for p in checked if p["role"] == "AGENT"] or sorted(ids)
    return {
        "schema": "fa3.deliberation-session.v1",
        "profile_id": PROFILE_ID,
        "session_id": session_id,
        "objective": objective,
        "status": "OPEN",
        "mode": mode,
        "phase": "EVIDENCE_COLLECTION",
        "participants": checked,
        "authorized_participant_ids": sorted(ids),
        "required_deliberators": required,
        "moderator_id": moderator_id,
        "current_turn": None,
        "sealed_submissions": {},
        "independent_revealed": False,
        "objections": {},
        "objection_window_closed": False,
        "human_approval_required": bool(human_approval_required),
        "human_approval_receipt_ref": None,
    }


def set_turn(session: dict[str, Any], participant_id: str | None) -> dict[str, Any]:
    updated = deepcopy(session)
    if participant_id is not None and participant_id not in updated.get("authorized_participant_ids", []):
        raise DeliberationContractError("turn owner must be authorized")
    updated["current_turn"] = participant_id
    return updated


def _participant(session: dict[str, Any], participant_id: str) -> dict[str, Any]:
    for participant in session.get("participants", []):
        if participant.get("participant_id") == participant_id:
            return participant
    raise DeliberationContractError("sender is not an authorized participant")


def can_speak(
    session: dict[str, Any],
    participant_id: str,
    *,
    addressed_to: list[str] | None = None,
) -> bool:
    participant = _participant(session, participant_id)
    if session.get("status") != "OPEN" or session.get("mode") == "CLOSED":
        return False
    mode = session.get("mode")
    if mode not in MODES:
        return False
    if mode == "OPEN":
        return True
    if mode == "DIRECTED":
        return participant_id in set(addressed_to or [])
    if mode in {"ROUND_ROBIN", "CHALLENGE"}:
        return session.get("current_turn") == participant_id
    if mode == "MODERATOR":
        return participant_id == session.get("moderator_id") or session.get("current_turn") == participant_id
    if mode == "INDEPENDENT":
        return participant_id in set(session.get("required_deliberators", [])) and participant_id not in session.get("sealed_submissions", {})
    if mode == "CONSENSUS_CHECK":
        return participant_id in set(session.get("required_deliberators", [])) and participant_id not in session.get("objections", {})
    if mode == "HUMAN_ONLY":
        return participant.get("role") == "HUMAN"
    return False


def validate_message(
    session: dict[str, Any],
    message: dict[str, Any],
    *,
    addressed_to: list[str] | None = None,
) -> None:
    sender = message.get("sender_id")
    if not _nonempty(sender):
        raise DeliberationContractError("sender_id required")
    if not can_speak(session, sender, addressed_to=addressed_to):
        raise DeliberationContractError("turn policy denied message")
    if message.get("session_id") != session.get("session_id") or not _nonempty(message.get("message_id")):
        raise DeliberationContractError("message/session identity invalid")
    if message.get("communication_mode") not in {"HUMAN_LANGUAGE", "CANONICAL_STRUCTURED"}:
        raise DeliberationContractError("AI communication mode invalid")
    if not _nonempty(message.get("language_tag")) or not _nonempty(message.get("human_readable_text")):
        raise DeliberationContractError("human-readable semantics required")
    if message.get("human_readable_authoritative") is not True:
        raise DeliberationContractError("human-readable text must be authoritative")
    if message.get("secret_values_present") is not False:
        raise DeliberationContractError("secret values forbidden in transcript")
    if message.get("private_codebook") or message.get("model_only_slang") or message.get("opaque_primary_channel"):
        raise DeliberationContractError("private or opaque model communication forbidden")
    if message.get("client_asserted_host_verified") is not False:
        raise DeliberationContractError("client asserted host verification is not trusted")


def submit_independent(
    session: dict[str, Any],
    participant_id: str,
    human_readable_text: str,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    if session.get("mode") != "INDEPENDENT":
        raise DeliberationContractError("independent submission requires INDEPENDENT mode")
    if not can_speak(session, participant_id):
        raise DeliberationContractError("independent submission denied")
    if not _nonempty(human_readable_text):
        raise DeliberationContractError("independent submission text required")
    updated = deepcopy(session)
    digest = hashlib.sha256(human_readable_text.encode("utf-8")).hexdigest()
    updated["sealed_submissions"][participant_id] = {
        "sha256": digest,
        "evidence_refs": list(evidence_refs or []),
        "sealed": True,
    }
    return updated


def independent_reveal_ready(session: dict[str, Any]) -> bool:
    required = set(session.get("required_deliberators", []))
    submitted = set(session.get("sealed_submissions", {}))
    return bool(required) and required.issubset(submitted)


def reveal_independent(session: dict[str, Any]) -> dict[str, Any]:
    if not independent_reveal_ready(session):
        raise DeliberationContractError("reveal barrier not satisfied")
    updated = deepcopy(session)
    updated["independent_revealed"] = True
    for item in updated.get("sealed_submissions", {}).values():
        item["sealed"] = False
    return updated


def record_objection(session: dict[str, Any], participant_id: str, status: str) -> dict[str, Any]:
    if session.get("mode") != "CONSENSUS_CHECK":
        raise DeliberationContractError("objection record requires CONSENSUS_CHECK mode")
    if status not in {"NO_OBJECTION", "OBJECTED"}:
        raise DeliberationContractError("objection status invalid")
    if not can_speak(session, participant_id):
        raise DeliberationContractError("objection record denied")
    updated = deepcopy(session)
    updated["objections"][participant_id] = status
    return updated


def close_objection_window(session: dict[str, Any], *, approval_receipt_ref: str | None = None) -> dict[str, Any]:
    updated = deepcopy(session)
    updated["objection_window_closed"] = True
    if approval_receipt_ref is not None:
        if not _nonempty(approval_receipt_ref):
            raise DeliberationContractError("approval receipt ref invalid")
        updated["human_approval_receipt_ref"] = approval_receipt_ref
    return updated


def consensus_ready(session: dict[str, Any]) -> bool:
    if session.get("mode") != "CONSENSUS_CHECK" or not session.get("objection_window_closed"):
        return False
    required = set(session.get("required_deliberators", []))
    objections = session.get("objections", {})
    if not required or not required.issubset(set(objections)):
        return False
    if any(objections.get(pid) != "NO_OBJECTION" for pid in required):
        return False
    if session.get("human_approval_required") and not _nonempty(session.get("human_approval_receipt_ref")):
        return False
    return True


def validate_artifact(artifact: dict[str, Any]) -> None:
    if artifact.get("kind") not in ARTIFACT_KINDS:
        raise DeliberationContractError("artifact kind invalid")
    if not _nonempty(artifact.get("artifact_id")) or not _nonempty(artifact.get("human_readable_text")):
        raise DeliberationContractError("artifact identity/text required")
    if artifact.get("grants_authority") is not False:
        raise DeliberationContractError("room artifact cannot grant authority")


def completion_claim_valid(claim: dict[str, Any]) -> bool:
    claimant = claim.get("claimant_id")
    reviewer = claim.get("reviewer_id")
    evidence_refs = claim.get("evidence_refs")
    if not _nonempty(claimant) or not _nonempty(reviewer) or claimant == reviewer:
        return False
    if not isinstance(evidence_refs, list) or not evidence_refs or any(not _nonempty(x) for x in evidence_refs):
        return False
    if claim.get("review_status") != "VERIFIED":
        return False
    if claim.get("task_transition") != "COMPLETED":
        return False
    if claim.get("human_approval_required") and not _nonempty(claim.get("human_approval_receipt_ref")):
        return False
    return True


def close_session(session: dict[str, Any], closure_receipt_ref: str) -> dict[str, Any]:
    if not _nonempty(closure_receipt_ref):
        raise DeliberationContractError("closure receipt required")
    updated = deepcopy(session)
    updated["status"] = "CLOSED"
    updated["mode"] = "CLOSED"
    updated["phase"] = "CLOSED"
    updated["closure_receipt_ref"] = closure_receipt_ref
    return updated
