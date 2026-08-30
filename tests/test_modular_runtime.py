import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_modular_runtime import (
    DEFAULT_MODEL,
    HRB_LEASE_SCHEMA,
    HRB_PROFILE_ID,
    MAX_PROVIDER_ID,
    MaxServeRequest,
    PolicyDenied,
    build_max_serve_command,
    compiled_artifact_identity,
    load_allowlist,
    run_executable_conformance,
    validate_hrb_lease,
    validate_request,
)
from fa3_modular_current_host_gate import gate as current_host_gate

class ModularRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.allowlist = load_allowlist(ROOT)

    def test_executable_conformance_passes(self):
        report = run_executable_conformance(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertGreaterEqual(report["passed"], 13)
        self.assertEqual(report["passed"], report["total"])

    def test_gpu_requires_hrb_and_guard(self):
        with self.assertRaises(PolicyDenied):
            validate_request(MaxServeRequest(model_revision="9e6c6cc", devices="gpu:0"), self.allowlist)
        with self.assertRaises(PolicyDenied):
            validate_request(MaxServeRequest(
                model_revision="9e6c6cc", devices="gpu:0", hrb_lease_path="/tmp/lease.json"
            ), self.allowlist)

    def test_serve_command_is_loopback_pinned_revision_and_remote_code_off(self):
        req = MaxServeRequest(model_revision="9e6c6cc", devices="cpu")
        validate_request(req, self.allowlist)
        cmd = build_max_serve_command(req)
        self.assertIn("--huggingface-model-revision", cmd)
        self.assertIn("--no-trust-remote-code", cmd)
        self.assertIn("127.0.0.1", cmd)

    def test_hrb_lease_needs_broker_memory_reservation(self):
        req = MaxServeRequest(
            model_revision="9e6c6cc", devices="gpu:0",
            hrb_lease_path="/tmp/lease.json", device_memory_utilization=0.5,
        )
        lease = {
            "schema": HRB_LEASE_SCHEMA, "issuer": HRB_PROFILE_ID, "status": "ACTIVE",
            "accelerator_uuid": "GPU-test", "memory_max_bytes": 1024,
            "placement": {"ordinal_at_issue": 0}, "enforcement": {"gpu_memory": "provider_guard"},
        }
        with self.assertRaises(PolicyDenied):
            validate_hrb_lease(lease, req)

    def test_compiled_artifact_identity_changes_with_binary(self):
        a = compiled_artifact_identity("a", "Mojo 1.0", "x86_64", "b")
        b = compiled_artifact_identity("a", "Mojo 1.0", "x86_64", "c")
        self.assertNotEqual(a, b)

    def test_current_host_gate_fails_without_real_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "evidence/receipts").mkdir(parents=True)
            report = current_host_gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "MODULAR-HOST-001" for x in report["findings"]))

if __name__ == "__main__":
    unittest.main()
