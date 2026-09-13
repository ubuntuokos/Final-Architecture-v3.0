import unittest
from src.fa3_gui_mission_control_gate import validate

class MissionControlGateTest(unittest.TestCase):
    def test_gate(self):
        self.assertEqual(validate(), [])

if __name__ == "__main__": unittest.main()
