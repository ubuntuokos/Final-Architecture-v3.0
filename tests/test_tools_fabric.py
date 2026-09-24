import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ToolsFabricTests(unittest.TestCase):
    def test_tools_fabric_is_task_first_non_authoritative_and_uaf_bounded(self):
        doc = json.loads((ROOT / "canonical/FA3-TOOLS-FABRIC-001.json").read_text(encoding="utf-8"))
        self.assertEqual("CANONICAL", doc["status"])
        self.assertFalse(doc["execution_authority"])
        self.assertFalse(doc["policy_authority"])
        self.assertEqual(143, doc["capability_count"])
        self.assertFalse(doc["new_architectural_authority"])
        self.assertEqual("create.tools", doc["gui_contract"]["route_id"])
        self.assertEqual("FA3-UNIFIED-ACTION-FABRIC-001", doc["routing_contract"]["execution_fabric"])
        self.assertFalse(doc["routing_contract"]["direct_provider_bypass"])
        categories = {row["id"]: row for row in doc["categories"]}
        self.assertEqual("FA3-FILE-CONVERSION-001", categories["CONVERSION"]["canonical_execution_profile"])

    def test_convertx_is_user_local_external_quarantined_and_not_approved_app(self):
        provider = json.loads((ROOT / "canonical/FA3-PROVIDER-CONVERTX-001.json").read_text(encoding="utf-8"))
        self.assertEqual("QUARANTINED", provider["status"])
        self.assertEqual("USER_LOCAL_EXTERNAL", provider["distribution_class"])
        self.assertFalse(provider["product_bundle_allowed"])
        self.assertFalse(provider["machine_interface"]["machine_execution_enabled"])
        catalog = json.loads((ROOT / "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json").read_text(encoding="utf-8"))
        self.assertNotIn("convertx", {row["id"] for row in catalog["applications"]})

    def test_control_center_uses_semantic_tools_route_not_overlay_injection(self):
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
        main = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
        tools = (ROOT / "apps/fa3-control-center/qml/ToolsPage.qml").read_text(encoding="utf-8")
        registry = json.loads((ROOT / "canonical/FA3-GUI-SURFACE-REGISTRY-001.json").read_text(encoding="utf-8"))
        self.assertIn("qml/ToolsPage.qml", cmake)
        self.assertIn('"create.tools"', main)
        self.assertIn('routeId: "create.tools"', main)
        self.assertIn("ToolsPage {", main)
        self.assertFalse((ROOT / "apps/fa3-control-center/qml/ToolsOverlay.qml").exists())
        self.assertTrue(any(row.get("route_id") == "create.tools" and row.get("mutation") == "DRAFT_ONLY" for row in registry["surfaces"]))
        self.assertIn("UAF DRAFT ONLY", tools)
        self.assertIn("file.convert.plan", tools)
        self.assertIn("file.convert.execute", tools)
        self.assertIn("DRAFT_NOT_SUBMITTED", tools)

    def test_tools_surface_has_no_install_or_direct_provider_execution(self):
        text = (ROOT / "apps/fa3-control-center/qml/ToolsPage.qml").read_text(encoding="utf-8")
        for forbidden in ["installApproved(", "launchInstalled(", "/convert", "QNetworkAccessManager", "Qt.openUrlExternally"]:
            self.assertNotIn(forbidden, text)

    def test_file_conversion_uaf_actions_are_materialized(self):
        for action_id in ["file.convert.plan", "file.convert.execute", "file.convert.inspect"]:
            path = ROOT / "canonical/actions" / f"{action_id}.json"
            action = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("fa3.uaf.action-contract.v1", action["schema"])
            self.assertEqual(action_id, action["id"])
        execute = json.loads((ROOT / "canonical/actions/file.convert.execute.json").read_text(encoding="utf-8"))
        self.assertTrue(execute["resources"]["hrb_required"])

    def test_current_host_resource_blocker_remains_explicit(self):
        conformance = json.loads((ROOT / "canonical/FA3-CONVERTX-RUNTIME-CONFORMANCE-001.json").read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / "evidence/reference/fa3-convertx-reference-pending.json").read_text(encoding="utf-8"))
        self.assertEqual(
            "HRB_NON_ACCELERATOR_AUTHORIZATION_UNMATERIALIZED",
            conformance["resource_admission"]["current_authoritative_cpu_memory_verifier"],
        )
        self.assertEqual("PENDING_CURRENT_HOST", evidence["status"])
        self.assertFalse(evidence["runtime_claimed"])
        self.assertFalse(evidence["production_admitted"])
        self.assertFalse(evidence["machine_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
