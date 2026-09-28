import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class SkillFabricGuiContractTests(unittest.TestCase):
    def test_registry_route_and_single_main_stack_page(self):
        reg = json.loads((ROOT / "canonical/FA3-GUI-SURFACE-REGISTRY-001.json").read_text())
        routes = [item["route_id"] for item in reg["surfaces"]]
        self.assertEqual(len(routes), len(set(routes)))
        self.assertIn("decision.skill-fabric", routes)
        item = next(row for row in reg["surfaces"] if row["route_id"] == "decision.skill-fabric")
        self.assertFalse(item["authority"])
        self.assertFalse(item["direct_execution"])
        self.assertFalse(item["current_host_evidence_verifier"])
        main = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text()
        self.assertIn('"decision.skill-fabric": 39', main)
        self.assertEqual(main.count("                SkillFabricInspectorPage {"), 1)
        self.assertIn('routeId: "decision.skill-fabric"', main)
        self.assertIn('setContextProperty("fa3SkillFabric", &skillFabric)', (ROOT / "apps/fa3-control-center/src/main.cpp").read_text())

    def test_service_cannot_promote_static_report(self):
        h = (ROOT / "apps/fa3-control-center/src/SkillFabricService.h").read_text()
        cpp = (ROOT / "apps/fa3-control-center/src/SkillFabricService.cpp").read_text()
        qml = (ROOT / "apps/fa3-control-center/qml/SkillFabricInspectorPage.qml").read_text()
        self.assertIn('bool currentHostVerified() const { return false; }', h)
        self.assertIn("UNTRUSTED_RUNTIME_CLAIM", cpp)
        self.assertIn("STATIC_REFERENCE_PASS", cpp)
        self.assertIn('current_host_runtime_claim', cpp)
        self.assertIn("CURRENT-HOST: NINCS IGAZOLVA", qml)
        self.assertNotIn("QProcess", cpp)
        self.assertNotIn("onClicked: run", qml)
        self.assertIn("fa3SkillFabric.refresh()", qml)

    def test_packaging_links_and_multiple_existing_surfaces(self):
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text()
        for file in ("SkillFabricService.h", "SkillFabricService.cpp", "SkillFabricInspectorPage.qml"):
            self.assertIn(file, cmake)
        for name in ("AgentActionCenterPage.qml", "ContextInspectorPage.qml",
                     "DecisionInspectorPage.qml", "LanguageControlPage.qml"):
            body = (ROOT / "apps/fa3-control-center/qml" / name).read_text()
            self.assertIn('"decision.skill-fabric"', body, name)
        self.assertIn("qml/SkillFabricInspectorPage.qml",
                      cmake)


if __name__ == "__main__":
    unittest.main()
