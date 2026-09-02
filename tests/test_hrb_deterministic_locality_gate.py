import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_hrb_deterministic_locality_gate import evaluate


class HrbDeterministicLocalityGateTests(unittest.TestCase):
    def test_reference_gate_passes(self):
        result = evaluate(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["summary"], {"passed": 22, "total": 22})
        self.assertFalse(result["current_host_runtime_promotion_claim"])

    def test_authority_and_capability_count_are_preserved(self):
        result = evaluate(ROOT)
        by_name = {item["name"]: item for item in result["checks"]}
        self.assertEqual(by_name["capability-count-stable"]["status"], "PASS")
        self.assertEqual(by_name["no-new-authority"]["status"], "PASS")
        self.assertEqual(by_name["hrb-authority-preserved"]["status"], "PASS")

    def test_no_false_current_host_locality_claim(self):
        result = evaluate(ROOT)
        by_name = {item["name"]: item for item in result["checks"]}
        self.assertEqual(by_name["current-host-claim-honest"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
