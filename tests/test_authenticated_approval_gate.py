import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_authenticated_approval_gate import evaluate


class AuthenticatedApprovalGateTests(unittest.TestCase):
    def test_gate_passes_without_runtime_promotion_claim(self):
        result = evaluate(ROOT)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["summary"], {"passed": 15, "total": 15})
        self.assertFalse(result["current_host_runtime_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
