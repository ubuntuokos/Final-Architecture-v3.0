from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "FA3-JOURNAL-001"
ARCHIVE_PROFILE_ID = "FA3-JOURNAL-ARCHIVE-001"
GATESET_ID = "FA3-JOURNAL-GATESET-001"
RELEASE_PATH = ROOT / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
POLICY_PATH = ROOT / "canonical/enforcement-policy.json"
REQUIRED_MANIFEST_PATHS = {
    ".github/workflows/fa3-journal-archive-gate.yml",
    ".github/workflows/fa3-journal-reconcile.yml",
    "apps/fa3-control-center/CMakeLists.txt",
    "apps/fa3-control-center/README.md",
    "apps/fa3-control-center/qml/JournalPage.qml",
    "apps/fa3-control-center/qml/Main.qml",
    "apps/fa3-control-center/src/JournalService.cpp",
    "apps/fa3-control-center/src/JournalService.h",
    "apps/fa3-control-center/src/main.cpp",
    "canonical/FA3-GATE-JOURNAL-ARCHIVE-001.json",
    "canonical/FA3-JOURNAL-ARCHIVE-CONFORMANCE-MATRIX-001.json",
    "canonical/FA3-JOURNAL-ARCHIVE-RUNTIME-CONFORMANCE-001.json",
    "canonical/contracts/FA3-JOURNAL-CONTRACTS-001.json",
    "canonical/decisions/FA3-DEC-JOURNAL-ARCHIVE-2026-09-13.json",
    "canonical/journal-enforcement.json",
    "canonical/profiles/FA3-JOURNAL-001.json",
    "canonical/profiles/FA3-JOURNAL-ARCHIVE-001.json",
    "canonical/providers/FA3-PROVIDER-JOURNAL-LOCAL-001.json",
    "docs/FA3-JOURNAL-ARCHIVE-001.md",
    "evidence/reference/fa3-journal-archive-reference.json",
    "tests/test_journal_archive_gate.py",
    "tests/test_journal_global_reconciliation.py",
    "tools/fa3_journal_global_reconcile.py",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class JournalGlobalReconciliationTests(unittest.TestCase):
    def test_journal_gate_is_globally_mandatory(self) -> None:
        policy = load(POLICY_PATH)
        release = load(RELEASE_PATH)
        self.assertEqual(policy["canonical_capability_count"], 143)
        self.assertIn(GATESET_ID, policy["mandatory_reference_gates"])
        self.assertIn(GATESET_ID, release["mandatory_reference_gates"])
        self.assertEqual(
            set(policy["mandatory_reference_gates"]),
            set(release["mandatory_reference_gates"]),
        )
        self.assertEqual(policy["journal_profile_id"], PROFILE_ID)
        self.assertEqual(policy["journal_archive_profile_id"], ARCHIVE_PROFILE_ID)

    def test_journal_release_semantics_remain_non_authoritative_and_non_promoted(self) -> None:
        release = load(RELEASE_PATH)
        journal = release["journal_reconciliation"]
        self.assertEqual(journal["profile_id"], PROFILE_ID)
        self.assertEqual(journal["archive_profile_id"], ARCHIVE_PROFILE_ID)
        self.assertEqual(journal["active_log_integrity"], "APPEND_ONLY")
        self.assertEqual(journal["archive_integrity"], "SEALED_SHA256")
        self.assertEqual(journal["event_delete_semantics"], "TOMBSTONE")
        self.assertEqual(journal["archive_delete_semantics"], "RETENTION_TRASH")
        self.assertTrue(journal["restore_requires_integrity_pass"])
        self.assertEqual(journal["runtime_status"], "PENDING_CURRENT_HOST")
        self.assertIs(journal["production_admitted"], False)
        self.assertIs(journal["current_host_runtime_promotion_claimed"], False)
        self.assertIs(journal["provider_is_architectural_authority"], False)
        self.assertEqual(journal["new_capabilities"], 0)
        self.assertEqual(journal["new_architectural_authorities"], 0)
        self.assertEqual(journal["capability_count_after"], 143)

    def test_all_journal_release_surface_files_are_manifested(self) -> None:
        release = load(RELEASE_PATH)
        manifest_paths = {entry["path"] for entry in release["manifest"]}
        self.assertFalse(REQUIRED_MANIFEST_PATHS - manifest_paths)

    def test_projection_records_deterministic_journal_generator(self) -> None:
        release = load(RELEASE_PATH)
        verification = release["manifest_verification"]
        self.assertEqual(
            verification["journal_reconciliation_generator"],
            "tools/fa3_journal_global_reconcile.py",
        )
        self.assertIs(verification["journal_deterministic_regeneration_pass"], True)
        self.assertTrue(verification["journal_snapshot_head"])


if __name__ == "__main__":
    unittest.main()
