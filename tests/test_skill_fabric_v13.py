import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_skill_fabric_v13 import (
    activation_preview_allowed,
    browser_tab_lease_allowed,
    context_budget_allowed,
    evaluate,
    host_projection_allowed,
    interface_allowed,
    provenance_attestation_allowed,
)


class SkillFabricV13Tests(unittest.TestCase):
    def test_gate(self):
        report = evaluate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertGreaterEqual(report["regressions"]["total"], 18)

    def test_context_budget_overflow_fails_closed(self):
        self.assertFalse(context_budget_allowed({
            "metadata_max_tokens": 10, "instructions_max_tokens": 10, "references_max_tokens": 10,
            "metadata_used_tokens": 1, "instructions_used_tokens": 1, "references_used_tokens": 11,
            "overflow_policy": "FAIL_CLOSED",
        }))

    def test_projection_collision_fails_closed(self):
        self.assertFalse(host_projection_allowed({
            "admission_status": "ADMITTED", "skill_name": "x", "skill_version": "1",
            "content_sha256": "a" * 64, "target_root": ".agents/skills",
            "global_install": False, "global_config_mutation": False, "symlink_escape": False,
            "collision": {"present": True, "same_content_digest": False, "explicit_exact_digest_reuse": False},
        }, {".agents/skills"}))

    def test_unsigned_optional_attestation_is_allowed_but_not_trust(self):
        self.assertTrue(provenance_attestation_allowed({"present": False, "required": False}))

    def test_browser_lease_rejects_cookie_export(self):
        lease = {
            "session_id": "s", "tab_ref": "t", "origin_scope": "https://example.invalid",
            "action_scope": ["CLICK"], "issued_at_epoch": 1, "expires_at_epoch": 2,
            "approved": True, "return_required": True, "credential_access": False,
            "cookie_export": True, "token_export": False,
            "sibling_tab_authority_inheritance": False, "popup_authority_inheritance": False,
        }
        self.assertFalse(browser_tab_lease_allowed(lease))


if __name__ == "__main__":
    unittest.main()
