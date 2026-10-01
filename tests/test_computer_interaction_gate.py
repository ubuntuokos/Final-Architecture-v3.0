from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_computer_interaction_gate import gate


class ComputerInteractionGateTests(unittest.TestCase):
    def test_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report.get("findings"))

    def test_baseline_and_authority_delta_are_closed(self):
        profile = json.loads(
            (ROOT / "canonical/profiles/FA3-COMPUTER-INTERACTION-RUNTIME-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(175, profile["capability_count"])
        self.assertFalse(profile["new_capability"])
        self.assertFalse(profile["new_architectural_authority"])

    def test_cua_stays_analysis_only_without_registry_marker(self):
        assessment = json.loads(
            (
                ROOT
                / "canonical/assessments/FA3-COMPUTER-INTERACTION-RUNTIME-REUSE-ASSESSMENT-001.json"
            ).read_text(encoding="utf-8")
        )
        source = assessment["analysis_only_external_source"]
        self.assertEqual("UNREGISTERED_UNMARKED_ANALYSIS_ONLY", source["registry_status"])
        self.assertFalse(source["donor_id_created"])
        self.assertFalse(source["code_copied"])
        self.assertFalse(assessment["runtime_admission_authorized"])

    def test_physical_current_host_is_not_fabricated(self):
        impact = json.loads(
            (ROOT / "canonical/FA3-COMPUTER-INTERACTION-CURRENT-HOST-IMPACT-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("PENDING_PHYSICAL_REQUALIFICATION", impact["status"])
        self.assertFalse(impact["physical_current_host_pass_claimed"])
        self.assertEqual("CAP-013", impact["capability_subject"])


if __name__ == "__main__":
    unittest.main()
