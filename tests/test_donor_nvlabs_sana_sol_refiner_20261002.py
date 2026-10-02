"""NVlabs Sana / SoL-Refiner donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-NVLABS-SANA-SOL-REFINER-2026-10-02.json"

SANA_KEY = "github:nvlabs/sana"
ORG_KEY = "github:nvlabs"
SANA_ID = "FA3-DONOR-NVLABS-SANA-001"
ORG_ID = "FA3-DONOR-NVLABS-ORG-001"
SOL_URL = "https://github.com/NVlabs/Sana/tree/sol-engine/models/sol-refiner"
DENY_FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)


class NVlabsSanaDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_two_canonical_identities_and_175_baseline(self):
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(len(self.entries), 1357)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.by_key[SANA_KEY]["donor_id"], SANA_ID)
        self.assertEqual(self.by_key[ORG_KEY]["donor_id"], ORG_ID)
        self.assertEqual(self.delta["parent_entry_count"], 1355)
        self.assertEqual(self.delta["proposed_entry_count"], 1357)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_sol_refiner_url_is_component_provenance_not_duplicate_identity(self):
        sana = self.by_key[SANA_KEY]
        self.assertIn(SOL_URL, sana["source"]["discovery_urls"])
        matches = [e for e in self.entries if SOL_URL == e["source"].get("locator")]
        self.assertEqual(matches, [])
        component = sana["component_provenance"][0]
        self.assertEqual(component["submitted_url"], SOL_URL)
        self.assertEqual(component["branch"], "sol-engine")
        self.assertEqual(component["path"], "models/sol-refiner")
        self.assertEqual(component["commit"], "670482d8a857d578ac8a2ea89b052d0fb47badba")
        self.assertFalse(component["separate_donor_identity_created"])

    def test_repository_and_org_are_reference_only(self):
        for key in (SANA_KEY, ORG_KEY):
            row = self.by_key[key]
            self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
            self.assertTrue(all(row[flag] is False for flag in DENY_FLAGS))
        self.assertIn("DISCOVERY_INDEX", self.by_key[ORG_KEY]["donor_modes"])
        self.assertTrue(all(v is False for v in self.delta["boundaries"].values()))

    def test_upstream_snapshot_and_rights_boundary_are_pinned(self):
        snap = self.by_key[SANA_KEY]["source_snapshot"]
        self.assertEqual(snap["default_branch_commit"], "f9178744c096dcf2a2ea773da183e341bcbeb044")
        self.assertEqual(snap["sol_engine_branch_commit"], "670482d8a857d578ac8a2ea89b052d0fb47badba")
        self.assertEqual(snap["sol_refiner_tree_sha"], "67717f3cf6e22ea280c258acef196f6c1b8a0ab2")
        self.assertEqual(self.by_key[SANA_KEY]["license"]["declared"], "Apache-2.0")
        self.assertIn("SEPARATE", self.by_key[SANA_KEY]["license"]["status"])


if __name__ == "__main__":
    unittest.main()
