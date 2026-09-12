import json
import tempfile
import unittest
from pathlib import Path

import fa3_vaultwarden_gate as g


class VaultwardenGateTests(unittest.TestCase):
    def test_reference_materialization_passes(self):
        root = Path(__file__).resolve().parents[1]
        result = g.reference_check(root)
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual(23, result["rules_checked"])

    def test_regressions_pass(self):
        result = g.run_regressions()
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual(result["total"], result["passed"])
        self.assertEqual(24, result["total"])

    def test_runtime_promotion_requires_complete_real_evidence(self):
        self.assertTrue(g.runtime_promotion_valid(
            current_host_e2e=True,
            immutable_image_digest=True,
            compatibility_matrix=True,
            restore_drill=True,
            secure_transport=True,
            isolation_pass=True,
            synthetic=False,
        ))
        self.assertFalse(g.runtime_promotion_valid(
            current_host_e2e=True,
            immutable_image_digest=False,
            compatibility_matrix=True,
            restore_drill=True,
            secure_transport=True,
            isolation_pass=True,
            synthetic=False,
        ))
        self.assertFalse(g.runtime_promotion_valid(
            current_host_e2e=True,
            immutable_image_digest=True,
            compatibility_matrix=True,
            restore_drill=True,
            secure_transport=True,
            isolation_pass=True,
            synthetic=True,
        ))

    def test_machine_secret_authority_drift_is_rejected(self):
        policy = dict(g.POLICY)
        self.assertTrue(g.hardening_policy_valid(policy))
        policy["machine_secret_minting_or_lease_authority"] = True
        self.assertFalse(g.hardening_policy_valid(policy))

    def test_authority_assignment_scan_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "canonical").mkdir()
            (root / "canonical/bad.json").write_text(
                json.dumps({"secrets_authority": g.PROVIDER_ID}),
                encoding="utf-8",
            )
            result = g.scan_canonical_authority_assignments(root)
            self.assertEqual("FAIL", result["result"])


if __name__ == "__main__":
    unittest.main()
