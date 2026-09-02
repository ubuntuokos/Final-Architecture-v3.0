import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import fa3_openbmb_gate as o


class OpenBMBGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence", root / "evidence")
        return td, root

    @staticmethod
    def _write(path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        report = o.gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual((31, 31), (report["regressions"]["passed"], report["regressions"]["total"]))
        self.assertEqual("PASS", report["authority_scan"]["result"])
        self.assertFalse(report["current_host_provider_runtime_evidence"])

    def test_all_positive_and_negative_regressions_pass(self):
        report = o.run_regressions()
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(o.P0_RULES, [case["rule_id"] for case in report["cases"]])
        self.assertTrue(all(case["positive_case"] and case["negative_case"] for case in report["cases"]))

    def test_wrong_cpmcu_cuda_or_sm_fails(self):
        self.assertFalse(o.target_native_valid("sm86", "sm90", "cuda13.2", "cuda12.8", True))

    def test_static_hardware_defaults_fail(self):
        self.assertFalse(o.reference_host_semantics_valid("GLOBAL_THREAD_DEFAULT", False, True))

    def test_reference_ci_cannot_promote_current_host(self):
        self.assertFalse(o.promotion_valid(True, False, True))

    def test_provider_authority_assignment_fails_global_scan(self):
        td, root = self._copy_root()
        try:
            self._write(root / "canonical/openbmb-authority-escalation.json", {"workflow_authority": o.PROVIDER_IDS[0]})
            report = o.scan_authority_collisions(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(f["code"] == "OPENBMB-AUTH-001" for f in report["findings"]))
        finally:
            td.cleanup()

    def test_floating_upstream_pin_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / o.PATHS["reference"]
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["immutable_snapshots"]["CPM.cu"]["commit"] = "main"
            self._write(path, obj)
            self.assertEqual("FAIL", o.reference_check(root)["result"])
        finally:
            td.cleanup()

    def test_global_policy_binding_required(self):
        td, root = self._copy_root()
        try:
            path = root / o.PATHS["policy"]
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["mandatory_reference_gates"].remove(o.GATE_ID)
            self._write(path, obj)
            self.assertEqual("FAIL", o.reference_check(root)["result"])
        finally:
            td.cleanup()

    def test_agpl_vendoring_is_rejected(self):
        self.assertFalse(o.agpl_isolation_valid(True, False, False))

    def test_model_provider_does_not_admit_floating_weight(self):
        self.assertFalse(o.model_admission_valid("main", False, False, True))


if __name__ == "__main__":
    unittest.main()
