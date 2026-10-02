import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_workload_mode_current_host_gate import gate
class WorkloadModeCurrentHostGateTests(unittest.TestCase):
 def test_scoped_receipt_passes_without_overclaim(self):
  r={"schema":"fa3.workload-mode-current-host-receipt.v1","result":"PASS","source_sha":"a"*40,"capability_count":175,"global_promotion_claim":False,"status":{"fa3_state":"CONNECTED","authority":"FA3_HRB"},"systemd_cgroup_resource_mutation_proven":False,"vendor_gpu_telemetry_proven":False}
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"r.json";p.write_text(json.dumps(r));out=gate(p,"a"*40);self.assertEqual("PASS",out["result"],out["findings"]);self.assertFalse(out["global_promotion_claim"])
 def test_global_overclaim_fails(self):
  r={"schema":"fa3.workload-mode-current-host-receipt.v1","result":"PASS","source_sha":"a"*40,"capability_count":175,"global_promotion_claim":True,"status":{"fa3_state":"CONNECTED","authority":"FA3_HRB"},"systemd_cgroup_resource_mutation_proven":False,"vendor_gpu_telemetry_proven":False}
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"r.json";p.write_text(json.dumps(r));self.assertEqual("FAIL",gate(p,"a"*40)["result"])
if __name__=="__main__":unittest.main()
