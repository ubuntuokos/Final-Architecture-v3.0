#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cfa3_development_ai_behavior_guard import RULE_IDS, authorize_action
from fa3_agent_workload import WorkloadContractError, compile_execution_plan
from fa3_release_baseline import active_capability_count
from fa3_task_scope_closure import goal_scope_binding, start_task_control

POLICY = Path("canonical/CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001.json")
DECISION = Path("canonical/decisions/CFA3-DEC-DEVELOPMENT-AI-BEHAVIOR-LAYERING-2026-10-05.json")
GATE_RECORD = Path("canonical/FA3-GATE-CFA3-DEVELOPMENT-AI-BEHAVIOR-001.json")
GATE_REGISTRY = Path("canonical/FA3-GATE-REGISTRY-001.json")
ENFORCEMENT_POLICY = Path("canonical/enforcement-policy.json")
CURRENT_HOST_IMPACT = Path("canonical/current-host-impact/FA3-CH-IMPACT-CFA3-DEVELOPMENT-AI-BEHAVIOR-20261005.json")
REUSE_ASSESSMENT = Path("canonical/assessments/CFA3-DEVELOPMENT-AI-BEHAVIOR-REUSE-ASSESSMENT-2026-10-05.json")
GATE_ID = "CFA3-DEVELOPMENT-AI-BEHAVIOR-GATESET-001"

