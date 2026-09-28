from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_donor_chat_import import _candidate_sources, _conversations, ingest, read_export
from fa3_donor_registry import REGISTRY_REL


class DonorChatImportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / REGISTRY_REL
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({
            "id": "FA3-DONOR-REFERENCE-REGISTRY-001",
            "entries": [], "backfill": {"entry_count": 0},
        }), encoding="utf-8")

    def entries(self):
        return json.loads(self.path.read_text(encoding="utf-8"))["entries"]

    def test_hungarian_and_english_link_mentions_merge_without_raw_text(self):
        records = [
            "Lehet donor: https://github.com/example/CreativeKit private-email@example.org token=SECRET123",
            "This could be a donor https://github.com/example/CreativeKit",
            "Unrelated https://github.com/other/not-a-donor",
        ]
        report = ingest(self.root, records, origin="chatgpt-export")
        self.assertEqual((report["created"], report["merged"]), (1, 0))
        self.assertEqual(len(self.entries()), 1)
        entry = self.entries()[0]
        self.assertEqual(entry["status"], "CANDIDATE")
        self.assertEqual(entry["source"]["normalized_key"], "github:example/creativekit")
        self.assertFalse(entry["automatic_code_import"])
        persisted = self.path.read_text(encoding="utf-8")
        self.assertNotIn("SECRET123", persisted)
        self.assertNotIn("private-email@example.org", persisted)

    def test_same_name_different_sources_are_distinct(self):
        report = ingest(self.root, [
            "Donor: https://github.com/alice/tool",
            "Donor: https://github.com/bob/tool",
        ], origin="chatgpt-export")
        self.assertEqual(report["created"], 2)
        self.assertEqual(len(self.entries()), 2)

    def test_project_name_requires_explicit_opt_in_for_new_public_entry(self):
        mention = "donor: Private Project Name"
        result = ingest(self.root, [mention], origin="chatgpt-export")
        self.assertEqual(result["unlinked_skipped"], 1)
        self.assertEqual(self.entries(), [])
        result = ingest(self.root, [mention], origin="chatgpt-export", allow_unlinked_names=True)
        self.assertEqual(result["created"], 1)
        self.assertEqual(self.entries()[0]["source"]["normalized_key"], "project:private project name")

    def test_dry_run_and_reimport_do_not_duplicate(self):
        mention = ["donornak alkalmas lehet: https://github.com/example/test"]
        dry = ingest(self.root, mention, origin="chatgpt-export", dry_run=True)
        self.assertEqual(dry["created"], 1)
        self.assertEqual(self.entries(), [])
        actual = ingest(self.root, mention, origin="chatgpt-export")
        repeat = ingest(self.root, mention, origin="chatgpt-export")
        self.assertEqual(actual["created"], 1)
        self.assertEqual(repeat["created"], 0)
        self.assertEqual(repeat["merged"], 1)
        self.assertEqual(len(self.entries()), 1)

    def test_multi_url_mentions_capture_each_public_source(self):
        result = ingest(self.root, [
            "Potential donor: https://github.com/example/one and https://github.com/example/two"
        ], origin="chatgpt-export")
        self.assertEqual(result["created"], 2)

    def test_rejections_and_non_signals_do_not_create_candidates(self):
        result = ingest(self.root, [
            "Look at https://github.com/example/ordinary",
            "not a donor https://github.com/example/rejected",
            "donornak alkalmatlan: https://github.com/example/bad",
            "donor: https://github.com/ubuntuokos/Final-Architecture-v3.0"
        ], origin="chatgpt-export")
        self.assertEqual(result["created"], 0)
        self.assertEqual(self.entries(), [])

    def test_export_zip_and_numbered_json_without_extraction(self):
        conversation = [{
            "title": "sensitive title - must not be persisted",
            "mapping": {
                "u1": {"message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["Potential donor: https://github.com/example/fromuser"]},
                }},
                "a1": {"message": {
                    "author": {"role": "assistant"},
                    "content": {"parts": ["donornak alkalmas: https://github.com/example/fromassistant"]},
                }},
                "t1": {"message": {
                    "author": {"role": "tool"},
                    "content": {"parts": ["donor: https://github.com/example/fromtool"]},
                }},
            },
        }]
        archive = self.root / "chatgpt-export.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("export/conversations.json", json.dumps(conversation))
            zf.writestr("export/conversations_2.json", json.dumps(conversation))
            zf.writestr("export/other-sensitive-file.json", '{"private":true}')
        self.assertEqual(len(list(read_export(archive))), 2)
        report = ingest(self.root, _conversations(archive, {"user", "assistant"}), origin="chatgpt-export")
        self.assertEqual(report["created"], 2)
        self.assertEqual(len(self.entries()), 2)
        saved = self.path.read_text(encoding="utf-8")
        self.assertNotIn("sensitive title", saved)
        self.assertNotIn("fromtool", saved)
        self.assertNotIn("other-sensitive-file", saved)

    def test_bare_github_domain_is_normalized_as_repository(self):
        result = ingest(self.root, [
            "donorként alkalmas lehet: github.com/example/domain-only"
        ], origin="chatgpt-export")
        self.assertEqual(result["created"], 1)
        self.assertEqual(self.entries()[0]["source"]["normalized_key"], "github:example/domain-only")

    def test_bare_repo_and_explicit_adapter_event(self):
        report = ingest(self.root, [
            "This could be a donor p4nda0s/reverse-skills",
            {"potential_donor": True, "name": "Another", "source": "https://github.com/example/another"}
        ], origin="approved-chat-event")
        self.assertEqual(report["created"], 2)
        self.assertEqual({e["source"]["normalized_key"] for e in self.entries()}, {
            "github:p4nda0s/reverse-skills", "github:example/another"
        })

    def test_malformed_export_never_mutates_registry(self):
        before = self.path.read_bytes()
        broken = self.root / "conversations.json"
        broken.write_text('{"not":"conversation array"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            ingest(self.root, _conversations(broken, {"user"}), origin="chatgpt-export")
        self.assertEqual(self.path.read_bytes(), before)

    def test_canonical_bridge_boundary_contract(self):
        contract = json.loads((ROOT / "canonical/contracts/FA3-DONOR-CHAT-INGEST-001.json").read_text(encoding="utf-8"))
        self.assertFalse(contract["architectural_authority"])
        self.assertFalse(contract["automatic_code_import"])
        self.assertFalse(contract["automatic_dependency"])
        self.assertFalse(contract["unattended_chatgpt_account_access"])
        self.assertEqual(contract["accepted_inputs"], ["CHATGPT_EXPORT_ZIP", "CONVERSATIONS_JSON", "APPROVED_LOCAL_EVENT_JSONL"])
        self.assertTrue(contract["raw_conversation_persistence_forbidden"])


if __name__ == "__main__":
    unittest.main()
