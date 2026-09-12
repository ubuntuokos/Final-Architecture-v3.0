from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "FA3-MANAGER-001"
GATESET_ID = "FA3-MANAGER-GATESET-001"
RELEASE_PATH = ROOT / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
POLICY_PATH = ROOT / "canonical/enforcement-policy.json"
REQUIRED_MANIFEST_PATHS = {
    ".github/workflows/fa3-manager-gate.yml",
    ".github/workflows/fa3-manager-reconcile.yml",
    "canonical/FA3-MANAGER-CONFORMANCE-MATRIX-001.json",
    "canonical/FA3-MANAGER-RUNTIME-CONFORMANCE-001.json",
    "canonical/FA3-GATE-MANAGER-001.json",
    "canonical/manager-enforcement.json",
    "canonical/contracts/FA3-MANAGER-CONTRACTS-001.json",
    "canonical/decisions/FA3-DEC-MANAGER-2026-09-12.json",
    "canonical/profiles/FA3-MANAGER-001.json",
    "canonical/providers/FA3-PROVIDER-MANAGER-LOCAL-001.json",
    "evidence/reference/fa3-manager-reference-pending.json",
    "src/fa3_manager.py",
    "src/fa3_manager_gate.py",
    "tests/test_manager_gate.py",
    "tests/test_manager_global_reconciliation.py",
    "tools/fa3_manager_global_reconcile.py",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ManagerGlobalReconciliationTests(unittest.TestCase):
    def test_manager_gate_is_globally_mandatory(self) -> None:
        policy = load(POLICY_PATH)
        release = load(RELEASE_PATH)
        self.assertIn(GATESET_ID, policy["mandatory_reference_gates"])
        self.assertIn(GATESET_ID, release["mandatory_reference_gates"])
        self.assertEqual(set(policy["mandatory_reference_gates"]), set(release["mandatory_reference_gates"]))

    def test_manager_release_semantics_remain_non_authoritative_and_non_promoted(self) -> None:
        release = load(RELEASE_PATH)
        manager = release["manager_reconciliation"]
        self.assertEqual(manager["profile_id"], PROFILE_ID)
        self.assertEqual(manager["direct_execution"], "FORBIDDEN")
        self.assertEqual(manager["typed_action_delegation"], "REQUIRED")
        self.assertEqual(manager["dependency_graph"], "ACYCLIC_REQUIRED")
        self.assertEqual(manager["implicit_done"], "FORBIDDEN")
        self.assertEqual(manager["verified_closure"], "ACCEPTANCE_PLUS_EVIDENCE_REQUIRED")
        self.assertEqual(manager["knowledge_gap_delegation"], "FA3-MENTOR-001")
        self.assertEqual(manager["coaching_delegation"], "FA3-COACH-001")
        self.assertEqual(manager["runtime_status"], "PENDING_CURRENT_HOST")
        self.assertIs(manager["production_admitted"], False)
        self.assertIs(manager["current_host_runtime_promotion_claimed"], False)
        self.assertIs(manager["provider_is_architectural_authority"], False)
        self.assertEqual(manager["new_capabilities"], 0)
        self.assertEqual(manager["new_architectural_authorities"], 0)
        self.assertEqual(manager["capability_count_after"], 143)

    def test_all_manager_release_surface_files_are_manifested(self) -> None:
        release = load(RELEASE_PATH)
        manifest_paths = {entry["path"] for entry in release["manifest"]}
        self.assertFalse(REQUIRED_MANIFEST_PATHS - manifest_paths)


if __name__ == "__main__":
    unittest.main()
