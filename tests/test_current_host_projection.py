from pathlib import Path
import json
import unittest

from fa3_current_host import verify_projection

ROOT = Path(__file__).resolve().parents[1]


class CurrentHostProjectionTests(unittest.TestCase):
    def test_projection_verifies(self):
        report = verify_projection(ROOT)
        self.assertEqual(report["result"], "PASS", report)

    def test_collection_cannot_claim_pass(self):
        text_value = (ROOT / "evidence/collect-current-host.sh").read_text(encoding="utf-8")
        self.assertIn("COLLECTED_UNVALIDATED", text_value)
        self.assertIn("not PASS", text_value)

    def test_promotion_is_explicit_and_fail_closed(self):
        manifest = json.loads((ROOT / "fa3-current-host/manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["fail_closed"])
        self.assertFalse(manifest["automatic_promotion"])
        self.assertTrue(manifest["promotion"]["explicit_only"])
        self.assertFalse(manifest["promotion"]["global_promotion_claim_from_collection"])
        self.assertEqual(manifest["capability_count"], 143)
        self.assertEqual(manifest["new_capabilities"], 0)
        self.assertEqual(manifest["new_architectural_authorities"], 0)


if __name__ == "__main__":
    unittest.main()
