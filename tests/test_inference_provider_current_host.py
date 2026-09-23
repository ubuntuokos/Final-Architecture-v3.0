import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_inference_provider_current_host import embedded_onnx_identity
from fa3_inference_provider_current_host_gate import (
    CONFORMANCE_ID,CURRENT_HOST_GATE_ID,EVIDENCE_LEVEL,PROVIDERS,RULES,
    advisory_valid,materialization_gate,provider_receipt_valid,scope_valid,
)

class InferenceProviderCurrentHostTests(unittest.TestCase):
    def cpu_scope(self):
        return {
          "scope_id":"CPU","execution_kind":"CPU","status":"ADMITTED",
          "evidence_level":EVIDENCE_LEVEL,"e2e":{"result":"PASS"},"runtime_pin":"1.0",
          "model_probe_sha256":"a"*64,"hardware_binding":{"accelerator":False,"hrb_lease":None},
          "support_matrix":{"result":"NOT_REQUIRED_CPU_SCOPE"},
        }

    def provider(self,pid="FA3-PROVIDER-OPENVINO-001"):
        return {
          "provider_id":pid,"provider_version":"1.0","expected_reference_version":"1.0",
          "version_match":True,"present":True,"status":"ADMITTED","admitted_scopes":["CPU"],
          "scopes":{"CPU":self.cpu_scope()},"direct_probe_scope":"ADMISSION_HARNESS_ONLY_NOT_APPLICATION_PATH",
          "auto_install_performed":False,"network_model_fetch_performed":False,"global_promotion_claim":False,
        }

    def test_materialization_gate_passes(self):
        r=materialization_gate(ROOT)
        self.assertEqual(r["result"],"PASS",r)

    def test_rule_set_is_exact(self):
        self.assertEqual(len(RULES),12)
        self.assertEqual(len(set(RULES)),12)

    def test_cpu_admission_receipt_passes_without_hrb(self):
        self.assertTrue(provider_receipt_valid(self.provider()))

    def test_cpu_admission_with_accelerator_lease_fails(self):
        p=self.provider()
        p["scopes"]["CPU"]["hardware_binding"]={"accelerator":False,"hrb_lease":{"result":"PASS"}}
        self.assertFalse(provider_receipt_valid(p))

    def test_accelerator_scope_requires_hrb_and_support_matrix(self):
        s={
          "scope_id":"CUDA_EP","execution_kind":"ACCELERATOR","status":"ADMITTED",
          "evidence_level":EVIDENCE_LEVEL,"e2e":{"result":"PASS"},"runtime_pin":"1.0",
          "model_probe_sha256":"b"*64,
          "hardware_binding":{"accelerator":True,"hrb_lease":{"result":"PASS"}},
          "support_matrix":{"result":"PASS"},
        }
        self.assertTrue(scope_valid(s))
        self.assertFalse(scope_valid({**s,"hardware_binding":{"accelerator":True,"hrb_lease":{"result":"MISSING"}}}))
        self.assertFalse(scope_valid({**s,"support_matrix":{"result":"MISSING"}}))

    def test_admission_requires_exact_reference_version(self):
        p=self.provider(); p["version_match"]=False
        self.assertFalse(provider_receipt_valid(p))

    def test_direct_probe_cannot_be_application_path(self):
        p=self.provider(); p["direct_probe_scope"]="APPLICATION_DIRECT_PROVIDER_CALL"
        self.assertFalse(provider_receipt_valid(p))

    def test_decision_advisory_cannot_expand(self):
        present={"A","B"}
        good={"status":"DECIDED","authority":False,"candidate_set_expanded":False,"result":{"ranked":["B","A"]}}
        bad={"status":"DECIDED","authority":False,"candidate_set_expanded":False,"result":{"ranked":["A","B","C"]}}
        self.assertTrue(advisory_valid(good,present))
        self.assertFalse(advisory_valid(bad,present))

    def test_tensorrt_rtx_cannot_be_admitted_without_cache_observability(self):
        p=self.provider("FA3-PROVIDER-TENSORRT-RTX-001")
        p["admitted_scopes"]=["NVIDIA_RTX_NATIVE"]
        p["scopes"]={"NVIDIA_RTX_NATIVE":{
          "scope_id":"NVIDIA_RTX_NATIVE","execution_kind":"ACCELERATOR","status":"ADMITTED",
          "evidence_level":EVIDENCE_LEVEL,"e2e":{"result":"PASS"},"runtime_pin":"1.0",
          "model_probe_sha256":"c"*64,
          "hardware_binding":{"accelerator":True,"hrb_lease":{"result":"PASS"}},
          "support_matrix":{"result":"PASS"},
          "runtime_cache_observability":{"result":"MISSING"},
        }}
        self.assertFalse(provider_receipt_valid(p))

    def test_absent_provider_is_valid_non_admission(self):
        p={
          "provider_id":"FA3-PROVIDER-TENSORRT-001","provider_version":None,
          "expected_reference_version":"11.3.0.99","version_match":False,"present":False,
          "status":"NOT_PRESENT","admitted_scopes":[],"scopes":{},
          "direct_probe_scope":"ADMISSION_HARNESS_ONLY_NOT_APPLICATION_PATH",
          "auto_install_performed":False,"network_model_fetch_performed":False,"global_promotion_claim":False,
        }
        self.assertTrue(provider_receipt_valid(p))

    def test_embedded_onnx_probe_is_deterministic_nonempty(self):
        a=embedded_onnx_identity(); b=embedded_onnx_identity()
        self.assertEqual(a,b); self.assertGreater(len(a),20)

    def test_all_provider_records_bound_to_framework(self):
        for pid in PROVIDERS:
            d=json.loads((ROOT/"canonical/providers"/f"{pid}.json").read_text(encoding="utf-8"))
            self.assertEqual(d["current_host_admission"]["framework_id"],CONFORMANCE_ID)
            self.assertEqual(d["current_host_admission"]["gate_id"],CURRENT_HOST_GATE_ID)
            self.assertFalse(d["current_host_admission"]["automatic_install"])
            self.assertFalse(d["current_host_admission"]["global_promotion_claim"])

if __name__=="__main__":
    unittest.main()
