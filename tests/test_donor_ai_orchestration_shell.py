"""Metadata-only Shell orchestration donor registry invariants."""
import json
import unittest
from pathlib import Path
REG = Path(__file__).resolve().parents[1] / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
KEYS = ["github:topics/ai-orchestration","github:nyldn/claude-octopus","github:johnvouros/skillmaxxing","github:spencermarx/orc","github:dryvist/ai-assistant-instructions","github:jvogan/symphony-claude-lane","github:noahrasheta/director","github:kellvembarbosa/team-orchestrator","github:airc-ai/airc-orchestration","github:rorogogogo/claude-cracks-the-whip"]
FLAGS = ["authority","automatic_selection","automatic_fetch","automatic_install","automatic_activation","automatic_dependency","automatic_code_import","automatic_provider_admission","automatic_model_selection"]
class TestShellOrchestrationDonors(unittest.TestCase):
    def test_non_authoritative_unique_candidates(self):
        d = json.loads(REG.read_text(encoding="utf-8"))
        e = d["entries"]
        self.assertEqual(175, d["capability_count"])
        self.assertEqual(len(e), d["backfill"]["entry_count"])
        self.assertEqual(len(e), len({x["donor_id"] for x in e}))
        self.assertEqual(len(e), len({x["source"]["normalized_key"] for x in e}))
        refs = {x["source"]["normalized_key"]: x for x in e}
        self.assertEqual(len(KEYS), len(set(KEYS)))
        for key in KEYS:
            self.assertIn(key, refs)
            item = refs[key]
            self.assertEqual("CANDIDATE", item["status"])
            self.assertTrue(item['discoverable_for_planning'])
            self.assertTrue(item["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))
            for flag in FLAGS:
                self.assertIs(item[flag], False)
        self.assertEqual(["DISCOVERY_INDEX"], refs["github:topics/ai-orchestration"]["donor_modes"])
        self.assertEqual("Shell", refs["github:topics/ai-orchestration"]["discovery_filter"]["language"])
        self.assertEqual("PROPRIETARY", refs["github:airc-ai/airc-orchestration"]["license"]["declared"])

if __name__ == "__main__":
    unittest.main()
