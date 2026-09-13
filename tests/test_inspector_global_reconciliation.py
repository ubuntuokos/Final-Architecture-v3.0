from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "FA3-INSPECTOR-001"
GATESET_ID = "FA3-INSPECTOR-GATESET-001"
RELEASE_PATH = ROOT / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
POLICY_PATH = ROOT / "canonical/enforcement-policy.json"
REQUIRED_MANIFEST_PATHS = {
    ".github/workflows/fa3-inspector-gate.yml",
    ".github/workflows/fa3-inspector-reconcile.yml",
    "canonical/FA3-INSPECTION-CONFORMANCE-MATRIX-001.json",
    "canonical/FA3-INSPECTION-EVIDENCE-001.json",
    "canonical/FA3-INSPECTION-POLICY-001.json",
    "canonical/FA3-INSPECTOR-RUNTIME-CONFORMANCE-001.json",
    "canonical/FA3-GATE-INDEPENDENT-VERIFICATION-001.json",
    "canonical/inspector-enforcement.json",
    "canonical/contracts/FA3-INSPECTION-CONTRACTS-001.json",
    "canonical/decisions/FA3-DEC-INSPECTOR-2026-09-12.json",
    "canonical/profiles/FA3-INSPECTOR-001.json",
    "canonical/providers/FA3-PROVIDER-INSPECTOR-LOCAL-001.json",
    "evidence/reference/fa3-inspector-reference-pending.json",
    "src/fa3_inspector.py",
    "src/fa3_inspector_gate.py",
    "tests/test_inspector_gate.py",
    "tests/test_inspector_global_reconciliation.py",
    "tools/fa3_inspector_global_reconcile.py",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class InspectorGlobalReconciliationTests(unittest.TestCase):
    def test_inspector_gate_is_globally_mandatory(self) -> None:
        policy = load(POLICY_PATH)
        release = load(RELEASE_PATH)
        self.assertIn(GATESET_ID, policy["mandatory_reference_gates"])
        self.assertIn(GATESET_ID, release["mandatory_reference_gates"])
        self.assertEqual(set(policy["mandatory_reference_gates"]), set(release["mandatory_reference_gates"]))

    def test_inspector_release_semantics_remain_independent_non_authoritative_and_non_promoted(self) -> None:
        release = load(RELEASE_PATH)
        inspector = release["inspector_reconciliation"]
        self.assertEqual(inspector["profile_id"], PROFILE_ID)
        self.assertEqual(inspector["inspection_levels"], ["L1_STATIC", "L2_RUNTIME", "L3_PRODUCTION"])
        self.assertIs(inspector["executor_may_be_sole_accepting_verifier"], False)
        self.assertEqual(inspector["self_attestation_only_p0_must_production_pass"], "BLOCKED")
        self.assertEqual(inspector["silent_repair_during_certification"], "FORBIDDEN")
        self.assertIs(inspector["remediation_requires_reinspection"], True)
        self.assertEqual(inspector["runtime_status"], "PENDING_CURRENT_HOST")
        self.assertIs(inspector["production_admitted"], False)
        self.assertIs(inspector["current_host_runtime_promotion_claimed"], False)
        self.assertIs(inspector["provider_is_architectural_authority"], False)
        self.assertEqual(inspector["new_capabilities"], 0)
        self.assertEqual(inspector["new_architectural_authorities"], 0)
        self.assertEqual(inspector["capability_count_after"], 143)

    def test_all_inspector_release_surface_files_are_manifested(self) -> None:
        release = load(RELEASE_PATH)
        manifest_paths = {entry["path"] for entry in release["manifest"]}
        self.assertFalse(REQUIRED_MANIFEST_PATHS - manifest_paths)


if __name__ == "__main__":
    unittest.main()
