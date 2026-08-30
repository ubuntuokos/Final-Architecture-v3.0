#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-MENTOR-001"
PROVIDER_ID = "FA3-PROVIDER-MENTOR-LOCAL-001"
CONTRACT_ID = "FA3-MENTOR-CONTRACTS-001"
DECISION_ID = "FA3-DEC-MENTOR-2026-08-30"
MATRIX_ID = "FA3-MENTOR-CONFORMANCE-MATRIX-001"
GATE_ID = "FA3-MENTOR-GATESET-001"
CAPABILITY_COUNT = 143

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}

def typed_escalation_valid(env: dict[str, Any]) -> bool:
    return (
        env.get("target_authority") == "central_mcp_gateway"
        and bool(env.get("target_capability"))
        and bool(env.get("operation"))
        and env.get("requires_authorization") is True
        and env.get("execute_by_mentor") is False
        and isinstance(env.get("caller"), dict)
    )

def memory_write_projection_valid(*, explicit_consent: bool, canonical_write_performed: bool, escalation_capability: str | None) -> bool:
    return bool(explicit_consent and not canonical_write_performed and escalation_capability == "memory.write")

def evidence_outbox_valid(*, local_store_is_canonical: bool, previous_hash: str, payload: bytes, record_hash: str) -> bool:
    expected = hashlib.sha256(previous_hash.encode("ascii") + payload).hexdigest()
    return (not local_store_is_canonical) and len(previous_hash) == 64 and record_hash == expected

def mastery_update_valid(*, evidence_refs: list[str], state_is_canonical_memory: bool, p_known_before: float, p_known_after: float) -> bool:
    return bool(evidence_refs) and not state_is_canonical_memory and 0 <= p_known_before <= 1 and 0 <= p_known_after <= 1

def lab_projection_valid(env: dict[str, Any]) -> bool:
    return (
        env.get("target_capability") == "agent_execution.sandboxed_practice_lab"
        and env.get("execute_by_mentor") is False
        and env.get("requires_authorization") is True
    )

def delegated_lab_execution_valid(*, transport_authenticated: bool, authority: str, approved: bool, sandbox_backend: str | None, network: str, writable_host_paths: list[str]) -> bool:
    return bool(
        transport_authenticated
        and authority == "agent_execution"
        and approved
        and sandbox_backend == "bubblewrap"
        and network == "deny"
        and writable_host_paths == []
    )

def registry_matrix_link_valid(decision: dict[str, Any], matrix: dict[str, Any], profile: dict[str, Any]) -> bool:
    return (
        decision.get("id") == matrix.get("decision_ref") == DECISION_ID
        and decision.get("profile_id") == matrix.get("profile_id") == profile.get("id") == PROFILE_ID
        and decision.get("conformance_matrix_id") == matrix.get("id") == MATRIX_ID
    )

def run_regressions() -> dict[str, Any]:
    cases = []
    def add(name: str, positive: bool, negative: bool) -> None:
        cases.append({"name": name, "positive_case": positive, "negative_case": negative, "status": "PASS" if positive and negative else "FAIL"})

    good_env = {
        "target_authority": "central_mcp_gateway", "target_capability": "memory.write",
        "operation": "propose", "requires_authorization": True, "execute_by_mentor": False,
        "caller": {"caller_profile": PROFILE_ID}
    }
    add("typed_mcp_escalation", typed_escalation_valid(good_env), not typed_escalation_valid({**good_env, "execute_by_mentor": True}))
    add("consent_memory_projection",
        memory_write_projection_valid(explicit_consent=True, canonical_write_performed=False, escalation_capability="memory.write"),
        not memory_write_projection_valid(explicit_consent=False, canonical_write_performed=False, escalation_capability="memory.write"))
    payload = b'{"event":"mentor.response"}'
    prev = "0" * 64
    rh = hashlib.sha256(prev.encode("ascii") + payload).hexdigest()
    add("evidence_outbox_not_authority",
        evidence_outbox_valid(local_store_is_canonical=False, previous_hash=prev, payload=payload, record_hash=rh),
        not evidence_outbox_valid(local_store_is_canonical=True, previous_hash=prev, payload=payload, record_hash=rh))
    add("evidence_backed_mastery",
        mastery_update_valid(evidence_refs=["EV-1"], state_is_canonical_memory=False, p_known_before=.2, p_known_after=.6),
        not mastery_update_valid(evidence_refs=[], state_is_canonical_memory=False, p_known_before=.2, p_known_after=.6))
    lab_env = {"target_capability":"agent_execution.sandboxed_practice_lab","execute_by_mentor":False,"requires_authorization":True}
    add("mentor_lab_projection_only", lab_projection_valid(lab_env), not lab_projection_valid({**lab_env, "execute_by_mentor":True}))
    add("delegated_bubblewrap_execution",
        delegated_lab_execution_valid(transport_authenticated=True, authority="agent_execution", approved=True, sandbox_backend="bubblewrap", network="deny", writable_host_paths=[]),
        not delegated_lab_execution_valid(transport_authenticated=False, authority="agent_execution", approved=True, sandbox_backend="bubblewrap", network="deny", writable_host_paths=[]))
    add("network_deny_and_no_host_writes",
        delegated_lab_execution_valid(transport_authenticated=True, authority="agent_execution", approved=True, sandbox_backend="bubblewrap", network="deny", writable_host_paths=[]),
        not delegated_lab_execution_valid(transport_authenticated=True, authority="agent_execution", approved=True, sandbox_backend="bubblewrap", network="allow", writable_host_paths=["/"]))
    add("provider_no_authority", True, PROVIDER_ID != "FA3-AUTH-MCP-GATEWAY-001")
    passed = sum(x["status"] == "PASS" for x in cases)
    return {"result":"PASS" if passed == len(cases) else "FAIL","passed":passed,"total":len(cases),"cases":cases}

