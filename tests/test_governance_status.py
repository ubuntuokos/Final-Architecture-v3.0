import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fa3_gate_registry import gate as gate_registry_gate
from fa3_governance_status import gate as governance_status_gate, project


ROOT = Path(__file__).resolve().parents[1]


class GovernanceStatusTests(unittest.TestCase):
    def test_projection_is_read_only_and_missing_generated_outputs_fail_closed_to_unknown(self):
        with patch("fa3_governance_status.datetime") as dt:
            dt.now.return_value = datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc)
            dt.fromisoformat = datetime.fromisoformat
            projection = project(ROOT, now=datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc))
        self.assertTrue(projection["non_authoritative"])
        self.assertFalse(projection["source_of_truth"])
        self.assertFalse(projection["current_host_runtime_promotion_claim"])
        self.assertEqual("UNKNOWN_OR_PENDING", projection["assurance_state"])
        self.assertEqual("UNKNOWN_OR_PENDING", projection["canonical_state"])
        if not (ROOT / "acceptance/acceptance-report.json").is_file():
            self.assertEqual("UNKNOWN_OR_PENDING", projection["acceptance"]["state"])
        if not (ROOT / "promotion/runtime-status.json").is_file():
            self.assertEqual("UNKNOWN_OR_PENDING", projection["promotion"]["state"])
        self.assertEqual(175, projection["repository"]["capability_count"])
        self.assertEqual(175, projection["evidence"]["record_count"])

    def test_governance_status_gate_passes_without_claiming_runtime(self):
        result = governance_status_gate(ROOT)
        self.assertEqual("PASS", result["result"], result)
        self.assertFalse(result["current_host_runtime_promotion_claim"])

    def test_gate_registry_is_single_membership_source_and_policy_mirror_matches(self):
        registry = json.loads((ROOT / "canonical/FA3-GATE-REGISTRY-001.json").read_text())
        policy = json.loads((ROOT / "canonical/enforcement-policy.json").read_text())
        self.assertEqual(registry["mandatory_reference_gates"], policy["mandatory_reference_gates"])
        self.assertEqual(len(registry["mandatory_reference_gates"]), len(set(registry["mandatory_reference_gates"])))
        result = gate_registry_gate(ROOT)
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual(len(registry["mandatory_reference_gates"]), result["mandatory_gate_count"])


if __name__ == "__main__":
    unittest.main()
