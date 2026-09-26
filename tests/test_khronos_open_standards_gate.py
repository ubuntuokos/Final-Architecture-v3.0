import tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from fa3_khronos_open_standards_gate import EXPECTED, validate

class KhronosOpenStandardsGateTest(unittest.TestCase):
    def test_repository_tree_passes(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(validate(root),[])

    def test_pin_inventory_is_complete(self):
        self.assertEqual(len(EXPECTED),15)
        self.assertIn("KhronosGroup/Vulkan-Profiles",EXPECTED)
        self.assertIn("KhronosGroup/NNEF-Tools",EXPECTED)

if __name__=="__main__":
    unittest.main()
