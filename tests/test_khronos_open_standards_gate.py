import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_khronos_open_standards_gate import EXPECTED,gate
from fa3_khronos_adapters import load_registry
class KhronosOpenStandardsTests(unittest.TestCase):
 def test_static_gate(self):
  r=gate(ROOT);self.assertEqual("PASS",r["result"],r["findings"]);self.assertEqual(0,r["capability_delta"]);self.assertEqual(0,r["authority_delta"]);self.assertFalse(r["current_host_runtime_promotion_claim"])
 def test_pin_inventory(self):
  self.assertEqual(15,len(EXPECTED))
 def test_adapter_registry_non_authoritative(self):
  r=load_registry(ROOT);self.assertTrue(r["adapters"]);self.assertTrue(all(x["authority"] is False for x in r["adapters"]))
if __name__=="__main__":unittest.main()