EXPECTED_DEV = {f"DEV-{i:02d}" for i in range(1, 12)}
EXPECTED_AI = {f"AI-{i:02d}" for i in range(1, 12)}
EXPECTED_LAYERS = {"L0", "L1", "L2", "L3", "L4", "L5"}
EXPECTED_POLICY_SEMANTICS = json.loads(r'''{"scope":{"development_process":true,"cfa3_ai_models":true,"cfa3_agents":true,"cfa3_orchestrators":true,"coding_agents":true,"workflow_agents":true,"model_router_invoked_models":true,"local_and_external_models":true},"owner_override":{"allowed":true,"explicit_only":true,"conversation_bounded":true,"direct_continuation_allowed_when_explicitly_bound":true,"not_inherited_to_other_tasks":true,"not_inferred_from_generic_approval":true,"must_identify_rule_or_scope":true,"expiry":"END_OF_SCOPED_CONVERSATION_OR_EXPLICIT_REVOCATION"},"precedence":["PLATFORM_AND_SAFETY_CONSTRAINTS","CURRENT_EXPLICIT_OWNER_SCOPE_AND_RESTRICTIONS","CURRENT_EXPLICIT_OWNER_OVERRIDE","THIS_POLICY","TASK_PLAN_AND_APPROVAL","EARLIER_AUTONOMY_GRANTS"],"composition":{"layers_are_distinct":true,"higher_layer_does_not_replace_lower_layer":true,"lower_layer_may_be_more_restrictive":true,"silent_precedence_inference_forbidden":true,"contradiction_result":"BLOCKER","unknown_authority_result":"BLOCKER","cross_layer_overlap_without_explicit_resolution":"BLOCKER","pending_pr_is_not_canonical_authority":true,"published_main_canonical_records_remain_authoritative":true},"development_rules":[{"id":"DEV-01","name":"BLOCKER_IS_IMMEDIATE_STOP","requirement":"Conflict, changed main, failed gate, uncertain state, overlapping work or unexpected CI causes immediate STOP and report."},{"id":"DEV-02","name":"NO_AUTONOMOUS_WORKAROUND","requirement":"After a blocker, no autonomous rebase, workflow, replacement PR, component change, bypass or alternative route."},{"id":"DEV-03","name":"THREAD_SCOPE_LOCK","requirement":"A conversation may affect only the explicitly scoped task files, PRs and directly authorized dependencies."},{"id":"DEV-04","name":"FRESH_STATE_BEFORE_WRITE","requirement":"Before every GitHub mutation re-check main SHA, target head and relevant open PR state."},{"id":"DEV-05","name":"OVERLAP_IS_BLOCKER","requirement":"Concurrent modification of the same canonical file, gate, workflow or exclusive resource is a blocker unless explicitly owner-overridden for this conversation."},{"id":"DEV-06","name":"NO_AUTOMATIC_WORKFLOW_OR_GATE_START","requirement":"Start a workflow or gate only when required for task closure and only when no equivalent run is already active."},{"id":"DEV-07","name":"REPORT_AFTER_EVERY_MUTATION","requirement":"After each mutation report what changed, current SHA, next step and blocker status."},{"id":"DEV-08","name":"EXACT_HEAD_BEFORE_MERGE","requirement":"Merge requires exact checked head and base/main; any drift blocks merge."},{"id":"DEV-09","name":"NO_SILENT_REDESIGN_OR_REPAIR","requirement":"Unexpected conditions requiring redesign or repair must be reported before changing strategy."},{"id":"DEV-10","name":"CURRENT_OWNER_RESTRICTION_WINS","requirement":"Current explicit owner restrictions override earlier autonomy grants and broader approvals."},{"id":"DEV-11","name":"SELF_CORRECTION_EXCEPTION","requirement":"The development AI may autonomously correct only its own clearly mechanical or technical mistake when the correction is deterministic, preserves owner intent, remains inside the active scope and approved architecture/policy, creates no workaround or unnecessary side effect, and does not bypass a blocker, gate, security rule or authority boundary. The AI must notify the owner when the mistake is recognized and correction begins; if partial mutation may have occurred, exact state must be verified first; after correction the AI must report the mistake, correction, state change, current head/SHA or relevant state, and remaining blockers."}],"ai_behavior_rules":[{"id":"AI-01","name":"STOP_ON_BLOCKER","requirement":"AI execution stops on a blocker and reports it before any further side effect."},{"id":"AI-02","name":"NO_AUTONOMOUS_BYPASS","requirement":"An AI may not infer permission to bypass a blocker from the user's end goal."},{"id":"AI-03","name":"ACTIVE_SCOPE_BINDING","requirement":"AI execution must carry explicit task scope, allowed/forbidden actions and applicable overrides."},{"id":"AI-04","name":"FRESH_STATE_BEATS_MEMORY","requirement":"Live verified state outranks remembered or cached repository, workflow and runtime state."},{"id":"AI-05","name":"CROSS_AGENT_COLLISION_DETECTION","requirement":"Conflicting concurrent work by another agent, task or PR blocks mutating execution."},{"id":"AI-06","name":"EXPLICIT_SIDE_EFFECT_LEVEL","requirement":"READ, ANALYZE, PLAN, WRITE, COMMIT, PUSH, PR, WORKFLOW, GATE, MERGE, RELEASE and EXTERNAL_ACTION permissions do not imply one another."},{"id":"AI-07","name":"MUTATION_AUDIT","requirement":"Every state-changing AI operation requires an attributable audit record."},{"id":"AI-08","name":"EXACT_STATE_COMMITMENT","requirement":"An authorization based on a concrete state expires when that state materially changes."},{"id":"AI-09","name":"UNCERTAINTY_IS_BLOCKER","requirement":"Unknown current state, authority, scope ownership or approval validity fails closed."},{"id":"AI-10","name":"LATEST_OWNER_CONSTRAINT_PRIORITY","requirement":"Current explicit owner restrictions override earlier model autonomy and execution permissions."},{"id":"AI-11","name":"SELF_CORRECTION_EXCEPTION","requirement":"A CFA3 AI/model/agent may autonomously correct only its own clearly mechanical or technical mistake under the same deterministic, scope-preserving, authority-preserving and fail-closed conditions as DEV-11. It must notify before correction, verify exact state first when partial mutation is possible, and report the correction and resulting state. Redesign, alternative technical solutions, new PR/branch, cross-component changes, restriction weakening, review-discovered design or implementation defects, new permissions/side effects, or uncertain corrections remain BLOCKER -> STOP -> REPORT."}],"state_machine":{"normal":["REQUESTED","SCOPE_LOCKED","STATE_VERIFIED","AUTHORIZED","EXECUTING","MUTATION_REPORTED","VERIFIED","COMPLETED"],"blocker":["BLOCKER_DETECTED","STOPPED","BLOCKER_REPORTED","AWAITING_HUMAN_DECISION"],"resume":["REAUTHORIZED","STATE_VERIFIED"],"forbidden_direct_transitions_from_blocker":["EXECUTING","MERGE","RELEASE","EXTERNAL_ACTION"]},"fail_closed":{"unknown_permission":"DENY","unknown_scope":"DENY","unknown_state":"BLOCKER","unknown_overlap":"BLOCKER","silence_is_approval":false,"prior_autonomy_is_current_authority":false},"self_correction_exception":{"ids":["DEV-11","AI-11"],"summary":"The AI may correct its own unambiguous technical mistake. It may not redesign the task under the guise of correction.","notification_required_on_detection_and_correction_start":true,"independently_correctable_examples":["TYPO","WRONG_VARIABLE_OR_FILE_NAME","SYNTAX_ERROR","FORMATTING_ERROR","MALFORMED_TOOL_OR_API_ARGUMENT","UNAMBIGUOUS_COMMAND_PARAMETER_ERROR","CONSISTENCY_ERROR_IN_AI_GENERATED_FILE","RETRY_OF_FAILED_OPERATION_PROVEN_TO_HAVE_NO_STATE_CHANGE","TECHNICALLY_CORRECT_RESUBMISSION_OF_THE_SAME_APPROVED_OPERATION"],"mandatory_conditions":["ERROR_PROVABLY_CAUSED_BY_THE_AI","CORRECTION_IS_UNAMBIGUOUS_AND_DETERMINISTIC","OWNER_INTENT_UNCHANGED","TASK_OR_CONVERSATION_SCOPE_NOT_EXPANDED","ARCHITECTURE_AUTHORITY_POLICY_AND_APPROVED_PLAN_UNCHANGED","NO_NEW_COMPONENT_USED_AS_WORKAROUND","NO_BLOCKER_GATE_OR_SECURITY_BYPASS","NO_UNNECESSARY_WORKFLOW_GATE_OR_SIDE_EFFECT","IF_PARTIAL_MUTATION_IS_POSSIBLE_EXACT_STATE_VERIFICATION_PRECEDES_CORRECTION","POST_CORRECTION_REPORT_REQUIRED"],"post_correction_report_fields":["OWN_ERROR","CORRECTION","STATE_CHANGE","CURRENT_HEAD_SHA_OR_RELEVANT_STATE","REMAINING_BLOCKER"],"not_self_correctable":["REDESIGN_REQUIRED","ALTERNATIVE_TECHNICAL_SOLUTION_SELECTION","NEW_PR_OR_BRANCH_REQUIRED","OTHER_COMPONENT_MODIFICATION_REQUIRED","USER_RESTRICTION_WEAKENING","REVIEW_DISCOVERED_REAL_DESIGN_OR_IMPLEMENTATION_DEFECT","NEW_PERMISSION_OR_SIDE_EFFECT_REQUIRED","CORRECT_FIX_IS_UNCERTAIN"],"non_self_correctable_result":"BLOCKER_STOP_REPORT","precedence":["CURRENT_EXPLICIT_OWNER_PROHIBITION","SCOPE_LOCK","SAFETY_AND_AUTHORITY_BOUNDARIES","EXACT_STATE_REQUIREMENT","REAL_BLOCKER_RULE"],"may_override_precedence":false},"runtime_enforcement_binding":{"agent_workload_runtime":"FA3-AGENT-WORKLOAD-RUNTIME-001","execution_plan_compiler":"src/fa3_agent_workload.py::compile_execution_plan","execution_plan_behavior_preflight_required":true,"start_resume_require_execution_plan":true,"unified_action_fabric_remains_effect_boundary":true,"security_governance_remains_authorization_authority":true,"host_resource_broker_remains_resource_authority":true,"model_router_remains_model_routing_authority":true,"behavior_preflight_is_effect_authority":false}}''')
EXPECTED_DONOR_SNAPSHOT = {
    "published_main_commit": "6f3cadb792ca8bd1b49bac62dfe9c92325090e5c",
    "donor_registry_id": "FA3-DONOR-REFERENCE-REGISTRY-001",
    "donor_registry_blob_sha": "1362d75186c6da74e5cf947fdf0b8867d462636a",
    "donor_registry_sha256": "b8d0eb42ee02885863af375071ffae89033664089ddba3c69682a8d0f7c7cff1",
    "donor_registry_entry_count": 1427,
}


