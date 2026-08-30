#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-MUNDER-DIFFLIN-001"
DECISION_ID = "FA3-DEC-MUNDER-DIFFLIN-2026-08-30"
REFERENCE_ID = "FA3-MUNDER-DIFFLIN-UPSTREAM-REFERENCE-2026-08-30"
GATE_ID = "FA3-MUNDER-DIFFLIN-GATESET-001"
CAPABILITY_COUNT = 143
REFERENCE_RELEASE = "v0.4.6"
REFERENCE_RELEASE_COMMIT = "64bd64df0e8d315a6e895283f776b81f84eef2cc"
REFERENCE_MAIN_COMMIT = "fc436bd8b673913c71e3230de08e44f355ffc2e3"

P0_RULES = [
    "MUNDER_EXECUTION_NOT_AUTHORITY",
    "MUNDER_SINGLE_WRITER_COORDINATION",
    "MUNDER_SINGLE_COMMITTER_REPOSITORY_MUTATION",
    "MUNDER_ATOMIC_MESSAGE_PUBLICATION",
    "MUNDER_IDEMPOTENT_MESSAGE_CONSUMPTION",
    "MUNDER_BOUNDED_AGENT_MESSAGE_HOPS",
    "MUNDER_CONCURRENT_WORKSPACE_ISOLATION",
    "MUNDER_CRITICAL_ACTION_HUMAN_ESCALATION",
    "MUNDER_PROGRESSIVE_CIRCUIT_BREAKER",
    "MUNDER_TELEMETRY_POSITIVE_ALLOWLIST",
    "MUNDER_CONTEXT_CANNOT_GRANT_AUTHORITY",
    "MUNDER_TRANSITION_SPECIFIC_LIFECYCLE_EVIDENCE",
    "MUNDER_UNREACHABLE_FAILURE_PATH_FAULT_INJECTION",
    "MUNDER_EPHEMERAL_WORKER_CLEANUP",
    "MUNDER_CAPABILITY_STATE_SEPARATION",
    "MUNDER_DISABLED_PROVIDER_NOT_RUNTIME_DEPENDENCY",
]

MANDATORY_CONSTRAINT = (
    "Munder Difflin SHALL NOT become an FA3 identity, authorization, MCP/tool-mediation, "
    "model-routing, secrets, network-egress, host-resource, workflow/orchestration, evidence, "
    "developer-execution, git/release or registry authority."
)

PROHIBITED_AUTHORITY_MARKERS = (
    "identity_authority", "authorization_authority", "mcp_authority", "tool_mediation_authority",
    "model_routing_authority", "secrets_authority", "secret_authority", "network_egress_authority",
    "host_resource_authority", "workflow_authority", "orchestration_authority", "evidence_authority",
    "developer_execution_authority", "git_authority", "release_authority", "registry_authority",
)

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **kw: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **kw}

def _is_munder(value: Any) -> bool:
    if isinstance(value, str):
        u = value.upper()
        return PROVIDER_ID in value or "MUNDER-DIFFLIN" in u or "MUNDER_DIFFLIN" in u
    if isinstance(value, dict):
        return any(_is_munder(v) for v in value.values())
    if isinstance(value, list):
        return any(_is_munder(v) for v in value)
    return False

def provider_shape_valid(provider: dict[str, Any]) -> bool:
    return bool(
        provider.get("id") == PROVIDER_ID
        and provider.get("status") == "ACCEPTED_REFERENCE"
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT"
        and provider.get("global_runtime_promotion_required_when_disabled") is False
        and provider.get("runtime_activation_requires_current_host_conformance") is True
        and provider.get("upstream_reference") == REFERENCE_ID
        and provider.get("normative_constraint") == MANDATORY_CONSTRAINT
    )

def single_writer_valid(writers_by_object: dict[str, list[str]]) -> bool:
    return all(len(set(writers)) <= 1 for writers in writers_by_object.values())

def single_committer_valid(committers: list[str]) -> bool:
    return len(set(committers)) <= 1

def atomic_message_publication_valid(*, one_file_per_message: bool, temp_then_atomic_rename: bool, shared_mailbox_file: bool) -> bool:
    return one_file_per_message and temp_then_atomic_rename and not shared_mailbox_file

def message_consumption_action(*, message_id: str, processed_ids: set[str], independent_cursor: bool) -> str:
    if not message_id or not independent_cursor:
        return "DENY"
    if message_id in processed_ids:
        return "NOOP"
    return "PROCESS"

