from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_shared_real2sim_3d import (  # noqa: E402
    CAPABILITY_BINDINGS,
    HANDOFF_SCHEMA,
    PLAN_SCHEMA,
    REQUEST_SCHEMA,
    Real2Sim3DError,
    build_dcc_handoff,
    build_plan,
    plugin_manifest,
)


def request(**overrides):
    value = {
        "schema": REQUEST_SCHEMA,
        "project_id": "project-demo",
        "source_asset_ref": "sha256:source-video",
        "features": [
            "ROOM_GEOMETRY",
            "CAMERA_RECOVERY",
            "ACTOR_RECONSTRUCTION",
            "CONTACT_REFINEMENT",
            "MOTION_TRANSFER",
            "PLACEMENT_VALIDATION",
            "PREVIEW_REVIEW",
        ],
        "dcc_host": "BFORARTISTS",
        "ai_enabled": True,
        "allow_network": False,
        "commit_to_dcc": False,
    }
    value.update(overrides)
    return value


class SharedReal2Sim3DTests(unittest.TestCase):
    def test_manifest_preserves_175_and_has_no_aha_runtime_dependency(self):
        manifest = plugin_manifest()
        self.assertEqual(175, manifest["capability_count"])
        self.assertEqual(list(CAPABILITY_BINDINGS), manifest["capability_bindings"])
        self.assertFalse(manifest["new_capability"])
        self.assertFalse(manifest["new_architectural_authority"])
        self.assertFalse(manifest["runtime_dependency_on_aha3d"])
        self.assertEqual("ANALYSIS_ONLY_NOT_ADMITTED", manifest["upstream_bridge_status"])

    def test_plan_composes_existing_authorities_without_execution(self):
        plan = build_plan(request())
        self.assertEqual(PLAN_SCHEMA, plan["schema"])
        self.assertFalse(plan["execution_authorized"])
        self.assertFalse(plan["direct_dcc_mutation_authorized"])
        self.assertEqual("FA3-3D-GEOM-001", plan["geometry_authority"])
        self.assertEqual("FA3-DCC-RT3D-001", plan["dcc_scene_and_final_asset_authority"])
        self.assertEqual("FA3-AUTH-MODEL-ROUTER-001", plan["model_provider_selection"])
        self.assertEqual("FA3-AUTH-HOST-RESOURCE-BROKER-001", plan["host_resource_admission"])
        self.assertTrue(plan["cpu_only_control_path_valid"])
        self.assertFalse(plan["display_gpu_implicit_enlistment"])
        self.assertEqual("UNAVAILABLE_NO_SILENT_FALLBACK", plan["compute_stage_without_compatible_provider"])

    def test_blender_compatibility_host_is_supported(self):
        plan = build_plan(request(dcc_host="BLENDER"))
        self.assertEqual("BLENDER", plan["dcc_host_id"])
        self.assertEqual("COMPATIBILITY_DCC_HOST", plan["dcc_host"]["role"])
        self.assertFalse(plan["dcc_host"]["direct_host_mutation"])

    def test_commit_request_requires_approval_reference(self):
        with self.assertRaises(Real2Sim3DError):
            build_plan(request(commit_to_dcc=True))

    def test_handoff_requires_matching_explicit_approval(self):
        plan = build_plan(request())
        with self.assertRaises(Real2Sim3DError):
            build_dcc_handoff(plan, {"id": "a1", "approved": False, "project_id": "project-demo"})
        handoff = build_dcc_handoff(plan, {"id": "a1", "approved": True, "project_id": "project-demo"})
        self.assertEqual(HANDOFF_SCHEMA, handoff["schema"])
        self.assertFalse(handoff["direct_host_mutation"])
        self.assertFalse(handoff["execution_authorized_by_this_handoff"])
        self.assertTrue(handoff["native_project_preservation_required"])
        self.assertTrue(handoff["blender_compatible_interchange_required"])

    def test_unknown_feature_fails_closed(self):
        with self.assertRaises(Real2Sim3DError):
            build_plan(request(features=["ROOM_GEOMETRY", "MAGIC_UNKNOWN_FEATURE"]))

    def test_explicit_ai_and_network_switches_are_required(self):
        bad = request()
        bad.pop("ai_enabled")
        with self.assertRaises(Real2Sim3DError):
            build_plan(bad)
        bad = request()
        bad.pop("allow_network")
        with self.assertRaises(Real2Sim3DError):
            build_plan(bad)


if __name__ == "__main__":
    unittest.main()
