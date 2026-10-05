from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"


class HistoricalPartialDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_name = {entry["name"].casefold(): entry for entry in cls.entries}

    def test_review_is_bounded_and_preserves_base(self):
        review = self.registry["historical_partial_reuse_review"]
        self.assertEqual(review["scoped_textual_artifacts"], 37)
        self.assertEqual(review["scoped_library_files"], 48)
        self.assertEqual(review["excluded_library_project"], "Optimalizálás")
        self.assertEqual(review["created"], 77)
        self.assertGreaterEqual(review["enriched"], 14)
        self.assertEqual(review["reviewed_rows"], review["created"] + review["enriched"])
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertGreaterEqual(len(self.entries), 251)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.registry["authority"])

    def test_selected_partial_patterns_and_application_targets(self):
        examples = {
            "AutoCache": ("layered-cache", "Model Manager"),
            "AgentBase": ("visual-agent-mission-control", "Agent Collaboration Room"),
            "MovieAgent": ("filmmaking-multi-agent-coordination", "Film Planning"),
            "Dramatron": ("script-outline-development", "Story/Screenplay"),
            "FreeMoCap": ("camera-based-motion-capture", "Choreography"),
            "OpenViking": ("hierarchical-agent-context", "Memory Fabric"),
            "OpenColorIO": ("color-management-reference", "Color Fabric"),
        }
        for name, (capability, target) in examples.items():
            with self.subTest(donor=name):
                row = self.by_name[name.casefold()]
                scope = row["selection_scope"]
                self.assertEqual(scope["mode"], "SELECTIVE_CAPABILITIES_AND_PATTERNS_ONLY")
                self.assertFalse(scope["full_upstream_application_adoption"])
                self.assertIn(capability, row["capability_hints"])
                self.assertIn(target, row["target_hints"])
                self.assertIn(capability, scope["selected_capabilities"])
                self.assertIn(target, scope["intended_fa3_targets"])

    def test_source_identity_and_safety_remain_intact(self):
        keys = [row["source"]["normalized_key"] for row in self.entries]
        ids = [row["donor_id"] for row in self.entries]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(any("optimalizálás" in row["source"]["normalized_key"].casefold() for row in self.entries))
        selected = [row for row in self.entries if "selection_scope" in row]
        self.assertGreaterEqual(len(selected), 91)
        for row in selected:
            with self.subTest(donor=row["donor_id"]):
                self.assertFalse(row["authority"])
                self.assertFalse(row["automatic_fetch"])
                self.assertFalse(row["automatic_install"])
                self.assertFalse(row["automatic_activation"])
                self.assertFalse(row["automatic_code_import"])
                self.assertFalse(row["automatic_provider_admission"])
                self.assertFalse(row["automatic_model_selection"])
                self.assertFalse(row["selection_scope"]["full_upstream_application_adoption"])


if __name__ == "__main__":
    unittest.main()