def idempotent_consumption_valid(*, message_id: str, processed_ids: set[str], independent_cursor: bool) -> bool:
    return message_consumption_action(
        message_id=message_id,
        processed_ids=processed_ids,
        independent_cursor=independent_cursor,
    ) in {"PROCESS", "NOOP"}

def bounded_hops_valid(*, hops: int, max_hops: int, terminal_acts: set[str], act: str) -> bool:
    if max_hops <= 0 or hops < 0 or hops > max_hops:
        return False
    if act in terminal_acts:
        return True
    return hops < max_hops

def concurrent_workspace_isolation_valid(*, mutating_agents: list[str], workspace_by_agent: dict[str, str]) -> bool:
    if any(agent not in workspace_by_agent or not workspace_by_agent[agent] for agent in mutating_agents):
        return False
    return len({workspace_by_agent[a] for a in mutating_agents}) == len(mutating_agents)

def execution_authority_separation_valid(*, execution_provider: str, authority_owner: str) -> bool:
    if _is_munder(authority_owner):
        return False
    return bool(execution_provider and authority_owner)

def human_escalation_valid(*, risk_class: str, approved: bool) -> bool:
    critical = {"DESTRUCTIVE", "SPEND", "SCOPE_CHANGE", "UNRESOLVED_CONFLICT", "RELEASE", "CREDENTIAL"}
    return approved if risk_class in critical else True

def circuit_breaker_valid(*, states: list[str], deterministic_termination: bool) -> bool:
    required = ["STEER", "CONSTRAIN", "TERMINATE"]
    pos = 0
    for state in states:
        if pos < len(required) and state == required[pos]:
            pos += 1
    return pos == len(required) and deterministic_termination

def telemetry_allowlist_valid(*, properties: dict[str, Any], allowed_properties: set[str], sensitive_properties: set[str], free_form_allowed: bool) -> bool:
    keys = set(properties)
    return not free_form_allowed and keys <= allowed_properties and not (keys & sensitive_properties)

def context_authority_valid(*, trust_class: str, grants_authority: bool) -> bool:
    return trust_class in {"UNTRUSTED_SCOPED_CONTEXT", "PROVIDER_LOCAL_WORKING_MEMORY"} and not grants_authority

def transition_evidence_valid(*, mechanism_present: bool, transition_exercised: bool, evidence_status: str) -> bool:
    return mechanism_present and transition_exercised and evidence_status == "PASS"

def fault_injection_valid(*, unreachable_in_happy_path: bool, explicit_fault_injection: bool, evidence_status: str) -> bool:
    if not unreachable_in_happy_path:
        return evidence_status == "PASS"
    return explicit_fault_injection and evidence_status == "PASS"

def worker_cleanup_valid(*, processes: int, worktrees: int, active_leases: int, pending_messages: int) -> bool:
    return processes == 0 and worktrees == 0 and active_leases == 0 and pending_messages == 0

def capability_state_valid(*, state: str, executable_evidence: bool) -> bool:
    allowed = {"DESIGNED", "IMPLEMENTED", "VERIFIED"}
    if state not in allowed:
        return False
    if state == "VERIFIED":
        return executable_evidence
    return True

def disabled_provider_valid(*, enabled: bool, resident_processes: int, background_pollers: int, active_leases: int) -> bool:
    if enabled:
        return True
    return resident_processes == 0 and background_pollers == 0 and active_leases == 0

def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    canonical = root / "canonical"
    for path in sorted(canonical.rglob("*.json")) if canonical.exists() else []:
        scanned += 1
        try:
            data = _load(path)
        except Exception as exc:
            findings.append(_finding("MUNDER-AUTH-000", "Canonical JSON parse failure", file=str(path), error=str(exc)))
            continue
        def walk(value: Any, trail: str = "$", munder_scope: bool = False) -> None:
            nonlocal findings
            if isinstance(value, dict):
                local_scope = munder_scope or _is_munder({k: value[k] for k in ("id","provider_id","name","provider") if k in value})
                if local_scope and value.get("architectural_authority") is True:
                    findings.append(_finding("MUNDER-AUTH-001", "Munder architectural authority enabled", file=str(path.relative_to(root)), path=trail))
                for key, item in value.items():
                    nk = key.lower().replace("-", "_")
                    if ("authority" in nk or nk in PROHIBITED_AUTHORITY_MARKERS) and _is_munder(item):
                        findings.append(_finding("MUNDER-AUTH-002", "Munder assigned to authority-bearing field", file=str(path.relative_to(root)), path=f"{trail}.{key}"))
                    if key == "authority_boundaries" and isinstance(item, dict):
                        for domain, owner in item.items():
                            if _is_munder(owner):
                                findings.append(_finding("MUNDER-AUTH-003", "Munder owns an external authority boundary", file=str(path.relative_to(root)), path=f"{trail}.{key}.{domain}"))
                    walk(item, f"{trail}.{key}", local_scope)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    walk(item, f"{trail}[{i}]", munder_scope)
        walk(data)
    if not canonical.exists():
        findings.append(_finding("MUNDER-AUTH-004", "canonical directory missing"))
    return {"result": "PASS" if not findings else "FAIL", "scanned_json_files": scanned, "findings": findings}

