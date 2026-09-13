from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "canonical/profiles/FA3-JOURNAL-001.json"
ARCHIVE_PROFILE = ROOT / "canonical/profiles/FA3-JOURNAL-ARCHIVE-001.json"
CONTRACTS = ROOT / "canonical/contracts/FA3-JOURNAL-CONTRACTS-001.json"
PROVIDER = ROOT / "canonical/providers/FA3-PROVIDER-JOURNAL-LOCAL-001.json"
DECISION = ROOT / "canonical/decisions/FA3-DEC-JOURNAL-ARCHIVE-2026-09-13.json"
ENFORCEMENT = ROOT / "canonical/journal-enforcement.json"
GATE = ROOT / "canonical/FA3-GATE-JOURNAL-ARCHIVE-001.json"
MATRIX = ROOT / "canonical/FA3-JOURNAL-ARCHIVE-CONFORMANCE-MATRIX-001.json"
RUNTIME = ROOT / "canonical/FA3-JOURNAL-ARCHIVE-RUNTIME-CONFORMANCE-001.json"
EVIDENCE = ROOT / "evidence/reference/fa3-journal-archive-reference.json"
CPP = ROOT / "apps/fa3-control-center/src/JournalService.cpp"
HEADER = ROOT / "apps/fa3-control-center/src/JournalService.h"
MAIN_QML = ROOT / "apps/fa3-control-center/qml/Main.qml"
JOURNAL_QML = ROOT / "apps/fa3-control-center/qml/JournalPage.qml"
CMAKE = ROOT / "apps/fa3-control-center/CMakeLists.txt"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class JournalArchiveGateTests(unittest.TestCase):
    def test_canonical_materialization_is_p0_must_without_new_authority(self) -> None:
        profile = load(PROFILE)
        archive = load(ARCHIVE_PROFILE)
        provider = load(PROVIDER)
        decision = load(DECISION)
        self.assertEqual(profile["status"], "CANONICAL")
        self.assertEqual(profile["priority"], "P0")
        self.assertEqual(profile["requirement"], "MUST")
        self.assertEqual(archive["parent_profile"], "FA3-JOURNAL-001")
        self.assertEqual(archive["relationship"], "SUBPROFILE-OF")
        self.assertFalse(provider["architectural_authority"])
        self.assertEqual(decision["capability_count_after"], 143)
        self.assertEqual(decision["capability_change"], 0)
        self.assertEqual(decision["architectural_authority_change"], 0)

    def test_archive_contract_is_fail_closed(self) -> None:
        contracts = load(CONTRACTS)
        archive = contracts["contracts"]["archive"]
        delete = contracts["contracts"]["delete"]
        self.assertEqual(archive["digest_algorithm"], "SHA-256")
        self.assertTrue(archive["restore_requires_integrity_pass"])
        self.assertEqual(delete["event_delete"], "TOMBSTONE")
        self.assertEqual(delete["archive_delete"], "RETENTION_TRASH")
        self.assertEqual(delete["physical_purge"], "POLICY_OR_ADMIN_ONLY")
        self.assertIn("DIGEST_MISMATCH_RESTORE_FORBIDDEN", contracts["fail_closed_rules"])

    def test_gate_and_enforcement_are_consistent(self) -> None:
        enforcement = load(ENFORCEMENT)
        gate = load(GATE)
        matrix = load(MATRIX)
        self.assertTrue(enforcement["fail_closed"])
        self.assertEqual(enforcement["mandatory_rule_count"], len(enforcement["rules"]))
        self.assertEqual(gate["gateset_id"], enforcement["gate_id"])
        self.assertEqual(gate["rule_count"], enforcement["mandatory_rule_count"])
        self.assertEqual(matrix["gateset_id"], enforcement["gate_id"])
        self.assertEqual(gate["capability_count_after"], 143)

    def test_runtime_and_reference_evidence_do_not_overclaim(self) -> None:
        runtime = load(RUNTIME)
        evidence = load(EVIDENCE)
        self.assertEqual(runtime["status"], "PENDING_CURRENT_HOST")
        self.assertFalse(runtime["production_admitted"])
        self.assertFalse(runtime["current_host_runtime_promotion_claimed"])
        self.assertFalse(evidence["claims"]["current_host_runtime_pass"])
        self.assertFalse(evidence["claims"]["production_admitted"])

    def test_reference_archive_engine_contains_required_integrity_and_retention_paths(self) -> None:
        cpp = CPP.read_text(encoding="utf-8")
        header = HEADER.read_text(encoding="utf-8")
        required_cpp = [
            "QCryptographicHash::Sha256",
            "fa3.journal-archive.v1",
            "payload_sha256",
            "VERIFY_FAIL",
            "RESTORE_BLOCKED_",
            "TOMBSTONE",
            "ARCHIVE_RETIRED",
            "xdg-email",
            "FA3_CHAT_SHARE_URL",
            "PRINT_SUBMITTED",
        ]
        for token in required_cpp:
            self.assertIn(token, cpp)
        for method in ["archiveAll", "archiveByPolicy", "verifyArchive", "restoreArchive", "retireArchive", "softDeleteEvent", "exportJournal", "printJournal", "shareJournal"]:
            self.assertIn(method, header)

    def test_control_center_exposes_journal_archive_gui(self) -> None:
        main = MAIN_QML.read_text(encoding="utf-8")
        journal = JOURNAL_QML.read_text(encoding="utf-8")
        cmake = CMAKE.read_text(encoding="utf-8")
        self.assertIn('label: "Napló / Journal"', main)
        self.assertIn("JournalPage", main)
        self.assertIn("JournalService.cpp", cmake)
        self.assertIn("JournalPage.qml", cmake)
        for label in ["Áttekintés", "Rendszer", "Beszélgetések", "Projektek", "Események", "Archívum"]:
            self.assertIn(label, journal)
        for action in ["Mentés / MD", "Nyomtatás", "E-mail", "Chat", "Archiválás most", "Integritás", "Visszaállítás", "Archív törlése"]:
            self.assertIn(action, journal)


if __name__ == "__main__":
    unittest.main()