def _load(root: Path, rel: Path) -> dict[str, Any]:
    return json.loads((root / rel).read_text(encoding="utf-8"))



def _runtime_behavior_context() -> dict[str, Any]:
    return {
        "action": "READ",
        "current_owner_restriction_allows": True,
        "scope_bound": True,
        "scope_allows_action": True,
        "scope_origin": "REQUIRED_FOR_APPROVED_GOAL",
        "scope_refs": ["approved:cfa3-behavior-gate"],
        "uncertain_state": False,
        "blocker_kind": None,
        "autonomous_workaround": False,
        "silent_redesign_or_repair": False,
    }


def _runtime_wiring_check() -> dict[str, Any]:
    binding = goal_scope_binding({"goal_id":"behavior-gate-task","revision":1,"scope":{"in_scope":["approved:cfa3-behavior-gate"],"out_of_scope":[]}})
    control = start_task_control(binding, task_id="behavior-gate-task", root_task_id="behavior-gate-task")
    task = {
        "schema": "fa3.agent-workload-task.v1",
        "task_id": "behavior-gate-task",
        "root_task_id": "behavior-gate-task",
        "scope_origin": "REQUIRED_FOR_APPROVED_GOAL",
        "scope_refs": ["approved:cfa3-behavior-gate"],
        "goal_scope_binding": binding,
        "action_ref": "orchestration.execute",
        "agent_definition_ref": "agent:def:behavior-gate",
        "workspace_refs": [],
        "resource_requirements": {},
        "network_envelope_ref": "net:behavior-gate",
        "model_intent": {"required_capabilities": []},
        "authorized_ai_participants": ["agent:def:behavior-gate"],
        "fanout_limits": {"max_children": 0, "max_depth": 0, "max_concurrent_children": 0, "max_runtime_seconds": 60, "max_retries": 0, "max_tool_calls": 0, "max_model_requests": 0},
        "provenance_refs": [],
    }
    graph = {"schema": "fa3.agent-workflow-graph.v1", "graph_id": "behavior-gate-graph", "entry_node": "n1", "yaml_is_canonical": False, "nodes": [{"node_id": "n1", "kind": "AGENT", "side_effecting": False}], "edges": []}
    model = {"schema": "fa3.model-capability-descriptor.v1", "logical_model_id": "behavior-gate-model", "source": "PROVIDER_DECLARED", "router_authority": "FA3-AUTH-MODEL-ROUTER-001", "model_id_heuristic": False, "capabilities": {"tools": False, "structured_output": False, "media_input": False, "media_output": False, "streaming": False}}
    context = _runtime_behavior_context()
    plan = compile_execution_plan(task, graph, model, task_spec_digest="sha256:behavior-gate", max_transfer_hops=0, behavior_context=context, task_control=control)
    malformed = dict(context)
    malformed.pop("blocker_kind")
    missing_fact_blocked = False
    try:
        compile_execution_plan(task, graph, model, task_spec_digest="sha256:behavior-gate", max_transfer_hops=0, behavior_context=malformed, task_control=control)
    except WorkloadContractError:
        missing_fact_blocked = True
    receipt = plan.get("behavior_preflight", {})
    return {
        "pass": receipt.get("policy_preflight_passed") is True
            and receipt.get("side_effect_authorized") is False
            and receipt.get("policy_id") == "CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001"
            and missing_fact_blocked,
        "receipt": receipt,
        "missing_fact_blocked": missing_fact_blocked,
    }

