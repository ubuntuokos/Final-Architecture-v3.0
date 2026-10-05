from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "FA3-OS-001"
PRIVACY_PROFILE_ID = "FA3-OS-POLICY-001"
EVENT_CONTRACT_ID = "FA3-OS-EVENT-001"
GATESET_ID = "FA3-OS-EVENT-PRIVACY-GATESET-001"
LEDGER_AUTHORITY = "FA3-JOURNAL-001"
RELEASE_PATH = ROOT / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
POLICY_PATH = ROOT / "canonical/enforcement-policy.json"
REQUIRED_MANIFEST_PATHS = {
    ".github/workflows/fa3-os-reconcile.yml",
    "canonical/contracts/FA3-OS-EVENT-001.schema.json",
    "canonical/fa3-os-event-privacy-enforcement.json",
    "canonical/profiles/FA3-OS-001.json",
    "canonical/profiles/FA3-OS-POLICY-001.json",
    "src/fa3_os_event_privacy_gate.py",
    "tests/test_fa3_os_event_privacy_gate.py",
    "tests/test_fa3_os_global_reconciliation.py",
    "tools/fa3_os_global_reconcile.py",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class FA3OSGlobalReconciliationTests(unittest.TestCase):
    def test_fa3_os_gate_is_globally_mandatory(self) -> None:
        policy = load(POLICY_PATH)
        release = load(RELEASE_PATH)
        self.assertEqual(policy["canonical_capability_count"], 175)
        self.assertIn(GATESET_ID, policy["mandatory_reference_gates"])
        self.assertIn(GATESET_ID, release["mandatory_reference_gates"])
        self.assertEqual(set(policy["mandatory_reference_gates"]), set(release["mandatory_reference_gates"]))
        self.assertEqual(policy["fa3_os_profile_id"], PROFILE_ID)
        self.assertEqual(policy["fa3_os_privacy_profile_id"], PRIVACY_PROFILE_ID)
        self.assertEqual(policy["fa3_os_event_contract_id"], EVENT_CONTRACT_ID)
        self.assertEqual(policy["fa3_os_ledger_authority"], LEDGER_AUTHORITY)

    def test_fa3_os_release_semantics_remain_non_authoritative(self) -> None:
        release = load(RELEASE_PATH)
        item = release["fa3_os_reconciliation"]
        self.assertEqual(item["profile_id"], PROFILE_ID)
        self.assertEqual(item["privacy_profile_id"], PRIVACY_PROFILE_ID)
        self.assertEqual(item["event_contract_id"], EVENT_CONTRACT_ID)
        self.assertEqual(item["gateset_id"], GATESET_ID)
        self.assertEqual(item["ledger_authority"], LEDGER_AUTHORITY)
        self.assertIs(item["runtime_authority"], False)
        self.assertIs(item["historical_truth_authority"], False)
        self.assertIs(item["resume_plan_execution_authority"], False)
        self.assertTrue(item["privacy_gate_before_persistence"])
        self.assertEqual(item["keylogging_default"], "DENY")
        self.assertEqual(item["generic_clipboard_default"], "DENY")
        self.assertEqual(item["generic_screen_capture_default"], "DENY")
        self.assertEqual(item["terminal_capture_default"], "METADATA_ONLY")
        self.assertIs(item["derived_memory_authoritative"], False)
        self.assertEqual(item["new_capabilities"], 0)
        self.assertEqual(item["new_architectural_authorities"], 0)
        self.assertLessEqual(item["capability_count_after"], 175)

    def test_all_fa3_os_release_surface_files_are_manifested(self) -> None:
        release = load(RELEASE_PATH)
        manifest_paths = {entry["path"] for entry in release["manifest"]}
        self.assertFalse(REQUIRED_MANIFEST_PATHS - manifest_paths)

    def test_projection_records_deterministic_fa3_os_generator(self) -> None:
        release = load(RELEASE_PATH)
        verification = release["manifest_verification"]
        self.assertEqual(
            verification["fa3_os_reconciliation_generator"],
            "tools/fa3_os_global_reconcile.py",
        )
        self.assertIs(verification["fa3_os_deterministic_regeneration_pass"], True)
        self.assertTrue(verification["fa3_os_snapshot_head"])


if __name__ == "__main__":
    unittest.main()
