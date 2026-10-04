"""Owner-marked Cloudflare OS donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-CLOUDFLARE-OS-2026-10-04.json"

KEY = "github:cloudflare/cloudflare-os"
URL = "https://github.com/cloudflare/cloudflare-os"
DONOR_ID = "FA3-DONOR-CLOUDFLARE-OS-001"
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class CloudflareOsDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_fixed_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1427)
        self.assertEqual(self.delta["proposed_entry_count"], 1428)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_cloudflare_os_is_reference_only(self):
        row = self.by_key[KEY]
        self.assertEqual(row["donor_id"], DONOR_ID)
        self.assertEqual(row["source"]["locator"], URL)
        self.assertEqual(row["source"]["kind"], "GITHUB")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["license"]["declared"], "Apache-2.0")
        self.assertIn("SECURITY_PATTERN", row["donor_modes"])
        self.assertIn("SANDBOX_PATTERN", row["donor_modes"])
        self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_speculative_execution_is_non_authoritative(self):
        self.assertFalse(self.delta["boundaries"]["speculative_result_can_be_evidence"])
        self.assertFalse(self.delta["boundaries"]["cloudflare_runtime_admitted"])
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])

    def test_intake_has_no_runtime_or_capability_effect(self):
        self.assertFalse(self.delta["boundaries"]["runtime_change"])
        self.assertFalse(self.delta["boundaries"]["current_host_pass_claimed"])
        self.assertFalse(self.delta["boundaries"]["authority_change"])
        self.assertFalse(self.delta["boundaries"]["capability_count_change"])

if __name__ == "__main__":
    unittest.main()
