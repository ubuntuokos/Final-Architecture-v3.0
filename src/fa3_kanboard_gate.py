#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-KANBOARD-001"
GATE_ID = "FA3-KANBOARD-GATESET-001"
DECISION_ID = "FA3-DEC-KANBOARD-2026-08-30"
REFERENCE_ID = "FA3-KANBOARD-UPSTREAM-REFERENCE-2026-08-30"
CAPABILITY_COUNT = 143
REFERENCE_RELEASE = "v1.2.54"
REFERENCE_COMMIT = "9ce6a5edc5b646ef15780cb445bc6d2c39d9898f"
MANDATORY_CONSTRAINT = "Kanboard SHALL NOT become an FA3 identity, authorization, MCP, workflow, event, evidence, secrets, network-egress, artifact-trust or canonical work-item authority."

P0_INVARIANTS = [
    "KANBOARD_STATE_TRANSITION_REQUIRES_SCOPED_AUTHORIZATION",
    "KANBOARD_EVENT_DOES_NOT_IMPLY_ACTION_AUTHORIZATION",
    "KANBOARD_INTEGRATION_CREDENTIAL_CANNOT_BYPASS_SCOPED_AUTHORIZATION",
    "KANBOARD_PROVIDER_NEUTRAL_WORK_ITEM_IDENTITY_REQUIRED",
    "KANBOARD_REMOTE_PROVIDER_STATE_RECONCILIATION_EXPLICIT",
    "KANBOARD_WEBHOOK_REQUIRES_TYPED_NORMALIZATION_AND_IS_NOT_EVIDENCE",
    "KANBOARD_PLUGIN_ADMISSION_REQUIRES_SUPPLY_CHAIN_EVIDENCE",
    "KANBOARD_PLUGIN_EXTENSIBILITY_DOES_NOT_GRANT_AUTHORITY",
    "KANBOARD_PROVIDER_URL_REQUIRES_CANONICAL_EGRESS_AUTHORIZATION",
    "KANBOARD_PROVIDER_FAILURE_MUST_NOT_REPLACE_CANONICAL_STATE",
    "KANBOARD_DISABLED_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST",
    "KANBOARD_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY"
]

EXPECTED_EXTERNAL_BOUNDARIES = {
    "identity": "EXISTING_FA3_IDENTITY_AUTHORITY_ONLY",
    "authorization_policy": "FA3-AUTH-SECURITY-GOV-001",
    "mcp_tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
    "workflow": "EXISTING_FA3_WORKFLOW_AUTHORITY_ONLY",
    "event": "EXISTING_FA3_EVENT_AUTHORITY_ONLY",
    "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
    "secrets": "EXISTING_FA3_SECRETS_AUTHORITY_ONLY",
    "network_egress": "EXISTING_FA3_NETWORK_EGRESS_AUTHORITY_ONLY",
    "artifact_trust": "FA3-REG-ARTIFACT-MODEL-001",
    "registry": "FA3-REGISTRY-001",
}

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}

def state_transition_authorized(*, caller_identity: str, project_scope: str, capability_scope: list[str],
                                current_state: str, requested_state: str, policy_authority: str,
                                policy_decision: str) -> bool:
    return bool(
        caller_identity and project_scope and capability_scope
        and "work_item.transition" in capability_scope
        and current_state and requested_state and current_state != requested_state
        and policy_authority == "FA3-AUTH-SECURITY-GOV-001"
        and policy_decision == "ALLOW"
    )

def event_action_allowed(*, event_validated: bool, event_type: str, action_capability: str,
                         actor_identity: str, project_scope: str, policy_authority: str,
                         policy_decision: str, event_implies_authorization: bool) -> bool:
    return bool(
        event_validated and event_type and action_capability and actor_identity and project_scope
        and policy_authority == "FA3-AUTH-SECURITY-GOV-001"
        and policy_decision == "ALLOW"
        and not event_implies_authorization
    )

