from pathlib import Path
import unittest
from fa3_creative_operations_dashboard_gate import gate

ROOT=Path(__file__).resolve().parents[1]
class CreativeOperationsDashboardGateTests(unittest.TestCase):
    def test_gate(self):
        r=gate(ROOT)
        self.assertEqual("PASS",r["result"],r)
        self.assertFalse(r["current_host_runtime_promotion_claim"])
if __name__=="__main__": unittest.main()
