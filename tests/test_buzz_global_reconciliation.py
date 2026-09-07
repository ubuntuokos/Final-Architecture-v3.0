import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_buzz_global_reconciliation import (
    CAPABILITY_ID,
    GLOBAL_EVIDENCE_PATH,
    PROVIDER_ID,
    REFERENCE_EVIDENCE_PATH,
    REGISTRY_PATH,
    RELEASE_PROJECTION_PATH,
    reconciliation_check,
)


class BuzzGlobalReconciliationTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        for rel in (
            REGISTRY_PATH,
            RELEASE_PROJECTION_PATH,
            REFERENCE_EVIDENCE_PATH,
            GLOBAL_EVIDENCE_PATH,
        ):
            src = ROOT / rel
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return td, root

    def _load(self, root, rel):
        return json.loads((root / rel).read_text(encoding="utf-8"))

    def _write(self, root, rel, obj):
        path = root / rel
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_global_reconciliation_passes(self):
        report = reconciliation_check(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["provider_id"], PROVIDER_ID)
        self.assertEqual(report["capability_id"], CAPABILITY_ID)

    def test_missing_global_evidence_fails_closed(self):
        td, root = self._copy_root()
        try:
            (root / GLOBAL_EVIDENCE_PATH).unlink()
            report = reconciliation_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REC-001" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_registry_evidence_link_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            registry = self._load(root, REGISTRY_PATH)
            cap = next(x for x in registry["records"] if x["subject_id"] == CAPABILITY_ID)
            cap["evidence_artifacts"] = [x for x in cap["evidence_artifacts"] if x != GLOBAL_EVIDENCE_PATH]
            self._write(root, REGISTRY_PATH, registry)
            report = reconciliation_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REC-004" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_release_inventory_evidence_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            release = self._load(root, RELEASE_PROJECTION_PATH)
            release["overlay_inventory"]["reference_evidence_records"].remove(GLOBAL_EVIDENCE_PATH)
            self._write(root, RELEASE_PROJECTION_PATH, release)
            report = reconciliation_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REC-007" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_release_capability_binding_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            release = self._load(root, RELEASE_PROJECTION_PATH)
            release["evidence_registry"]["buzz_capability_binding"]["subject_id"] = "CAP-011"
            self._write(root, RELEASE_PROJECTION_PATH, release)
            report = reconciliation_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REC-008" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_reconciliation_flag_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            release = self._load(root, RELEASE_PROJECTION_PATH)
            release["buzz_reconciliation"]["deterministic_regeneration_pass"] = False
            self._write(root, RELEASE_PROJECTION_PATH, release)
            report = reconciliation_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REC-009" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_authority_count_escalation_in_projection_fails_closed(self):
        td, root = self._copy_root()
        try:
            release = self._load(root, RELEASE_PROJECTION_PATH)
            release["buzz_reconciliation"]["new_architectural_authorities"] = 1
            self._write(root, RELEASE_PROJECTION_PATH, release)
            report = reconciliation_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REC-009" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_current_host_runtime_claim_fails_closed(self):
        td, root = self._copy_root()
        try:
            evidence = self._load(root, GLOBAL_EVIDENCE_PATH)
            evidence["current_host_runtime_evidence"] = "PASS"
            self._write(root, GLOBAL_EVIDENCE_PATH, evidence)
            report = reconciliation_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REC-006" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_manifest_omission_fails_closed(self):
        td, root = self._copy_root()
        try:
            release = self._load(root, RELEASE_PROJECTION_PATH)
            release["manifest"] = [x for x in release["manifest"] if x.get("path") != "src/fa3_buzz_global_reconciliation.py"]
            release["manifest_entry_count"] = len(release["manifest"])
            self._write(root, RELEASE_PROJECTION_PATH, release)
            report = reconciliation_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REC-011" for x in report["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
