#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-OPENHANDS-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-OPENHANDS-001"
PROVIDER_ID = "FA3-PROVIDER-OPENHANDS-001"
CONTRACT_ID = "FA3-OPENHANDS-DEVELOPER-EXECUTION-CONTRACTS-001"
DECISION_ID = "FA3-DEC-OPENHANDS-2026-09-01"
REFERENCE_ID = "FA3-OPENHANDS-UPSTREAM-REFERENCE-2026-09-01"
EVIDENCE_ID = "FA3-EVIDENCE-OPENHANDS-CI-2026-09-01"
CAPABILITY_COUNT = 143
PINNED_COMMIT = "a9e0a8a1aab2164b46bae00a18157a343aaa94c9"
PINNED_COMPONENT_VERSION = "1.44.1"
RUNTIME_STATUS = "MATERIALIZED_CURRENT_HOST_E2E_PENDING"

P0_RULES = [
    "OPENHANDS_PROVIDER_NOT_AUTHORITY",
    "OPENHANDS_AGENT_APPLICATION_LAYER_SEPARATION",
    "OPENHANDS_TYPED_SERIALIZABLE_AGENT_CONFIG_REQUIRED",
    "OPENHANDS_SINGLE_EXECUTION_STATE_PROJECTION",
    "OPENHANDS_APPEND_ONLY_ACTION_OBSERVATION_TRAJECTORY",
    "OPENHANDS_CRASH_SAFE_RESUME_FROM_COMMITTED_STATE",
    "OPENHANDS_REPLAY_SIDE_EFFECT_REEXECUTION_FORBIDDEN",
    "OPENHANDS_TOOL_EXECUTION_REQUIRES_CANONICAL_MEDIATION",
    "OPENHANDS_DIRECT_EXECUTE_TOOL_BYPASS_FORBIDDEN",
    "OPENHANDS_MCP_DISCOVERY_AND_EXECUTION_BEHIND_CENTRAL_GATEWAY",
    "OPENHANDS_SECURITY_ANALYZER_SIGNAL_NOT_AUTHORITY",
    "OPENHANDS_CONFIRMATION_POLICY_CANNOT_WEAKEN_FA3_POLICY",
    "OPENHANDS_WORKSPACE_NOT_PLACEMENT_OR_ISOLATION_AUTHORITY",
    "OPENHANDS_LOCAL_UNISOLATED_EXECUTION_REQUIRES_EXPLICIT_ADMISSION",
    "OPENHANDS_SECRET_VALUES_NOT_PROVIDER_PERSISTED",
    "OPENHANDS_COMPONENT_VERSION_TUPLE_IMMUTABLY_PINNED",
    "OPENHANDS_SUBAGENT_CAPABILITIES_MONOTONIC_NARROWING",
    "OPENHANDS_EXECUTION_EVIDENCE_EXPORTED_VIA_CANONICAL_AUTHORITY",
    "OPENHANDS_CURRENT_HOST_PROMOTION_REQUIRES_REAL_E2E",
    "OPENHANDS_DISABLED_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST",
]

PATHS = {
    "provider": "canonical/providers/FA3-PROVIDER-OPENHANDS-001.json",
    "contract": "canonical/contracts/FA3-OPENHANDS-DEVELOPER-EXECUTION-CONTRACTS-001.json",
    "decision": "canonical/decisions/FA3-DEC-OPENHANDS-2026-09-01.json",
    "reference": "canonical/references/FA3-OPENHANDS-UPSTREAM-REFERENCE-2026-09-01.json",
    "gate_record": "canonical/FA3-GATE-OPENHANDS-001.json",
    "enforcement": "canonical/openhands-enforcement.json",
    "admission": "canonical/openhands-runtime-admission.json",
    "evidence": "evidence/reference/openhands-ci-2026-09-01.json",
    "policy": "canonical/enforcement-policy.json",
    "runtime_conformance": "canonical/FA3-OPENHANDS-RUNTIME-CONFORMANCE-001.json",
    "current_host_enforcement": "canonical/openhands-current-host-enforcement.json",
    "current_host_decision": "canonical/decisions/FA3-DEC-OPENHANDS-CURRENT-HOST-2026-09-03.json",
}

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}

def provider_not_authority(*, canonical_root: bool, architectural_authority: bool, authority_owner: str) -> bool:
    return not canonical_root and not architectural_authority and authority_owner != PROVIDER_ID

