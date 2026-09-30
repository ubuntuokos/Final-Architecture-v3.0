from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from fa3_provider_model_gateway_assurance_gate import evaluate
class ProviderModelGatewayAssuranceTests(unittest.TestCase):
 def test_static_assurance_contract(self): self.assertEqual(evaluate()["result"],"PASS",evaluate()["findings"])
if __name__=="__main__": unittest.main()
