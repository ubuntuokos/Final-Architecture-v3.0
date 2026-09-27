#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from fa3_agent_deliberation import (
    DeliberationContractError,
    can_speak,
    close_objection_window,
    close_session,
    completion_claim_valid,
    consensus_ready,
    independent_reveal_ready,
    new_session,
    record_objection,
    reveal_independent,
    set_turn,
    submit_independent,
    validate_artifact,
    validate_message,
    validate_participant,
)
from fa3_release_baseline import load_active_release_baseline
from fa3_agent_deliberation_runtime import make_server

PROFILE = "canonical/profiles/FA3-AGENT-COLLABORATION-DELIBERATION-001.json"
CONTRACT = "canonical/contracts/FA3-AGENT-COLLABORATION-DELIBERATION-CONTRACTS-001.json"
DECISION = "canonical/decisions/FA3-DEC-AGENT-COLLABORATION-DELIBERATION-2026-09-27.json"
REFERENCE = "canonical/references/FA3-AGENT-ROOM-PATTERN-REFERENCE-2026-09-27.json"
ENFORCEMENT = "canonical/agent-collaboration-deliberation-enforcement.json"
INTENT = "canonical/intents/FA3-AGENT-COLLABORATION-DELIBERATION-APPLICATION-INTENT-001.json"
REUSE = "canonical/assessments/FA3-AGENT-COLLABORATION-DELIBERATION-REUSE-ASSESSMENT-001.json"
DFA = "canonical/assessments/FA3-AGENT-COLLABORATION-DELIBERATION-DECISION-ASSESSMENT-2026-09-27.json"
REPORT = "reports/agent-collaboration-deliberation-gate-report.json"


