from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_model_manager_current_host_gate import gate
from fa3_model_manager_provider_adapter import (
    HF_PROVIDER_ID,LM_STUDIO_PROVIDER_ID,OLLAMA_PROVIDER_ID,EVIDENCE_LEVEL,RUNTIME_ID,
)

D="a"*64

def unavailable(provider_id):
    return {
        "provider_id":provider_id,
        "status":"UNAVAILABLE_OR_FAILED",
        "evidence_level":"CURRENT_HOST_PROVIDER_NOT_ADMITTED",
        "error_type":"RuntimeError",
        "error_fingerprint_sha256":D,
        "production_admission_claim":False,
    }

def lm_pass():
    return {
        "provider_id":LM_STUDIO_PROVIDER_ID,
        "status":"PASS",
        "evidence_level":"CURRENT_HOST_RUNTIME_E2E_PASS",
        "lms_binary_sha256":D,
        "catalog_count":1,
        "selected_model_key":"runtime-selected",
        "load_policy":{"local_only":True,"gpu_offload":"off"},
        "inference_stdout_length":1,
        "inference_stdout_sha256":D,
        "network_model_fetch_performed":False,
        "accelerator_execution_claimed":False,
    }

def base_receipt():
    return {
        "schema":"fa3.model-manager-current-host-receipt.v2",
        "runtime_id":RUNTIME_ID,
        "status":"PASS",
        "evidence_level":EVIDENCE_LEVEL,
        "execution_policy":{
            "local_artifacts_only":True,
            "network_download_or_pull":False,
            "cpu_first":True,
            "accelerator_execution_claimed":False,
            "accelerator_requires_hrb_for_separate_evidence":True,
            "optional_provider_absence_blocks_other_provider_admission":False,
        },
        "providers":{
            HF_PROVIDER_ID:unavailable(HF_PROVIDER_ID),
            LM_STUDIO_PROVIDER_ID:lm_pass(),
            OLLAMA_PROVIDER_ID:unavailable(OLLAMA_PROVIDER_ID),
        },
        "admitted_provider_ids":[LM_STUDIO_PROVIDER_ID],
        "serving_provider_ids":[LM_STUDIO_PROVIDER_ID],
        "unavailable_provider_ids":[HF_PROVIDER_ID,OLLAMA_PROVIDER_ID],
        "provider_coverage":"PARTIAL",
        "combined_pass_semantics":"AT_LEAST_ONE_REAL_LOCAL_SERVING_RUNTIME_PASS",
        "new_capabilities":0,
        "new_architectural_authorities":0,
        "capability_count_after":143,
    }

class TestModelManagerCurrentHostGate(unittest.TestCase):
    def run_gate(self,receipt):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=root/"evidence/receipts/model-manager-current-host.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps(receipt),encoding="utf-8")
            return gate(root)

    def test_lm_studio_only_can_pass(self):
        report=self.run_gate(base_receipt())
        self.assertEqual(report["result"],"PASS",report["findings"])

    def test_optional_ollama_absence_does_not_block(self):
        r=base_receipt()
        self.assertEqual(self.run_gate(r)["result"],"PASS")

    def test_no_serving_provider_fails(self):
        r=base_receipt()
        r["providers"][LM_STUDIO_PROVIDER_ID]=unavailable(LM_STUDIO_PROVIDER_ID)
        r["admitted_provider_ids"]=[]
        r["serving_provider_ids"]=[]
        r["unavailable_provider_ids"]=[HF_PROVIDER_ID,LM_STUDIO_PROVIDER_ID,OLLAMA_PROVIDER_ID]
        r["status"]="FAIL"
        r["evidence_level"]="CURRENT_HOST_MODEL_PROVIDER_E2E_FAIL"
        report=self.run_gate(r)
        self.assertEqual(report["result"],"FAIL")

if __name__=="__main__":
    unittest.main()
