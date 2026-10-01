from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Tests(unittest.TestCase):
    def test_surface_is_registered_non_authoritative(self):
        reg = json.loads((ROOT / "canonical/FA3-GUI-SURFACE-REGISTRY-001.json").read_text())
        row = next(x for x in reg["surfaces"] if x.get("route_id") == "agents.orchestration-monitor")
        self.assertFalse(row["authority"])
        self.assertFalse(row["direct_runtime_execution"])
        self.assertEqual(row["mutation"], "DRAFT_ONLY")

    def test_qml_exposes_draft_only_changes(self):
        text = (ROOT / "apps/fa3-control-center/qml/OrchestrationMonitorPage.qml").read_text()
        self.assertIn("DRAFT ONLY", text)
        self.assertIn("stageChangeRequest", text)
        self.assertNotIn("direct_provider_execution: true", text)

    def test_service_rejects_authoritative_projection(self):
        text = (ROOT / "apps/fa3-control-center/src/OrchestrationMonitorService.cpp").read_text()
        self.assertIn('fa3.orchestration-monitor-projection.v1', text)
        self.assertIn('toBool(true)', text)
        self.assertIn('REJECTED_PROJECTION', text)

    def test_control_center_route_is_materialized(self):
        main = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text()
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text()
        self.assertIn('"agents.orchestration-monitor": 39', main)
        self.assertIn("OrchestrationMonitorPage", main)
        self.assertIn("OrchestrationMonitorService.cpp", cmake)

if __name__ == "__main__":
    unittest.main()
