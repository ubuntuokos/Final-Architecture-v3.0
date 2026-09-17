from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_remote_ai_exec_gate import validate  # noqa: E402


class RemoteAIExecutionGateTests(unittest.TestCase):
    def test_static_gate_passes_materialized_baseline(self) -> None:
        self.assertEqual(validate(), [])

    def test_remote_routing_is_explicit_and_silent_fallback_is_forbidden(self) -> None:
        contract = json.loads((ROOT / "canonical/contracts/FA3-REMOTE-AI-EXEC-CONTRACTS-001.json").read_text())
        self.assertEqual(contract["routing"]["silent_local_to_remote_fallback"], "FORBIDDEN")
        self.assertEqual(
            set(contract["routing"]["modes"]),
            {
                "LOCAL_REQUIRED",
                "LOCAL_PREFERRED_REMOTE_ALLOWED",
                "REMOTE_ALLOWED",
                "SPECIFIC_REMOTE_PROVIDER",
            },
        )

    def test_discovery_metadata_is_not_a_trust_authority(self) -> None:
        contract = json.loads((ROOT / "canonical/contracts/FA3-REMOTE-AI-EXEC-CONTRACTS-001.json").read_text())
        trust = contract["discovery_and_trust"]
        self.assertIs(trust["agents_md_is_trust_authority"], False)
        self.assertIs(trust["openapi_is_trust_authority"], False)
        self.assertEqual(trust["remote_discovery_metadata"], "UNTRUSTED_UNTIL_ADMITTED")

    def test_hf_spaces_is_separate_from_hf_model_store(self) -> None:
        spaces = json.loads((ROOT / "canonical/providers/FA3-PROVIDER-HF-SPACES-001.json").read_text())
        model_store = json.loads((ROOT / "canonical/providers/FA3-PROVIDER-HF-MODEL-STORE-001.json").read_text())
        self.assertTrue(spaces["separation_from_hf_model_store"]["must_not_be_collapsed"])
        self.assertEqual(model_store["parent_profile"], "FA3-MODEL-MANAGER-001")
        self.assertIn("MODEL_SOURCE_PROVIDER", model_store["classification"])
        self.assertFalse(model_store["architectural_authority"])
        self.assertFalse(spaces["global_hard_dependency"])
        self.assertFalse(spaces["automatic_local_fallback_target"])

    def test_gui_exposes_remote_ai_hub_as_featured_projection(self) -> None:
        qml = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text()
        contract = json.loads((ROOT / "canonical/contracts/FA3-REMOTE-AI-EXEC-CONTRACTS-001.json").read_text())
        provider = json.loads((ROOT / "canonical/providers/FA3-PROVIDER-HF-SPACES-001.json").read_text())
        self.assertIn('label: "Remote AI Hub"; pageIndex: 1', qml)
        self.assertIn('label: "Projects"; pageIndex: 2', qml)
        self.assertLess(qml.index('label: "Remote AI Hub"; pageIndex: 1'), qml.index('label: "Projects"; pageIndex: 2'))
        for token in ["Hosted Execution", "Hugging Face Spaces", "Remote Queue", "Egress Policy"]:
            self.assertIn(token, qml)
        self.assertEqual(provider["id"], "FA3-PROVIDER-HF-SPACES-001")
        self.assertTrue(provider["trust_and_security"]["credential_reference_only"])
        self.assertFalse(contract["discovery_and_trust"]["agents_md_is_trust_authority"])
        self.assertFalse(contract["discovery_and_trust"]["openapi_is_trust_authority"])
        self.assertNotIn("HF_TOKEN=", qml)


if __name__ == "__main__":
    unittest.main()
