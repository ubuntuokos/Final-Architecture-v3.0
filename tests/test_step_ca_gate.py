import copy
import unittest
from pathlib import Path

import fa3_step_ca_gate as g

class StepCAGateTests(unittest.TestCase):
    def test_reference_materialization_passes(self):
        root = Path(__file__).resolve().parents[1]
        result = g.reference_check(root)
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual(20, result["rules_checked"])

    def test_regressions_pass(self):
        result = g.run_regressions()
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual(result["total"], result["passed"])

    def test_online_root_key_is_rejected(self):
        provider = {
            "id":g.PROVIDER_ID, "parent_profile":g.PROFILE_ID,
            "architectural_authority":False, "new_capability":False,
            "new_architectural_authority":False, "capability_count":g.CAPABILITY_COUNT,
            "upstream":{"release":g.RELEASE,"release_commit":g.COMMIT,"license":"Apache-2.0","release_artifact_sigstore_available":True},
            "pki_policy":{"offline_root_private_key_required":True,"online_root_private_key_allowed":False,
                "online_issuer":"INTERMEDIATE_ONLY","default_workload_certificate_ttl":"12h",
                "maximum_workload_certificate_ttl":"24h","certificate_identity_is_authorization":False,
                "current_host_e2e_required_for_runtime_promotion":True},
            "promotion":{"production_runtime_promoted":False},
        }
        self.assertTrue(g.provider_policy_valid(provider))
        bad = copy.deepcopy(provider)
        bad["pki_policy"]["online_root_private_key_allowed"] = True
        self.assertFalse(g.provider_policy_valid(bad))

    def test_duration_parser(self):
        self.assertEqual(12, g.duration_hours("12h"))
        self.assertEqual(24, g.duration_hours("24h"))
        self.assertEqual(0.5, g.duration_hours("30m"))

if __name__ == "__main__":
    unittest.main()
