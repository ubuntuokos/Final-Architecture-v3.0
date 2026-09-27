from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from fa3_story_presentation_gate import gate, interchange_contract_valid, presenton_superseded

ROOT = Path(__file__).resolve().parents[1]


class StoryPresentationGateTests(unittest.TestCase):
    def test_current_canonical_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report["findings"])
        self.assertEqual(175, report["capability_count"])
        self.assertEqual("PENDING_CURRENT_HOST", report["current_host_status"])
        self.assertFalse(report["runtime_promotion_claim"])

    def test_one_way_codec_fails_closed(self):
        contract = json.loads((ROOT / "canonical/contracts/FA3-STORY-PRESENTATION-CONTRACTS-001.json").read_text(encoding="utf-8"))
        self.assertTrue(interchange_contract_valid(contract))
        broken = copy.deepcopy(contract)
        broken["contracts"]["CanonicalDocumentInterchange"]["admitted_file_types"][0]["export"] = False
        self.assertFalse(interchange_contract_valid(broken))

    def test_presenton_is_superseded_reference_only(self):
        provider = json.loads((ROOT / "canonical/providers/FA3-PROVIDER-PRESENTON-001.json").read_text(encoding="utf-8"))
        self.assertTrue(presenton_superseded(provider))
        provider["runtime_admitted"] = True
        self.assertFalse(presenton_superseded(provider))


if __name__ == "__main__":
    unittest.main()
