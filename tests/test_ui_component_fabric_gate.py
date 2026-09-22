import json
import unittest
from pathlib import Path

from src import fa3_ui_component_fabric_gate


ROOT = Path(__file__).resolve().parents[1]


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class UiComponentFabricGateTests(unittest.TestCase):
    def test_gate_is_fail_closed_and_authority_neutral(self):
        self.assertEqual([], fa3_ui_component_fabric_gate.validate())

    def test_profile_is_desktop_subprofile_without_capability_drift(self):
        profile = load("canonical/profiles/FA3-UI-COMPONENT-FABRIC-001.json")
        self.assertEqual("FA3-DESKTOP-001", profile["parent_profile"])
        self.assertTrue(profile["provider_neutral"])
        self.assertFalse(profile["new_capability"])
        self.assertFalse(profile["new_architectural_authority"])
        self.assertEqual(143, profile["capability_count"])

    def test_uiverse_galaxy_is_reference_only(self):
        ref = load("canonical/FA3-REFERENCE-UIVERSE-GALAXY-001.json")
        self.assertEqual("EXTERNAL_REFERENCE", ref["class"])
        self.assertEqual("adbd2adde0a299a3956ea288fb444ec01891ca41", ref["source"]["pinned_revision"])
        self.assertEqual("MIT", ref["source"]["license"])
        self.assertTrue(all(ref["dependency"][k] is False for k in [
            "build", "runtime", "git_submodule", "network_runtime", "vendored_repository"
        ]))
        self.assertEqual("FORBIDDEN", ref["import_policy"]["automatic_import"])
        self.assertEqual("FORBIDDEN", ref["import_policy"]["raw_copy_paste_adoption"])
        self.assertTrue(ref["import_policy"]["production_component_must_be_fa3_native"])
        self.assertFalse(ref["promotion_rule"]["provider_materialization_implied"])

    def test_contract_requires_security_accessibility_tokens_and_provenance(self):
        contract = load("canonical/contracts/FA3-UI-COMPONENT-FABRIC-CONTRACTS-001.json")
        intake = contract["source_intake"]
        for key in [
            "script_elements",
            "inline_event_handlers",
            "javascript_urls",
            "iframes",
            "remote_executable_resources",
            "tracking_or_analytics_resources",
            "remote_fonts_in_production_component",
        ]:
            self.assertEqual("FORBIDDEN", intake[key])
        self.assertTrue(contract["accessibility"]["keyboard_operation_required_for_interactive_controls"])
        self.assertTrue(contract["accessibility"]["visible_focus_required"])
        self.assertTrue(contract["accessibility"]["reduced_motion_fallback_required_for_animation"])
        self.assertTrue(contract["normalization"]["hardcoded_colors_to_fa3_tokens"])
        self.assertTrue(contract["normalization"]["spacing_radius_shadow_and_motion_to_fa3_tokens"])
        self.assertTrue(contract["promotion"]["fail_closed"])

    def test_reference_evidence_does_not_claim_runtime_or_component_admission(self):
        acceptance = load("canonical/FA3-UI-COMPONENT-FABRIC-EVIDENCE-ACCEPTANCE-001.json")
        evidence = load("evidence/reference/fa3-ui-component-fabric-reference-pass.json")
        self.assertEqual("PASS", evidence["status"])
        self.assertTrue(set(acceptance["required_reference_claims"]) <= set(evidence["claims"]))
        self.assertTrue(set(acceptance["required_non_claims"]) <= set(evidence["non_claims"]))
        self.assertFalse(evidence["current_host_runtime_claim"])
        self.assertFalse(evidence["individual_component_production_admitted"])


if __name__ == "__main__":
    unittest.main()
