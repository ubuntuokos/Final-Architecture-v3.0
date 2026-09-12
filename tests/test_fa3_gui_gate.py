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