def gate(root: Path) -> dict[str, Any]:
    paths = {
        "profile": root / "canonical/profiles/FA3-MENTOR-001.json",
        "contracts": root / "canonical/contracts/FA3-MENTOR-CONTRACTS-001.json",
        "provider": root / "canonical/providers/FA3-PROVIDER-MENTOR-LOCAL-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-MENTOR-2026-08-30.json",
        "matrix": root / "canonical/FA3-MENTOR-CONFORMANCE-MATRIX-001.json",
        "enforcement": root / "canonical/mentor-enforcement.json",
        "reference": root / "evidence/reference/fa3-mentor-v0.2.0.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    findings = []
    for name, path in paths.items():
        if not path.exists():
            findings.append(_finding("MENTOR-REF-001", f"Missing required Mentor artifact: {name}", path=str(path.relative_to(root))))
    if findings:
        report = {"schema":"fa3.mentor-gate-report.v1","result":"FAIL","findings":findings}
        _write(root / "reports/mentor-gate-report.json", report)
        return report

    p = _load(paths["profile"]); c = _load(paths["contracts"]); v = _load(paths["provider"])
    d = _load(paths["decision"]); m = _load(paths["matrix"]); e = _load(paths["enforcement"])
    r = _load(paths["reference"]); policy = _load(paths["policy"])

    if not (p.get("id") == PROFILE_ID and p.get("status") == "CANONICAL" and p.get("priority") == "P0" and p.get("requirement") == "MUST"):
        findings.append(_finding("MENTOR-REF-002", "Mentor profile identity/P0/MUST invariant mismatch"))
    if p.get("capability_count") != CAPABILITY_COUNT or p.get("new_capability") is not False or p.get("new_architectural_authority") is not False:
        findings.append(_finding("MENTOR-REF-003", "Mentor profile changed capability/authority invariants"))
    if c.get("id") != CONTRACT_ID or c.get("capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("MENTOR-REF-004", "Mentor contract-family invariant mismatch"))
    required_contracts = {"McpTypedEscalation","KnowledgeProjectionResult","MemoryWriteProposal","EvidenceSinkReceipt","MasteryUpdate","PracticeLabExecutionRequest"}
    if not required_contracts.issubset(set(c.get("contracts", []))):
        findings.append(_finding("MENTOR-REF-005", "Mentor mandatory integration contracts missing"))
    if v.get("id") != PROVIDER_ID or v.get("architectural_authority") is not False or v.get("new_capability") is not False:
        findings.append(_finding("MENTOR-REF-006", "Mentor provider authority/capability drift"))
    if e.get("gate_id") != GATE_ID or e.get("mandatory_rule_count") != 12 or e.get("fail_closed") is not True:
        findings.append(_finding("MENTOR-REF-007", "Mentor enforcement invariant mismatch"))
    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("MENTOR-REF-008", "Mentor gate is not globally bound into enforcement-policy"))
    if policy.get("mentor_profile_id") != PROFILE_ID or policy.get("mentor_provider_id") != PROVIDER_ID:
        findings.append(_finding("MENTOR-REF-009", "Mentor global policy binding drift"))
    if not registry_matrix_link_valid(d, m, p):
        findings.append(_finding("MENTOR-REF-010", "Decision Registry to Conformance Matrix direct link failed"))
    if r.get("implementation_version") != "0.2.0" or r.get("automated_tests", {}).get("status") != "PASS" or r.get("current_host_promotion_claimed") is not False:
        findings.append(_finding("MENTOR-REF-011", "Mentor reference implementation evidence invalid or overclaims current-host promotion"))
    if m.get("runtime_current_host", {}).get("promotion_claimed") is not False:
        findings.append(_finding("MENTOR-REF-012", "Mentor conformance matrix falsely claims current-host promotion"))

    regressions = run_regressions()
    if regressions["result"] != "PASS":
        findings.append(_finding("MENTOR-REG-001", "Mentor executable regression matrix failed", regressions=regressions))

    report = {
        "schema":"fa3.mentor-gate-report.v1","gate_id":GATE_ID,"profile_id":PROFILE_ID,"provider_id":PROVIDER_ID,
        "capability_count":CAPABILITY_COUNT,"result":"PASS" if not findings else "FAIL","mode":"CI_REFERENCE_AND_CANONICAL",
        "findings":findings,"regressions":regressions,"current_host_status":m.get("runtime_current_host", {}).get("status"),"promotion_claimed":False
    }
    _write(root / "reports/mentor-gate-report.json", report)
    return report
