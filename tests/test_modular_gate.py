import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_modular_gate import (
    CAPABILITY_COUNT,
    GATE_ID,
    MAX_PROVIDER_ID,
    MOJO_PROVIDER_ID,
    PROVIDER_IDS,
    RULES,
    gate,
    run_regressions,
    scan_canonical_authority_assignments,
)

class ModularGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        return td, root

    def _write(self, path: Path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["gate_id"], GATE_ID)
        self.assertEqual(report["provider_ids"], list(PROVIDER_IDS))
        self.assertEqual(report["capability_count"], CAPABILITY_COUNT)
        self.assertEqual(report["reference"]["result"], "PASS")
        self.assertEqual(report["authority_scan"]["result"], "PASS")
        self.assertEqual(report["regressions"]["result"], "PASS")
        self.assertFalse(report["runtime_provider_required"])

    def test_exact_fourteen_regressions_pass(self):
        report = run_regressions()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], 14)
        self.assertEqual(report["total"], 14)
        self.assertEqual([c["invariant"] for c in report["cases"]], list(RULES))

    def test_max_cannot_be_host_resource_authority(self):
        td, root = self._copy_root()
        try:
            self._write(root / "canonical/max-authority-mutation.json", {
                "schema":"fa3.test-mutation.v1",
                "id":"FA3-MAX-AUTH-MUTATION",
                "provider_id":MAX_PROVIDER_ID,
                "host_resource_authority":MAX_PROVIDER_ID,
            })
            scan = scan_canonical_authority_assignments(root)
            self.assertEqual(scan["result"], "FAIL")
            self.assertTrue(any(f["code"] == "MODULAR-AUTH-004" for f in scan["findings"]))
        finally:
            td.cleanup()

    def test_mojo_cannot_own_authority_boundary(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/providers/FA3-PROVIDER-MOJO-001.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["authority_boundaries"]["host_resource_admission_placement"] = MOJO_PROVIDER_ID
            self._write(p, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(f["code"] == "MODULAR-AUTH-003" for f in report["authority_scan"]["findings"]))
        finally:
            td.cleanup()

    def test_canonical_root_or_capability_drift_fails(self):
        for filename in ("FA3-PROVIDER-MAX-001.json", "FA3-PROVIDER-MOJO-001.json"):
            with self.subTest(filename=filename):
                td, root = self._copy_root()
                try:
                    p = root / "canonical/providers" / filename
                    obj = json.loads(p.read_text(encoding="utf-8"))
                    obj["canonical_root"] = True
                    obj["new_capability"] = True
                    obj["capability_count"] = CAPABILITY_COUNT + 1
                    self._write(p, obj)
                    report = gate(root)
                    self.assertEqual(report["result"], "FAIL")
                    self.assertTrue(any(f["code"] in {"MODULAR-REF-010","MODULAR-REF-011"} for f in report["reference"]["findings"]))
                finally:
                    td.cleanup()

    def test_snapshot_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/references/FA3-MODULAR-UPSTREAM-REFERENCE-2026-08-30.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["snapshot_commit"] = "floating-main"
            self._write(p, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(f["code"] == "MODULAR-REF-013" for f in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_rule_set_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/modular-enforcement.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["p0_invariants"] = obj["p0_invariants"][:-1]
            self._write(p, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(f["code"] == "MODULAR-REF-014" for f in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_global_policy_binding_is_required(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/enforcement-policy.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["mandatory_reference_gates"] = [x for x in obj["mandatory_reference_gates"] if x != GATE_ID]
            self._write(p, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(f["code"] == "MODULAR-REF-015" for f in report["reference"]["findings"]))
        finally:
            td.cleanup()

if __name__ == "__main__":
    unittest.main()
