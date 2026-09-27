import json,tempfile,unittest
from pathlib import Path
from fa3_wan22_current_host_gate import gate
ROOT=Path(__file__).resolve().parents[1]
PIN="1ea34ff48f87168174e12956e200b1d908b1c5ff"
class Wan22CurrentHostGateTests(unittest.TestCase):
 def test_missing_receipts_fail_closed(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)
   self.assertEqual(gate(ROOT,p/"m.json",p/"a.json")["result"],"FAIL")
 def test_bound_real_receipts_pass(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);a=p/"a.json";m=p/"m.json"
   a.write_text(json.dumps({"schema":"fa3.wan22-provider-admission-receipt.v1","provider_id":"FA3-PROVIDER-WAN22-001","status":"PASS","source_revision":PIN,"license_decision":"ALLOW","network_fetch_performed":False,"auto_install_performed":False,"current_host_runtime_execution_claim":False}))
   m.write_text(json.dumps({"schema":"fa3.motion-video-execution-receipt.v1","status":"PASS","provider_id":"FA3-PROVIDER-WAN22-001","evidence_scope":"REAL_PROVIDER_CURRENT_HOST","synthetic_or_mock_provider":False,"cost_class":"FREE_LOCAL","execution_topology":"LOCAL","requires_accelerator":True,"hrb_receipt_sha256":"a"*64,"artifact_reference":"/tmp/out.mp4","artifact_sha256":"b"*64,"provider_native_result":{"source_revision":PIN,"network_model_fetch_performed":False,"runtime_ordinal_is_identity":False}}))
   self.assertEqual(gate(ROOT,m,a)["result"],"PASS")
if __name__=="__main__":unittest.main()
