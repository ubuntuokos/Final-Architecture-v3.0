import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ToolsFabricTests(unittest.TestCase):
    def test_tools_fabric_is_task_first_and_non_authoritative(self):
        doc = json.loads((ROOT / "canonical/FA3-TOOLS-FABRIC-001.json").read_text(encoding="utf-8"))
        self.assertEqual("CANONICAL", doc["status"])
        self.assertFalse(doc["execution_authority"])
        self.assertFalse(doc["policy_authority"])
        self.assertTrue(doc["gui_contract"]["task_first_navigation"])
        self.assertFalse(doc["routing_contract"]["direct_provider_bypass"])
        categories = {row["id"]: row for row in doc["categories"]}
        self.assertEqual("FA3-FILE-CONVERSION-001", categories["CONVERSION"]["canonical_execution_profile"])

    def test_convertx_is_not_exposed_as_approved_app(self):
        catalog = json.loads((ROOT / "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json").read_text(encoding="utf-8"))
        app_ids = {row["id"] for row in catalog["applications"]}
        self.assertNotIn("convertx", app_ids)

    def test_control_center_packages_tools_surface(self):
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
        main_cpp = (ROOT / "apps/fa3-control-center/src/main.cpp").read_text(encoding="utf-8")
        tools = (ROOT / "apps/fa3-control-center/qml/ToolsPage.qml").read_text(encoding="utf-8")
        overlay = (ROOT / "apps/fa3-control-center/qml/ToolsOverlay.qml").read_text(encoding="utf-8")
        self.assertIn("qml/ToolsPage.qml", cmake)
        self.assertIn("qml/ToolsOverlay.qml", cmake)
        self.assertIn("FA3-TOOLS-FABRIC-001.json", cmake)
        self.assertIn("ToolsOverlay.qml", main_cpp)
        self.assertIn("Ctrl+Shift+T", overlay)
        self.assertIn("ConvertX · P2 · QUARANTINED", tools)
        self.assertIn("XeLaTeX DENY", tools)

    def test_tools_surface_has_no_install_or_direct_execution_action(self):
        text = (ROOT / "apps/fa3-control-center/qml/ToolsPage.qml").read_text(encoding="utf-8")
        self.assertNotIn("installApproved(", text)
        self.assertNotIn("launchInstalled(", text)
        self.assertNotIn("/convert", text)


if __name__ == "__main__":
    unittest.main()