def integration_credential_valid(*, global_application_credential: bool, actor_scoped_identity: str,
                                 project_scope: str, permission_checks_enforced: bool) -> bool:
    return bool(
        not global_application_credential
        and actor_scoped_identity and project_scope and permission_checks_enforced
    )

def work_item_projection_valid(*, canonical_work_item_id: str, provider_instance: str,
                               provider_object_id: str, sync_state: str,
                               provider_owns_canonical_identity: bool) -> bool:
    return bool(
        canonical_work_item_id and provider_instance and provider_object_id
        and sync_state in {"SYNCED", "PENDING", "CONFLICT", "STALE"}
        and not provider_owns_canonical_identity
    )

def remote_state_reconciliation_valid(*, provider_revision: str, observed_canonical_revision: str,
                                      reconciliation_state: str, provider_state_authoritative: bool) -> bool:
    return bool(
        provider_revision and observed_canonical_revision
        and reconciliation_state in {"SYNCED", "PENDING", "CONFLICT", "STALE"}
        and not provider_state_authoritative
    )

def webhook_projection_valid(*, authenticated: bool, validated: bool, typed_normalized: bool,
                             canonical_event_id: str, webhook_is_authorization: bool,
                             webhook_is_canonical_evidence: bool) -> bool:
    return bool(
        authenticated and validated and typed_normalized and canonical_event_id
        and not webhook_is_authorization and not webhook_is_canonical_evidence
    )

def plugin_admission_valid(*, source_identity: str, pinned_version: str, digest: str,
                           provenance_verified: bool, license_admitted: bool,
                           policy_admitted: bool, adhoc_web_install: bool) -> bool:
    return bool(
        source_identity and pinned_version and digest.startswith("sha256:")
        and provenance_verified and license_admitted and policy_admitted
        and not adhoc_web_install
    )

def plugin_authority_valid(*, grants_authority: bool, authority_owner: str) -> bool:
    return bool(
        not grants_authority
        and authority_owner
        and authority_owner not in {PROVIDER_ID, "KANBOARD_PLUGIN"}
    )

def provider_egress_valid(*, provider_configured_url: bool, canonical_egress_authorized: bool,
                          ssrf_controls: bool, dns_rebinding_controls: bool) -> bool:
    if not provider_configured_url:
        return True
    return bool(canonical_egress_authorized and ssrf_controls and dns_rebinding_controls)

def provider_failure_isolated(*, provider_available: bool, canonical_state_available: bool,
                              fail_open_to_provider_state: bool) -> bool:
    if provider_available:
        return bool(canonical_state_available and not fail_open_to_provider_state)
    return bool(canonical_state_available and not fail_open_to_provider_state)

def disabled_zero_cost(state: dict[str, Any]) -> bool:
    return bool(
        state.get("resident_process_count") == 0
        and state.get("background_worker_count") == 0
        and state.get("network_session_count") == 0
        and state.get("accelerator_reservation_count") == 0
        and state.get("active_polling") is False
        and state.get("background_fetch") is False
    )

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
        and provider.get("normative_constraint") == MANDATORY_CONSTRAINT
        and provider.get("authority_boundaries") == EXPECTED_EXTERNAL_BOUNDARIES
    )

