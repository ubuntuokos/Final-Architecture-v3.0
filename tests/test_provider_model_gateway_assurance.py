from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from fa3_provider_model_gateway_assurance_gate import evaluate
class ProviderModelGatewayAssuranceTests(unittest.TestCase):
 def test_static_assurance_contract(self):
  result=evaluate()
  self.assertEqual(result["result"],"PASS",result["findings"])
  self.assertEqual(result["capability_count"],175)
  self.assertEqual(result["evaluated_donor_patterns"],2)
  self.assertFalse(result["runtime_promotion"])
if __name__=="__main__": unittest.main()
