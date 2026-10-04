import json
import unittest
from pathlib import Path
from fa3_release_baseline import load_active_release_baseline

import fa3_ui_component_fabric_gate


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
        self.assertEqual(load_active_release_baseline(ROOT).capability_count, profile["capability_count"])

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


    def test_one_click_new_conversation_handoff_is_mandatory_and_atomic(self):
        contract = load("canonical/contracts/FA3-UI-COMPONENT-FABRIC-CONTRACTS-001.json")
        self.assertEqual(load_active_release_baseline(ROOT).capability_count, contract["capability_count"])
        self.assertIn("NewConversationHandoffDescriptor", contract["contracts"])
        handoff = contract["new_conversation_handoff"]
        self.assertEqual("FA3-RULE-ONE-CLICK-NEW-CONVERSATION-HANDOFF-001", handoff["rule_id"])
        self.assertEqual("P0", handoff["priority"])
        self.assertEqual("MUST", handoff["requirement"])
        payload = handoff["payload_integrity"]
        self.assertTrue(payload["complete_payload_in_exactly_one_copy_target"])
        self.assertEqual("FORBIDDEN", payload["split_payload_across_copy_targets"])
        self.assertEqual("FORBIDDEN", payload["payload_fragment_outside_single_copy_target"])
        self.assertFalse(payload["one_word_or_single_character_exempt"])
        self.assertFalse(payload["payload_length_exempt"])
        interaction = handoff["interaction"]
        self.assertTrue(interaction["visible_direct_copy_control_required"])
        self.assertEqual(1, interaction["required_copy_activation_count"])
        self.assertFalse(interaction["manual_text_selection_required"])
        self.assertFalse(interaction["scrolling_required_to_copy_complete_payload"])
        self.assertTrue(interaction["visual_scrolling_may_not_change_copy_scope"])

    def test_handoff_clipboard_is_explicit_write_only_and_decision_covers_both_lines(self):
        contract = load("canonical/contracts/FA3-UI-COMPONENT-FABRIC-CONTRACTS-001.json")
        clipboard = contract["new_conversation_handoff"]["clipboard"]
        self.assertEqual("EXPLICIT_USER_INITIATED_WRITE_ONLY", clipboard["mode"])
        self.assertFalse(clipboard["read_before_copy"])
        self.assertFalse(clipboard["background_capture"])
        self.assertFalse(clipboard["generic_clipboard_capture"])
        self.assertEqual("FAIL_CLOSED_NOT_READY", clipboard["unavailable_or_copy_failure"])

        decision = load("canonical/decisions/FA3-DEC-ONE-CLICK-NEW-CONVERSATION-HANDOFF-2026-10-04.json")
        self.assertEqual("CANONICAL_CLOSED", decision["status"])
        self.assertEqual("ACCEPT_AND_MANDATE", decision["decision"])
        self.assertTrue(decision["applies_to"]["fa3_cfa3_development_process"])
        self.assertTrue(decision["applies_to"]["cfa3_fa3_product"])
        self.assertFalse(decision["invariants"]["one_word_or_single_character_exception"])
        self.assertEqual(1, decision["invariants"]["required_copy_activation_count"])
        self.assertEqual(175, decision["capability_count_after"])
        self.assertEqual(0, decision["new_capabilities"])
        self.assertEqual(0, decision["new_architectural_authorities"])


if __name__ == "__main__":
    unittest.main()
