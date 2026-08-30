import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_demucs_provider import (
    HRB_LEASE_SCHEMA,
    HRB_PROFILE_ID,
    HRBLeaseDenied,
    PROVIDER_ID,
    PROVIDER_VERSION,
    PolicyDenied,
    SeparationRequest,
    load_allowlist,
    run_executable_conformance,
    validate_hrb_lease_document,
    validate_hrb_broker_output,
    validate_request,
)
from fa3_demucs_current_host_gate import validate_receipt

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

class DemucsProviderRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.allowlist = load_allowlist(ROOT)

    def test_executable_conformance_is_full_pass(self):
        report = run_executable_conformance(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], report["total"])
        self.assertGreaterEqual(report["total"], 13)

    def test_arbitrary_hf_model_is_rejected(self):
        request = SeparationRequest(
            input_path="/tmp/in.wav",
            output_dir="/tmp/out",
            model="hf://attacker/model",
        )
        with self.assertRaises(PolicyDenied):
            validate_request(request, self.allowlist)

    def test_cuda_requires_hrb_lease_and_verifier(self):
        request = SeparationRequest(
            input_path="/tmp/in.wav",
            output_dir="/tmp/out",
            device="cuda:0",
        )
        with self.assertRaises(PolicyDenied):
            validate_request(request, self.allowlist)

    def _valid_hrb_lease(self):
        import time
        return {
            "schema": HRB_LEASE_SCHEMA,
            "lease_id": "hrb-test",
            "issuer": HRB_PROFILE_ID,
            "accelerator_uuid": "GPU-test",
            "memory_max_bytes": 4096,
            "expires_epoch": int(time.time()) + 60,
            "issued_epoch": int(time.time()),
            "purpose": "FA3 Demucs provider test",
            "host": "test-host",
            "status": "ACTIVE",
            "nonce": "00" * 16,
            "placement": {"ordinal_at_issue": 0, "pci_bus_id": "00000000:01:00.0", "numa_node": 0},
            "enforcement": {"gpu_memory": "provider_guard+broker_reservation"},
            "signature": {"alg": "HMAC-SHA256", "key_id": "host-local-v1", "value": "11" * 32},
        }

    def test_expired_hrb_lease_is_rejected(self):
        import time
        request = SeparationRequest(
            input_path="/tmp/in.wav",
            output_dir="/tmp/out",
            device="cuda:0",
            hrb_lease_path="/tmp/lease.json",
        )
        lease = self._valid_hrb_lease()
        lease["expires_epoch"] = int(time.time()) - 1
        with self.assertRaises(HRBLeaseDenied):
            validate_hrb_lease_document(lease, request)

    def test_hrb_issuer_mismatch_is_rejected(self):
        request = SeparationRequest(
            input_path="/tmp/in.wav",
            output_dir="/tmp/out",
            device="cuda:0",
            hrb_lease_path="/tmp/lease.json",
        )
        lease = self._valid_hrb_lease()
        lease["issuer"] = "OTHER"
        with self.assertRaises(HRBLeaseDenied):
            validate_hrb_lease_document(lease, request)

    def test_hrb_broker_must_return_valid(self):
        validate_hrb_broker_output(0, "VALID\n")
        with self.assertRaises(HRBLeaseDenied):
            validate_hrb_broker_output(0, "INVALID\n")
        with self.assertRaises(HRBLeaseDenied):
            validate_hrb_broker_output(2, "")

    def _build_receipt(self, root: Path, *, level: str, synthetic: bool, device: str = "cpu", lease=None, trust=True):
        runtime = root / "runtime"
        runtime.mkdir(parents=True, exist_ok=True)
        execution = {
            "status":"PASS",
            "provider_id":PROVIDER_ID,
            "model_trust":{
                "container":"SAFETENSORS" if trust else "PICKLE",
                "class_allowlisted":trust,
                "legacy_pickle_used":not trust,
            },
            "provider_runtime":{"device":device},
            "device_lease":lease,
            "hrb": (
                None if not device.startswith("cuda:") or not lease else {
                    "schema": HRB_LEASE_SCHEMA,
                    "issuer": HRB_PROFILE_ID,
                    "broker_validation": "VALID",
                    "accelerator_uuid": "GPU-test",
                    "lease_id": lease,
                }
            ),
            "resource_guard": (
                None if not device.startswith("cuda:") or not lease else {
                    "mechanism":"torch.cuda.set_per_process_memory_fraction",
                    "memory_max_bytes":4096,
                }
            ),
            "output_hashes":{"vocals":"abc"},
            "quality_evidence":{"vocals":{"samples":44100}},
        }
        execution_path = runtime / "execution-evidence.json"
        execution_path.write_text(json.dumps(execution))
        receipt = {
            "status":"PASS",
            "evidence_level":level,
            "provider_id":PROVIDER_ID,
            "provider_version":PROVIDER_VERSION,
            "synthetic_input":synthetic,
            "executable_conformance":{
                "result":"PASS",
                "passed":13,
                "total":13,
            },
            "hrb_enforced":not device.startswith("cuda") or bool(lease),
            "model_trust_enforced":trust,
            "execution_evidence":{
                "path":str(execution_path),
                "sha256":sha256(execution_path),
            },
        }
        p = root / "evidence/receipts/demucs-current-host.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(receipt))

    def test_production_gate_rejects_synthetic_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._build_receipt(root, level="CURRENT_HOST_SYNTHETIC_E2E_PASS", synthetic=True)
            result = validate_receipt(root, require_production=True)
            self.assertEqual(result["result"], "FAIL")
            self.assertTrue(any(x["code"] == "DEMUCS-HOST-005" for x in result["findings"]))

    def test_valid_production_cpu_receipt_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._build_receipt(root, level="CURRENT_HOST_PRODUCTION_E2E_PASS", synthetic=False)
            result = validate_receipt(root, require_production=True)
            self.assertEqual(result["result"], "PASS")

    def test_cuda_production_receipt_without_lease_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._build_receipt(root, level="CURRENT_HOST_PRODUCTION_E2E_PASS", synthetic=False, device="cuda:0", lease=None)
            result = validate_receipt(root, require_production=True)
            self.assertEqual(result["result"], "FAIL")
            codes = {x["code"] for x in result["findings"]}
            self.assertIn("DEMUCS-HOST-008", codes)
            self.assertIn("DEMUCS-HOST-016", codes)

    def test_untrusted_model_evidence_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._build_receipt(root, level="CURRENT_HOST_PRODUCTION_E2E_PASS", synthetic=False, trust=False)
            result = validate_receipt(root, require_production=True)
            self.assertEqual(result["result"], "FAIL")
            codes = {x["code"] for x in result["findings"]}
            self.assertIn("DEMUCS-HOST-009", codes)
            self.assertIn("DEMUCS-HOST-015", codes)

if __name__ == "__main__":
    unittest.main()
