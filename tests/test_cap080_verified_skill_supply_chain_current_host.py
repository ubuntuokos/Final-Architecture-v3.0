import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_cap080_verified_skill_supply_chain_current_host import (
    _run_negative,
    _run_positive,
    _run_rollback,
    validate_skill_fabric,
)


class Cap080VerifiedSkillSupplyChainCurrentHostTests(unittest.TestCase):
    def test_skill_fabric_canonical_invariants(self):
        self.assertEqual(validate_skill_fabric(ROOT), [])

    def test_positive_executes_full_skill_admission_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            result = _run_positive(ROOT, Path(td))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["canonical_gate"], "PASS")
            self.assertGreaterEqual(result["regression_total"], 45)
            self.assertEqual(result["regression_passed"], result["regression_total"])
            self.assertTrue(result["case_ids_exact"])
            self.assertTrue(result["positive_package_admitted"])
            self.assertTrue(result["positive_use_receipt_admitted"])
            self.assertFalse(result["reference_provider_runtime_claim"])

    def test_negative_drill_rejects_supply_chain_boundary_bypasses(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            result = _run_negative(ROOT, Path(td))
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["dependency_cycle_rejected"])
            self.assertTrue(result["path_traversal_rejected"])
            self.assertTrue(result["direct_credential_access_rejected"])
            self.assertTrue(result["active_execution_rejected"])
            self.assertTrue(result["central_mcp_bypass_rejected"])
            self.assertTrue(result["skipped_review_rejected"])
            self.assertTrue(result["noncommercial_redistribution_rejected"])
            self.assertTrue(result["runtime_remote_fetch_rejected"])
            self.assertTrue(result["candidate_expansion_rejected"])

    def test_rollback_restores_exact_admissible_descriptor(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            result = _run_rollback(ROOT, Path(td))
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["fault_rejected"])
            self.assertTrue(result["rollback_hash_equal"])
            self.assertTrue(result["restored_package_admitted"])
            self.assertEqual(result["pre_sha256"], result["post_sha256"])
            self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])


if __name__ == "__main__":
    unittest.main()
