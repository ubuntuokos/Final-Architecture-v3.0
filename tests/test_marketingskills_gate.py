from __future__ import annotations
import copy
import unittest
from pathlib import Path

from fa3_marketingskills_gate import (
    gate,
    good_package,
    good_use_receipt,
    package_admission_allowed,
    run_regressions,
    skill_use_allowed,
)

ROOT = Path(__file__).resolve().parents[1]

class MarketingSkillsAdmissionGateTests(unittest.TestCase):
    def test_regression_matrix_exact_pass(self):
        r = run_regressions()
        self.assertEqual(r["result"], "PASS")
        self.assertEqual(r["total"], 32)
        self.assertEqual(r["passed"], 32)
        self.assertTrue(r["case_ids_exact"])

    def test_shell_directive_must_remain_inert(self):
        p = good_package()
        self.assertTrue(package_admission_allowed(p))
        p["execution"]["shell_interpolation_exec_allowed"] = True
        self.assertFalse(package_admission_allowed(p))

    def test_dependency_cycle_fails_closed(self):
        p = good_package()
        p["dependencies"]["edges"].append({"from":"product-marketing","to":"copywriting"})
        self.assertFalse(package_admission_allowed(p))

    def test_path_and_symlink_escape_fail_closed(self):
        p = good_package()
        p["files"].append("../escape")
        self.assertFalse(package_admission_allowed(p))
        p = good_package()
        p["symlinks"].append({"path":"skills/x/link","target":"../../../etc/passwd"})
        self.assertFalse(package_admission_allowed(p))

    def test_use_receipt_requires_central_mcp_for_tool_intent(self):
        r = good_use_receipt()
        self.assertTrue(skill_use_allowed(r))
        r["tool_intent"]["via_central_mcp"] = False
        self.assertFalse(skill_use_allowed(r))

    def test_canonical_gate_passes(self):
        r = gate(ROOT)
        self.assertEqual(r["result"], "PASS", r)

if __name__ == "__main__":
    unittest.main()