def layer_separation_valid(*, agent_core: str, application: str, workspace: str, agent_server: str) -> bool:
    return all(x and x != "SAME_AUTHORITY" for x in (agent_core, application, workspace, agent_server)) and len({agent_core, application, workspace, agent_server}) == 4

def typed_config_valid(*, typed: bool, serializable: bool, versioned: bool, authority_inferred: bool) -> bool:
    return typed and serializable and versioned and not authority_inferred

def execution_state_projection_valid(*, single_projection: bool, canonical_authority_external: bool) -> bool:
    return single_projection and canonical_authority_external

def append_only_trajectory_valid(events: list[dict[str, Any]]) -> bool:
    if not events:
        return False
    seqs = [e.get("seq") for e in events]
    ids = [e.get("event_id") for e in events]
    kinds = [e.get("kind") for e in events]
    return seqs == list(range(1, len(events) + 1)) and len(ids) == len(set(ids)) and all(ids) and all(k in {"ACTION", "OBSERVATION"} for k in kinds)

def crash_resume_valid(*, committed_cursor: int, resume_cursor: int, state_committed: bool) -> bool:
    return state_committed and committed_cursor >= 0 and resume_cursor == committed_cursor

def replay_side_effect_valid(*, external_side_effect: bool, reexecute: bool, replay_mode: str, idempotency_key: str | None) -> bool:
    if not external_side_effect:
        return True
    return not reexecute and replay_mode in {"SKIP", "VERIFY", "IDEMPOTENT_APPLY"} and (replay_mode != "IDEMPOTENT_APPLY" or bool(idempotency_key))

def canonical_tool_mediation_valid(*, canonical_mediated: bool, authorized: bool) -> bool:
    return canonical_mediated and authorized

def direct_execute_tool_valid(*, api: str, canonical_mediated: bool) -> bool:
    if api == "conversation.execute_tool":
        return canonical_mediated
    return True

def mcp_projection_valid(*, discovered: bool, canonical_gateway: bool, auto_authorized: bool) -> bool:
    return (not discovered) or (canonical_gateway and not auto_authorized)

def security_signal_valid(*, analyzer_is_authority: bool, advisory_signal: bool) -> bool:
    return advisory_signal and not analyzer_is_authority

def confirmation_policy_valid(*, fa3_authorized: bool, provider_confirmed: bool, execution_allowed: bool) -> bool:
    expected = fa3_authorized and provider_confirmed
    return execution_allowed == expected

def workspace_authority_valid(*, provider_selects_placement: bool, provider_selects_isolation: bool) -> bool:
    return not provider_selects_placement and not provider_selects_isolation

def local_unisolated_admission_valid(*, local_unisolated: bool, explicit_admission: bool, bounded_scope: bool) -> bool:
    return (not local_unisolated) or (explicit_admission and bounded_scope)

def secret_persistence_valid(*, raw_secret_values: list[str], secret_reference_handles: list[str], redacted: bool) -> bool:
    return not raw_secret_values and redacted and all(x.startswith("secret-ref:") for x in secret_reference_handles)

def component_tuple_valid(component_tuple: dict[str, str]) -> bool:
    required = {
        "commit": PINNED_COMMIT,
        "openhands-sdk": PINNED_COMPONENT_VERSION,
        "openhands-agent-server": PINNED_COMPONENT_VERSION,
        "openhands-tools": PINNED_COMPONENT_VERSION,
        "openhands-workspace": PINNED_COMPONENT_VERSION,
    }
    return all(component_tuple.get(k) == v for k, v in required.items()) and all(component_tuple.get(k) not in {"latest", "main", "*", "floating", ""} for k in required)

def subagent_narrowing_valid(*, parent: set[str], child: set[str], authority_expansion: bool) -> bool:
    return child <= parent and not authority_expansion

def evidence_export_valid(*, provider_log_authoritative: bool, exported_via_canonical_authority: bool) -> bool:
    return not provider_log_authoritative and exported_via_canonical_authority

def current_host_promotion_valid(*, reference_ci_pass: bool, real_current_host_e2e_pass: bool, claims_current_host: bool) -> bool:
    return claims_current_host == real_current_host_e2e_pass and (not claims_current_host or real_current_host_e2e_pass)

def disabled_provider_valid(*, enabled: bool, resident_processes: int, background_agents: int, active_leases: int) -> bool:
    return enabled or (resident_processes == 0 and background_agents == 0 and active_leases == 0)

