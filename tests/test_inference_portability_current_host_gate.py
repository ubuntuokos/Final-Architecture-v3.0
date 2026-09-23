import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_inference_portability_current_host_gate import (
    CAPABILITY_COUNT,GATE_ID,PROVIDER_IDS,RULES,gate,reference_gate,validate_runtime_receipt
)

class InferencePortabilityCurrentHostTests(unittest.TestCase):
    def test_reference_materialization_passes(self):
        r=gate(ROOT)
        self.assertEqual(r["result"],"PASS")
        self.assertEqual(r["gate_id"],GATE_ID)
        self.assertEqual(CAPABILITY_COUNT,143)
        self.assertFalse(r["provider_runtime_promotion_claim"])
        self.assertFalse(r["existing_429_closure_reopened"])

    def _receipt(self):
        providers=[]
        for pid in PROVIDER_IDS:
            providers.append({
              "provider_id":pid,"presence_status":"ABSENT_OPTIONAL","runtime_version":None,
              "reference_version":"x","reference_version_match":False,"probe_status":"ABSENT",
              "execution_candidates":[],"cpu_smoke":{"status":"NOT_APPLICABLE"},
              "accelerator_e2e":{"status":"NOT_RUN_NO_HRB_BOUND_EXECUTION","runtime_promotion_eligible":False},
              "admission_state":"ABSENT_OPTIONAL","production_runtime_promoted":False,
              "global_promotion_claim":False,"model_router_semantics":"PROBE_ONLY_NOT_ROUTING_AUTHORITY",
              "agent_native_action":False,"ai_participant_set_expanded":False,
              "network_fetch":False,"runtime_mutation":False
            })
        return {
          "schema":"fa3.inference-portability-current-host-receipt.v1",
          "collector_id":"FA3-INFERENCE-PORTABILITY-CURRENT-HOST-COLLECTOR-001",
          "captured_at":"2026-09-23T00:00:00Z","current_host":True,"synthetic":False,"ci_reference_only":False,
          "collection_policy":{"read_only":True,"network_fetch":False,"package_install":False,"provider_mutation":False,"secret_collection":"PROHIBITED"},
          "host":{},"hardware":{"accelerator_count":0,"cpu_only_host":True},"providers":providers,
          "result":{"status":"PASS","claims":["CURRENT_HOST_INFERENCE_PROVIDER_INVENTORY_PASS"],"non_claims":["GLOBAL_FA3_PROMOTION","GLOBAL_429_REOPEN","PROVIDER_PRODUCTION_RUNTIME_PASS","ACCELERATOR_E2E_WITHOUT_HRB","MODEL_ROUTER_PRODUCTION_ROUTE_E2E"]}
        }

    def test_all_optional_providers_absent_is_valid_inventory(self):
        self.assertEqual(validate_runtime_receipt(self._receipt())["result"],"PASS")

    def test_presence_does_not_permit_production_claim(self):
        r=self._receipt(); p=r["providers"][1]
        p.update({"presence_status":"PRESENT","runtime_version":"1.30.0","probe_status":"PRESENT","admission_state":"PRESENT_UNADMITTED","production_runtime_promoted":True})
        self.assertEqual(validate_runtime_receipt(r)["result"],"FAIL")

    def test_accelerator_discovery_cannot_claim_device_binding(self):
        r=self._receipt(); p=r["providers"][2]
        p.update({"presence_status":"PRESENT","runtime_version":"11.3.0.99","probe_status":"PRESENT","admission_state":"ACCELERATOR_RUNTIME_PRESENT_HRB_E2E_PENDING"})
        p["execution_candidates"]=[{"backend":"TENSORRT","execution_kind":"ACCELERATOR","binding_scope":"DEVICE","hrb_lease_required":True,"runtime_promotion_eligible":False}]
        self.assertEqual(validate_runtime_receipt(r)["result"],"FAIL")

    def test_probe_cannot_be_model_router(self):
        r=self._receipt(); r["providers"][0]["model_router_semantics"]="ROUTING_AUTHORITY"
        self.assertEqual(validate_runtime_receipt(r)["result"],"FAIL")

    def test_probe_cannot_expand_ai_participants(self):
        r=self._receipt(); r["providers"][0]["ai_participant_set_expanded"]=True
        self.assertEqual(validate_runtime_receipt(r)["result"],"FAIL")

    def test_synthetic_receipt_rejected(self):
        r=self._receipt(); r["synthetic"]=True
        self.assertEqual(validate_runtime_receipt(r)["result"],"FAIL")

    def test_collector_network_or_install_forbidden(self):
        r=self._receipt(); r["collection_policy"]["network_fetch"]=True
        self.assertEqual(validate_runtime_receipt(r)["result"],"FAIL")

    def test_rules_are_exact_twenty(self):
        self.assertEqual(len(RULES),20)

if __name__=="__main__":
    unittest.main()
