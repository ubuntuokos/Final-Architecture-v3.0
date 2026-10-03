from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_scp_gate import REQUIRED, evaluate_request, gate  # noqa: E402


class ScpFabricTests(unittest.TestCase):
    def allow_context(self):
        return {key: True for key in REQUIRED}

    def test_default_deny(self):
        self.assertEqual(evaluate_request({})["decision"], "DENY")

    def test_complete_internal_context_can_allow(self):
        self.assertEqual(evaluate_request(self.allow_context())["decision"], "ALLOW")

    def test_external_requires_explicit_permission(self):
        ctx = dict(self.allow_context(), traffic_class="EXTERNAL_EGRESS")
        self.assertEqual(evaluate_request(ctx)["decision"], "DENY")
        ctx["external_permission"] = True
        self.assertEqual(evaluate_request(ctx)["decision"], "ALLOW")

    def test_ai_off_blocks_provider_egress(self):
        ctx = dict(
            self.allow_context(),
            traffic_class="EXTERNAL_EGRESS",
            external_permission=True,
            ai_request=True,
            ai_enabled=False,
            provider_admitted=True,
            model_route_approved=True,
        )
        result = evaluate_request(ctx)
        self.assertEqual(result["decision"], "DENY")
        self.assertIn("AI_POLICY_DENY:ai_enabled", result["reasons"])

    def test_static_materialization_gate(self):
        result = gate(ROOT)
        self.assertEqual(result["result"], "PASS", result["findings"])
        self.assertEqual(result["capability_baseline"], 175)
        self.assertFalse(result["runtime_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
