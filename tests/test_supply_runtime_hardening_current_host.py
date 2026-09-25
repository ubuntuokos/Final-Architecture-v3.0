from __future__ import annotations
import importlib.util
import unittest
from pathlib import Path
from src.fa3_supply_runtime_hardening_current_host_gate import gate,validate_scs,validate_provider,validate_hrb,validate_hu
ROOT=Path(__file__).resolve().parents[1]
_spec=importlib.util.spec_from_file_location("fa3_hrb_composite_current_host",ROOT/"evidence/collect-hrb-composite-current-host.py")
assert _spec is not None and _spec.loader is not None
_hrb_collector=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_hrb_collector)
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
    def test_live_hrb_plan_is_vendor_neutral_and_cpu_only_safe(self):
        discovery={"cpu":{"logical_cpu_count":4},"accelerators":{"devices":[]}}
        plan,capacity=_hrb_collector.derive_live_plan_capacity(discovery)
        self.assertEqual([],plan["accelerators"])
        self.assertEqual(0,capacity["vram_bytes"])
        self.assertEqual(False,plan["hold_and_wait"])
        self.assertEqual(True,plan["atomic_admission"])
        self.assertGreater(plan["queue_policy"]["deadline_seconds"],0)

    def test_live_hrb_plan_uses_stable_accelerator_identity_not_ordinal(self):
        discovery={"cpu":{"logical_cpu_count":8},"accelerators":{"devices":[{"stable_id":"pci:0000:01:00.0","eligible_for_workload_admission":True,"vram_mib_evidence_only":8192}]}}
        plan,capacity=_hrb_collector.derive_live_plan_capacity(discovery)
        self.assertEqual("pci:0000:01:00.0",plan["accelerators"][0]["stable_id"])
        self.assertFalse(plan["accelerators"][0]["runtime_ordinal_is_identity"])
        self.assertGreater(capacity["vram_bytes"],0)

if __name__=="__main__":unittest.main()
