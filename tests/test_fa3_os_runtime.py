from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fa3_os_runtime import PolicyViolation, build_derived_projection, ingest_event, normalize_capture_request, query_events, run_reference_conformance
from fa3_os_runtime_gate import gate as runtime_gate


class Fa3OsRuntimeTests(unittest.TestCase):
    def base_event(self) -> dict:
        return {
            "source_kind": "APPLICATION", "capture_kind": "APPLICATION_EVENT", "action": "FILE_SAVE",
            "subject": {"kind": "FILE", "reference": "/projects/demo/a.png"}, "application_id": "Krita",
            "project_id": "DEMO", "session_id": "S1", "workstream_id": "WS1", "artifact_id": "ART1",
            "provenance": {"source_class": "APPLICATION_ADAPTER", "source_reference": "krita-adapter"},
            "confidence": 1.0, "tags": ["save"],
        }

    def test_reference_conformance_passes(self):
        self.assertEqual(run_reference_conformance()["result"], "PASS")

    def test_valid_event_is_appended_and_projected(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = Path(temp) / "active.jsonl"
            receipt = ingest_event(self.base_event(), journal)
            self.assertEqual(receipt["result"], "PASS")
            rows = query_events(journal, project_id="DEMO")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["integrity"], "APPEND_ONLY")
            projection = build_derived_projection(journal)
            self.assertFalse(projection["authoritative_history"])
            self.assertTrue(projection["rebuildable"])
            self.assertEqual(projection["workstreams"][0]["id"], "WS1")

    def test_secret_is_redacted_before_persistence(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = Path(temp) / "active.jsonl"
            event = self.base_event(); event["summary"] = "api_key=DO_NOT_PERSIST_THIS_VALUE"
            ingest_event(event, journal)
            raw = journal.read_text(encoding="utf-8")
            self.assertNotIn("DO_NOT_PERSIST_THIS_VALUE", raw)
            self.assertIn("[REDACTED]", raw)

    def test_prohibited_capture_classes_fail_closed(self):
        for capture_kind in ("KEYLOGGER", "CLIPBOARD", "SCREENSHOT", "SCREEN_CAPTURE"):
            event = self.base_event(); event["capture_kind"] = capture_kind
            with self.assertRaises(PolicyViolation):
                normalize_capture_request(event)

    def test_terminal_content_fails_closed(self):
        event = self.base_event(); event["source_kind"] = "TERMINAL"; event["command"] = "cat ~/.ssh/id_rsa"
        with self.assertRaises(PolicyViolation):
            normalize_capture_request(event)

    def test_password_manager_fails_closed(self):
        event = self.base_event(); event["application_id"] = "keepassxc"
        with self.assertRaises(PolicyViolation):
            normalize_capture_request(event)

    def test_sensitive_path_fails_closed(self):
        event = self.base_event(); event["subject"] = {"kind": "FILE", "reference": "~/.ssh/id_ed25519"}
        with self.assertRaises(PolicyViolation):
            normalize_capture_request(event)

    def test_runtime_materialization_gate(self):
        root = Path(__file__).resolve().parents[1]
        report = runtime_gate(root)
        self.assertEqual(report["result"], "PASS", json.dumps(report, indent=2))


if __name__ == "__main__":
    unittest.main()
