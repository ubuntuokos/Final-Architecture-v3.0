from __future__ import annotations
import unittest
from pathlib import Path
from src.fa3_supply_runtime_hardening_current_host_gate import gate,validate_scs,validate_provider,validate_hrb,validate_hu
ROOT=Path(__file__).resolve().parents[1]
class CurrentHostHardeningTests(unittest.TestCase):
    def test_hosted_reference_stays_pending(self):
        r=gate(ROOT);self.assertEqual("PASS",r["result"]);self.assertEqual("PENDING_CURRENT_HOST",r["status"]);self.assertFalse(r["global_promotion_claim"])
    def test_hrb_overclaim_rejected(self):
        row={"schema":"fa3.hrb-composite-current-host-receipt.v1","status":"CURRENT_HOST_CONTROL_PLANE_PASS","overflow_refused":True,"forged_parent_refused":True,"parent_revocation_cascades":True,"test_only_ephemeral_hmac":True,"hmac_secret_persisted":False,"production_broker_promotion_claim":True,"global_promotion_claim":False}
        self.assertTrue(validate_hrb(row))
    def test_hu_missing_category_rejected(self):
        profile={"golden_corpus":{"categories":["A","B"]}}
        row={"schema":"fa3.hu-aqc-golden-corpus-current-host-receipt.v1","status":"CURRENT_HOST_PASS","observed_categories":["A"],"sample_count":1,"threshold_relaxation_performed":False,"synthetic":False,"global_promotion_claim":False}
        self.assertTrue(validate_hu(row,profile))
    def test_scs_manual_compatibility_claim_is_not_enough(self):
        row={"schema":"fa3.software-supply-chain-receipt.v1","current_host_execution":True,"synthetic":False,"admission":{"result":"PASS","admitted":True},"license":{"policy_result":"FAIL","declaration_matches_detection":True},"artifact":{"hash_scope":"FILE_CONTENT"}}
        self.assertTrue(validate_scs(row))
    def test_provider_runtime_overclaim_rejected(self):
        row={"schema":"fa3.provider-runtime-current-host-receipt.v1","status":"CURRENT_HOST_PASS","execution_class":"VENV","synthetic":False,"global_promotion_claim":True}
        self.assertTrue(validate_provider(row))
if __name__=="__main__":unittest.main()
