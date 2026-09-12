import unittest

from src import fa3_gui_gate


class Fa3GuiGateTests(unittest.TestCase):
    def test_gui_materialization_is_fail_closed_and_authority_neutral(self):
        self.assertEqual([], fa3_gui_gate.validate())


if __name__ == "__main__":
    unittest.main()
