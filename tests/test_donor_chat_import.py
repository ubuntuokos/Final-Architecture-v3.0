"""Exact owner donor-command and approved intake boundary regressions."""
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
from fa3_donor_registry import REGISTRY_REL, REJECTION_AUDIT_REL, capture_candidate, parse_donor_mention

class DonorChatImportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / REGISTRY_REL
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({
            "id": "FA3-DONOR-REFERENCE-REGISTRY-001",
            "entries": [], "backfill": {"entry_count": 0}
        }), encoding="utf-8")
        self.audit_path = self.root / REJECTION_AUDIT_REL
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_path.write_text(json.dumps({
            "id": "FA3-DONOR-REJECTION-AUDIT-001", "entries": []
        }), encoding="utf-8")

    def entries(self):
        return json.loads(self.path.read_text(encoding="utf-8"))["entries"]

    def user(self, text):
        return {"speaker_role": "user", "text": text}

    def test_unmarked_links_are_analysis_only_even_with_potential_signals(self):
        before = self.path.read_bytes()
        report = ingest(self.root, [
            self.user("Maybe donor: https://github.com/example/one"),
            self.user("Donor: https://github.com/example/two"),
            self.user("donorként alkalmas lehet https://github.com/example/three"),
            self.user("https://github.com/example/four"),
            {"speaker_role": "assistant", "text": "donornak: https://github.com/example/five"},
            "donornak: https://github.com/example/unknown-speaker",
            {"potential_donor": True, "source": "https://github.com/example/six",
             "name": "six", "owner_submitted_link": True},
        ], origin="chatgpt-export")
        self.assertEqual((report["created"], report["merged"]), (0, 0))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertGreaterEqual(report["analysis_only"], 7)

    def test_command_may_precede_or_follow_links_but_only_owner_role_counts(self):
        report = ingest(self.root, [
            self.user("https://github.com/example/before donornak: https://github.com/example/after"),
            {"speaker_role": "assistant", "text": "donornak: https://github.com/example/assistant"}
        ], origin="chatgpt-export")
        self.assertEqual(report["created"], 2)
        self.assertEqual(
            {row["source"]["normalized_key"] for row in self.entries()},
            {"github:example/before", "github:example/after"},
        )
        self.assertTrue(all(row["status"] == "ACCEPTED_REFERENCE" for row in self.entries()))
        self.assertTrue(all(row["automatic_code_import"] is False for row in self.entries()))
        self.assertTrue(all(row["automatic_provider_admission"] is False for row in self.entries()))

    def test_marked_owner_batches_and_organization_topic_links(self):
        links = " ".join("https://github.com/example/tool" + str(n) for n in range(20))
        report = ingest(self.root, [self.user(
            "donornak: https://github.com/oracle https://github.com/topics/video?l=python " + links
        )], origin="chatgpt-export")
        self.assertEqual(report["created"], 22)
        self.assertEqual(len(self.entries()), 22)
        self.assertTrue(all(row["status"] == "ACCEPTED_REFERENCE" for row in self.entries()))

    def test_metadata_event_requires_owner_marker_and_explicit_owner_role(self):
        records = [
            {"potential_donor": True, "name": "one", "source": "https://github.com/example/one",
             "speaker_role": "user", "owner_submitted_link": True},
            {"potential_donor": True, "name": "two", "source": "https://github.com/example/two",
             "owner_donor_marker": "donornak", "owner_submitted_link": True},
            {"potential_donor": True, "name": "three", "source": "https://github.com/example/three",
             "owner_donor_marker": "donornak", "owner_submitted_link": True, "speaker_role": "user"},
            {"speaker_role": "user", "text": "donornak: https://github.com/example/four",
             "owner_submitted_link": True}
        ]
        report = ingest(self.root, records, origin="approved-chat-event")
        self.assertEqual(report["created"], 2)
        self.assertEqual({row["source"]["normalized_key"] for row in self.entries()},
                         {"github:example/three", "github:example/four"})

    def test_untrusted_event_claim_cannot_enroll(self):
        report = ingest(self.root, [
            {"speaker_role": "user", "text": "donornak: https://github.com/example/forged"}
        ], origin="approved-chat-event")
        self.assertEqual(report["created"], 0)
        self.assertEqual(self.entries(), [])

    def test_direct_reimport_idempotent_preserves_owner_pre_review(self):
        records = [self.user("donornak: https://github.com/example/one")]
        dry = ingest(self.root, records, origin="chatgpt-export", dry_run=True)
        self.assertEqual(dry["created"], 1)
        self.assertEqual(self.entries(), [])
        first = ingest(self.root, records, origin="chatgpt-export")
        second = ingest(self.root, records, origin="chatgpt-export")
        self.assertEqual((first["created"], second["merged"]), (1, 1))
        self.assertEqual(len(self.entries()), 1)
        self.assertFalse(self.entries()[0]["submission_review"]["second_registry_approval_required"])

    def test_rejected_history_blocks_normal_reentry_without_partial_write(self):
        capture_candidate(self.root, name="denied", source_kind="GITHUB",
                          source_locator="https://github.com/example/denied",
                          explicit_donor_marker=True, owner_submitted_link=True)
        data=json.loads(self.path.read_text(encoding="utf-8"))
        rejected=data["entries"].pop()
        data["backfill"]["entry_count"]=0
        self.path.write_text(json.dumps(data), encoding="utf-8")
        self.audit_path.write_text(json.dumps({
            "id":"FA3-DONOR-REJECTION-AUDIT-001",
            "entries":[{"donor":rejected}]
        }), encoding="utf-8")
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,
                "REJECTED_DONOR_REENTRY_REQUIRES_VERIFIED_SAFE_MAINTENANCE"):
            ingest(self.root, [self.user("donornak: https://github.com/example/new https://github.com/example/denied")],
                   origin="chatgpt-export")
        self.assertEqual(self.path.read_bytes(), before)

    def test_unmarked_intake_never_modifies_an_existing_entry(self):
        ingest(self.root, [self.user("donornak: https://github.com/example/one")],
               origin="chatgpt-export")
        before=self.path.read_bytes()
        ingest(self.root, [self.user("candidate https://github.com/example/one")],
               origin="chatgpt-export")
        self.assertEqual(self.path.read_bytes(), before)

    def test_private_export_only_owner_marked_text_registration(self):
        conversation=[{"title":"PRIVATE SECRET","mapping":{
            "u1":{"message":{"author":{"role":"user"},
                             "content":{"parts":["Candidate https://github.com/example/not"]}}},
            "u2":{"message":{"author":{"role":"user"},
                             "content":{"parts":["donornak: https://github.com/example/yes SECRET123"]}}},
            "a1":{"message":{"author":{"role":"assistant"},
                             "content":{"parts":["donornak: https://github.com/example/assistant"]}}}}}]
        archive=self.root/"export.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("conversations.json", json.dumps(conversation))
            zf.writestr("other-secret.txt","PRIVATE")
        self.assertEqual(len(list(read_export(archive))), 1)
        report=ingest(self.root, _conversations(archive, {"user","assistant"}, include_roles=True),
                      origin="chatgpt-export")
        self.assertEqual(report["created"], 1)
        saved=self.path.read_text(encoding="utf-8")
        self.assertNotIn("SECRET123", saved)
        self.assertNotIn("PRIVATE", saved)
        self.assertNotIn("example/not", saved)
        self.assertNotIn("example/assistant", saved)

    def test_explicit_owner_marker_parser_positive(self):
        sources, ambiguous = _candidate_sources("donornak: https://github.com/example/one", owner_direct=True)
        self.assertFalse(ambiguous)
        self.assertEqual(sources, [("example/one", "GITHUB", "https://github.com/example/one")])

    def test_owner_donornak_without_colon_before_link(self):
        sources, ambiguous = _candidate_sources(
            "donornak https://github.com/example/no-colon", owner_direct=True)
        self.assertFalse(ambiguous)
        self.assertEqual(sources, [("example/no-colon", "GITHUB",
                                    "https://github.com/example/no-colon")])
        result = ingest(self.root, [self.user(
            "donornak https://github.com/example/no-colon")],
            origin="chatgpt-export")
        self.assertEqual(result["created"], 1)
        self.assertEqual(self.entries()[0]["status"], "ACCEPTED_REFERENCE")

    def test_negated_owner_marker_is_not_an_intake_instruction(self):
        before = self.path.read_bytes()
        result = ingest(self.root, [self.user(
            "nem donornak: https://github.com/example/never-register"),
            self.user("not donornak https://github.com/example/also-not")],
            origin="chatgpt-export")
        self.assertEqual(result["created"], 0)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(
            _candidate_sources("nem donornak: https://github.com/example/no",
                               owner_direct=True)[0], [])

    def test_missing_marker_never_passes_candidate_sources(self):
        self.assertEqual(_candidate_sources("Donor: https://github.com/example/one", owner_direct=True)[0], [])
        self.assertEqual(_candidate_sources("donornak: https://github.com/example/one", owner_direct=False)[0], [])

    def test_canonical_bridge_boundary_contract(self):
        contract=json.loads((ROOT/"canonical/contracts/FA3-DONOR-CHAT-INGEST-001.json").read_text())
        self.assertFalse(contract["explicit_owner_donornak_before_link_required"])
        self.assertEqual(
            contract["approved_owner_donor_commands"],
            ["donornak", "vedd fel donornak", "add a donorlistához"],
        )
        self.assertTrue(contract["exact_command_set_only"])
        self.assertFalse(contract["command_inside_url_authorizes_intake"])
        self.assertFalse(contract["negated_command_authorizes_intake"])
        self.assertTrue(contract["approved_plan_registration"]["committed_approval_required"])
        self.assertEqual(contract["unmarked_link_disposition"], "ANALYSIS_ONLY_NO_REGISTRY_MUTATION")
        self.assertFalse(contract["automatic_code_import"])
        self.assertFalse(contract["unattended_chatgpt_account_access"])

    def test_exact_owner_commands_are_equivalent(self):
        for index, command in enumerate(("donornak", "vedd fel donornak", "add a donorlistához"), 1):
            with self.subTest(command=command):
                result = ingest(
                    self.root,
                    [self.user(f"{command}: https://github.com/example/equivalent-{index}")],
                    origin="chatgpt-export",
                )
                self.assertEqual(result["created"], 1)
        self.assertEqual(len(self.entries()), 3)

    def test_near_match_url_embedded_command_and_clause_negation_do_not_authorize(self):
        before=self.path.read_bytes()
        records=[
            self.user("add donorlistahoz https://github.com/example/near-match"),
            self.user("https://github.com/example/donornak"),
            self.user("https://example.com/search?q=donornak"),
            self.user("don't ever add a donorlistához https://github.com/example/negated"),
            self.user("do not: add a donorlistához https://github.com/example/negated-two"),
        ]
        result=ingest(self.root,records,origin="chatgpt-export")
        self.assertEqual(result["created"],0)
        self.assertEqual(self.path.read_bytes(),before)

    def test_command_only_followup_targets_only_immediately_previous_owner_message(self):
        result=ingest(self.root,[
            self.user("https://github.com/example/followup"),
            self.user("vedd fel donornak"),
        ],origin="chatgpt-export")
        self.assertEqual(result["created"],1)
        self.assertEqual(self.entries()[0]["source"]["normalized_key"],"github:example/followup")

        before=self.path.read_bytes()
        result=ingest(self.root,[
            self.user("https://github.com/example/stale"),
            self.user("intervening owner message with no URL"),
            self.user("add a donorlistához"),
        ],origin="chatgpt-export")
        self.assertEqual(result["created"],0)
        self.assertEqual(self.path.read_bytes(),before)

    def test_skipped_owner_message_clears_followup_target(self):
        before=self.path.read_bytes()
        result=ingest(self.root,[
            self.user("https://github.com/example/stale-skipped"),
            {"speaker_role":"user","text":"","skipped":True,"message_boundary":True},
            self.user("donornak"),
        ],origin="chatgpt-export")
        self.assertEqual(result["created"],0)
        self.assertEqual(self.path.read_bytes(),before)

    def test_command_only_followup_cannot_cross_conversation_boundary(self):
        export = self.root / "conversations.json"
        export.write_text(json.dumps([
            {
                "mapping": {
                    "a": {
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["https://github.com/example/from-conversation-a"]},
                        }
                    }
                }
            },
            {
                "mapping": {
                    "b": {
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["donornak"]},
                        }
                    }
                }
            },
        ]), encoding="utf-8")
        records = list(_conversations(export, {"user"}, include_roles=True))
        self.assertTrue(any(row.get("conversation_boundary") is True for row in records))
        before = self.path.read_bytes()
        result = ingest(self.root, records, origin="chatgpt-export")
        self.assertEqual(result["created"], 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_supplied_source_must_match_commanded_url(self):
        self.assertEqual(
            parse_donor_mention(
                "add a donorlistához https://github.com/example/approved",
                source="https://github.com/example/approved",
            )[2],
            "https://github.com/example/approved",
        )
        with self.assertRaisesRegex(ValueError,"contradicts"):
            parse_donor_mention(
                "vedd fel donornak https://github.com/example/approved",
                source="https://github.com/example/other",
            )
        with self.assertRaisesRegex(ValueError,"conversation importer context"):
            parse_donor_mention(
                "add a donorlistához",
                source="https://github.com/example/context-free",
            )

if __name__ == "__main__":
    unittest.main()
