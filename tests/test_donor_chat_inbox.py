from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_donor_chat_inbox import process_inbox
from fa3_donor_registry import REGISTRY_REL


class PrivateDonorInboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.home = Path(self.temp.name) / "private"
        self.target = self.root / REGISTRY_REL
        self.target.parent.mkdir(parents=True)
        self.target.write_text(json.dumps({
            "id":"FA3-DONOR-REFERENCE-REGISTRY-001",
            "entries":[], "backfill":{"entry_count":0}
        }), encoding="utf-8")
        (self.home / "inbox").mkdir(parents=True)

    def _donor_count(self):
        return len(json.loads(self.target.read_text(encoding="utf-8"))["entries"])

    def test_private_inbox_import_is_idempotent_and_privately_checkpointed(self):
        export = self.home / "inbox" / "history.zip"
        rows = [{
            "title":"Do not publish this private chat title",
            "mapping":{
                "u":{"message":{
                    "author":{"role":"user"},
                    "content":{"parts":["Donor: https://github.com/example/inbox"]}
                }}
            }
        }]
        with zipfile.ZipFile(export, "w") as archive:
            archive.writestr("conversations.json", json.dumps(rows))
        first = process_inbox(self.root, self.home)
        second = process_inbox(self.root, self.home)
        self.assertEqual(first["imports"], 1)
        self.assertEqual(first["created"], 1)
        self.assertEqual(second["imports"], 0)
        self.assertEqual(second["previously_seen"], 1)
        self.assertEqual(self._donor_count(), 1)
        checkpoint = self.home / "processed.json"
        self.assertEqual(checkpoint.stat().st_mode & 0o777, 0o600)
        persisted = self.target.read_text(encoding="utf-8")
        self.assertNotIn("Do not publish this", persisted)
        self.assertNotIn("history.zip", persisted)

    def test_new_export_reuses_same_donor_identity(self):
        inbox = self.home / "inbox"
        rows = lambda url: [{"mapping":{"u":{"message":{
            "author":{"role":"user"}, "content":{"parts":[f"potential donor: {url}"]}
        }}}}]
        (inbox / "conversations.json").write_text(json.dumps(rows("https://github.com/example/shared")), encoding="utf-8")
        first = process_inbox(self.root, self.home)
        self.assertEqual(first["created"], 1)
        (inbox / "conversations_2.json").write_text(json.dumps(rows("https://github.com/example/shared")), encoding="utf-8")
        again = process_inbox(self.root, self.home)
        self.assertEqual(again["created"], 0)
        self.assertEqual(again["merged"], 1)
        self.assertEqual(self._donor_count(), 1)

    def test_malformed_export_does_not_checkpoint(self):
        (self.home / "inbox" / "conversations.json").write_text('{"wrong":"shape"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            process_inbox(self.root, self.home)
        self.assertFalse((self.home / "processed.json").exists())
        self.assertEqual(self._donor_count(), 0)


if __name__ == "__main__":
    unittest.main()
