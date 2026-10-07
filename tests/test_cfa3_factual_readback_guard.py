from __future__ import annotations

import unittest

from src.cfa3_factual_readback_guard import POLICY_ID, evaluate_readback


class FactualReadbackGuardTests(unittest.TestCase):
    def _valid(self) -> dict:
        return {
            "task_id": "task-1",
            "prior_state_required": True,
            "source_refs": ["github:main@61ea39772a1eb7ac8d11b05303895cab5dfbb022"],
            "readback_complete": True,
            "reanalysis_complete": True,
            "current_state_verified": True,
            "contradictions": [],
            "unknown_facts": [],
            "scope_guard_passed": True,
        }

    def test_valid_continuation_passes_without_effect_authority(self) -> None:
        result = evaluate_readback(self._valid())
        self.assertEqual(POLICY_ID, result["policy_id"])
        self.assertEqual("ALLOW_CONTINUATION", result["decision"])
        self.assertTrue(result["pass"])
        self.assertFalse(result["effect_authority_granted"])

    def test_memory_only_or_missing_source_refs_block(self) -> None:
        record = self._valid()
        record["source_refs"] = []
        result = evaluate_readback(record)
        self.assertEqual("BLOCKER_STOP", result["decision"])
        self.assertEqual("FACTUAL_SOURCE_REFS_REQUIRED", result["reason"])

    def test_incomplete_readback_blocks(self) -> None:
        record = self._valid()
        record["readback_complete"] = False
        result = evaluate_readback(record)
        self.assertEqual("BLOCKER_STOP", result["decision"])
        self.assertIn("readback_complete", result["missing"])

    def test_unresolved_contradiction_blocks(self) -> None:
        record = self._valid()
        record["contradictions"] = [{"id": "c1", "resolved": False}]
        result = evaluate_readback(record)
        self.assertEqual("UNRESOLVED_CONTRADICTION", result["reason"])

    def test_unknown_fact_blocks(self) -> None:
        record = self._valid()
        record["unknown_facts"] = ["previous execution state"]
        result = evaluate_readback(record)
        self.assertEqual("UNKNOWN_FACTS_REMAIN", result["reason"])

    def test_self_contained_new_task_does_not_require_readback(self) -> None:
        record = self._valid()
        record["prior_state_required"] = False
        record["source_refs"] = []
        record["readback_complete"] = False
        record["reanalysis_complete"] = False
        record["current_state_verified"] = False
        record["scope_guard_passed"] = False
        result = evaluate_readback(record)
        self.assertEqual("NEW_TASK_NO_READBACK_REQUIRED", result["decision"])
        self.assertTrue(result["pass"])
        self.assertFalse(result["effect_authority_granted"])


if __name__ == "__main__":
    unittest.main()
