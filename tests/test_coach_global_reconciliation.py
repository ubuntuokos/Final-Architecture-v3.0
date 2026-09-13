from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "FA3-COACH-001"
GATESET_ID = "FA3-COACH-GATESET-001"
RELEASE_PATH = ROOT / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
POLICY_PATH = ROOT / "canonical/enforcement-policy.json"
REQUIRED_MANIFEST_PATHS = {
    ".github/workflows/fa3-coach-gate.yml",
    ".github/workflows/fa3-coach-reconcile.yml",
    "canonical/FA3-COACH-CONFORMANCE-MATRIX-001.json",
    "canonical/FA3-COACH-RUNTIME-CONFORMANCE-001.json",
    "canonical/FA3-GATE-COACH-001.json",
    "canonical/coach-enforcement.json",
    "canonical/contracts/FA3-COACH-CONTRACTS-001.json",
    "canonical/decisions/FA3-DEC-COACH-2026-09-12.json",
    "canonical/profiles/FA3-COACH-001.json",
    "canonical/providers/FA3-PROVIDER-COACH-LOCAL-001.json",
    "evidence/reference/fa3-coach-reference-pending.json",
    "src/fa3_coach.py",
    "src/fa3_coach_gate.py",
    "tests/test_coach_gate.py",
    "tests/test_coach_global_reconciliation.py",
    "tools/fa3_coach_global_reconcile.py",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CoachGlobalReconciliationTests(unittest.TestCase):
    def test_coach_gate_is_globally_mandatory(self) -> None:
        policy = load(POLICY_PATH)
        release = load(RELEASE_PATH)
        self.assertIn(GATESET_ID, policy["mandatory_reference_gates"])
        self.assertIn(GATESET_ID, release["mandatory_reference_gates"])
        self.assertEqual(
            set(policy["mandatory_reference_gates"]),
            set(release["mandatory_reference_gates"]),
        )

    def test_coach_release_semantics_remain_non_authoritative_and_non_promoted(self) -> None:
        release = load(RELEASE_PATH)
        coach = release["coach_reconciliation"]
        self.assertEqual(coach["profile_id"], PROFILE_ID)
        self.assertEqual(coach["goal_owner"], "USER")
        self.assertEqual(coach["knowledge_gap_delegation"], "FA3-MENTOR-001")
        self.assertEqual(coach["direct_execution"], "FORBIDDEN")
        self.assertEqual(coach["typed_action_delegation"], "REQUIRED")
        self.assertEqual(coach["runtime_status"], "PENDING_CURRENT_HOST")
        self.assertIs(coach["production_admitted"], False)
        self.assertIs(coach["current_host_runtime_promotion_claimed"], False)
        self.assertIs(coach["provider_is_architectural_authority"], False)
        self.assertEqual(coach["new_capabilities"], 0)
        self.assertEqual(coach["new_architectural_authorities"], 0)
        self.assertEqual(coach["capability_count_after"], 143)

    def test_all_coach_release_surface_files_are_manifested(self) -> None:
        release = load(RELEASE_PATH)
        manifest_paths = {entry["path"] for entry in release["manifest"]}
        self.assertFalse(REQUIRED_MANIFEST_PATHS - manifest_paths)


if __name__ == "__main__":
    unittest.main()
