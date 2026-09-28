"""Positive and fail-closed goal execution foundation tests (metadata/design only)."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_goal_execution import (
    GoalContractError, assess_evidence, compile_plan, digest,
    prepare_goal, propose_repair, validate_goal,
)


def fixture():
    return {
        "schema": "fa3.goal-contract.v1",
        "goal_id": "goal-fixture",
        "revision": 1,
        "owner_ref": "user-approved-owner",
        "objective": "Add a narrow testable feature in an isolated workspace",
        "workspace_ref": "workspace-immutable-commit",
        "scope": {
            "in_scope": ["synthetic test fixture"],
            "out_of_scope": ["protected main branch", "host configuration"],
        },
        "acceptance_criteria": [
            {
                "criterion_id": "C-01",
                "expected_observation": "An independently executed regression test passes",
                "verification": {
                    "kind": "DETERMINISTIC",
                    "verifier_ref": "canonical-gate:test-01",
                    "evidence_kinds": ["test-log", "immutable-artifact-digest"],
                },
            }
        ],
        "execution_policy": {
            "mode": "HYBRID",
            "policy_ref": "security-policy:user-grant",
            "approval_policy_ref": "human-approval:scope-01",
            "allowed_action_ids": ["orchestration.inspect"],
            "allowed_effects": ["READ", "WRITE"],
            "authorized_ai_participants": ["agent-existing-01"],
            "limits": {
                "max_children": 2,
                "max_depth": 2,
                "max_concurrent_children": 1,
                "max_runtime_seconds": 120,
                "max_retries": 1,
                "max_tool_calls": 10,
                "max_model_requests": 4,
            },
        },
    }


def task():
    return {
        "task_id": "task-01", "criterion_ids": ["C-01"],
        "action_id": "orchestration.inspect", "effect": "READ",
        "agent_definition_ref": "agent-existing-01",
        "domain": "durable-workflow",
        "required_capabilities": ["durable_lifecycle"],
        "required_authorities": [],
        "resource_requirements": {},
        "network_envelope_ref": "network-envelope:deny-all",
        "model_intent": {"logical_route": "preauthorized-logical-route"},
    }


def preflight():
    return {
        "reuse_profile": "FA3-REUSE-DISCOVERY-001",
        "reuse_assessment_ref": "reuse:existing-assessment",
        "hardware_resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "hardware_audit_ref": "hardware-audit:cpu-only",
        "model_route_authority": "FA3-AUTH-MODEL-ROUTER-001",
        "security_policy_ref": "security:approved-scope",
    }


def evidence():
    return [{
        "criterion_id": "C-01", "verifier_ref": "canonical-gate:test-01",
        "status": "PASS", "artifact_digest": "a" * 64,
        "evidence_ref": "evidence:untrusted-reference-must-be-rechecked",
        "evidence_authority": "FA3-AUTH-OBS-EVIDENCE-001",
    }]


class GoalFoundationTests(unittest.TestCase):
    def test_intake_is_version_bound_and_no_execution(self):
        x = prepare_goal(fixture())
        self.assertEqual(x["status"], "VALIDATED_PLAN_ONLY")
        self.assertFalse(x["authority"])
        self.assertFalse(x["execution_performed"])
        self.assertEqual(x["goal_digest"], digest(fixture()))
        g = fixture()
        g["revision"] = 2
        self.assertNotEqual(digest(g), x["goal_digest"])

    def test_goal_validation_does_not_change_input(self):
        g = fixture()
        original = copy.deepcopy(g)
        self.assertEqual(validate_goal(g), original)
        self.assertEqual(g, original)

    def test_missing_verifier_fails(self):
        g = fixture()
        del g["acceptance_criteria"][0]["verification"]["verifier_ref"]
        with self.assertRaises(GoalContractError):
            validate_goal(g)

    def test_duplicate_and_unknown_verifier_fail(self):
        g = fixture()
        g["acceptance_criteria"].append(copy.deepcopy(g["acceptance_criteria"][0]))
        with self.assertRaises(GoalContractError):
            validate_goal(g)
        g = fixture()
        g["acceptance_criteria"][0]["verification"]["kind"] = "MODEL_OPINION_ONLY"
        with self.assertRaises(GoalContractError):
            validate_goal(g)

    def test_semantic_judge_must_be_independent(self):
        g = fixture()
        v = g["acceptance_criteria"][0]["verification"]
        v["kind"] = "SEMANTIC_ADVISORY_WITH_INDEPENDENT_CHECK"
        with self.assertRaises(GoalContractError):
            validate_goal(g)
        v["independent_verifier_ref"] = v["verifier_ref"]
        with self.assertRaises(GoalContractError):
            validate_goal(g)

    def test_direct_provider_secret_and_device_pins_fail(self):
        for field in ("api_key", "physical_model_id", "direct_provider_endpoint", "gpu_ordinal"):
            with self.subTest(field=field):
                g = fixture()
                g[field] = "untrusted"
                with self.assertRaises(GoalContractError):
                    validate_goal(g)

    def test_boolean_and_unbounded_budgets_fail(self):
        g = fixture()
        g["execution_policy"]["limits"]["max_retries"] = True
        with self.assertRaises(GoalContractError):
            validate_goal(g)
        g = fixture()
        g["execution_policy"]["limits"]["max_runtime_seconds"] = 0
        with self.assertRaises(GoalContractError):
            validate_goal(g)

    def test_auto_destructive_effect_denied(self):
        g = fixture()
        g["execution_policy"]["mode"] = "AUTO"
        g["execution_policy"]["allowed_effects"].append("DESTRUCTIVE")
        with self.assertRaises(GoalContractError):
            validate_goal(g)

    def test_design_only_plan_uses_real_workforce_and_workload_contracts(self):
        plan = compile_plan(ROOT, fixture(), [task()], preflight())
        self.assertEqual(plan["status"], "PLAN_ONLY_REQUIRES_EXISTING_AUTHORITY_ADMISSION")
        self.assertFalse(plan["execution_performed"])
        self.assertFalse(plan["authority"])
        self.assertEqual(plan["steps"][0]["design_route"]["specialist_id"],
                         "FA3-SPECIALIST-DURABLE-LIFECYCLE-001")
        self.assertEqual(plan["steps"][0]["workload_candidate"]["schema"],
                         "fa3.agent-workload-task.v1")
        self.assertEqual(plan["steps"][0]["runtime_admission"],
                         "PENDING_EXISTING_AUTHORITIES")

    def test_preflight_missing_authority_fails(self):
        p = preflight()
        p["model_route_authority"] = "direct-ollama"
        with self.assertRaises(GoalContractError):
            compile_plan(ROOT, fixture(), [task()], p)

    def test_no_model_or_agent_expansion(self):
        t = task()
        t["model_intent"] = {"logical_route": "a", "model_id": "unapproved"}
        with self.assertRaises(GoalContractError):
            compile_plan(ROOT, fixture(), [t], preflight())
        t = task()
        t["agent_definition_ref"] = "agent-not-authorized"
        with self.assertRaises(GoalContractError):
            compile_plan(ROOT, fixture(), [t], preflight())

    def test_no_unknown_action_or_effect(self):
        t = task()
        t["action_id"] = "shell.execute"
        with self.assertRaises(GoalContractError):
            compile_plan(ROOT, fixture(), [t], preflight())
        t = task()
        t["effect"] = "DESTRUCTIVE"
        with self.assertRaises(GoalContractError):
            compile_plan(ROOT, fixture(), [t], preflight())

    def test_no_unknown_criterion_or_unbounded_fanout(self):
        t = task()
        t["criterion_ids"] = ["C-nonexistent"]
        with self.assertRaises(GoalContractError):
            compile_plan(ROOT, fixture(), [t], preflight())
        with self.assertRaises(GoalContractError):
            compile_plan(ROOT, fixture(), [task(), {**task(), "task_id": "task-02"},
                                          {**task(), "task_id": "task-03"}], preflight())

    def test_valid_evidence_is_only_canonical_gate_candidate(self):
        plan = compile_plan(ROOT, fixture(), [task()], preflight())
        result = assess_evidence(fixture(), evidence(), plan=plan)
        self.assertEqual(result["status"], "CANONICAL_GATE_REQUIRED")
        self.assertEqual(result["criteria"][0]["status"], "READY_FOR_CANONICAL_VERIFICATION")
        self.assertFalse(result["verification_claim"])
        self.assertTrue(result["canonical_gate_required"])

    def test_forged_or_missing_provenance_never_verifies(self):
        cases = [
            [],
            [{**evidence()[0], "artifact_digest": "not-sha256"}],
            [{**evidence()[0], "evidence_ref": ""}],
            [{**evidence()[0], "evidence_authority": "agent-self"}],
            [{**evidence()[0], "verifier_ref": "agent-self"}],
        ]
        for rows in cases:
            with self.subTest(rows=rows):
                x = assess_evidence(fixture(), rows)
                self.assertEqual(x["status"], "INCOMPLETE_OR_BLOCKED")
                self.assertFalse(x["verification_claim"])

    def test_human_approval_is_not_implicitly_created(self):
        g = fixture()
        g["acceptance_criteria"][0]["verification"]["kind"] = "HUMAN"
        x = assess_evidence(g, evidence())
        self.assertEqual(x["criteria"][0]["reason"], "HUMAN_SIGNOFF_REQUIRED")

    def test_stale_revision_evidence_is_rejected(self):
        p = compile_plan(ROOT, fixture(), [task()], preflight())
        g = fixture()
        g["revision"] = 2
        with self.assertRaises(GoalContractError):
            assess_evidence(g, evidence(), plan=p)

    def test_repair_is_bounded_and_never_executes(self):
        a = assess_evidence(fixture(), [])
        first = propose_repair(fixture(), a, 0)
        self.assertEqual(first["status"], "PROPOSE_AUTHORIZED_REPAIR")
        self.assertFalse(first["effect_authorization"])
        last = propose_repair(fixture(), a, 1)
        self.assertEqual(last["status"], "ESCALATE_BUDGET_EXHAUSTED")
        self.assertFalse(last["execution_performed"])

    def test_contract_schema_has_no_new_authority(self):
        x = json.loads((ROOT / "canonical/contracts/FA3-GOAL-EXECUTION-CONTRACTS-001.schema.json").read_text())
        self.assertEqual(x["x-fa3-contract-id"], "FA3-GOAL-EXECUTION-CONTRACTS-001")
        self.assertIs(x["x-fa3-invariants"]["new_architectural_authority"], False)
        self.assertIs(x["x-fa3-invariants"]["new_capability"], False)
        self.assertEqual(x["x-fa3-invariants"]["capability_baseline"], 175)


if __name__ == "__main__":
    unittest.main()
