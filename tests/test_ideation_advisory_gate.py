from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_ideation_advisory import build_projection, self_check  # noqa: E402
from fa3_ideation_advisory_gate import validate  # noqa: E402


class IdeationAdvisoryGateTest(unittest.TestCase):
    def test_self_check(self) -> None:
        self_check()

    def test_canonical_gate(self) -> None:
        self.assertEqual(validate(), [])

    def test_ideas_are_hypotheses(self) -> None:
        projection = build_projection({"mode": "IDEATE", "problem": "Explore", "candidates": ["A", "B"]})
        self.assertTrue(all(c["semantic_status"] == "HYPOTHESIS" for c in projection["candidates"]))
        self.assertFalse(projection["semantic_boundaries"]["idea_is_fact"])

    def test_recommendation_is_not_decision(self) -> None:
        projection = build_projection({
            "mode": "RECOMMEND", "problem": "Choose",
            "evidence": [{"ref": "E1", "claim": "Observed", "status": "VERIFIED"}],
            "requested_recommendation": "A",
        })
        self.assertEqual(projection["recommendation"]["semantic_status"], "RECOMMENDATION_NOT_DECISION")
        self.assertTrue(projection["recommendation"]["decision_required"])
        self.assertFalse(projection["authority"]["decision_authority"])

    def test_missing_evidence_fails_closed_to_unverified(self) -> None:
        projection = build_projection({
            "mode": "RECOMMEND", "problem": "Choose without evidence", "requested_recommendation": "A",
        })
        self.assertEqual(projection["recommendation"]["evidence_status"], "UNVERIFIED")
        self.assertEqual(projection["recommendation"]["confidence"], "LOW")

    def test_conflict_remains_visible(self) -> None:
        projection = build_projection({
            "mode": "RISK_ASSESSMENT", "problem": "Conflicting sources",
            "evidence": [{"ref": "E2", "claim": "Conflict", "status": "CONFLICTED"}],
        })
        self.assertEqual(projection["recommendation"]["evidence_status"], "CONFLICTED")
        self.assertEqual(projection["recommendation"]["conflict_refs"], ["E2"])

    def test_high_impact_requires_inspector_handoff(self) -> None:
        projection = build_projection({"mode": "RECOMMEND", "problem": "High-impact change", "high_impact": True})
        targets = {item["target"] for item in projection["delegations"]}
        self.assertIn("FA3-INSPECTOR-001", targets)

    def test_no_direct_execution_or_repository_write(self) -> None:
        projection = build_projection({"mode": "RECOMMEND", "problem": "Actionable change", "actionable_request": True})
        authority = projection["authority"]
        self.assertFalse(authority["direct_tool_execution_allowed"])
        self.assertFalse(authority["direct_agent_execution_allowed"])
        self.assertFalse(authority["direct_repository_write_allowed"])
        self.assertFalse(authority["direct_production_mutation_allowed"])


if __name__ == "__main__":
    unittest.main()
