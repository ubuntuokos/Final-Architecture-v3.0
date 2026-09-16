from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_accelerator_guard import (  # noqa: E402
    AcceleratorProcess,
    NO_CONTENTION,
    OBSERVABILITY_INSUFFICIENT,
    PRE_EXISTING_EXTERNAL_OCCUPANCY,
    RUNTIME_EXTERNAL_CONTENTION,
    Snapshot,
    classify,
    decide,
)


class AcceleratorGuardTests(unittest.TestCase):
    def snapshot(self, *pids: int, observable: bool = True) -> Snapshot:
        return Snapshot(
            observable=observable,
            processes=tuple(
                AcceleratorProcess("NVIDIA", "GPU-test", pid, f"p{pid}", 100)
                for pid in pids
            ),
        )

    def test_no_contention(self):
        owned = {101}
        self.assertEqual(classify(self.snapshot(101), self.snapshot(101), owned), NO_CONTENTION)
        decision = decide(NO_CONTENTION)
        self.assertFalse(decision["user_decision_required"])
        self.assertFalse(decision["automatic_resolution"])

    def test_preexisting_external_occupancy(self):
        state = classify(self.snapshot(777), self.snapshot(777), {101})
        self.assertEqual(state, PRE_EXISTING_EXTERNAL_OCCUPANCY)
        decision = decide(state)
        self.assertEqual(decision["action"], "NOTIFY_AND_REQUIRE_USER_DECISION")
        self.assertTrue(decision["user_decision_required"])

    def test_runtime_external_contention(self):
        state = classify(self.snapshot(101), self.snapshot(101, 888), {101})
        self.assertEqual(state, RUNTIME_EXTERNAL_CONTENTION)
        decision = decide(state)
        self.assertEqual(decision["mode"], "RECOMMEND")
        self.assertFalse(decision["automatic_resolution"])

    def test_observability_insufficient(self):
        state = classify(self.snapshot(observable=False), self.snapshot(), set())
        self.assertEqual(state, OBSERVABILITY_INSUFFICIENT)
        self.assertEqual(decide(state)["action"], "RECOMMEND_OBSERVABILITY_REMEDIATION")

    def test_default_never_auto_resolves(self):
        for state in (PRE_EXISTING_EXTERNAL_OCCUPANCY, RUNTIME_EXTERNAL_CONTENTION):
            decision = decide(state)
            self.assertEqual(decision["mode"], "RECOMMEND")
            self.assertTrue(decision["user_decision_required"])
            self.assertFalse(decision["automatic_resolution"])
            self.assertFalse(decision["destructive_action_authorized"])

    def test_explicit_policy_can_select_bounded_automatic_resolution(self):
        policy = {
            "explicit_user_policy": True,
            "created_before_conflict": True,
            "automatic_resolution": True,
            "policy_id": "USER-POLICY-ACCEL-001",
            "bounded_action": "DEFER_FA3_WORKLOAD",
        }
        decision = decide(RUNTIME_EXTERNAL_CONTENTION, policy)
        self.assertEqual(decision["action"], "APPLY_EXPLICIT_POLICY")
        self.assertTrue(decision["automatic_resolution"])
        self.assertFalse(decision["destructive_action_authorized"])

    def test_incomplete_policy_does_not_enable_automation(self):
        policy = {"explicit_user_policy": True, "automatic_resolution": True}
        decision = decide(RUNTIME_EXTERNAL_CONTENTION, policy)
        self.assertEqual(decision["mode"], "RECOMMEND")
        self.assertTrue(decision["user_decision_required"])
        self.assertFalse(decision["automatic_resolution"])


if __name__ == "__main__":
    unittest.main()
