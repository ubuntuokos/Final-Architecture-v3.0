from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "FA3-IDEATION-ADVISORY-001"
GATESET_ID = "FA3-IDEATION-ADVISORY-GATESET-001"
RELEASE_PATH = ROOT / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
POLICY_PATH = ROOT / "canonical/enforcement-policy.json"
REQUIRED_MANIFEST_PATHS = {
    ".github/workflows/fa3-ideation-advisory-gate.yml",
    ".github/workflows/fa3-ideation-advisory-reconcile.yml",
    "canonical/FA3-GATE-IDEATION-ADVISORY-001.json",
    "canonical/FA3-IDEATION-ADVISORY-CONFORMANCE-MATRIX-001.json",
    "canonical/FA3-IDEATION-ADVISORY-RUNTIME-CONFORMANCE-001.json",
    "canonical/ideation-advisory-enforcement.json",
    "canonical/contracts/FA3-IDEATION-ADVISORY-CONTRACTS-001.json",
    "canonical/decisions/FA3-DEC-IDEATION-ADVISORY-2026-09-12.json",
    "canonical/profiles/FA3-IDEATION-ADVISORY-001.json",
    "canonical/providers/FA3-PROVIDER-IDEATION-ADVISORY-LOCAL-001.json",
    "evidence/reference/fa3-ideation-advisory-reference-pending.json",
    "src/fa3_ideation_advisory.py",
    "src/fa3_ideation_advisory_gate.py",
    "tests/test_ideation_advisory_gate.py",
    "tests/test_ideation_advisory_global_reconciliation.py",
    "tools/fa3_ideation_advisory_global_reconcile.py",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class IdeationAdvisoryGlobalReconciliationTests(unittest.TestCase):
    def test_gate_is_globally_mandatory(self) -> None:
        policy = load(POLICY_PATH)
        release = load(RELEASE_PATH)
        self.assertIn(GATESET_ID, policy["mandatory_reference_gates"])
        self.assertIn(GATESET_ID, release["mandatory_reference_gates"])
        self.assertEqual(set(policy["mandatory_reference_gates"]), set(release["mandatory_reference_gates"]))

    def test_release_semantics_remain_non_authoritative_and_non_promoted(self) -> None:
        release = load(RELEASE_PATH)
        record = release["ideation_advisory_reconciliation"]
        self.assertEqual(record["profile_id"], PROFILE_ID)
        self.assertEqual(record["subprofile_ids"], ["FA3-IDEATOR-001", "FA3-ADVISOR-001"])
        self.assertEqual(record["direct_execution"], "FORBIDDEN")
        self.assertEqual(record["direct_repository_write"], "FORBIDDEN")
        self.assertIs(record["verified_recommendation_requires_evidence"], True)
        self.assertEqual(record["high_impact_verification_handoff"], "FA3-INSPECTOR-001")
        self.assertEqual(record["runtime_status"], "PENDING_CURRENT_HOST")
        self.assertIs(record["production_admitted"], False)
        self.assertIs(record["current_host_runtime_promotion_claimed"], False)
        self.assertIs(record["provider_is_architectural_authority"], False)
        self.assertEqual(record["new_capabilities"], 0)
        self.assertEqual(record["new_architectural_authorities"], 0)
        self.assertEqual(record["capability_count_after"], 143)

    def test_release_surface_is_manifested(self) -> None:
        release = load(RELEASE_PATH)
        manifest_paths = {entry["path"] for entry in release["manifest"]}
        self.assertFalse(REQUIRED_MANIFEST_PATHS - manifest_paths)


if __name__ == "__main__":
    unittest.main()