def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0

    def walk(obj: Any, path: str, source: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                here = f"{path}.{key}" if path else key
                if isinstance(value, str) and value == PROVIDER_ID and (
                    key == "authority" or key.endswith("_authority")
                ):
                    findings.append(_finding(
                        "KANBOARD-AUTH-001",
                        "Kanboard was assigned a prohibited canonical authority role",
                        source=source, field=here,
                    ))
                walk(value, here, source)
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                walk(value, f"{path}[{idx}]", source)

    for path in sorted((root / "canonical").rglob("*.json")):
        scanned += 1
        try:
            walk(_load(path), "", str(path.relative_to(root)))
        except Exception as exc:
            findings.append(_finding(
                "KANBOARD-AUTH-002", "Unreadable canonical JSON during Kanboard authority scan",
                source=str(path.relative_to(root)), error=str(exc),
            ))

    provider_path = root / "canonical/providers/FA3-PROVIDER-KANBOARD-001.json"
    if provider_path.exists():
        provider = _load(provider_path)
        if any(value == PROVIDER_ID for value in provider.get("authority_boundaries", {}).values()):
            findings.append(_finding(
                "KANBOARD-AUTH-003",
                "Kanboard authority-boundary owner escalation detected",
            ))
        if provider.get("architectural_authority") is not False or provider.get("canonical_root") is not False:
            findings.append(_finding(
                "KANBOARD-AUTH-004",
                "Kanboard provider was promoted to architectural authority or canonical root",
            ))

    return {
        "result": "PASS" if not findings else "FAIL",
        "scanned_canonical_json_files": scanned,
        "findings": findings,
    }

def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-KANBOARD-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-KANBOARD-2026-08-30.json",
        "reference": root / "canonical/references/FA3-KANBOARD-UPSTREAM-REFERENCE-2026-08-30.json",
        "enforcement": root / "canonical/kanboard-enforcement.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    for name, path in paths.items():
        if not path.exists():
            findings.append(_finding(
                "KANBOARD-REF-001", f"Missing required Kanboard canonical artifact: {name}",
                path=str(path.relative_to(root)),
            ))
    if findings:
        return {"result": "FAIL", "findings": findings}

    provider = _load(paths["provider"])
    decision = _load(paths["decision"])
    reference = _load(paths["reference"])
    enforcement = _load(paths["enforcement"])
    policy = _load(paths["policy"])

    if not provider_shape_valid(provider):
        findings.append(_finding("KANBOARD-REF-002", "Kanboard provider authority/capability/boundary invariant drift"))
    required_classes = {
        "OPTIONAL_PROVIDER", "WORK_MANAGEMENT_PROVIDER", "ARCHITECTURAL_PATTERN_SOURCE",
        "AUTHORIZATION_PATTERN_SOURCE", "STATE_TRANSITION_POLICY_PATTERN_SOURCE",
        "EVENT_ACTION_PATTERN_SOURCE", "EXTERNAL_TASK_PROVIDER_PATTERN_SOURCE",
        "PLUGIN_BOUNDARY_PATTERN_SOURCE", "SUPPLY_CHAIN_ANTI_PATTERN_SOURCE",
    }
    if not required_classes.issubset(set(provider.get("classification", []))):
        findings.append(_finding("KANBOARD-REF-003", "Kanboard provider classification drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("mandatory_constraint") == MANDATORY_CONSTRAINT
        and decision.get("mandatory_canonical_rules") == P0_INVARIANTS
    ):
        findings.append(_finding("KANBOARD-REF-004", "Kanboard canonical decision invariant drift"))

    stable = reference.get("stable_reference", {})
    disp = reference.get("fa3_disposition", {})
    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("provider_id") == PROVIDER_ID
        and reference.get("repository") == "kanboard/kanboard"
        and stable.get("release") == REFERENCE_RELEASE
        and stable.get("commit_sha") == REFERENCE_COMMIT
        and disp.get("floating_main_allowed_as_promotion_evidence") is False
        and disp.get("application_wide_credential_authorization_bypass_allowed") is False
        and disp.get("webhook_payload_is_authorization_or_canonical_evidence") is False
        and disp.get("plugin_curation_implies_transitive_trust") is False
        and disp.get("provider_configured_url_implies_egress_authorization") is False
        and disp.get("provider_runtime_required_for_global_promotion") is False
    ):
        findings.append(_finding("KANBOARD-REF-005", "Kanboard immutable upstream/security disposition drift"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("provider_id") == PROVIDER_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("runtime_provider_required_for_global_promotion") is False
        and enforcement.get("floating_main_allowed_as_promotion_evidence") is False
        and enforcement.get("mandatory_rule_count") == len(P0_INVARIANTS)
        and enforcement.get("p0_invariants") == P0_INVARIANTS
        and enforcement.get("regression_case_count") == 12
    ):
        findings.append(_finding("KANBOARD-REF-006", "Kanboard fail-closed enforcement record drift"))

    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("KANBOARD-REF-007", "Kanboard gate is not bound into mandatory_reference_gates"))
    if policy.get("kanboard_provider_id") != PROVIDER_ID:
        findings.append(_finding("KANBOARD-REF-008", "Global enforcement policy Kanboard provider identity drift"))
    if policy.get("kanboard_mandatory_p0_rules") != P0_INVARIANTS:
        findings.append(_finding("KANBOARD-REF-009", "Global enforcement policy Kanboard P0 invariant drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}

def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def add(rule_id: str, name: str, positive: bool, negative: bool) -> None:
        cases.append({
            "rule_id": rule_id,
            "name": name,
            "status": "PASS" if positive and negative else "FAIL",
            "positive_case": positive,
            "negative_case": negative,
        })

    add("FA3-KANBOARD-P0-001", "state-transition scoped authorization",
        state_transition_authorized(caller_identity="user:1", project_scope="project:1",
            capability_scope=["work_item.transition"], current_state="READY", requested_state="DOING",
            policy_authority="FA3-AUTH-SECURITY-GOV-001", policy_decision="ALLOW"),
        not state_transition_authorized(caller_identity="agent:1", project_scope="",
            capability_scope=["work_item.transition"], current_state="READY", requested_state="DONE",
            policy_authority=PROVIDER_ID, policy_decision="ALLOW"))

    add("FA3-KANBOARD-P0-002", "event does not imply action authorization",
        event_action_allowed(event_validated=True, event_type="task.moved", action_capability="work_item.update",
            actor_identity="user:1", project_scope="project:1", policy_authority="FA3-AUTH-SECURITY-GOV-001",
            policy_decision="ALLOW", event_implies_authorization=False),
        not event_action_allowed(event_validated=True, event_type="task.moved", action_capability="work_item.update",
            actor_identity="event", project_scope="project:1", policy_authority="FA3-AUTH-SECURITY-GOV-001",
            policy_decision="ALLOW", event_implies_authorization=True))

    add("FA3-KANBOARD-P0-003", "integration-wide credential authorization bypass denial",
        integration_credential_valid(global_application_credential=False, actor_scoped_identity="user:1",
            project_scope="project:1", permission_checks_enforced=True),
        not integration_credential_valid(global_application_credential=True, actor_scoped_identity="application",
            project_scope="*", permission_checks_enforced=False))

    add("FA3-KANBOARD-P0-004", "provider-neutral work-item identity",
        work_item_projection_valid(canonical_work_item_id="FA3-WORK-1", provider_instance="kb:local",
            provider_object_id="task:42", sync_state="SYNCED", provider_owns_canonical_identity=False),
        not work_item_projection_valid(canonical_work_item_id="", provider_instance="kb:local",
            provider_object_id="task:42", sync_state="SYNCED", provider_owns_canonical_identity=True))

    add("FA3-KANBOARD-P0-005", "remote provider state reconciliation",
        remote_state_reconciliation_valid(provider_revision="kb:rev:5", observed_canonical_revision="fa3:rev:8",
            reconciliation_state="SYNCED", provider_state_authoritative=False),
        not remote_state_reconciliation_valid(provider_revision="kb:rev:6", observed_canonical_revision="",
            reconciliation_state="SYNCED", provider_state_authoritative=True))

    add("FA3-KANBOARD-P0-006", "webhook normalization and non-evidence boundary",
        webhook_projection_valid(authenticated=True, validated=True, typed_normalized=True,
            canonical_event_id="evt:1", webhook_is_authorization=False, webhook_is_canonical_evidence=False),
        not webhook_projection_valid(authenticated=True, validated=False, typed_normalized=False,
            canonical_event_id="", webhook_is_authorization=True, webhook_is_canonical_evidence=True))

    add("FA3-KANBOARD-P0-007", "plugin supply-chain admission",
        plugin_admission_valid(source_identity="repo:plugin", pinned_version="1.0.0", digest="sha256:abc",
            provenance_verified=True, license_admitted=True, policy_admitted=True, adhoc_web_install=False),
        not plugin_admission_valid(source_identity="url:random", pinned_version="", digest="",
            provenance_verified=False, license_admitted=False, policy_admitted=False, adhoc_web_install=True))

    add("FA3-KANBOARD-P0-008", "plugin authority escalation denial",
        plugin_authority_valid(grants_authority=False, authority_owner="FA3-AUTH-SECURITY-GOV-001"),
        not plugin_authority_valid(grants_authority=True, authority_owner=PROVIDER_ID))

    add("FA3-KANBOARD-P0-009", "provider-configured URL egress denial",
        provider_egress_valid(provider_configured_url=True, canonical_egress_authorized=True,
            ssrf_controls=True, dns_rebinding_controls=True),
        not provider_egress_valid(provider_configured_url=True, canonical_egress_authorized=False,
            ssrf_controls=False, dns_rebinding_controls=False))

    add("FA3-KANBOARD-P0-010", "provider failure isolation",
        provider_failure_isolated(provider_available=False, canonical_state_available=True,
            fail_open_to_provider_state=False),
        not provider_failure_isolated(provider_available=False, canonical_state_available=False,
            fail_open_to_provider_state=True))

    zero = {"resident_process_count":0, "background_worker_count":0, "network_session_count":0,
            "accelerator_reservation_count":0, "active_polling":False, "background_fetch":False}
    add("FA3-KANBOARD-P0-011", "disabled provider zero runtime dependency",
        disabled_zero_cost(zero),
        not disabled_zero_cost({**zero, "background_worker_count":1}))

    good_provider = {
        "id": PROVIDER_ID, "status":"ACCEPTED_REFERENCE", "canonical_root":False,
        "architectural_authority":False, "new_capability":False, "capability_count":CAPABILITY_COUNT,
        "activation_mode":"OPTIONAL_DISABLED_BY_DEFAULT",
        "global_runtime_promotion_required_when_disabled":False,
        "normative_constraint":MANDATORY_CONSTRAINT,
        "authority_boundaries":dict(EXPECTED_EXTERNAL_BOUNDARIES),
    }
    bad_provider = dict(good_provider)
    bad_provider["architectural_authority"] = True
    bad_provider["capability_count"] = CAPABILITY_COUNT + 1
    add("FA3-KANBOARD-P0-012", "provider authority/capability drift denial",
        provider_shape_valid(good_provider), not provider_shape_valid(bad_provider))

    passed = sum(case["status"] == "PASS" for case in cases)
    return {
        "schema":"fa3.kanboard-regression-report.v1",
        "result":"PASS" if passed == len(cases) else "FAIL",
        "passed":passed, "total":len(cases), "cases":cases,
    }

def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    authority_scan = scan_canonical_authority_assignments(root)
    regressions = run_regressions()
    ok = all(section["result"] == "PASS" for section in (reference, authority_scan, regressions))
    report = {
        "schema":"fa3.kanboard-gate-report.v1",
        "gate_id":GATE_ID,
        "provider_id":PROVIDER_ID,
        "capability_count":CAPABILITY_COUNT,
        "result":"PASS" if ok else "FAIL",
        "mode":"CANONICAL_AUTHORIZATION_EVENT_PLUGIN_SECURITY_REGRESSIONS",
        "reference":reference,
        "authority_scan":authority_scan,
        "regressions":regressions,
        "runtime_provider_required":False,
        "promotion_effect":"MANDATORY_CANONICAL_RULES_PROVIDER_RUNTIME_OPTIONAL",
    }
    _write(root / "reports/kanboard-gate-report.json", report)
    return report

def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Kanboard fail-closed authorization/event/plugin regression gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
