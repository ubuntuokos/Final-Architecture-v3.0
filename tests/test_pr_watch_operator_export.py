import hashlib
import hmac
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_pr_watch import ProjectionStore,normalize_webhook,PRWatchDenied
from fa3_pr_watch_operator_export import export_operator_view,SCHEMA

SECRET=b"reference-export-hmac-only-0001"


class OperatorExportTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.store=ProjectionStore(self.root/"state")
        self.export_dir=self.root/"operator-view"
        self.export_dir.mkdir(mode=0o750)
        self.export_dir.chmod(0o750)
        self.destination=self.export_dir/"operator.json"

    def ingest(self):
        body=json.dumps({"action":"opened",
            "repository":{"full_name":"fa3/reference-fixture"},"sender":{"login":"attacker"},
            "pull_request":{"number":1,"title":"Fixture PR",
                "updated_at":"2026-09-28T12:00:00Z","head":{"sha":"a"*40},
                "base":{"sha":"b"*40},
                "body":"HIDDEN_UNTRUSTED_PROMPT_AND_TOKEN"}},
            sort_keys=True).encode()
        event=normalize_webhook(body,signature="sha256="+
            hmac.new(SECRET,body,hashlib.sha256).hexdigest(),
            secret=SECRET,event_type="pull_request",delivery_id="group-view")
        self.store.ingest(event)

    def test_export_keeps_private_replay_cache_and_redacts_input(self):
        self.ingest()
        receipt=export_operator_view(self.store,self.destination)
        self.assertEqual(1,receipt["count"])
        self.assertFalse(receipt["authority"])
        doc=json.loads(self.destination.read_text())
        self.assertEqual(SCHEMA,doc["schema"])
        self.assertFalse(doc["authority"])
        self.assertFalse(doc["execution_enabled"])
        self.assertTrue(doc["redacted"])
        raw=json.dumps(doc)
        self.assertNotIn("HIDDEN_UNTRUSTED_PROMPT",raw)
        self.assertNotIn("attacker",raw)
        self.assertNotIn(SECRET.decode(),raw)
        self.assertEqual(0o640,stat.S_IMODE(self.destination.stat().st_mode))
        private=self.store.state_dir/"projection.json"
        self.assertEqual(0o600,stat.S_IMODE(private.stat().st_mode))

    def test_export_rejects_world_readable_directory(self):
        self.export_dir.chmod(0o755)
        with self.assertRaises(PRWatchDenied):
            export_operator_view(self.store,self.destination)

    def test_export_rejects_symlink_target(self):
        outside=self.root/"outside"
        outside.write_text("protected")
        self.destination.symlink_to(outside)
        with self.assertRaises(PRWatchDenied):
            export_operator_view(self.store,self.destination)
        self.assertEqual("protected",outside.read_text())

    def test_export_no_default_world_file_from_empty_projection(self):
        receipt=export_operator_view(self.store,self.destination)
        self.assertEqual(0,receipt["count"])
        self.assertEqual({},json.loads(self.destination.read_text())["items"])

if __name__=="__main__":unittest.main()