def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    required = [POLICY, DECISION, GATE_RECORD, GATE_REGISTRY, ENFORCEMENT_POLICY, CURRENT_HOST_IMPACT, REUSE_ASSESSMENT]
    missing = [str(p) for p in required if not (root / p).exists()]
    if missing:
        return {
            "schema": "cfa3.development-ai-behavior-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "checks": [{"name": "required-artifacts", "status": "FAIL", "detail": missing}],
        }

    policy = _load(root, POLICY)
    decision = _load(root, DECISION)
    gate_record = _load(root, GATE_RECORD)
    registry = _load(root, GATE_REGISTRY)
    enforcement = _load(root, ENFORCEMENT_POLICY)
    ch = _load(root, CURRENT_HOST_IMPACT)
    reuse = _load(root, REUSE_ASSESSMENT)
    active_count = active_capability_count(root)

    dev_ids = {row.get("id") for row in policy.get("development_rules", [])}
    ai_ids = {row.get("id") for row in policy.get("ai_behavior_rules", [])}
    layer_ids = {row.get("level") for row in policy.get("layers", [])}

    overlap_ctx = {
        "action": "WRITE",
        "current_owner_restriction_allows": True,
        "scope_bound": True,
        "scope_allows_action": True,
        "uncertain_state": False,
        "blocker_kind": "OVERLAP",
        "autonomous_workaround": False,
        "fresh_state_verified": True,
        "mutation_report_pending": False,
        "side_effect_permission": "WRITE",
        "silent_redesign_or_repair": False,
    }
    overlap_stop = authorize_action(overlap_ctx)
    overlap_ctx["owner_override"] = {
        "rule_ids": ["DEV-05", "AI-01"],
        "explicit": True,
        "conversation_bound": True,
        "scope_matches": True,
    }
    overlap_override = authorize_action(overlap_ctx)

    self_correction_ctx = {
        "action": "WRITE",
        "current_owner_restriction_allows": True,
        "scope_bound": True,
        "scope_allows_action": True,
        "uncertain_state": False,
        "blocker_kind": None,
        "autonomous_workaround": False,
        "fresh_state_verified": True,
        "mutation_report_pending": False,
        "side_effect_permission": "WRITE",
        "silent_redesign_or_repair": False,
        "self_correction": {
            "requested": True,
            "error_caused_by_ai": True,
            "mechanical_or_technical": True,
            "correction_deterministic": True,
            "user_intent_preserved": True,
            "scope_preserved": True,
            "architecture_authority_policy_plan_preserved": True,
            "no_new_component_workaround": True,
            "notification_sent": True,
            "existing_authorization_covers_corrected_action": True,
            "blocker_gate_or_security_bypass": False,
            "unnecessary_workflow_gate_or_side_effect": False,
            "redesign_required": False,
            "alternative_technical_solution": False,
            "new_pr_or_branch_required": False,
            "other_component_modification_required": False,
            "user_restriction_weakened": False,
            "review_discovered_real_design_or_implementation_defect": False,
            "new_permission_or_side_effect_required": False,
            "correction_uncertain": False,
            "partial_mutation_possible": False,
            "exact_state_verified": False,
        },
    }
    self_correction_allow = authorize_action(self_correction_ctx)
    self_correction_ctx["self_correction"]["partial_mutation_possible"] = True
    self_correction_exact_state_stop = authorize_action(self_correction_ctx)
    runtime_wiring = _runtime_wiring_check()
    observed_semantics = {key: policy.get(key) for key in EXPECTED_POLICY_SEMANTICS}

    checks = {
        "canonical-policy": policy.get("id") == "CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001"
            and policy.get("status") == "CANONICAL"
            and policy.get("priority") == "P0",
        "development-and-product-scope": policy.get("scope", {}).get("development_process") is True
            and policy.get("scope", {}).get("cfa3_ai_models") is True
            and policy.get("scope", {}).get("cfa3_agents") is True,
        "exact-development-rules": dev_ids == EXPECTED_DEV,
        "exact-ai-rules": ai_ids == EXPECTED_AI,
        "guard-rule-set": RULE_IDS == EXPECTED_DEV | EXPECTED_AI,
        "policy-semantics": observed_semantics == EXPECTED_POLICY_SEMANTICS,
        "runtime-enforcement-binding": runtime_wiring.get("pass") is True,
        "reuse-assessment": reuse.get("result") == "PASS"
            and reuse.get("donor_planning_snapshot") == EXPECTED_DONOR_SNAPSHOT
            and reuse.get("pending_or_unmerged_donors_consumed") is False
            and reuse.get("donor_usage_edges_created") == 0
            and reuse.get("shared_capability_placement", {}).get("disposition") == "SHARED"
            and reuse.get("shared_capability_placement", {}).get("local_duplicate_created") is False,
        "self-correction-policy": policy.get("self_correction_exception", {}).get("ids") == ["DEV-11", "AI-11"]
            and policy.get("self_correction_exception", {}).get("non_self_correctable_result") == "BLOCKER_STOP_REPORT"
            and policy.get("self_correction_exception", {}).get("may_override_precedence") is False,
        "self-correction-valid-path": self_correction_allow.get("decision") == "ALLOW"
            and self_correction_allow.get("self_correction_authorized") is True
            and self_correction_allow.get("post_correction_report_required") is True,
        "self-correction-partial-mutation-exact-state": self_correction_exact_state_stop.get("decision") == "STOP"
            and "AI-08" in self_correction_exact_state_stop.get("rule_ids", []),
        "layer-model": layer_ids == EXPECTED_LAYERS
            and policy.get("composition", {}).get("layers_are_distinct") is True
            and policy.get("composition", {}).get("contradiction_result") == "BLOCKER",
        "pending-pr-not-authority": policy.get("composition", {}).get("pending_pr_is_not_canonical_authority") is True
            and decision.get("pending_pr_semantics", {}).get("listed_prs_are_canonical_authority") is False,
        "owner-override-bounded": policy.get("owner_override", {}).get("explicit_only") is True
            and policy.get("owner_override", {}).get("conversation_bounded") is True
            and policy.get("owner_override", {}).get("not_inferred_from_generic_approval") is True,
        "overlap-default-stop": overlap_stop.get("decision") == "STOP"
            and "DEV-05" in overlap_stop.get("rule_ids", []),
        "overlap-explicit-override": overlap_override.get("decision") == "ALLOW",
        "decision-binding": decision.get("policy_id") == policy.get("id")
            and decision.get("status") == "CANONICAL_CLOSED",
        "baseline-preserved": policy.get("capability_baseline") == active_count
            and decision.get("capability_count_after") == active_count
            and policy.get("capability_delta") == 0
            and policy.get("architectural_authority_delta") == 0,
        "gate-record": gate_record.get("id") == "FA3-GATE-CFA3-DEVELOPMENT-AI-BEHAVIOR-001"
            and gate_record.get("enforcement_id") == GATE_ID
            and gate_record.get("fail_closed") is True,
        "global-gate-membership": GATE_ID in registry.get("mandatory_reference_gates", [])
            and registry.get("mandatory_reference_gates", []) == enforcement.get("mandatory_reference_gates", []),
        "current-host-boundary": ch.get("physical_requalification_required") is False
            and ch.get("current_host_runtime_promotion_claim") is False
            and ch.get("historical_evidence_reused") is False,
    }

    passed = all(checks.values())
    return {
        "schema": "cfa3.development-ai-behavior-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if passed else "FAIL",
        "capability_count": active_count,
        "checks": [
            {"name": name, "status": "PASS" if value else "FAIL"}
            for name, value in checks.items()
        ],
        "current_host_runtime_promotion_claim": False,
    }


def gate(root: Path) -> dict[str, Any]:
    return evaluate(root)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = evaluate(root)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
