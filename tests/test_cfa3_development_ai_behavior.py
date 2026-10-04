import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cfa3_development_ai_behavior_guard import RULE_IDS, authorize_action

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
        self.assertEqual(10, len(policy["development_rules"]))
        self.assertEqual(10, len(policy["ai_behavior_rules"]))
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

    def test_silent_redesign_blocks(self):
        ctx = base_context("PLAN")
        ctx["silent_redesign_or_repair"] = True
        result = authorize_action(ctx)
        self.assertEqual("STOP", result["decision"])
        self.assertIn("DEV-09", result["rule_ids"])


if __name__ == "__main__":
    unittest.main()
