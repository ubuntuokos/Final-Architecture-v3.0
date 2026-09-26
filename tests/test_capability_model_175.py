from pathlib import Path
import unittest

from fa3_capability_model_175_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]

class CapabilityModel175Tests(unittest.TestCase):
    def test_capability_model_175_is_consistent(self):
        result = evaluate(ROOT)
        self.assertEqual(result["result"], "PASS", result)

if __name__ == "__main__":
    unittest.main()
