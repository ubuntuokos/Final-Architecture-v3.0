from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_model_manager_llmfit_gui_gate import gate, validate_provider  # noqa: E402


class ModelManagerLlmfitGuiGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = json.loads(
            (ROOT / "canonical/providers/FA3-PROVIDER-LLMFIT-001.json").read_text(encoding="utf-8")
        )

    def test_reference_materialization_passes(self) -> None:
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report["findings"])
        self.assertFalse(report["current_host_runtime_promotion_claim"])

    def test_provider_cannot_become_authority(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["architectural_authority"] = True
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-003", codes)

    def test_fit_estimate_cannot_be_runtime_evidence(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["fa3_usage_policy"]["model_fit_estimate"] = "RUNTIME_EVIDENCE"
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-008", codes)

    def test_floating_upstream_release_is_rejected(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["upstream_release"] = "latest"
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-005", codes)

    def test_placement_authority_remains_hrb(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["fa3_usage_policy"]["accelerator_placement"] = "LLMFIT"
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-009", codes)


if __name__ == "__main__":
    unittest.main()
