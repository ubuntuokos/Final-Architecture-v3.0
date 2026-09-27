import unittest
from pathlib import Path

from fa3_reproducibility_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]


class ReproducibilityGateTests(unittest.TestCase):
    def test_gate_passes_and_has_no_runtime_claim(self):
        result = evaluate(ROOT)
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual({"passed": 18, "total": 18}, result["summary"])
        self.assertFalse(result["current_host_runtime_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
