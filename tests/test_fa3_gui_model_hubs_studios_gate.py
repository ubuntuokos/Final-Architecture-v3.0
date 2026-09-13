import unittest
from src import fa3_gui_model_hubs_studios_gate


class Fa3GuiModelHubsStudiosGateTests(unittest.TestCase):
    def test_gate(self):
        self.assertEqual([], fa3_gui_model_hubs_studios_gate.validate())


if __name__ == "__main__":
    unittest.main()
