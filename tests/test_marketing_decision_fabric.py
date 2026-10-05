from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_marketing_decision_fabric import (
    DecisionRequest,
    MarketingDecisionError,
    decide,
)


class MarketingDecisionFabricTests(unittest.TestCase):
    def request(self, **changes):
        values = {
            "decision_id": "decision-1",
            "kind": "CANDIDATE_RANKING",
            "scope": "marketing.segment.preview",
            "candidates": (
                {"id": "b", "priority": 1, "relevance": 0.5},
                {"id": "a", "priority": 2, "relevance": 0.2},
            ),
        }
        values.update(changes)
        return DecisionRequest(**values)

    def test_deterministic_policy_rank_and_receipt(self):
        first = decide(self.request())
        second = decide(self.request())
        self.assertEqual(["a"], first["selected_ids"])
        self.assertEqual(first["receipt_digest"], second["receipt_digest"])
        self.assertFalse(first["advisory_provider_is_authority"])
        self.assertFalse(first["candidate_expansion"])

    def test_advisory_cannot_expand_candidate_set(self):
        with self.assertRaises(MarketingDecisionError) as error:
            decide(self.request(), advisory=lambda ids, signals: [*ids, "injected"])
        self.assertEqual("MDF-ADVISORY-EXPANSION", error.exception.code)

    def test_policy_filter_runs_before_advisory(self):
        seen = []
        request = self.request(candidates=(
            {"id": "allowed", "eligible": True},
            {"id": "blocked", "suppressed": True},
        ))
        receipt = decide(request, advisory=lambda ids, signals: seen.extend(ids) or list(ids))
        self.assertEqual(["allowed"], seen)
        self.assertEqual([{"id": "blocked", "reason": "suppressed"}], receipt["rejected"])

    def test_empty_and_duplicate_candidates_fail_closed(self):
        with self.assertRaises(MarketingDecisionError):
            decide(self.request(candidates=()))
        with self.assertRaises(MarketingDecisionError):
            decide(self.request(candidates=({"id": "x"}, {"id": "x"})))

    def test_semantic_validation_retries_then_stops(self):
        retry = decide(self.request(signals={"semantic_valid": False}, attempt=0, max_attempts=1))
        stopped = decide(self.request(signals={"semantic_valid": False}, attempt=1, max_attempts=1))
        self.assertEqual("RETRY", retry["outcome"])
        self.assertEqual("STOP_FAILED", stopped["outcome"])

    def test_context_envelope_is_bounded_and_digest_bound(self):
        context = tuple({"id": f"ctx-{index}", "relevance": index} for index in range(40))
        receipt = decide(self.request(context=context))
        envelope = receipt["context_envelope"]
        self.assertEqual(32, len(envelope["selected"]))
        self.assertEqual(8, len(envelope["rejected"]))
        self.assertTrue(envelope["digest"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
