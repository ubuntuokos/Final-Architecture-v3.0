import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_os_event_privacy_gate import GATE_ID, PROFILE_ID, POLICY_ID, gate


class FA3OSEventPrivacyGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        return td, root

    @staticmethod
    def _load(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, obj):
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["gate_id"], GATE_ID)
        self.assertEqual(report["profile_id"], PROFILE_ID)
        self.assertEqual(report["privacy_profile_id"], POLICY_ID)
        self.assertEqual(report["ledger_authority"], "FA3-JOURNAL-001")
        self.assertEqual(report["capability_count"], 175)

    def test_parallel_ledger_authority_is_rejected(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/profiles/FA3-OS-001.json"
            obj = self._load(path)
            obj["ledger_authority"] = "FA3-OS-001"
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "FA3-OS-AUTH-003" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_new_authority_or_capability_is_rejected(self):
        for field in ("new_architectural_authority", "new_capability"):
            with self.subTest(field=field):
                td, root = self._copy_root()
                try:
                    path = root / "canonical/profiles/FA3-OS-001.json"
                    obj = self._load(path)
                    obj[field] = True
                    self._write(path, obj)
                    report = gate(root)
                    self.assertEqual(report["result"], "FAIL")
                finally:
                    td.cleanup()

    def test_keylogging_allow_is_rejected(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/profiles/FA3-OS-POLICY-001.json"
            obj = self._load(path)
            obj["default_capture"]["keylogging"] = "ALLOW"
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "FA3-OS-PRIV-006" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_clipboard_default_allow_is_rejected(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/profiles/FA3-OS-POLICY-001.json"
            obj = self._load(path)
            obj["default_capture"]["generic_clipboard"] = "ALLOW"
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
        finally:
            td.cleanup()

    def test_event_schema_without_capture_policy_is_rejected(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/contracts/FA3-OS-EVENT-001.schema.json"
            obj = self._load(path)
            obj["required"].remove("capture_policy_id")
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "FA3-OS-SCHEMA-005" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_inline_sensitive_content_field_is_rejected(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/contracts/FA3-OS-EVENT-001.schema.json"
            obj = self._load(path)
            obj["properties"]["keystrokes"] = {"type": "string"}
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "FA3-OS-SCHEMA-007" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_resume_plan_execution_authority_is_rejected(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/profiles/FA3-OS-001.json"
            obj = self._load(path)
            obj["session_resume"]["execution_authority"] = True
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "FA3-OS-AUTH-005" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_historical_rewrite_erasure_is_rejected(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/profiles/FA3-OS-POLICY-001.json"
            obj = self._load(path)
            obj["selective_erasure"]["historical_event_rewrite"] = True
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "FA3-OS-ERASE-002" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_journal_append_only_drift_is_rejected(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/profiles/FA3-JOURNAL-001.json"
            obj = self._load(path)
            obj["invariants"].remove("EVENT_STORAGE_APPEND_ONLY_BY_DEFAULT")
            self._write(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "FA3-OS-JRN-002" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
