import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cfa3_development_ai_behavior_guard import RULE_IDS, authorize_action, authorize_development_action

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


def development_context(action="WRITE"):
    ctx = base_context(action)
    ctx["development_work_status"] = {
        "long_or_multi_operation_task": False,
        "initial_notice_sent_before_first_substantive_action": False,
        "entering_new_long_phase": False,
        "phase_notice_sent_before_start": False,
        "blocker_detected": False,
        "unexpected_github_state": False,
        "security_sensitive_operation": False,
        "special_notice_sent_before_operation": False,
        "long_github_sequence": False,
        "status_update_due": False,
        "status_update_sent": False,
    }
    return ctx


class Cfa3DevelopmentAiBehaviorTests(unittest.TestCase):
    def test_policy_has_exact_rule_sets_and_layering(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual("CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001", policy["id"])
        self.assertEqual(175, policy["capability_baseline"])
        self.assertEqual(0, policy["capability_delta"])
        self.assertEqual(0, policy["architectural_authority_delta"])
        self.assertEqual(15, len(policy["development_rules"]))
        self.assertEqual(11, len(policy["ai_behavior_rules"]))
        self.assertTrue(policy["scope"]["fa3_development_process"])
        self.assertTrue(policy["scope"]["cfa3_development_process"])
        self.assertEqual(["DEV-12", "DEV-13", "DEV-14", "DEV-15"], policy["development_work_status_protocol"]["rule_ids"])
        self.assertEqual(["DEV-11", "AI-11"], policy["self_correction_exception"]["ids"])
        self.assertEqual({"L0", "L1", "L2", "L3", "L4", "L5"},
                         {layer["level"] for layer in policy["layers"]})
        observed = {r["id"] for r in policy["development_rules"] + policy["ai_behavior_rules"]}
        self.assertEqual(RULE_IDS, observed)
        self.assertTrue(policy["composition"]["layers_are_distinct"])
        self.assertEqual("BLOCKER", policy["composition"]["contradiction_result"])

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


    def test_long_task_requires_notice_before_first_substantive_operation(self):
        ctx = development_context()
        ctx["development_work_status"]["long_or_multi_operation_task"] = True
        result = authorize_development_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-12", result["rule_ids"])
        ctx["development_work_status"]["initial_notice_sent_before_first_substantive_action"] = True
        self.assertEqual("ALLOW", authorize_development_action(ctx)["decision"])

    def test_new_long_phase_requires_fresh_prenotice(self):
        ctx = development_context()
        status = ctx["development_work_status"]
        status["entering_new_long_phase"] = True
        result = authorize_development_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-13", result["rule_ids"])
        status["phase_notice_sent_before_start"] = True
        self.assertEqual("ALLOW", authorize_development_action(ctx)["decision"])

    def test_security_sensitive_operation_requires_separate_prenotice(self):
        ctx = development_context()
        status = ctx["development_work_status"]
        status["security_sensitive_operation"] = True
        result = authorize_development_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-14", result["rule_ids"])
        status["special_notice_sent_before_operation"] = True
        self.assertEqual("ALLOW", authorize_development_action(ctx)["decision"])

    def test_blocker_notice_does_not_override_blocker_stop(self):
        ctx = development_context()
        ctx["blocker_kind"] = "UNEXPECTED_GITHUB_STATE"
        status = ctx["development_work_status"]
        status["blocker_detected"] = True
        status["unexpected_github_state"] = True
        status["special_notice_sent_before_operation"] = True
        result = authorize_development_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-01", result["rule_ids"])

    def test_long_github_sequence_cannot_run_silently(self):
        ctx = development_context()
        status = ctx["development_work_status"]
        status["long_github_sequence"] = True
        status["status_update_due"] = True
        result = authorize_development_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-15", result["rule_ids"])
        status["status_update_sent"] = True
        allowed = authorize_development_action(ctx)
        self.assertEqual("ALLOW", allowed["decision"])
        self.assertTrue(allowed["development_work_status_protocol_passed"])

    def test_development_preflight_fails_closed_without_work_status(self):
        result = authorize_development_action(base_context("WRITE"))
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-12", result["rule_ids"])
        self.assertIn("AI-09", result["rule_ids"])


if __name__ == "__main__":
    unittest.main()
