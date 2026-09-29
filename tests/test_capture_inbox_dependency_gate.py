"""Negative and positive tests for Capture prerequisite boundaries; never runtime proof."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fa3_capture_inbox_dependency_gate import load_snapshot, validate

class CaptureInboxDependencyBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = load_snapshot(Path(__file__).resolve().parents[1])

    def verify_rejected(self, key, change, fragment):
        altered = copy.deepcopy(self.snapshot)
        change(altered[key])
        errors = validate(altered)
        self.assertTrue(any(fragment in text for text in errors), errors)

    def test_valid_snapshot_static_only(self):
        self.assertEqual([], validate(self.snapshot))
        self.assertFalse(self.snapshot["contract"]["admission"]["current_host_runtime_promotion_claim"])

    def test_cannot_reduce_175_capabilities(self):
        self.verify_rejected("model", lambda x: x.__setitem__("canonical_capability_count", 143), "175")

    def test_privacy_deny_by_default(self):
        self.verify_rejected("privacy", lambda x: x["default_capture"].__setitem__("generic_clipboard", "ALLOW"), "privacy")

    def test_implicit_camera_or_ambient_capture_rejected(self):
        self.verify_rejected("contract", lambda x: x["capture"].__setitem__("capture_initiation", "BACKGROUND_AUTOMATIC"), "privacy/cloud")

    def test_cloud_auto_upload_rejected(self):
        self.verify_rejected("contract", lambda x: x["capture"].__setitem__("no_automatic_ai_content_upload", False), "privacy/cloud")

    def test_handoff_to_unconnected_recipient_fails_closed(self):
        self.verify_rejected("contract", lambda x: x["handoff"].__setitem__("inaccessible_or_unconnected_recipient", "ACK"), "handoff")

    def test_parallel_capture_sync_rejected(self):
        self.verify_rejected("contract", lambda x: x["lan_sync"].__setitem__("implementation", "CAPTURE_SYNC_SERVER"), "CAP-150 sync")

    def test_fake_two_host_promotion_rejected(self):
        def mutate(x):
            next(r for r in x["recipes"] if r["capability_id"] == "CAP-150")["minimum_distinct_host_identities_for_cross_host_promotion"] = 1
        self.verify_rejected("recipes", mutate, "two-host")

    def test_new_authority_rejected(self):
        self.verify_rejected("intent", lambda x: x.__setitem__("proposed_authority_roles", ["CAPTURE_POLICY"]), "new authorities")

    def test_donor_auto_install_rejected(self):
        def mutate(x):
            next(r for r in x["entries"] if r["source"]["normalized_key"] == "github:syncthing/syncthing")["automatic_install"] = True
        self.verify_rejected("donors", mutate, "auto-admission")

    def test_duplicate_source_rejected(self):
        def mutate(x):
            x["entries"].append(copy.deepcopy(x["entries"][0]))
            x["backfill"]["entry_count"] += 1
        self.verify_rejected("donors", mutate, "duplicate normalized")

    def test_fictional_current_host_pass_rejected(self):
        def mutate(x):
            next(r for r in x["records"] if r["subject_id"] == "CAP-150")["status"] = "PASS"
        self.verify_rejected("evidence", mutate, "unexpectedly claimed closed")

    def test_default_port_or_upstream_uninstall_rejected(self):
        self.verify_rejected("intent", lambda x: x["namespace_claims"].__setitem__("claims_default_port", True), "unsafe")

if __name__ == "__main__":
    unittest.main()
