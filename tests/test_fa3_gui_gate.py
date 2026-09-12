import unittest
from src import fa3_gui_gate


class Fa3GuiGateTests(unittest.TestCase):
    def test_gui_materialization_is_fail_closed_and_authority_neutral(self):
        self.assertEqual([], fa3_gui_gate.validate())

    def test_mentor_and_coach_roles_remain_distinct(self):
        interaction = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["mentor_coach_contract"])
        self.assertIn("MENTOR_TEACHES_COACH_GUIDES_EXECUTION", interaction["invariants"])

    def test_settings_backend_is_local_preferences_only(self):
        contract = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["gui_settings_contract"])
        self.assertEqual("QSettings/XDG", contract["storage"]["backend"])
        self.assertEqual("FORBIDDEN", contract["mutation_model"]["fstab_mutation"])

    def test_roles_are_configured_under_settings_not_primary_navigation(self):
        desktop = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["desktop_profile"])
        contract = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["desktop_contract"])
        self.assertEqual("SETTINGS", desktop["role_navigation_policy"]["configuration_location"])
        self.assertEqual("FORBIDDEN", fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["gui_settings_contract"])["role_ui"]["primary_navigation_role_pages"])
        self.assertIn("ROLE_CONFIGURATION_LIVES_UNDER_SETTINGS_NOT_PRIMARY_NAVIGATION", contract["role_ui_invariants"])

    def test_ask_role_button_visibility_is_ui_only(self):
        profile = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["gui_settings_profile"])
        contract = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["gui_settings_contract"])
        self.assertFalse(profile["role_settings"]["visibility_changes_canonical_role"])
        self.assertEqual("UI_ONLY", contract["role_ui"]["ask_button_visibility_effect"])

    def test_inspector_preferences_cannot_disable_independent_verification(self):
        contract = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["gui_settings_contract"])
        desktop = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["desktop_profile"])
        self.assertFalse(contract["role_ui"]["inspector_independence_can_be_disabled_by_preference"])
        self.assertIn("FA3-INSPECTOR-001", desktop["role_navigation_policy"]["roles"])

    def test_operations_gui_never_directly_resets_gpu(self):
        contract = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["desktop_contract"])
        self.assertEqual("FORBIDDEN", contract["mutation_model"]["direct_gpu_hard_reset"])
        self.assertIn("ROUTINE_GPU_MEMORY_CLEANUP_NEVER_REQUIRES_GPU_RESET", contract["maintenance_invariants"])

    def test_generic_cleanup_cannot_delete_evidence(self):
        profile = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["desktop_profile"])
        self.assertTrue(profile["maintenance_policy"]["evidence_excluded_from_generic_cleanup"])

    def test_peripheral_system_mutation_is_not_direct(self):
        contract = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["desktop_contract"])
        self.assertEqual("FORBIDDEN", contract["mutation_model"]["direct_peripheral_kernel_or_device_mutation"])
        self.assertIn("WEBCAM_CAMERA_V4L2", contract["peripheral_classes"])
        self.assertIn("MIDI_AUDIO_CONTROLLERS", contract["peripheral_classes"])

    def test_ai_web_ui_is_contained_inside_native_fa3_window(self):
        profile = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["desktop_profile"])
        contract = fa3_gui_gate.load_json(fa3_gui_gate.REQUIRED["desktop_contract"])
        self.assertFalse(profile["runtime"]["browser_shell"])
        self.assertEqual("Qt WebEngine", profile["runtime"]["embedded_web_runtime"])
        self.assertEqual("FORBIDDEN_BY_DEFAULT", profile["embedded_web_policy"]["external_browser_for_ai_ui"])
        self.assertIn("AI_WEB_UI_EMBEDDED_IN_FA3_NATIVE_WINDOW_BY_DEFAULT", contract["embedded_web_invariants"])
        self.assertIn("NEW_WINDOW_REQUESTS_RETAINED_INSIDE_FA3_WEB_SURFACE", contract["embedded_web_invariants"])


if __name__ == "__main__":
    unittest.main()