def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-MUNDER-DIFFLIN-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-MUNDER-DIFFLIN-2026-08-30.json",
        "reference": root / "canonical/references/FA3-MUNDER-DIFFLIN-UPSTREAM-REFERENCE-2026-08-30.json",
        "enforcement": root / "canonical/munder-difflin-enforcement.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    for name, path in paths.items():
        if not path.exists():
            findings.append(_finding("MUNDER-REF-001", f"Missing {name} artifact", path=str(path.relative_to(root))))
    if findings:
        return {"result": "FAIL", "findings": findings}
    provider = _load(paths["provider"])
    decision = _load(paths["decision"])
    reference = _load(paths["reference"])
    enforcement = _load(paths["enforcement"])
    policy = _load(paths["policy"])
    if not provider_shape_valid(provider):
        findings.append(_finding("MUNDER-REF-002", "Provider shape or authority invariant drift"))
    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("mandatory_constraint") == MANDATORY_CONSTRAINT
    ):
        findings.append(_finding("MUNDER-REF-003", "Decision invariant drift"))
    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("latest_release") == REFERENCE_RELEASE
        and reference.get("latest_release_commit") == REFERENCE_RELEASE_COMMIT
        and reference.get("observed_main_commit") == REFERENCE_MAIN_COMMIT
        and reference.get("promotion_evidence") is False
        and reference.get("floating_main_allowed_as_promotion_evidence") is False
        and reference.get("security_support_scope") == "MAIN_ONLY_EARLY_PROTOTYPE"
    ):
        findings.append(_finding("MUNDER-REF-004", "Upstream reference pin or security-support scope drift"))
    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("provider_id") == PROVIDER_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("runtime_provider_required_for_global_promotion") is False
        and enforcement.get("p0_invariants") == P0_RULES
        and enforcement.get("mandatory_rule_count") == len(P0_RULES)
        and enforcement.get("mandatory_constraint") == MANDATORY_CONSTRAINT
    ):
        findings.append(_finding("MUNDER-REF-005", "Enforcement invariant drift"))
    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("MUNDER-REF-006", "Munder gate not bound to global enforcement policy"))
    if policy.get("munder_difflin_provider_id") != PROVIDER_ID:
        findings.append(_finding("MUNDER-REF-007", "Global Munder provider identity drift"))
    if policy.get("munder_difflin_mandatory_p0_rules") != P0_RULES:
        findings.append(_finding("MUNDER-REF-008", "Global Munder P0 rule set drift"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}

def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    def add(rule: str, name: str, positive: bool, negative: bool) -> None:
        cases.append({"rule_id": rule, "name": name, "status": "PASS" if positive and negative else "FAIL",
                      "positive_case": positive, "negative_case": negative})
    add(P0_RULES[0], "execution provider cannot become authority",
        execution_authority_separation_valid(execution_provider=PROVIDER_ID, authority_owner="FA3-AUTH-SECURITY-GOV-001"),
        not execution_authority_separation_valid(execution_provider=PROVIDER_ID, authority_owner=PROVIDER_ID))
    add(P0_RULES[1], "single writer per coordination object",
        single_writer_valid({"board":["scribe"],"task-1":["agent-a"]}),
        not single_writer_valid({"board":["a","b"]}))
    add(P0_RULES[2], "single committer repository mutation",
        single_committer_valid(["integration","integration"]),
        not single_committer_valid(["agent-a","agent-b"]))
    add(P0_RULES[3], "atomic one-file-per-message publication",
        atomic_message_publication_valid(one_file_per_message=True,temp_then_atomic_rename=True,shared_mailbox_file=False),
        not atomic_message_publication_valid(one_file_per_message=False,temp_then_atomic_rename=False,shared_mailbox_file=True))
    duplicate_noop = message_consumption_action(message_id="m1",processed_ids={"m1"},independent_cursor=True) == "NOOP"
    add(P0_RULES[4], "idempotent message consumption with independent cursor",
        idempotent_consumption_valid(message_id="m1",processed_ids={"m0"},independent_cursor=True) and duplicate_noop,
        not idempotent_consumption_valid(message_id="",processed_ids=set(),independent_cursor=False))
    add(P0_RULES[5], "bounded agent message hops",
        bounded_hops_valid(hops=2,max_hops=4,terminal_acts={"inform","done"},act="request"),
        not bounded_hops_valid(hops=5,max_hops=4,terminal_acts={"inform","done"},act="request"))
    add(P0_RULES[6], "concurrent mutating workspace isolation",
        concurrent_workspace_isolation_valid(mutating_agents=["a","b"],workspace_by_agent={"a":"wt-a","b":"wt-b"}),
        not concurrent_workspace_isolation_valid(mutating_agents=["a","b"],workspace_by_agent={"a":"wt","b":"wt"}))
    add(P0_RULES[7], "critical action human escalation",
        human_escalation_valid(risk_class="READ_ONLY",approved=False),
        not human_escalation_valid(risk_class="DESTRUCTIVE",approved=False))
    add(P0_RULES[8], "progressive circuit breaker terminates deterministically",
        circuit_breaker_valid(states=["NORMAL","STEER","CONSTRAIN","TERMINATE"],deterministic_termination=True),
        not circuit_breaker_valid(states=["NORMAL","STEER","CONSTRAIN"],deterministic_termination=False))
    add(P0_RULES[9], "telemetry hard allowlist rejects sensitive/free-form fields",
        telemetry_allowlist_valid(properties={"provider":"codex"},allowed_properties={"provider","app_version"},sensitive_properties={"prompt","path","repo","secret"},free_form_allowed=False),
        not telemetry_allowlist_valid(properties={"provider":"codex","prompt":"x"},allowed_properties={"provider","app_version"},sensitive_properties={"prompt","path","repo","secret"},free_form_allowed=True))
    add(P0_RULES[10], "memory/imported context cannot grant authority",
        context_authority_valid(trust_class="UNTRUSTED_SCOPED_CONTEXT",grants_authority=False),
        not context_authority_valid(trust_class="TRUSTED_POLICY",grants_authority=True))
    add(P0_RULES[11], "lifecycle evidence must exercise the transition",
        transition_evidence_valid(mechanism_present=True,transition_exercised=True,evidence_status="PASS"),
        not transition_evidence_valid(mechanism_present=True,transition_exercised=False,evidence_status="PASS"))
    add(P0_RULES[12], "unreachable failure path requires fault injection",
        fault_injection_valid(unreachable_in_happy_path=True,explicit_fault_injection=True,evidence_status="PASS"),
        not fault_injection_valid(unreachable_in_happy_path=True,explicit_fault_injection=False,evidence_status="PASS"))
    add(P0_RULES[13], "ephemeral worker teardown releases all state",
        worker_cleanup_valid(processes=0,worktrees=0,active_leases=0,pending_messages=0),
        not worker_cleanup_valid(processes=1,worktrees=0,active_leases=0,pending_messages=0))
    add(P0_RULES[14], "designed implemented verified states remain distinct",
        capability_state_valid(state="VERIFIED",executable_evidence=True),
        not capability_state_valid(state="VERIFIED",executable_evidence=False))
    add(P0_RULES[15], "disabled provider creates no runtime dependency",
        disabled_provider_valid(enabled=False,resident_processes=0,background_pollers=0,active_leases=0),
        not disabled_provider_valid(enabled=False,resident_processes=1,background_pollers=0,active_leases=0))
    passed = sum(c["status"] == "PASS" for c in cases)
    return {"schema":"fa3.munder-difflin-regression-report.v1","result":"PASS" if passed == len(cases) else "FAIL",
            "passed":passed,"total":len(cases),"cases":cases}

def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    authority_scan = scan_canonical_authority_assignments(root)
    regressions = run_regressions()
    ok = reference["result"] == authority_scan["result"] == regressions["result"] == "PASS"
    report = {
        "schema":"fa3.munder-difflin-gate-report.v1",
        "gate_id":GATE_ID,
        "provider_id":PROVIDER_ID,
        "capability_count":CAPABILITY_COUNT,
        "result":"PASS" if ok else "FAIL",
        "reference":reference,
        "authority_scan":authority_scan,
        "regressions":regressions,
        "runtime_provider_required":False,
        "runtime_activation_status":"NOT_PROMOTED_REFERENCE_ONLY",
        "promotion_effect":"MANDATORY_COORDINATION_INVARIANTS_PROVIDER_RUNTIME_OPTIONAL",
    }
    _write(root / "reports/munder-difflin-gate-report.json", report)
    return report

def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Munder Difflin provider-neutral multi-agent coordination gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
