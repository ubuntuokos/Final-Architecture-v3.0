from __future__ import annotations

import unittest
from pathlib import Path

from fa3_canonical_language_gate import run_conformance

ROOT = Path(__file__).resolve().parents[1]


class CanonicalLanguageGateTests(unittest.TestCase):
    def test_canonical_machine_language_contract_passes(self):
        report = run_conformance(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertFalse(report["current_host_production_claim"])
        self.assertEqual(report["passed"], report["total"])


if __name__ == "__main__":
    unittest.main()