def load(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {rel}")
    return value


def participant(pid: str, *, role: str = "AGENT") -> dict[str, Any]:
    row: dict[str, Any] = {
        "participant_id": pid,
        "role": role,
        "identity_receipt_ref": f"identity:{pid}",
        "authorized": True,
        "authority_grants": [],
        "capability_grants": [],
    }
    if role == "AGENT":
        row["model_binding"] = {
            "router_authority": "FA3-AUTH-MODEL-ROUTER-001",
            "route_id": f"route:{pid}",
            "provider_id": f"provider:{pid}",
            "model_id": f"model:{pid}",
            "receipt_ref": f"router-receipt:{pid}",
            "binding_source": "MODEL_ROUTER_RECEIPT",
        }
    return row


def message(session_id: str, sender: str) -> dict[str, Any]:
    return {
        "message_id": f"m:{sender}",
        "session_id": session_id,
        "sender_id": sender,
        "communication_mode": "HUMAN_LANGUAGE",
        "language_tag": "en",
        "human_readable_text": "Evidence-backed position.",
        "human_readable_authoritative": True,
        "secret_values_present": False,
        "client_asserted_host_verified": False,
    }


def expect_raises(fn: Callable[[], Any]) -> bool:
    try:
        fn()
    except DeliberationContractError:
        return True
    return False


def regression_cases() -> list[tuple[str, bool]]:
    a, b, h = participant("a"), participant("b"), participant("human", role="HUMAN")
    open_room = new_session("s-open", "review", [a, b, h], moderator_id="human")
    directed = new_session("s-dir", "review", [a, b], mode="DIRECTED")
    rr = set_turn(new_session("s-rr", "review", [a, b], mode="ROUND_ROBIN"), "a")
    mod = new_session("s-mod", "review", [a, b, h], mode="MODERATOR", moderator_id="human")
    human_only = new_session("s-human", "review", [a, h], mode="HUMAN_ONLY")
    independent = new_session("s-ind", "review", [a, b], mode="INDEPENDENT")
    indep_a = submit_independent(independent, "a", "position a", ["e:a"])
    indep_all = submit_independent(indep_a, "b", "position b", ["e:b"])
    revealed = reveal_independent(indep_all)
    consensus = new_session("s-cons", "review", [a, b, h], mode="CONSENSUS_CHECK", human_approval_required=True)
    consensus = record_objection(consensus, "a", "NO_OBJECTION")
    consensus = record_objection(consensus, "b", "NO_OBJECTION")
    consensus_no_approval = close_objection_window(consensus)
    consensus_approved = close_objection_window(consensus, approval_receipt_ref="approval:1")
    objected = new_session("s-obj", "review", [a, b], mode="CONSENSUS_CHECK")
    objected = record_objection(objected, "a", "NO_OBJECTION")
    objected = record_objection(objected, "b", "OBJECTED")
    objected = close_objection_window(objected)
    closed = close_session(open_room, "closure:1")

    bad_binding = participant("bad")
    bad_binding["model_binding"]["binding_source"] = "SELF_ASSERTED"

    bad_secret = message("s-open", "a")
    bad_secret["secret_values_present"] = True
    bad_host = message("s-open", "a")
    bad_host["client_asserted_host_verified"] = True
    bad_codebook = message("s-open", "a")
    bad_codebook["private_codebook"] = {"x": "hidden"}

    return [
        ("valid-open-message", not expect_raises(lambda: validate_message(open_room, message("s-open", "a")))),
        ("unauthorized-participant-denied", expect_raises(lambda: can_speak(open_room, "outsider"))),
        ("directed-unaddressed-denied", not can_speak(directed, "a", addressed_to=["b"])),
        ("directed-addressed-allowed", can_speak(directed, "a", addressed_to=["a"])),
        ("round-robin-wrong-turn-denied", not can_speak(rr, "b")),
        ("round-robin-current-turn-allowed", can_speak(rr, "a")),
        ("moderator-can-speak", can_speak(mod, "human")),
        ("human-only-blocks-agent", not can_speak(human_only, "a")),
        ("self-asserted-model-binding-denied", expect_raises(lambda: validate_participant(bad_binding))),
        ("secret-transcript-denied", expect_raises(lambda: validate_message(open_room, bad_secret))),
        ("client-hostverified-denied", expect_raises(lambda: validate_message(open_room, bad_host))),
        ("private-codebook-denied", expect_raises(lambda: validate_message(open_room, bad_codebook))),
        ("independent-remains-sealed-before-barrier", not independent_reveal_ready(indep_a) and indep_a["sealed_submissions"]["a"]["sealed"] is True),
        ("independent-reveal-after-all", independent_reveal_ready(indep_all) and revealed["independent_revealed"] is True),
        ("consensus-blocked-without-human-approval", not consensus_ready(consensus_no_approval)),
        ("consensus-ready-after-objection-window-and-approval", consensus_ready(consensus_approved)),
        ("unresolved-objection-blocks-consensus", not consensus_ready(objected)),
        ("completion-without-evidence-denied", not completion_claim_valid({"claimant_id":"a","reviewer_id":"b","evidence_refs":[],"review_status":"VERIFIED","task_transition":"COMPLETED"})),
        ("self-verification-denied", not completion_claim_valid({"claimant_id":"a","reviewer_id":"a","evidence_refs":["e:1"],"review_status":"VERIFIED","task_transition":"COMPLETED"})),
        ("evidence-independent-verification-accepted", completion_claim_valid({"claimant_id":"a","reviewer_id":"b","evidence_refs":["e:1"],"review_status":"VERIFIED","task_transition":"COMPLETED"})),
        ("room-artifact-cannot-grant-authority", expect_raises(lambda: validate_artifact({"artifact_id":"x","kind":"DECISION","human_readable_text":"x","grants_authority":True}))),
        ("closed-room-blocks-speech", not can_speak(closed, "a")),
    ]


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    count = load_active_release_baseline(root).capability_count
    findings: list[dict[str, Any]] = []
    paths = [PROFILE, CONTRACT, DECISION, REFERENCE, ENFORCEMENT, INTENT, REUSE, DFA]
    runtime_paths = ["src/fa3_agent_deliberation_runtime.py", "evidence/collect-agent-deliberation-reference-e2e.py"]
    for rel in paths + runtime_paths:
        if not (root / rel).is_file():
            findings.append({"code": "DEL-001", "message": "required materialization missing", "path": rel})
    if findings:
        return {"schema":"fa3.agent-collaboration-deliberation-gate-report.v1","gate_id":"FA3-AGENT-COLLABORATION-DELIBERATION-GATESET-001","result":"FAIL","findings":findings}

    p, c, d, r, e, i, reuse, dfa = [load(root, rel) for rel in paths]
    checks: list[tuple[bool, str, str]] = [
        (p.get("id") == "FA3-AGENT-COLLABORATION-DELIBERATION-001" and p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count") == count and p.get("capability_bindings") == ["CAP-028", "CAP-070"], "DEL-010", "profile capability/authority baseline drift"),
        (c.get("id") == "FA3-AGENT-COLLABORATION-DELIBERATION-CONTRACTS-001" and c.get("provider_neutral") is True and c.get("fail_closed") is True and c.get("capability_count") == count, "DEL-011", "contract baseline drift"),
        (d.get("new_capabilities") == 0 and d.get("new_architectural_authorities") == 0 and d.get("capability_count_after") == count and d.get("current_host_runtime_promotion_claim") is False, "DEL-012", "decision overclaim or baseline drift"),
        (p.get("authority_boundaries", {}).get("model_routing") == "FA3-AUTH-MODEL-ROUTER-001" and p.get("authority_boundaries", {}).get("host_resources") == "FA3-AUTH-HOST-RESOURCE-BROKER-001" and p.get("authority_boundaries", {}).get("action_execution") == "FA3-UNIFIED-ACTION-FABRIC-001" and p.get("authority_boundaries", {}).get("ai_communication") == "FA3-AI-COMMS-001", "DEL-013", "authority boundary drift"),
        (p.get("participant_policy", {}).get("room_may_expand_participant_set") is False and p.get("participant_policy", {}).get("provider_may_expand_participant_set") is False and p.get("participant_policy", {}).get("agent_model_binding_source") == "MODEL_ROUTER_RECEIPT", "DEL-014", "participant/model binding guard drift"),
        (p.get("communication_policy", {}).get("client_asserted_host_verified_is_trusted") is False and p.get("communication_policy", {}).get("secret_values_in_transcript_allowed") is False and p.get("communication_policy", {}).get("human_readable_semantics_authoritative") is True, "DEL-015", "communication trust boundary drift"),
        (p.get("turn_policy", {}).get("independent_mode_seals_submissions_until_reveal_barrier") is True and p.get("turn_policy", {}).get("consensus_requires_objection_opportunity") is True, "DEL-016", "deliberation discipline drift"),
        (p.get("artifact_policy", {}).get("chat_message_is_task_transition") is False and p.get("artifact_policy", {}).get("completion_requires_evidence") is True and p.get("artifact_policy", {}).get("independent_verifier_must_differ_from_claimant") is True, "DEL-017", "completion/evidence boundary drift"),
        (r.get("status") == "REFERENCE_ONLY" and r.get("source_code_copied") is False and r.get("upstream_runtime_imported") is False and r.get("upstream_installers_admitted") is False, "DEL-018", "upstream reference boundary drift"),
        ({x.get("repository"): x.get("commit") for x in r.get("sources", [])} == {"steviebuilds/agent-room":"ae600ecb4790a4fdc526020fd6946e8f57e2b1b4","agent-room-alkl/agent-room":"080b13d2bf927a1ee3e66981dece0d2eee698d37","msitarzewski/agent-room":"c48e8036159c2bf0a03473a3352457a2ef2c3e7e"}, "DEL-019", "upstream pin drift"),
        (i.get("declared_new_capabilities") == [] and i.get("proposed_authority_roles") == [] and i.get("hardware_audit", {}).get("cpu_only_viable") is True and i.get("namespace_claims", {}).get("claims_default_port") is False, "DEL-020", "ApplicationIntent hardware/coexistence drift"),
        (reuse.get("result") == "PASS" and reuse.get("current_host_runtime_promotion_claim") is False and reuse.get("new_capabilities") == 0 and reuse.get("new_architectural_authorities") == 0 and p.get("id") in reuse.get("covered_ids", []), "DEL-021", "ReuseAssessment drift"),
        (dfa.get("assessment") == "REQUIRED" and dfa.get("project_radar_checked") is True and dfa.get("security_boundary", {}).get("may_expand_candidate_set") is False and dfa.get("hardware_audit", {}).get("cpu_only_viable") is True, "DEL-022", "Decision Fabric applicability boundary drift"),
        (e.get("fail_closed") is True and e.get("mandatory") is True and e.get("capability_count") == count and len(e.get("p0_invariants", [])) == 21, "DEL-023", "enforcement inventory drift"),
        (p.get("hardware_audit", {}).get("vendor_neutral") is True and p.get("hardware_audit", {}).get("cpu_only_viable") is True and p.get("hardware_audit", {}).get("accelerator_cardinality") == "0..N" and p.get("hardware_audit", {}).get("global_accelerator_requirement") is False, "DEL-024", "Hardware Audit drift"),
        (p.get("coexistence", {}).get("cap_175_applies") is True and p.get("coexistence", {}).get("requires_upstream_uninstall") is False and p.get("coexistence", {}).get("fixed_port_claim") is False and p.get("coexistence", {}).get("global_agent_config_mutation") is False, "DEL-025", "CAP-175 coexistence drift"),
        (p.get("current_host_runtime_promotion_claim") is False and p.get("global_promotion_claim") is False and p.get("runtime_status") == "REFERENCE_RUNTIME_MATERIALIZED_CI_E2E_CURRENT_HOST_PENDING", "DEL-026", "runtime promotion truth boundary drift"),
    ]
    for ok, code, message_text in checks:
        if not ok:
            findings.append({"code": code, "message": message_text})

    try:
        server = make_server(port=0)
        host, port = server.server_address
        runtime_smoke = host == "127.0.0.1" and isinstance(port, int) and port > 0
        server.server_close()
    except Exception:
        runtime_smoke = False
    if not runtime_smoke:
        findings.append({"code":"DEL-029","message":"loopback dynamic-port reference runtime smoke failed"})

    cases = regression_cases()
    for name, ok in cases:
        if not ok:
            findings.append({"code": "DEL-REGRESSION", "case": name, "message": "deterministic deliberation regression failed"})

    bin_text = (root / "bin/fa3-enforce").read_text(encoding="utf-8")
    workflow_text = (root / ".github/workflows/fa3-permanent-enforcement.yml").read_text(encoding="utf-8")
    if 'agent-deliberation' not in bin_text or 'fa3_agent_deliberation_gate.py' not in bin_text:
        findings.append({"code":"DEL-027","message":"bin/fa3-enforce binding missing"})
    if "./bin/fa3-enforce agent-deliberation" not in workflow_text or "collect-agent-deliberation-reference-e2e.py" not in workflow_text or "agent-collaboration-deliberation-gate-report.json" not in workflow_text:
        findings.append({"code":"DEL-028","message":"permanent CI/report binding missing"})

    return {
        "schema": "fa3.agent-collaboration-deliberation-gate-report.v1",
        "gate_id": "FA3-AGENT-COLLABORATION-DELIBERATION-GATESET-001",
        "profile_id": p.get("id"),
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "regression_case_count": len(cases),
        "capability_count": count,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "hardware_audit": p.get("hardware_audit"),
        "current_host_runtime_promotion_claim": False,
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default=REPORT)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = gate(root)
    out = root / args.report
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
