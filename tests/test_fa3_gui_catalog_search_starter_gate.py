import unittest
from src.fa3_gui_catalog_search_starter_gate import validate

class TestFa3GuiCatalogSearchStarterGate(unittest.TestCase):
    def test_gate(self):
        self.assertEqual(validate(), [])

if __name__ == "__main__":
    unittest.main()
