import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_inference_portability_gate import (
    CAPABILITY_COUNT, CAPABILITY_IDS, GATE_ID, PROFILE_ID, PROVIDER_IDS, RULES,
    gate, reference_check, run_regressions, scan_canonical_authority_assignments,
)

class InferencePortabilityGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        for name in ("canonical","evidence"):
            shutil.copytree(ROOT / name, root / name)
        return td, root

    def _write(self, path: Path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["gate_id"], GATE_ID)
        self.assertEqual(report["profile_id"], PROFILE_ID)
        self.assertEqual(report["provider_ids"], list(PROVIDER_IDS))
        self.assertEqual(report["capability_bindings"], list(CAPABILITY_IDS))
        self.assertEqual(report["capability_count"], CAPABILITY_COUNT)
        self.assertFalse(report["runtime_provider_required"])
        self.assertFalse(report["current_host_runtime_promotion_claim"])

    def test_exact_twenty_regressions_pass(self):
        report = run_regressions()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], 20)
        self.assertEqual(report["total"], 20)
        self.assertEqual([x["invariant"] for x in report["cases"]], list(RULES))

    def test_openvino_nvidia_default_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/providers/FA3-PROVIDER-OPENVINO-001.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["official_gpu_device_scope"] = "GENERIC_GPU_INCLUDING_NVIDIA"
            obj["nvidia_contrib_plugin"]["production_default_for_nvidia"] = True
            self._write(p, obj)
            report = reference_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "INFER-REF-014" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_execution_provider_cannot_be_authority(self):
        td, root = self._copy_root()
        try:
            self._write(root / "canonical/inference-provider-authority-mutation.json", {
                "schema":"fa3.test-mutation.v1",
                "id":"INFERENCE-AUTH-MUTATION",
                "provider_id":"FA3-PROVIDER-TENSORRT-001",
                "host_resource_authority":"FA3-PROVIDER-TENSORRT-001",
            })
            scan = scan_canonical_authority_assignments(root)
            self.assertEqual(scan["result"], "FAIL")
            self.assertTrue(any(x["code"] == "INFER-AUTH-004" for x in scan["findings"]))
        finally:
            td.cleanup()

    def test_policy_rule_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/enforcement-policy.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["inference_portability_mandatory_p0_rules"] = obj["inference_portability_mandatory_p0_rules"][:-1]
            self._write(p, obj)
            report = reference_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "INFER-REF-021" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_evidence_registry_binding_missing_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "evidence/evidence-registry.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            rec = next(x for x in obj["records"] if x["subject_id"] == "CAP-005")
            rec["evidence_artifacts"] = [x for x in rec["evidence_artifacts"] if "inference-portability" not in x]
            self._write(p, obj)
            report = reference_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "INFER-REF-023" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_projection_reconciliation_missing_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj.pop("inference_portability_reconciliation", None)
            self._write(p, obj)
            report = reference_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "INFER-REF-024" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_provider_runtime_remains_not_admitted(self):
        for filename in (
            "FA3-PROVIDER-OPENVINO-001.json","FA3-PROVIDER-ONNXRUNTIME-001.json",
            "FA3-PROVIDER-TENSORRT-001.json","FA3-PROVIDER-TENSORRT-RTX-001.json",
        ):
            obj = json.loads((ROOT / "canonical/providers" / filename).read_text(encoding="utf-8"))
            self.assertEqual(obj["runtime_activation_status"], "NOT_ADMITTED_REFERENCE_ONLY")
            self.assertEqual(obj["current_host_production_evidence"], "NOT_CLAIMED")
            self.assertFalse(obj["global_runtime_promotion_required_when_disabled"])

if __name__ == "__main__":
    unittest.main()
