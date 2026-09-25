import json,unittest
from pathlib import Path
from fa3_wan22_gate import gate
ROOT=Path(__file__).resolve().parents[1]
class Wan22GateTests(unittest.TestCase):
 def test_static_gate_passes(self):self.assertEqual(gate()["result"],"PASS")
 def test_provider_is_free_open_candidate_not_authority(self):
  p=json.loads((ROOT/"canonical/providers/FA3-PROVIDER-WAN22-001.json").read_text())
  self.assertFalse(p["architectural_authority"]);self.assertEqual(p["execution"]["cost_class"],"FREE_LOCAL");self.assertEqual(p["current_host_production_evidence"],"PENDING")
if __name__=="__main__":unittest.main()
