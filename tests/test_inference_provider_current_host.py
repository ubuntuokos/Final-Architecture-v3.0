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
        probe={
          "environment_id":"TEST_ENV","discovery_scope":"EXPLICIT_RUNTIME_ENVIRONMENT",
          "python_executable":"/usr/bin/python3","python_executable_sha256":"1"*64,
          "cli_path":None,"cli_sha256":None,"source_refs":["TEST"],"descriptor_receipt_id":"TEST-DESC",
          "host_wide_absence_claim":False,
        }
        identity={
          "environment_id":"TEST_ENV","python_executable":"/usr/bin/python3",
          "python_executable_sha256":"1"*64,"module_file":"/tmp/provider.so",
          "module_file_sha256":"2"*64,"cli_path":None,"cli_sha256":None,
        }
        return {
          "provider_id":pid,"provider_version":"1.0","reference_version":"1.1",
          "reference_version_match":False,
          "admission_pin":{"result":"PASS","provider_version":"1.0","immutable":True,"identity_match":True,
                           "entry":{"runtime_identity":dict(identity)}},
          "admission_pin_match":True,"admission_identity_match":True,"runtime_identity":identity,
          "present":True,"status":"ADMITTED","admitted_scopes":["CPU"],"scopes":{"CPU":self.cpu_scope()},
          "probe_environment":probe,
          "module":{"present":True,"module_file":"/tmp/provider.so","module_file_sha256":"2"*64},
          "cli":{"name":None,"path":None,"sha256":None},
          "host_wide_absence_claim":False,
          "direct_probe_scope":"ADMISSION_HARNESS_ONLY_NOT_APPLICATION_PATH",
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

    def test_reference_version_mismatch_does_not_override_explicit_pin(self):
        p=self.provider()
        self.assertFalse(p["reference_version_match"])
        self.assertTrue(provider_receipt_valid(p))

    def test_admission_requires_explicit_immutable_runtime_pin(self):
        p=self.provider(); p["admission_pin"]={"result":"MISSING","provider_version":None}; p["admission_pin_match"]=False
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
          "reference_version":"11.3.0.99","reference_version_match":False,
          "admission_pin":{"result":"MISSING","provider_version":None,"identity_match":False},"admission_pin_match":False,
          "admission_identity_match":False,
          "runtime_identity":{"environment_id":"CURRENT_RUNNER_ENVIRONMENT","python_executable":sys.executable,
                              "python_executable_sha256":"3"*64,"module_file":None,"module_file_sha256":None,
                              "cli_path":None,"cli_sha256":None},
          "present":False,"status":"NOT_PRESENT_IN_PROBE_ENVIRONMENT","admitted_scopes":[],"scopes":{},
          "probe_environment":{"environment_id":"CURRENT_RUNNER_ENVIRONMENT","discovery_scope":"DEFAULT_RUNNER_ENVIRONMENT_ONLY",
                               "python_executable":sys.executable,"python_executable_sha256":"3"*64,
                               "cli_path":None,"cli_sha256":None,"source_refs":["TEST"],"descriptor_receipt_id":None,
                               "host_wide_absence_claim":False},
          "module":{"present":False,"error_class":"IMPORT_FAILED","python_executable":sys.executable},
          "cli":{"name":"trtexec","path":None,"sha256":None},
          "host_wide_absence_claim":False,
          "direct_probe_scope":"ADMISSION_HARNESS_ONLY_NOT_APPLICATION_PATH",
          "auto_install_performed":False,"network_model_fetch_performed":False,"global_promotion_claim":False,
        }
        self.assertTrue(provider_receipt_valid(p))

    def test_host_wide_absence_claim_is_rejected(self):
        p=self.provider(); p["host_wide_absence_claim"]=True
        self.assertFalse(provider_receipt_valid(p))

    def test_probe_environment_scope_is_required(self):
        p=self.provider(); p["probe_environment"]["discovery_scope"]="HOST_WIDE_SCAN"
        self.assertFalse(provider_receipt_valid(p))

    def test_runtime_identity_digest_is_required(self):
        p=self.provider()
        p["probe_environment"]["python_executable_sha256"]=None
        self.assertFalse(provider_receipt_valid(p))

    def test_runtime_pin_must_match_observed_execution_identity(self):
        p=self.provider()
        p["runtime_identity"]["python_executable_sha256"]="4"*64
        p["probe_environment"]["python_executable_sha256"]="4"*64
        self.assertFalse(provider_receipt_valid(p))

    def test_tensorrt_cli_execution_identity_must_be_pinned(self):
        p=self.provider("FA3-PROVIDER-TENSORRT-001")
        p["runtime_identity"]["cli_path"]="/opt/fa3/trtexec"
        p["runtime_identity"]["cli_sha256"]="5"*64
        p["probe_environment"]["cli_path"]="/opt/fa3/trtexec"
        p["probe_environment"]["cli_sha256"]="5"*64
        p["cli"]={"name":"trtexec","path":"/opt/fa3/trtexec","sha256":"5"*64}
        p["admission_pin"]["entry"]["runtime_identity"]=dict(p["runtime_identity"])
        self.assertTrue(provider_receipt_valid(p))
        p["runtime_identity"]["cli_sha256"]="6"*64
        p["probe_environment"]["cli_sha256"]="6"*64
        p["cli"]["sha256"]="6"*64
        self.assertFalse(provider_receipt_valid(p))

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
            self.assertFalse(d["current_host_admission"]["host_wide_absence_claim"])
            self.assertFalse(d["current_host_admission"]["automatic_environment_scanning"])
            self.assertEqual(d["current_host_admission"]["absence_status"],"NOT_PRESENT_IN_PROBE_ENVIRONMENT")

if __name__=="__main__":
    unittest.main()
