from __future__ import annotations

import unittest
from pathlib import Path

from src.fa3_external_rt3d_engine_exclusion_gate import (
    DECISION_PATH,
    gate,
    token_findings,
)

ROOT = Path(__file__).resolve().parents[1]


class ExternalRt3dEngineExclusionGateTests(unittest.TestCase):
    def test_repository_is_clean_and_cap027_is_provider_neutral(self):
        result = gate(ROOT)
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual("Realtime / Virtual Production Interchange", result["capability_027_subject"])
        self.assertEqual(0, result["capability_count_delta"])
        self.assertEqual(0, result["architectural_authority_delta"])

    def test_forbidden_engine_tokens_are_rejected_outside_tombstone(self):
        token = "Un" + "realEditor"
        self.assertTrue(token_findings("src/provider.py", f"launch {token}"))
        self.assertTrue(token_findings("docs/ue5-integration.md", "legacy"))
        self.assertTrue(token_findings("src/provider.py", "Epic Games runtime registration"))
        self.assertEqual([], token_findings(DECISION_PATH.as_posix(), f"excluded {token}"))


if __name__ == "__main__":
    unittest.main()
