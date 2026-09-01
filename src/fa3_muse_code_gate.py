#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-MUSE-CODE-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-MUSE-CODE-001"
PROVIDER_ID = "FA3-PROVIDER-MUSE-CODE-001"
CONTRACT_ID = "FA3-DURABLE-REPLAYABLE-MULTI-AGENT-EXECUTION-CONTRACTS-001"
DECISION_ID = "FA3-DEC-MUSE-CODE-2026-09-01"
REFERENCE_ID = "FA3-MUSE-CODE-UPSTREAM-REFERENCE-2026-09-01"
EVIDENCE_ID = "FA3-EVIDENCE-MUSE-CODE-CI-2026-09-01"
CAPABILITY_COUNT = 143

MANDATORY_CONSTRAINT = (
    "Muse Code SHALL remain an optional provider/pattern source and SHALL NOT become an FA3 "
    "identity, authorization, MCP/tool-mediation, model-routing, secrets, network-egress, "
    "host-resource, workflow/orchestration, evidence, developer-execution, git/release or "
    "registry authority."
)

P0_RULES = [
    "MUSE_CODE_PROVIDER_NOT_AUTHORITY",
    "MUSE_CODE_DURABLE_SESSION_EVENT_SOURCE_REQUIRED",
    "MUSE_CODE_APPEND_ONLY_MONOTONIC_EVENT_SEQUENCE",
    "MUSE_CODE_MODEL_TOOL_APPROVAL_EDIT_ATTRIBUTION",
    "MUSE_CODE_APPROVAL_PRECEDES_GATED_MUTATION",
    "MUSE_CODE_CRASH_RESUME_FROM_COMMITTED_CURSOR",
    "MUSE_CODE_REPLAY_RECONSTRUCTS_WITHOUT_SIDE_EFFECT_REEXECUTION",
    "MUSE_CODE_REPLAY_EXTERNAL_SIDE_EFFECT_IDEMPOTENCY",
    "MUSE_CODE_CHECKPOINT_BOUND_TO_EVENT_RANGE_AND_STATE_DIGEST",
    "MUSE_CODE_PROVENANCE_SURVIVES_CONTEXT_COMPACTION",
    "MUSE_CODE_PERSISTENT_SUBAGENT_CAPABILITY_NARROWING",
    "MUSE_CODE_BOUNDED_PARALLEL_SUBAGENT_EXECUTION",
    "MUSE_CODE_CANCEL_TERMINATE_RELEASES_SUBAGENT_RESOURCES",
    "MUSE_CODE_PENDING_APPROVAL_NOT_AUTO_GRANTED_ON_RESUME",
    "MUSE_CODE_RUNTIME_MODEL_TOOL_IDENTITY_PINNED_FOR_REPLAY",
    "MUSE_CODE_LOCAL_EVENT_LOG_NOT_CANONICAL_EVIDENCE_AUTHORITY",
    "MUSE_CODE_EVENT_LOG_SECRET_REDACTION_REQUIRED",
    "MUSE_CODE_PLAN_CRITIQUE_GOAL_PRIMITIVES_NOT_AUTHORIZATION",
    "MUSE_CODE_LONG_HORIZON_GOAL_SCOPE_BUDGET_BOUNDED",
    "MUSE_CODE_DISABLED_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST",
]

