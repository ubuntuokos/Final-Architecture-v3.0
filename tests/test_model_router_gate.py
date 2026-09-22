import unittest
from pathlib import Path

from fa3_model_router_gate import gate


class ModelRouterGateTests(unittest.TestCase):
    def test_repository_materialization(self):
        root = Path(__file__).resolve().parents[1]
        report = gate(root)
        self.assertEqual(report["result"], "PASS", report)


if __name__ == "__main__":
    unittest.main()
