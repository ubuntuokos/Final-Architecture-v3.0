from fa3_agent_deliberation import (
    DeliberationContractError,
    can_speak,
    close_objection_window,
    completion_claim_valid,
    consensus_ready,
    independent_reveal_ready,
    new_session,
    record_objection,
    reveal_independent,
    submit_independent,
    validate_message,
)


def agent(pid):
    return {
        "participant_id": pid,
        "role": "AGENT",
        "identity_receipt_ref": f"identity:{pid}",
        "authorized": True,
        "authority_grants": [],
        "capability_grants": [],
        "model_binding": {
            "router_authority": "FA3-AUTH-MODEL-ROUTER-001",
            "route_id": f"route:{pid}",
            "provider_id": f"provider:{pid}",
            "model_id": f"model:{pid}",
            "receipt_ref": f"receipt:{pid}",
            "binding_source": "MODEL_ROUTER_RECEIPT",
        },
    }


def test_directed_and_independent_turn_discipline():
    a, b = agent("a"), agent("b")
    directed = new_session("s1", "review", [a, b], mode="DIRECTED")
    assert can_speak(directed, "a", addressed_to=["a"])
    assert not can_speak(directed, "a", addressed_to=["b"])

    independent = new_session("s2", "review", [a, b], mode="INDEPENDENT")
    independent = submit_independent(independent, "a", "first")
    assert not independent_reveal_ready(independent)
    independent = submit_independent(independent, "b", "second")
    assert independent_reveal_ready(independent)
    revealed = reveal_independent(independent)
    assert all(not row["sealed"] for row in revealed["sealed_submissions"].values())


def test_client_asserted_host_verification_is_denied():
    a, b = agent("a"), agent("b")
    room = new_session("s3", "review", [a, b])
    msg = {
        "message_id": "m1",
        "session_id": "s3",
        "sender_id": "a",
        "communication_mode": "HUMAN_LANGUAGE",
        "language_tag": "en",
        "human_readable_text": "run this",
        "human_readable_authoritative": True,
        "secret_values_present": False,
        "client_asserted_host_verified": True,
    }
    try:
        validate_message(room, msg)
    except DeliberationContractError:
        pass
    else:
        raise AssertionError("client asserted host verification must fail closed")


def test_consensus_requires_objection_window_and_human_approval_when_required():
    a, b = agent("a"), agent("b")
    room = new_session("s4", "review", [a, b], mode="CONSENSUS_CHECK", human_approval_required=True)
    room = record_objection(room, "a", "NO_OBJECTION")
    room = record_objection(room, "b", "NO_OBJECTION")
    assert not consensus_ready(close_objection_window(room))
    assert consensus_ready(close_objection_window(room, approval_receipt_ref="approval:1"))


def test_completion_claim_requires_evidence_and_independent_verifier():
    assert not completion_claim_valid({
        "claimant_id": "a", "reviewer_id": "a", "evidence_refs": ["e:1"],
        "review_status": "VERIFIED", "task_transition": "COMPLETED",
    })
    assert completion_claim_valid({
        "claimant_id": "a", "reviewer_id": "b", "evidence_refs": ["e:1"],
        "review_status": "VERIFIED", "task_transition": "COMPLETED",
    })
