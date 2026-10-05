import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_inference_portability_reconciliation_gate import (
    CAPABILITY_COUNT,RULES,SUBGATE_ID,advisory_valid,agent_invocation_valid,
    ai_topology_valid,backend_candidate_valid,drift_event_valid,execution_receipt_valid,
    gate,reference_check,run_regressions,
)

class InferencePortabilityReconciliationTests(unittest.TestCase):
    def _copy_root(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        for name in ("canonical","evidence"): shutil.copytree(ROOT/name,root/name)
        return td,root
    def _write(self,path,obj):
        path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")

    def test_baseline_gate_passes(self):
        r=gate(ROOT)
        self.assertEqual(r["result"],"PASS")
        self.assertEqual(r["subgate_id"],SUBGATE_ID)
        self.assertEqual(r["capability_count"],CAPABILITY_COUNT)
        self.assertFalse(r["current_host_runtime_promotion_claim"])
        self.assertFalse(r["global_promotion_claim"])

    def test_exact_fifteen_regressions_pass(self):
        r=run_regressions()
        self.assertEqual(r["result"],"PASS")
        self.assertEqual(r["passed"],15)
        self.assertEqual(r["total"],15)
        self.assertEqual([x["invariant"] for x in r["cases"]],list(RULES))

    def test_host_unbound_backend_cannot_authorize_accelerator(self):
        obj={"execution_kind":"ACCELERATOR","accelerator_id":"a","binding_scope":"HOST_UNBOUND","detected":True,"available":True,"compatibility_result":"PASS","hardware_discovery_receipt_id":"h","hrb_lease_required":True}
        self.assertFalse(backend_candidate_valid(obj))

    def test_agent_native_requires_uaf_and_no_bypass(self):
        good={"origin":"AGENT_NATIVE","uaf_action_contract":"FA3-UAF-ACTION-CONTRACT-001","uaf_action_receipt_id":"u","direct_provider_bypass":False,"model_router_bypass":False,"hrb_bypass":False,"security_policy_bypass":False}
        self.assertTrue(agent_invocation_valid(good))
        self.assertFalse(agent_invocation_valid({**good,"direct_provider_bypass":True}))
        self.assertFalse(agent_invocation_valid({**good,"uaf_action_receipt_id":None}))

    def test_jev_advisory_cannot_expand_candidate_set(self):
        good={"deterministic_prefilter":True,"candidate_set_expanded":False,"authority":False,"action":"RERANK"}
        self.assertTrue(advisory_valid(good))
        self.assertFalse(advisory_valid({**good,"candidate_set_expanded":True}))
        self.assertFalse(advisory_valid({**good,"authority":True}))

    def test_backend_change_cannot_expand_ai_participant_set(self):
        good={"execution_backend_is_ai_participant":False,"participant_set_expanded":False,"provider_or_model_replacement_via_model_router":True}
        self.assertTrue(ai_topology_valid(good))
        self.assertFalse(ai_topology_valid({**good,"participant_set_expanded":True}))

    def test_backend_loss_invalidates_lease_and_derived_cache(self):
        good={"backend_available_after":False,"hrb_lease_invalidated":True,"derived_engine_cache_reuse_invalidated":True,"readmission_required":True}
        self.assertTrue(drift_event_valid(good))
        self.assertFalse(drift_event_valid({**good,"hrb_lease_invalidated":False}))

    def test_hardware_baseline_accelerator_min_must_remain_zero(self):
        td,root=self._copy_root()
        try:
            p=root/"canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json"
            obj=json.loads(p.read_text())
            obj["portable_minimum_envelope"]["accelerator_devices_min"]=1
            self._write(p,obj)
            r=reference_check(root)
            self.assertEqual(r["result"],"FAIL")
            self.assertTrue(any(x["code"]=="INFER-RECON-012" for x in r["findings"]))
        finally: td.cleanup()

    def test_provider_reference_versions_are_pinned_but_not_promoted(self):
        td,root=self._copy_root()
        try:
            p=root/"canonical/providers/FA3-PROVIDER-ONNXRUNTIME-001.json"
            obj=json.loads(p.read_text()); obj["observed_release"]="latest"
            self._write(p,obj)
            r=reference_check(root)
            self.assertEqual(r["result"],"FAIL")
            self.assertTrue(any(x["code"]=="INFER-RECON-014" for x in r["findings"]))
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main()