def provider_shape_valid(provider: dict[str, Any]) -> bool:
    tuple_ = provider.get("immutable_component_tuple", {})
    return (
        provider.get("id") == PROVIDER_ID
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("capability_projection") == ["CAP-028"]
        and provider.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT"
        and provider.get("global_runtime_promotion_required_when_disabled") is False
        and provider.get("runtime_activation_requires_current_host_conformance") is True
        and provider.get("runtime_activation_status") == RUNTIME_STATUS
        and provider.get("current_host_runtime_evidence") == "PENDING_REAL_CURRENT_HOST_EXECUTION"
        and provider.get("runtime_conformance") == "FA3-OPENHANDS-RUNTIME-CONFORMANCE-001"
        and provider.get("current_host_gate") == "FA3-OPENHANDS-CURRENT-HOST-GATESET-001"
        and provider.get("contract") == CONTRACT_ID
        and component_tuple_valid(tuple_)
    )

def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    canonical = root / "canonical"
    scanned = 0
    if not canonical.exists():
        return {"result": "FAIL", "scanned_json_files": 0, "findings": [_finding("OPENHANDS-AUTH-000", "canonical directory missing")]}

    def walk(value: Any, *, path: str, file_path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_path = f"{path}.{key}"
                normalized = key.lower().replace("-", "_")
                if "authority" in normalized and isinstance(item, str) and item == PROVIDER_ID:
                    findings.append(_finding("OPENHANDS-AUTH-001", "OpenHands assigned to authority-bearing field", file=file_path, path=key_path))
                if key == "authority_boundaries" and isinstance(item, dict):
                    for domain, owner in item.items():
                        if owner == PROVIDER_ID:
                            findings.append(_finding("OPENHANDS-AUTH-002", "OpenHands owns an FA3 authority boundary", file=file_path, path=f"{key_path}.{domain}"))
                walk(item, path=key_path, file_path=file_path)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, path=f"{path}[{i}]", file_path=file_path)

    for path in sorted(canonical.rglob("*.json")):
        scanned += 1
        try:
            walk(_load(path), path="$", file_path=str(path.relative_to(root)))
        except Exception as exc:
            findings.append(_finding("OPENHANDS-AUTH-003", "canonical JSON parse failure during OpenHands authority scan", file=str(path.relative_to(root)), error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL", "scanned_json_files": scanned, "findings": findings}

def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    loaded: dict[str, dict[str, Any]] = {}
    for name, rel in PATHS.items():
        path = root / rel
        if not path.is_file():
            findings.append(_finding("OPENHANDS-REF-001", "required OpenHands canonical file missing", path=rel))
            continue
        try:
            loaded[name] = _load(path)
        except Exception as exc:
            findings.append(_finding("OPENHANDS-REF-002", "required OpenHands JSON invalid", path=rel, error=str(exc)))
    if findings:
        return {"result": "FAIL", "findings": findings}

    provider, contract, decision = loaded["provider"], loaded["contract"], loaded["decision"]
    reference, enforcement, admission = loaded["reference"], loaded["enforcement"], loaded["admission"]
    evidence, policy, gate_record = loaded["evidence"], loaded["policy"], loaded["gate_record"]

    runtime_conformance = loaded["runtime_conformance"]
    current_host_enforcement = loaded["current_host_enforcement"]
    current_host_decision = loaded["current_host_decision"]
    required_materialized_surfaces = [
        "src/fa3_openhands_adapter.py",
        "src/fa3_openhands_router_bridge.py",
        "src/fa3_openhands_current_host_worker.py",
        "src/fa3_openhands_current_host_gate.py",
        "evidence/collect-openhands-current-host.py",
        "bin/fa3-openhands-bootstrap.sh",
        "bin/fa3-openhands-current-host.sh",
        "tests/test_openhands_current_host.py",
        ".github/workflows/fa3-openhands-current-host.yml",
    ]
    missing_materialized_surfaces = [
        rel for rel in required_materialized_surfaces if not (root / rel).is_file()
    ]
    if missing_materialized_surfaces:
        findings.append(
            _finding(
                "OPENHANDS-REF-015",
                "OpenHands current-host materialization surface incomplete",
                missing=missing_materialized_surfaces,
            )
        )
    if not (
        runtime_conformance.get("id") == "FA3-OPENHANDS-RUNTIME-CONFORMANCE-001"
        and runtime_conformance.get("provider_id") == PROVIDER_ID
        and runtime_conformance.get("status") == RUNTIME_STATUS
        and runtime_conformance.get("capability_count") == CAPABILITY_COUNT
        and runtime_conformance.get("evidence_levels", {}).get("production_e2e", {}).get("status")
        == "PENDING_REAL_CURRENT_HOST_EXECUTION"
    ):
        findings.append(_finding("OPENHANDS-REF-016", "OpenHands runtime conformance materialization drift"))
    if not (
        current_host_enforcement.get("id") == "FA3-OPENHANDS-CURRENT-HOST-GATESET-001"
        and current_host_enforcement.get("gate_id") == "FA3-GATE-OPENHANDS-CURRENT-HOST-001"
        and current_host_enforcement.get("provider_id") == PROVIDER_ID
        and current_host_enforcement.get("fail_closed") is True
        and current_host_enforcement.get("production_pass_requires_real_model_route") is True
        and current_host_enforcement.get("fixture_runtime_smoke_cannot_promote_production") is True
    ):
        findings.append(_finding("OPENHANDS-REF-017", "OpenHands current-host enforcement drift"))
    if not (
        current_host_decision.get("id") == "FA3-DEC-OPENHANDS-CURRENT-HOST-2026-09-03"
        and current_host_decision.get("status") == "CANONICAL_CLOSED"
        and current_host_decision.get("provider_id") == PROVIDER_ID
        and current_host_decision.get("admission_state") == RUNTIME_STATUS
        and current_host_decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(_finding("OPENHANDS-REF-018", "OpenHands current-host decision drift"))

    if not provider_shape_valid(provider):
        findings.append(_finding("OPENHANDS-REF-003", "provider shape/component tuple drift"))
    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("version") == "1.1.0"
        and contract.get("status") == "CANONICAL"
        and contract.get("provider_neutral") is True
        and contract.get("new_capability") is False
        and contract.get("new_architectural_authority") is False
        and contract.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append(_finding("OPENHANDS-REF-004", "developer execution contract drift"))
    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("contract_id") == CONTRACT_ID
        and decision.get("mandatory_p0_rules") == P0_RULES
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(_finding("OPENHANDS-REF-005", "decision semantics drift"))
    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("immutable_observed_commit") == PINNED_COMMIT
        and set(reference.get("component_versions", {}).values()) == {PINNED_COMPONENT_VERSION}
        and reference.get("promotion_evidence") is False
        and reference.get("floating_main_allowed_as_promotion_evidence") is False
    ):
        findings.append(_finding("OPENHANDS-REF-006", "upstream reference identity/version drift"))
    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("executable_gate_id") == EXECUTABLE_GATE_ID
        and enforcement.get("p0_invariants") == P0_RULES
        and enforcement.get("mandatory_rule_count") == 20
        and enforcement.get("fail_closed") is True
    ):
        findings.append(_finding("OPENHANDS-REF-007", "enforcement rule set drift"))
    if not (
        gate_record.get("id") == EXECUTABLE_GATE_ID
        and gate_record.get("gate_set_id") == GATE_ID
        and gate_record.get("rule_count") == 20
        and gate_record.get("fail_closed") is True
    ):
        findings.append(_finding("OPENHANDS-REF-008", "gate record drift"))
    if not (
        admission.get("provider_id") == PROVIDER_ID
        and admission.get("status") == RUNTIME_STATUS
        and admission.get("materialization_status") == RUNTIME_STATUS
        and admission.get("current_host_runtime_evidence") == "PENDING_REAL_CURRENT_HOST_EXECUTION"
        and admission.get("production_provider_admission") is False
        and admission.get("runtime_conformance_id") == "FA3-OPENHANDS-RUNTIME-CONFORMANCE-001"
        and admission.get("current_host_gate_id") == "FA3-OPENHANDS-CURRENT-HOST-GATESET-001"
    ):
        findings.append(_finding("OPENHANDS-REF-009", "runtime admission incorrectly promoted"))
    if not (
        evidence.get("id") == EVIDENCE_ID
        and evidence.get("provider_id") == PROVIDER_ID
        and evidence.get("contract_id") == CONTRACT_ID
        and evidence.get("gate_id") == GATE_ID
        and evidence.get("status") == "PASS"
        and evidence.get("regression_cases_total") == 20
        and evidence.get("regression_cases_passed") == 20
        and evidence.get("current_host_provider_runtime_evidence") is False
        and evidence.get("current_host_runtime_promotion_claim") is False
        and evidence.get("production_provider_admission_claim") is False
    ):
        findings.append(_finding("OPENHANDS-REF-010", "reference evidence semantics drift"))
    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("OPENHANDS-REF-011", "OpenHands gate missing from global enforcement policy"))
    if policy.get("openhands_provider_id") != PROVIDER_ID:
        findings.append(_finding("OPENHANDS-REF-012", "global OpenHands provider identity drift"))
    if policy.get("openhands_contract_id") != CONTRACT_ID:
        findings.append(_finding("OPENHANDS-REF-013", "global OpenHands contract identity drift"))
    if policy.get("openhands_mandatory_p0_rules") != P0_RULES:
        findings.append(_finding("OPENHANDS-REF-014", "global OpenHands P0 rule set drift"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}

def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    def add(rule: str, name: str, positive: bool, negative: bool) -> None:
        cases.append({"rule_id": rule, "name": name, "status": "PASS" if positive and negative else "FAIL", "positive_case": bool(positive), "negative_case": bool(negative)})

    add(P0_RULES[0], "provider cannot become authority",
        provider_not_authority(canonical_root=False, architectural_authority=False, authority_owner="FA3-AUTH-SECURITY-GOV-001"),
        not provider_not_authority(canonical_root=False, architectural_authority=True, authority_owner=PROVIDER_ID))
    add(P0_RULES[1], "agent/application/workspace/server layers remain separate",
        layer_separation_valid(agent_core="agent", application="app", workspace="workspace", agent_server="server"),
        not layer_separation_valid(agent_core="agent", application="agent", workspace="workspace", agent_server="server"))
    add(P0_RULES[2], "agent configuration is typed serializable versioned and non-authoritative",
        typed_config_valid(typed=True, serializable=True, versioned=True, authority_inferred=False),
        not typed_config_valid(typed=True, serializable=True, versioned=False, authority_inferred=True))
    add(P0_RULES[3], "single execution-state projection with external canonical authority",
        execution_state_projection_valid(single_projection=True, canonical_authority_external=True),
        not execution_state_projection_valid(single_projection=False, canonical_authority_external=False))
    good_events=[{"event_id":"e1","seq":1,"kind":"ACTION"},{"event_id":"e2","seq":2,"kind":"OBSERVATION"}]
    bad_events=[{"event_id":"e1","seq":1,"kind":"ACTION"},{"event_id":"e1","seq":3,"kind":"OBSERVATION"}]
    add(P0_RULES[4], "append-only action/observation trajectory", append_only_trajectory_valid(good_events), not append_only_trajectory_valid(bad_events))
    add(P0_RULES[5], "crash resume from committed state", crash_resume_valid(committed_cursor=7,resume_cursor=7,state_committed=True), not crash_resume_valid(committed_cursor=7,resume_cursor=8,state_committed=True))
    add(P0_RULES[6], "replay cannot blindly reexecute external side effects",
        replay_side_effect_valid(external_side_effect=True,reexecute=False,replay_mode="VERIFY",idempotency_key=None),
        not replay_side_effect_valid(external_side_effect=True,reexecute=True,replay_mode="APPLY",idempotency_key=None))
    add(P0_RULES[7], "tool execution requires canonical mediation",
        canonical_tool_mediation_valid(canonical_mediated=True,authorized=True),
        not canonical_tool_mediation_valid(canonical_mediated=False,authorized=True))
    add(P0_RULES[8], "direct execute_tool bypass is denied unless canonically mediated",
        direct_execute_tool_valid(api="conversation.execute_tool",canonical_mediated=True),
        not direct_execute_tool_valid(api="conversation.execute_tool",canonical_mediated=False))
    add(P0_RULES[9], "MCP discovery/execution stays behind central gateway",
        mcp_projection_valid(discovered=True,canonical_gateway=True,auto_authorized=False),
        not mcp_projection_valid(discovered=True,canonical_gateway=False,auto_authorized=True))
    add(P0_RULES[10], "security analyzer is advisory signal only",
        security_signal_valid(analyzer_is_authority=False,advisory_signal=True),
        not security_signal_valid(analyzer_is_authority=True,advisory_signal=True))
    add(P0_RULES[11], "provider confirmation cannot weaken FA3 policy",
        confirmation_policy_valid(fa3_authorized=True,provider_confirmed=True,execution_allowed=True),
        not confirmation_policy_valid(fa3_authorized=False,provider_confirmed=True,execution_allowed=True))
    add(P0_RULES[12], "workspace cannot own placement/isolation",
        workspace_authority_valid(provider_selects_placement=False,provider_selects_isolation=False),
        not workspace_authority_valid(provider_selects_placement=True,provider_selects_isolation=True))
    add(P0_RULES[13], "local unisolated execution requires explicit bounded admission",
        local_unisolated_admission_valid(local_unisolated=True,explicit_admission=True,bounded_scope=True),
        not local_unisolated_admission_valid(local_unisolated=True,explicit_admission=False,bounded_scope=False))
    add(P0_RULES[14], "raw secret values are not provider-persisted",
        secret_persistence_valid(raw_secret_values=[],secret_reference_handles=["secret-ref:model-key"],redacted=True),
        not secret_persistence_valid(raw_secret_values=["sk-secret"],secret_reference_handles=[],redacted=False))
    good_tuple={"commit":PINNED_COMMIT,"openhands-sdk":PINNED_COMPONENT_VERSION,"openhands-agent-server":PINNED_COMPONENT_VERSION,"openhands-tools":PINNED_COMPONENT_VERSION,"openhands-workspace":PINNED_COMPONENT_VERSION}
    bad_tuple=dict(good_tuple); bad_tuple["commit"]="main"
    add(P0_RULES[15], "component tuple is immutable and exact", component_tuple_valid(good_tuple), not component_tuple_valid(bad_tuple))
    add(P0_RULES[16], "subagent capabilities narrow monotonically",
        subagent_narrowing_valid(parent={"read","edit","test"},child={"read","test"},authority_expansion=False),
        not subagent_narrowing_valid(parent={"read"},child={"read","edit"},authority_expansion=True))
    add(P0_RULES[17], "execution evidence exports through canonical authority",
        evidence_export_valid(provider_log_authoritative=False,exported_via_canonical_authority=True),
        not evidence_export_valid(provider_log_authoritative=True,exported_via_canonical_authority=False))
    add(P0_RULES[18], "reference CI cannot claim current-host promotion",
        current_host_promotion_valid(reference_ci_pass=True,real_current_host_e2e_pass=False,claims_current_host=False),
        not current_host_promotion_valid(reference_ci_pass=True,real_current_host_e2e_pass=False,claims_current_host=True))
    add(P0_RULES[19], "disabled provider has zero/near-zero runtime cost",
        disabled_provider_valid(enabled=False,resident_processes=0,background_agents=0,active_leases=0),
        not disabled_provider_valid(enabled=False,resident_processes=1,background_agents=1,active_leases=0))
    passed=sum(c["status"]=="PASS" for c in cases)
    return {"schema":"fa3.openhands-regression-report.v1","result":"PASS" if passed==len(cases) else "FAIL","passed":passed,"total":len(cases),"cases":cases}

def gate(root: Path) -> dict[str, Any]:
    reference=reference_check(root)
    authority=scan_canonical_authority_assignments(root)
    regressions=run_regressions()
    ok=reference["result"]==authority["result"]==regressions["result"]=="PASS"
    report={"schema":"fa3.openhands-gate-report.v1","gate_id":GATE_ID,"executable_gate_id":EXECUTABLE_GATE_ID,"provider_id":PROVIDER_ID,"contract_id":CONTRACT_ID,"capability_count":CAPABILITY_COUNT,"result":"PASS" if ok else "FAIL","reference":reference,"authority_scan":authority,"regressions":regressions,"runtime_provider_required":False,"current_host_provider_runtime_evidence":"PENDING_REAL_CURRENT_HOST_EXECUTION","runtime_activation_status":RUNTIME_STATUS,"promotion_effect":"MANDATORY_OPENHANDS_BOUNDARY_INVARIANTS_PROVIDER_RUNTIME_OPTIONAL"}
    _write(root/"reports/openhands-gate-report.json",report)
    return report

def main() -> int:
    parser=argparse.ArgumentParser(description="FA3 OpenHands developer-agent execution canonical gate")
    parser.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    args=parser.parse_args()
    report=gate(Path(args.root).resolve())
    print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
