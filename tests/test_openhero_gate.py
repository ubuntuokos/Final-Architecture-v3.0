from __future__ import annotations
import unittest
from pathlib import Path

from fa3_openhero_gate import (
    asset_admission_allowed,
    gate,
    good_package,
    run_regressions,
)

ROOT = Path(__file__).resolve().parents[1]


class OpenHeroWebCreativeAssetGateTests(unittest.TestCase):
    def test_regression_matrix_exact_pass(self):
        r = run_regressions()
        self.assertEqual(r["result"], "PASS")
        self.assertEqual(r["total"], 32)
        self.assertEqual(r["passed"], 32)
        self.assertTrue(r["case_ids_exact"])

    def test_path_traversal_fails_closed(self):
        p = good_package()
        p["registry"]["assets"]["nature/cinematic-horizons"]["html_path"] = "../../etc/passwd"
        self.assertFalse(asset_admission_allowed(p))

    def test_script_origin_exact_match_not_substring(self):
        p = good_package()
        p["html_security"]["external_script_urls"] = ["https://cdn.jsdelivr.net.evil.example/x.js"]
        self.assertFalse(asset_admission_allowed(p))

    def test_preview_scripts_plus_same_origin_fails_closed(self):
        p = good_package()
        p["preview"]["sandbox_tokens"] = ["allow-scripts", "allow-same-origin"]
        self.assertFalse(asset_admission_allowed(p))

    def test_code_license_cannot_substitute_for_asset_rights(self):
        p = good_package()
        p["asset_rights"]["inherits_repository_code_license"] = True
        self.assertFalse(asset_admission_allowed(p))

    def test_canonical_gate_passes(self):
        r = gate(ROOT)
        self.assertEqual(r["result"], "PASS", r)


if __name__ == "__main__":
    unittest.main()
