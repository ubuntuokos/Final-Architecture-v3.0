import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_kdenlive_editorial_gate import gate, RULES

class KdenliveEditorialGateTests(unittest.TestCase):
    def test_rule_set_is_complete(self):
        self.assertEqual(len(RULES), 16)
        self.assertIn("OTIO_CANONICAL_TIMELINE_IR", RULES)
        self.assertIn("API_FIRST_EDITORIAL_AUTOMATION", RULES)
        self.assertIn("CRITICAL_EDITORIAL_MUTATION_REQUIRES_HITL", RULES)
        self.assertIn("KDENLIVE_NOT_HARD_BACKEND_DEPENDENCY", RULES)

    def test_canonical_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["capability_count"], 143)
        self.assertEqual(report["rules_checked"], 16)

if __name__ == "__main__":
    unittest.main()
