"""Metadata-only regressions for goal-driven agent donor curation."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical" / "FA3-DONOR-REFERENCE-REGISTRY-001.json"

SOURCES = {
    "https://dev.to/saaro_net/stop-prompting-endlessly-give-the-agent-a-goal-om5",
    "github:poponline63/north-star",
    "github:orziz/odai",
    "github:pydantic/pydantic-ai",
    "github:langchain-ai/langgraph",
    "github:temporalio/sdk-python",
    "github:langfuse/langfuse",
    "github:promptfoo/promptfoo",
    "github:openhands/software-agent-sdk",
}
AUTO_FLAGS = (
    "automatic_selection",
    "automatic_fetch",
    "automatic_install",
    "automatic_activation",
    "automatic_dependency",
    "automatic_code_import",
    "automatic_provider_admission",
    "automatic_model_selection",
)


class GoalDrivenDonorCurationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_source = {item["source"]["normalized_key"]: item for item in cls.entries}

    def test_unique_source_and_donor_ids(self):
        self.assertEqual(len(self.by_source), len(self.entries))
        self.assertEqual(len({r["donor_id"] for r in self.entries}), len(self.entries))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))

    def test_all_nine_research_sources_captured_once(self):
        self.assertTrue(SOURCES.issubset(self.by_source))
        for key in SOURCES:
            with self.subTest(key=key):
                row = self.by_source[key]
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertIn("goal-driven-agent-curation-2026-09-28", row["discovered_from"])
                self.assertTrue(row["target_hints"])
                self.assertTrue(row["capability_hints"])
                self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                self.assertFalse(row["authority"])
                for flag in AUTO_FLAGS:
                    self.assertIs(row[flag], False, f"{key} may not grant {flag}")

    def test_renamed_north_star_canonical_source_only(self):
        star = self.by_source["github:poponline63/north-star"]
        self.assertIn("original-alias:poponline63/hermes-jev-north-star", star["tags"])
        self.assertNotIn("github:poponline63/hermes-jev-north-star", self.by_source)

    def test_existing_hardware_and_runtime_boundaries_unchanged(self):
        audit = self.registry["hardware_audit"]
        self.assertTrue(audit["vendor_neutral"])
        self.assertTrue(audit["cpu_only_viable"])
        self.assertEqual(audit["accelerator_cardinality"], "0..N")
        self.assertFalse(audit["global_accelerator_requirement"])
        self.assertFalse(audit["runtime_hardware_dependency"])
        self.assertEqual(audit["live_resource_authority"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")
        self.assertIs(self.registry["new_capability"], False)
        self.assertIs(self.registry["new_architectural_authority"], False)


if __name__ == "__main__":
    unittest.main()