EVENT_CLASSES = {"MODEL_CALL", "TOOL_RUN", "APPROVAL", "EDIT_OR_MUTATION", "CHECKPOINT", "SUBAGENT"}
SENSITIVE_KEYS = {"secret", "token", "api_key", "password", "credential", "private_key"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def _is_muse(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return normalized in {
        PROVIDER_ID.lower(),
        "meta muse code",
        "muse code",
    }


def provider_shape_valid(provider: dict[str, Any]) -> bool:
    return (
        provider.get("id") == PROVIDER_ID
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT"
        and provider.get("global_runtime_promotion_required_when_disabled") is False
        and provider.get("runtime_activation_requires_current_host_conformance") is True
        and provider.get("runtime_activation_status") == "NOT_PROMOTED_REFERENCE_ONLY"
        and provider.get("current_host_runtime_evidence") is False
        and provider.get("durable_replay_contract") == CONTRACT_ID
    )


def provider_authority_separation_valid(*, provider_id: str, authority_owner: str) -> bool:
    return provider_id == PROVIDER_ID and authority_owner != PROVIDER_ID


def durable_event_source_valid(*, session_id: str, event_source: str, committed: bool) -> bool:
    return bool(session_id) and event_source == "APPEND_ONLY" and committed


def append_only_sequence_valid(events: list[dict[str, Any]]) -> bool:
    if not events:
        return False
    ids = [str(e.get("event_id", "")) for e in events]
    seqs = [e.get("seq") for e in events]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        return False
    if any(not isinstance(x, int) or x < 1 for x in seqs):
        return False
    return seqs == list(range(1, len(events) + 1))


def event_attribution_valid(event: dict[str, Any]) -> bool:
    event_type = event.get("event_type")
    if event_type not in {"MODEL_CALL", "TOOL_RUN", "APPROVAL", "EDIT_OR_MUTATION"}:
        return False
    required = ("event_id", "session_id", "actor_id", "seq")
    if any(not event.get(k) for k in required if k != "seq") or not isinstance(event.get("seq"), int):
        return False
    typed_requirements = {
        "MODEL_CALL": "model_id",
        "TOOL_RUN": "tool_id",
        "APPROVAL": "approval_id",
        "EDIT_OR_MUTATION": "mutation_id",
    }
    return bool(event.get(typed_requirements[event_type]))


def approval_precedes_mutation_valid(events: list[dict[str, Any]], *, mutation_id: str) -> bool:
    mutation = next((e for e in events if e.get("mutation_id") == mutation_id), None)
    if not mutation:
        return False
    if not mutation.get("approval_required", False):
        return True
    approval_id = mutation.get("approval_id")
    approval = next(
        (
            e
            for e in events
            if e.get("event_type") == "APPROVAL"
            and e.get("approval_id") == approval_id
            and e.get("decision") == "APPROVED"
        ),
        None,
    )
    return bool(approval and approval.get("seq", 0) < mutation.get("seq", 0))


def resume_cursor_valid(*, committed_sequences: set[int], resume_from_seq: int, next_seq: int) -> bool:
    return resume_from_seq in committed_sequences and next_seq == resume_from_seq + 1


def replay_without_side_effect_reexecution_valid(
    *, reconstructs_from_committed_events: bool, external_side_effects_enabled: bool
) -> bool:
    return reconstructs_from_committed_events and not external_side_effects_enabled


def external_side_effect_idempotency_valid(
    *, is_external_side_effect: bool, idempotency_key: str | None, replay_action: str
) -> bool:
    if not is_external_side_effect:
        return True
    return bool(idempotency_key) and replay_action in {"SKIP", "VERIFY", "IDEMPOTENT_APPLY"}


def checkpoint_valid(
    *, event_start: int, event_end: int, state_digest: str, chain_head: str, digest_payload: str
) -> bool:
    if event_start < 1 or event_end < event_start or not state_digest or not chain_head:
        return False
    expected = hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()
    return state_digest == expected


def compaction_provenance_valid(
    *, working_context_compacted: bool, full_event_lineage_retained: bool, checkpoint_bound: bool
) -> bool:
    if not working_context_compacted:
        return full_event_lineage_retained
    return full_event_lineage_retained and checkpoint_bound


def subagent_capability_narrowing_valid(
    *, parent_capabilities: set[str], child_capabilities: set[str], child_authority_expansion: bool
) -> bool:
    return child_capabilities <= parent_capabilities and not child_authority_expansion


def bounded_parallelism_valid(*, active_subagents: int, max_parallel_subagents: int) -> bool:
    return 0 <= active_subagents <= max_parallel_subagents and max_parallel_subagents > 0


def cancellation_cleanup_valid(
    *, terminated: bool, live_processes: int, active_leases: int, pending_mutations: int
) -> bool:
    return terminated and live_processes == 0 and active_leases == 0 and pending_mutations == 0


def pending_approval_resume_valid(*, before_restart: str, after_restart: str) -> bool:
    return before_restart == "PENDING" and after_restart == "PENDING"


def replay_identity_valid(*, runtime_id: str, model_id: str, toolset_digest: str) -> bool:
    return all(bool(x) and x not in {"latest", "floating", "*"} for x in (runtime_id, model_id, toolset_digest))


def local_event_log_evidence_valid(*, canonical_authority: bool, exported_via_evidence_authority: bool) -> bool:
    return not canonical_authority and exported_via_evidence_authority


def secret_redaction_valid(*, persisted_event: dict[str, Any], redacted: bool) -> bool:
    keys = {str(k).lower() for k in persisted_event}
    return redacted and not (keys & SENSITIVE_KEYS)


def primitive_authority_valid(*, primitive: str, grants_authority: bool) -> bool:
    return primitive in {"PLAN", "GRILL", "GOAL"} and not grants_authority


def goal_scope_budget_valid(*, scoped: bool, budget: int, consumed: int, can_expand_scope: bool) -> bool:
    return scoped and budget > 0 and 0 <= consumed <= budget and not can_expand_scope


def disabled_provider_valid(*, enabled: bool, resident_processes: int, background_agents: int, active_leases: int) -> bool:
    if enabled:
        return True
    return resident_processes == 0 and background_agents == 0 and active_leases == 0


def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    canonical = root / "canonical"
    scanned = 0
    if not canonical.exists():
        return {
            "result": "FAIL",
            "scanned_json_files": 0,
            "findings": [_finding("MUSE-AUTH-000", "canonical directory is missing")],
        }

    def walk(value: Any, *, path: str, file_path: str, muse_scope: bool = False) -> None:
        if isinstance(value, dict):
            local_scope = muse_scope or any(
                _is_muse(value.get(k)) for k in ("id", "provider_id", "name", "provider")
            )
            if local_scope and value.get("architectural_authority") is True:
                findings.append(
                    _finding(
                        "MUSE-AUTH-001",
                        "Muse Code architectural_authority was enabled",
                        file=file_path,
                        path=path,
                    )
                )
            for key, item in value.items():
                key_path = f"{path}.{key}"
                normalized = key.lower().replace("-", "_")
                if "authority" in normalized and _is_muse(item):
                    findings.append(
                        _finding(
                            "MUSE-AUTH-002",
                            "Muse Code was assigned to an authority-bearing field",
                            file=file_path,
                            path=key_path,
                        )
                    )
                if key == "authority_boundaries" and isinstance(item, dict):
                    for domain, owner in item.items():
                        if _is_muse(owner):
                            findings.append(
                                _finding(
                                    "MUSE-AUTH-003",
                                    "Muse Code owns an external FA3 authority boundary",
                                    file=file_path,
                                    path=f"{key_path}.{domain}",
                                )
                            )
                walk(item, path=key_path, file_path=file_path, muse_scope=local_scope)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, path=f"{path}[{index}]", file_path=file_path, muse_scope=muse_scope)

    for json_path in sorted(canonical.rglob("*.json")):
        scanned += 1
        try:
            data = _load(json_path)
        except Exception as exc:
            findings.append(
                _finding(
                    "MUSE-AUTH-004",
                    "Canonical JSON parse failure during Muse Code authority scan",
                    file=str(json_path.relative_to(root)),
                    error=str(exc),
                )
            )
            continue
        walk(data, path="$", file_path=str(json_path.relative_to(root)))

    return {
        "result": "PASS" if not findings else "FAIL",
        "scanned_json_files": scanned,
        "findings": findings,
    }


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-MUSE-CODE-001.json",
        "contract": root / "canonical/contracts/FA3-DURABLE-REPLAYABLE-MULTI-AGENT-EXECUTION-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-MUSE-CODE-2026-09-01.json",
        "reference": root / "canonical/references/FA3-MUSE-CODE-UPSTREAM-REFERENCE-2026-09-01.json",
        "gate": root / "canonical/FA3-GATE-MUSE-CODE-001.json",
        "enforcement": root / "canonical/muse-code-enforcement.json",
        "evidence": root / "evidence/reference/muse-code-ci-2026-09-01.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    for name, path in paths.items():
        if not path.exists():
            findings.append(
                _finding("MUSE-REF-001", f"Missing required Muse Code {name} artifact", path=str(path.relative_to(root)))
            )
    if findings:
        return {"result": "FAIL", "findings": findings}

    provider = _load(paths["provider"])
    contract = _load(paths["contract"])
    decision = _load(paths["decision"])
    reference = _load(paths["reference"])
    gate_record = _load(paths["gate"])
    enforcement = _load(paths["enforcement"])
    evidence = _load(paths["evidence"])
    policy = _load(paths["policy"])

    if not provider_shape_valid(provider):
        findings.append(_finding("MUSE-REF-002", "Muse Code provider shape/authority invariant drift"))

    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("status") == "CANONICAL"
        and contract.get("provider_neutral") is True
        and contract.get("parent_profile") == "FA3-AGENT-EXEC-001"
        and contract.get("new_capability") is False
        and contract.get("new_architectural_authority") is False
        and contract.get("capability_count") == CAPABILITY_COUNT
        and contract.get("event_log_semantics", {}).get("publication") == "APPEND_ONLY"
        and contract.get("replay_semantics", {}).get("side_effect_reexecution_default") == "FORBIDDEN"
    ):
        findings.append(_finding("MUSE-REF-003", "Durable/replayable contract invariant drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("contract_id") == CONTRACT_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("mandatory_constraint") == MANDATORY_CONSTRAINT
    ):
        findings.append(_finding("MUSE-REF-004", "Muse Code canonical decision invariant drift"))

    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("provider_id") == PROVIDER_ID
        and reference.get("upstream_status") == "BETA"
        and reference.get("source_confidence") == "OFFICIAL_META_AI_RESEARCH_ANNOUNCEMENT"
        and reference.get("promotion_evidence") is False
        and reference.get("floating_service_or_installer_state_allowed_as_promotion_evidence") is False
    ):
        findings.append(_finding("MUSE-REF-005", "Muse Code upstream-reference safety/identity drift"))

    if not (
        gate_record.get("id") == EXECUTABLE_GATE_ID
        and gate_record.get("gateset_id") == GATE_ID
        and gate_record.get("provider_id") == PROVIDER_ID
        and gate_record.get("contract_id") == CONTRACT_ID
        and gate_record.get("fail_closed") is True
        and gate_record.get("regression_case_count") == 20
        and gate_record.get("current_host_provider_runtime_evidence") is False
    ):
        findings.append(_finding("MUSE-REF-006", "Muse Code executable gate record drift"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("provider_id") == PROVIDER_ID
        and enforcement.get("contract_id") == CONTRACT_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("runtime_provider_required_for_global_promotion") is False
        and enforcement.get("p0_invariants") == P0_RULES
        and enforcement.get("mandatory_rule_count") == len(P0_RULES)
        and enforcement.get("mandatory_constraint") == MANDATORY_CONSTRAINT
    ):
        findings.append(_finding("MUSE-REF-007", "Muse Code fail-closed enforcement invariant drift"))

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
        findings.append(_finding("MUSE-REF-008", "Muse Code reference evidence semantics drift"))

    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("MUSE-REF-009", "Muse Code gate is not bound into global enforcement policy"))
    if policy.get("muse_code_provider_id") != PROVIDER_ID:
        findings.append(_finding("MUSE-REF-010", "Global Muse Code provider identity drift"))
    if policy.get("muse_code_contract_id") != CONTRACT_ID:
        findings.append(_finding("MUSE-REF-011", "Global Muse Code contract identity drift"))
    if policy.get("muse_code_mandatory_p0_rules") != P0_RULES:
        findings.append(_finding("MUSE-REF-012", "Global Muse Code P0 rule set drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def add(rule: str, name: str, positive: bool, negative: bool) -> None:
        cases.append(
            {
                "rule_id": rule,
                "name": name,
                "status": "PASS" if positive and negative else "FAIL",
                "positive_case": bool(positive),
                "negative_case": bool(negative),
            }
        )

    add(
        P0_RULES[0],
        "provider cannot become authority",
        provider_authority_separation_valid(provider_id=PROVIDER_ID, authority_owner="FA3-AUTH-SECURITY-GOV-001"),
        not provider_authority_separation_valid(provider_id=PROVIDER_ID, authority_owner=PROVIDER_ID),
    )
    add(
        P0_RULES[1],
        "durable session requires committed append-only event source",
        durable_event_source_valid(session_id="s1", event_source="APPEND_ONLY", committed=True),
        not durable_event_source_valid(session_id="s1", event_source="MUTABLE", committed=True),
    )

    good_events = [
        {"event_id": "e1", "seq": 1},
        {"event_id": "e2", "seq": 2},
        {"event_id": "e3", "seq": 3},
    ]
    bad_events = [
        {"event_id": "e1", "seq": 1},
        {"event_id": "e1", "seq": 2},
    ]
    add(P0_RULES[2], "append-only monotonic unique event sequence", append_only_sequence_valid(good_events), not append_only_sequence_valid(bad_events))

    attributed = {
        "event_type": "TOOL_RUN",
        "event_id": "e2",
        "session_id": "s1",
        "actor_id": "agent-a",
        "seq": 2,
        "tool_id": "git-diff@1",
    }
    unattributed = dict(attributed)
    unattributed.pop("actor_id")
    add(P0_RULES[3], "model/tool/approval/edit event attribution", event_attribution_valid(attributed), not event_attribution_valid(unattributed))

    approval_events = [
        {"event_type": "APPROVAL", "event_id": "a1", "seq": 1, "approval_id": "ap1", "decision": "APPROVED"},
        {"event_type": "EDIT_OR_MUTATION", "event_id": "m1", "seq": 2, "mutation_id": "mut1", "approval_required": True, "approval_id": "ap1"},
    ]
    missing_approval = [approval_events[1]]
    add(
        P0_RULES[4],
        "approval precedes gated mutation",
        approval_precedes_mutation_valid(approval_events, mutation_id="mut1"),
        not approval_precedes_mutation_valid(missing_approval, mutation_id="mut1"),
    )

    add(
        P0_RULES[5],
        "crash resume starts after committed cursor",
        resume_cursor_valid(committed_sequences={1, 2, 3}, resume_from_seq=3, next_seq=4),
        not resume_cursor_valid(committed_sequences={1, 2, 3}, resume_from_seq=4, next_seq=5),
    )
    add(
        P0_RULES[6],
        "replay reconstructs without default side-effect reexecution",
        replay_without_side_effect_reexecution_valid(reconstructs_from_committed_events=True, external_side_effects_enabled=False),
        not replay_without_side_effect_reexecution_valid(reconstructs_from_committed_events=True, external_side_effects_enabled=True),
    )
    add(
        P0_RULES[7],
        "external side effects are replay-idempotent or skipped",
        external_side_effect_idempotency_valid(is_external_side_effect=True, idempotency_key="task:42", replay_action="VERIFY"),
        not external_side_effect_idempotency_valid(is_external_side_effect=True, idempotency_key=None, replay_action="APPLY"),
    )

    payload = "session=s1;events=1-4;state=ready"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    add(
        P0_RULES[8],
        "checkpoint binds event range and state digest",
        checkpoint_valid(event_start=1, event_end=4, state_digest=digest, chain_head="h4", digest_payload=payload),
        not checkpoint_valid(event_start=1, event_end=4, state_digest="bad", chain_head="h4", digest_payload=payload),
    )
    add(
        P0_RULES[9],
        "context compaction preserves provenance",
        compaction_provenance_valid(working_context_compacted=True, full_event_lineage_retained=True, checkpoint_bound=True),
        not compaction_provenance_valid(working_context_compacted=True, full_event_lineage_retained=False, checkpoint_bound=True),
    )
    add(
        P0_RULES[10],
        "persistent subagent capabilities monotonically narrow",
        subagent_capability_narrowing_valid(parent_capabilities={"read", "edit", "test"}, child_capabilities={"read", "test"}, child_authority_expansion=False),
        not subagent_capability_narrowing_valid(parent_capabilities={"read"}, child_capabilities={"read", "edit"}, child_authority_expansion=True),
    )
    add(
        P0_RULES[11],
        "parallel subagents are explicitly bounded",
        bounded_parallelism_valid(active_subagents=3, max_parallel_subagents=4),
        not bounded_parallelism_valid(active_subagents=5, max_parallel_subagents=4),
    )
    add(
        P0_RULES[12],
        "cancel/terminate releases subagent resources",
        cancellation_cleanup_valid(terminated=True, live_processes=0, active_leases=0, pending_mutations=0),
        not cancellation_cleanup_valid(terminated=True, live_processes=1, active_leases=0, pending_mutations=0),
    )
    add(
        P0_RULES[13],
        "pending approval remains pending after resume",
        pending_approval_resume_valid(before_restart="PENDING", after_restart="PENDING"),
        not pending_approval_resume_valid(before_restart="PENDING", after_restart="APPROVED"),
    )
    add(
        P0_RULES[14],
        "runtime model and tool identities are replay-pinned",
        replay_identity_valid(runtime_id="muse-code-beta-2026-08-05", model_id="muse-spark-1.2", toolset_digest="sha256:abc"),
        not replay_identity_valid(runtime_id="latest", model_id="muse-spark-1.2", toolset_digest="sha256:abc"),
    )
    add(
        P0_RULES[15],
        "local event log is not canonical evidence authority",
        local_event_log_evidence_valid(canonical_authority=False, exported_via_evidence_authority=True),
        not local_event_log_evidence_valid(canonical_authority=True, exported_via_evidence_authority=False),
    )
    add(
        P0_RULES[16],
        "persisted event secret material is redacted",
        secret_redaction_valid(persisted_event={"event_id": "e1", "tool_id": "t1"}, redacted=True),
        not secret_redaction_valid(persisted_event={"event_id": "e1", "token": "secret"}, redacted=False),
    )
    add(
        P0_RULES[17],
        "plan critique goal primitives do not grant authorization",
        primitive_authority_valid(primitive="PLAN", grants_authority=False),
        not primitive_authority_valid(primitive="GOAL", grants_authority=True),
    )
    add(
        P0_RULES[18],
        "long-horizon goal remains scope and budget bounded",
        goal_scope_budget_valid(scoped=True, budget=100, consumed=40, can_expand_scope=False),
        not goal_scope_budget_valid(scoped=True, budget=100, consumed=140, can_expand_scope=True),
    )
    add(
        P0_RULES[19],
        "disabled provider has zero near-zero runtime footprint",
        disabled_provider_valid(enabled=False, resident_processes=0, background_agents=0, active_leases=0),
        not disabled_provider_valid(enabled=False, resident_processes=0, background_agents=1, active_leases=0),
    )

    passed = sum(case["status"] == "PASS" for case in cases)
    return {
        "schema": "fa3.muse-code-regression-report.v1",
        "result": "PASS" if passed == len(cases) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "cases": cases,
    }


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    authority_scan = scan_canonical_authority_assignments(root)
    regressions = run_regressions()
    ok = reference["result"] == authority_scan["result"] == regressions["result"] == "PASS"
    report = {
        "schema": "fa3.muse-code-gate-report.v1",
        "gate_id": GATE_ID,
        "executable_gate_id": EXECUTABLE_GATE_ID,
        "provider_id": PROVIDER_ID,
        "contract_id": CONTRACT_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if ok else "FAIL",
        "mode": "CANONICAL_DURABLE_REPLAYABLE_MULTI_AGENT_EXECUTION_REFERENCE_CONFORMANCE",
        "reference": reference,
        "authority_scan": authority_scan,
        "regressions": regressions,
        "runtime_provider_required": False,
        "current_host_provider_runtime_evidence": False,
        "runtime_activation_status": "NOT_PROMOTED_REFERENCE_ONLY",
        "promotion_effect": "MANDATORY_DURABLE_REPLAY_INVARIANTS_PROVIDER_RUNTIME_OPTIONAL",
    }
    _write(root / "reports/muse-code-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Muse Code durable/replayable multi-agent execution gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
