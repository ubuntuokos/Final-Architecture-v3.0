import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_triton_gate import CAPABILITY_COUNT, GATE_ID, PROVIDER_ID, gate


class TritonGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "deployment" / "triton", root / "deployment" / "triton")
        return td, root

    @staticmethod
    def _load(path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path, obj):
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["gate_id"], GATE_ID)
        self.assertEqual(report["provider_id"], PROVIDER_ID)
        self.assertEqual(report["capability_count"], CAPABILITY_COUNT)
        self.assertFalse(report["current_host_production_claim"])

    def test_authority_escalation_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/providers/FA3-PROVIDER-TRITON-001.json"
            obj = self._load(path)
            obj["architectural_authority"] = True
            self._write(path, obj)
            self.assertEqual(gate(root)["result"], "FAIL")
        finally:
            td.cleanup()

    def test_model_repository_authority_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/providers/FA3-PROVIDER-TRITON-001.json"
            obj = self._load(path)
            obj["model_repository_semantics"] = "CANONICAL_MODEL_REGISTRY"
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "TRITON-MODEL-001" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_poll_model_control_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/contracts/FA3-TRITON-INFERENCE-SERVER-CONTRACTS-001.json"
            obj = self._load(path)
            obj["model_control"]["poll_mode"] = "ALLOWED"
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "TRITON-CTRL-001" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_gpu_all_wildcard_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "deployment/triton/fa3-triton-start"
            text = path.read_text(encoding="utf-8")
            text = text.replace('--gpus "device=${FA3_TRITON_GPU_UUIDS}"', "--gpus all")
            path.write_text(text, encoding="utf-8")
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "TRITON-RUN-001" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_parent_provider_binding_is_required(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/inference-portability-enforcement.json"
            obj = self._load(path)
            obj["provider_ids"].remove(PROVIDER_ID)
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "TRITON-PARENT-001" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_unbounded_restart_policy_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "deployment/triton/fa3-triton.service"
            text = path.read_text(encoding="utf-8").replace("Restart=on-failure", "Restart=always")
            path.write_text(text, encoding="utf-8")
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "TRITON-SYSTEMD-001" for x in report["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
