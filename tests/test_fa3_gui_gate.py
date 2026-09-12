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

if __name__ == "__main__": unittest.main()
