import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cfa3_development_ai_behavior_guard import RULE_IDS, authorize_action, authorize_development_task_continuity

POLICY = ROOT / "canonical/CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001.json"


def base_context(action="READ"):
    ctx = {
        "action": action,
        "current_owner_restriction_allows": True,
        "scope_bound": True,
        "scope_allows_action": True,
        "uncertain_state": False,
        "blocker_kind": None,
        "autonomous_workaround": False,
        "fresh_state_verified": True,
        "mutation_report_pending": False,
        "side_effect_permission": action if action not in {"READ", "ANALYZE", "PLAN"} else None,
        "workflow_or_gate_required_for_closure": True,
        "equivalent_run_active": False,
        "exact_head_match": True,
        "exact_base_match": True,
        "silent_redesign_or_repair": False,
    }
    return ctx


class Cfa3DevelopmentAiBehaviorTests(unittest.TestCase):
    def test_policy_has_exact_rule_sets_and_layering(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual("CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001", policy["id"])
        self.assertEqual(175, policy["capability_baseline"])
        self.assertEqual(0, policy["capability_delta"])
        self.assertEqual(0, policy["architectural_authority_delta"])
        self.assertEqual(12, len(policy["development_rules"]))
        self.assertEqual(11, len(policy["ai_behavior_rules"]))
        self.assertEqual(["DEV-11", "AI-11"], policy["self_correction_exception"]["ids"])
        self.assertEqual({"L0", "L1", "L2", "L3", "L4", "L5"},
                         {layer["level"] for layer in policy["layers"]})
        observed = {r["id"] for r in policy["development_rules"] + policy["ai_behavior_rules"]}
        self.assertEqual(RULE_IDS, observed)
        self.assertTrue(policy["composition"]["layers_are_distinct"])
        self.assertEqual("BLOCKER", policy["composition"]["contradiction_result"])
        self.assertTrue(policy["scope"]["fa3_development_process"])
        self.assertTrue(policy["scope"]["cfa3_development_process"])
        self.assertTrue(policy["task_continuity"]["main_task_remains_primary"])
        self.assertTrue(policy["task_continuity"]["task_switch_requires_explicit_current_owner_directive"])


    def test_new_rule_remains_constraint_on_active_main_task(self):
        result = authorize_development_task_continuity({
            "main_task_id": "main-task",
            "current_task_id": "main-task",
            "action_serves_main_task": True,
            "task_switch_requested": False,
            "explicit_owner_task_switch": False,
            "diversion_trigger": "NEW_RULE",
        })
        self.assertEqual("ALLOW", result["decision"])
        self.assertTrue(result["main_task_preserved"])
        self.assertEqual("ACTIVE_MAIN_TASK_CONSTRAINT", result["disposition"])

    def test_parallel_pr_monitoring_cannot_become_main_task(self):
        result = authorize_development_task_continuity({
            "main_task_id": "main-task",
            "current_task_id": "parallel-pr-task",
            "action_serves_main_task": False,
            "task_switch_requested": True,
            "explicit_owner_task_switch": False,
            "diversion_trigger": "PARALLEL_PR",
        })
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-12", result["rule_ids"])

    def test_explicit_owner_can_authorize_main_task_switch_but_rebind_is_required(self):
        result = authorize_development_task_continuity({
            "main_task_id": "main-task",
            "current_task_id": "new-main-task",
            "action_serves_main_task": False,
            "task_switch_requested": True,
            "explicit_owner_task_switch": True,
            "diversion_trigger": "OTHER",
        })
        self.assertEqual("ALLOW", result["decision"])
        self.assertTrue(result["main_task_switch_authorized"])
        self.assertTrue(result["requires_main_task_rebind_before_execution"])

    def test_parallel_blocker_does_not_require_main_task_reassignment(self):
        continuity = authorize_development_task_continuity({
            "main_task_id": "main-task",
            "current_task_id": "main-task",
            "action_serves_main_task": True,
            "task_switch_requested": False,
            "explicit_owner_task_switch": False,
            "diversion_trigger": "PARALLEL_PR",
        })
        self.assertEqual("ALLOW", continuity["decision"])
        self.assertTrue(continuity["main_task_preserved"])
        ctx = base_context("WRITE")
        ctx["blocker_kind"] = "OVERLAP"
        blocked = authorize_action(ctx)
        self.assertEqual("STOP", blocked["decision"])
        self.assertIn("DEV-05", blocked["rule_ids"])

    def test_basic_read_allowed(self):
        result = authorize_action(base_context("READ"))
        self.assertEqual("ALLOW", result["decision"])

    def test_mutation_requires_fresh_state(self):
        ctx = base_context("WRITE")
        ctx["fresh_state_verified"] = False
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-04", result["rule_ids"])

    def test_overlap_is_blocker(self):
        ctx = base_context("WRITE")
        ctx["blocker_kind"] = "OVERLAP"
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-05", result["rule_ids"])
        self.assertIn("AI-01", result["rule_ids"])

    def test_explicit_conversation_bound_overlap_override(self):
        ctx = base_context("WRITE")
        ctx["blocker_kind"] = "OVERLAP"
        ctx["owner_override"] = {
            "rule_ids": ["DEV-05", "AI-01"],
            "explicit": True,
            "conversation_bound": True,
            "scope_matches": True,
        }
        result = authorize_action(ctx)
        self.assertEqual("ALLOW", result["decision"])
        self.assertEqual(["AI-01", "DEV-05"], result["applied_owner_overrides"])

    def test_generic_approval_cannot_become_override(self):
        ctx = base_context("WRITE")
        ctx["blocker_kind"] = "OVERLAP"
        ctx["owner_override"] = {
            "rule_ids": ["DEV-05", "AI-01"],
            "explicit": False,
            "conversation_bound": True,
            "scope_matches": True,
        }
        self.assertEqual("STOP", authorize_action(ctx)["decision"])

    def test_duplicate_workflow_run_blocks(self):
        ctx = base_context("WORKFLOW")
        ctx["equivalent_run_active"] = True
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-06", result["rule_ids"])

    def test_workflow_not_needed_for_closure_blocks(self):
        ctx = base_context("GATE")
        ctx["workflow_or_gate_required_for_closure"] = False
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-06", result["rule_ids"])

    def test_merge_requires_exact_head_and_base(self):
        ctx = base_context("MERGE")
        ctx["exact_head_match"] = False
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-08", result["rule_ids"])
        self.assertIn("AI-08", result["rule_ids"])

    def test_previous_mutation_report_is_mandatory(self):
        ctx = base_context("COMMIT")
        ctx["mutation_report_pending"] = True
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-07", result["rule_ids"])

    def test_current_owner_restriction_wins(self):
        ctx = base_context("WRITE")
        ctx["current_owner_restriction_allows"] = False
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-10", result["rule_ids"])
        self.assertIn("AI-10", result["rule_ids"])

    def test_unknown_action_fails_closed(self):
        ctx = base_context("READ")
        ctx["action"] = "INVENTED"
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("AI-09", result["rule_ids"])


    def test_self_correction_allows_own_deterministic_mechanical_error(self):
        ctx = base_context("WRITE")
        ctx["self_correction"] = {
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
        }
        result = authorize_action(ctx)
        self.assertEqual("ALLOW", result["decision"])
        self.assertTrue(result["self_correction_authorized"])
        self.assertTrue(result["post_correction_report_required"])

    def test_self_correction_requires_exact_state_after_possible_partial_mutation(self):
        ctx = base_context("WRITE")
        ctx["self_correction"] = {
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
            "partial_mutation_possible": True,
            "exact_state_verified": False,
        }
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-11", result["rule_ids"])
        self.assertIn("AI-11", result["rule_ids"])
        self.assertIn("AI-08", result["rule_ids"])

    def test_self_correction_cannot_hide_redesign_or_new_side_effect(self):
        ctx = base_context("WRITE")
        ctx["self_correction"] = {
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
            "redesign_required": True,
            "new_permission_or_side_effect_required": True,
        }
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-11", result["rule_ids"])
        self.assertIn("AI-11", result["rule_ids"])

    def test_self_correction_requires_notification(self):
        ctx = base_context("WRITE")
        ctx["self_correction"] = {
            "requested": True,
            "error_caused_by_ai": True,
            "mechanical_or_technical": True,
            "correction_deterministic": True,
            "user_intent_preserved": True,
            "scope_preserved": True,
            "architecture_authority_policy_plan_preserved": True,
            "no_new_component_workaround": True,
            "notification_sent": False,
            "existing_authorization_covers_corrected_action": True,
        }
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-11", result["rule_ids"])
        self.assertIn("AI-11", result["rule_ids"])


    def test_missing_blocker_fact_fails_closed(self):
        ctx = base_context("WRITE")
        ctx.pop("blocker_kind")
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("AI-09", result["rule_ids"])

    def test_owner_override_booleans_are_type_strict(self):
        ctx = base_context("WRITE")
        ctx["fresh_state_verified"] = False
        ctx["owner_override"] = {
            "rule_ids": ["DEV-04", "AI-04"],
            "explicit": "false",
            "conversation_bound": "false",
            "scope_matches": "false",
        }
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("AI-09", result["rule_ids"])

    def test_current_owner_restriction_cannot_be_overridden(self):
        ctx = base_context("WRITE")
        ctx["current_owner_restriction_allows"] = False
        ctx["owner_override"] = {
            "rule_ids": ["DEV-10", "AI-10"],
            "explicit": True,
            "conversation_bound": True,
            "scope_matches": True,
        }
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-10", result["rule_ids"])
        self.assertIn("AI-10", result["rule_ids"])

    def test_dormant_override_is_not_reported_as_applied(self):
        ctx = base_context("READ")
        ctx["owner_override"] = {
            "rule_ids": ["DEV-05", "AI-01"],
            "explicit": True,
            "conversation_bound": True,
            "scope_matches": True,
        }
        result = authorize_action(ctx)
        self.assertEqual("ALLOW", result["decision"])
        self.assertEqual([], result["applied_owner_overrides"])

    def test_behavior_preflight_never_claims_effect_authority(self):
        result = authorize_action(base_context("WRITE"))
        self.assertEqual("ALLOW", result["decision"])
        self.assertTrue(result["policy_preflight_passed"])
        self.assertFalse(result["side_effect_authorized"])
        self.assertTrue(result["effect_authority_required"])

    def test_silent_redesign_blocks(self):
        ctx = base_context("PLAN")
        ctx["silent_redesign_or_repair"] = True
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-09", result["rule_ids"])


if __name__ == "__main__":
    unittest.main()
