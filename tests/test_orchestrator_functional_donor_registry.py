"""Non-authoritative donor-plan regression for FA3 orchestrator functional expansion.

Metadata/source checks only: never a current-host runtime or production admission proof.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
PLAN = ROOT / "docs/FA3-ORCHESTRATOR-FUNCTIONAL-DONOR-EXPANSION-2026-09-29.md"

EXPECTED = {
    "github:dagger/dagger": "FA3-DONOR-DAGGER-DAGGER-001",
    "github:skypilot-org/skypilot": "FA3-DONOR-SKYPILOT-ORG-SKYPILOT-001",
    "github:nvidia/openshell": "FA3-DONOR-NVIDIA-OPENSHELL-001",
    "github:nvidia/skillspector": "FA3-DONOR-NVIDIA-SKILLSPECTOR-001",
    "github:cytostack/openwolf": "FA3-DONOR-CYTOSTACK-OPENWOLF-001",
    "github:boadij/pi-herdsman": "FA3-DONOR-BOADIJ-PI-HERDSMAN-001",
    "github:shopify/toxiproxy": "FA3-DONOR-TOXIPROXY-001",
    "github:test-zeus-ai/testzeus-hercules": "FA3-DONOR-TESTZEUS-HERCULES-001",
    "github:nvidia/nemo-agent-toolkit": "FA3-DONOR-NVIDIA-NEMO-AGENT-TOOLKIT-001",
    "project:inngest": "FA3-DONOR-INNGEST-001",
}
NEW = {
    "github:dagger/dagger": "fdb30c1d1b03b6ff22e90b30f9997c7e0b63e6e0",
    "github:skypilot-org/skypilot": "2df7061d22d6799339736659ca007bdd6ab49625",
}
AUTOMATIC_FLAGS = (
    "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)


class OrchestratorFunctionalDonorRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.data["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_unique_registry_and_175_baseline(self):
        self.assertEqual(self.data["capability_count"], 175)
        self.assertEqual(self.data["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(len(self.by_key), len(self.entries))
        self.assertEqual(len({e["donor_id"] for e in self.entries}), len(self.entries))

    def test_all_ten_sources_present_without_duplicate(self):
        for key, expected_id in EXPECTED.items():
            with self.subTest(key=key):
                self.assertIn(key, self.by_key)
                self.assertEqual(self.by_key[key]["donor_id"], expected_id)

    def test_two_new_sources_remain_unadmitted(self):
        for key, commit in NEW.items():
            with self.subTest(key=key):
                entry = self.by_key[key]
                self.assertEqual(entry["status"], "CANDIDATE")
                self.assertEqual(entry["source"]["kind"], "GITHUB")
                self.assertEqual(entry["source_snapshot"]["commit"], commit)
                self.assertEqual(entry["license"]["declared"], "Apache-2.0")
                self.assertFalse(entry["authority"])
                for flag in AUTOMATIC_FLAGS:
                    self.assertIs(entry[flag], False, f"{key}: {flag}")

    def test_existing_sources_preserve_identity(self):
        for key, expected_id in EXPECTED.items():
            with self.subTest(key=key):
                self.assertEqual(self.by_key[key]["donor_id"], expected_id)
        self.assertEqual(
            self.by_key["github:cytostack/openwolf"]["status"], "ACCEPTED_REFERENCE"
        )
        self.assertEqual(
            self.by_key["github:boadij/pi-herdsman"]["status"], "ACCEPTED_REFERENCE"
        )

    def test_plan_covers_authority_boundary_and_negative_tests(self):
        plan = PLAN.read_text(encoding="utf-8")
        for required in ("175", "Temporal", "HRB", "Model Router", "MCP Gateway",
                         "Software Coexistence", "current_host_batch_orchestration",
                         "T01", "T16", "Dagger", "SkyPilot"):
            with self.subTest(required=required):
                self.assertIn(required, plan)


if __name__ == "__main__":
    unittest.main()
