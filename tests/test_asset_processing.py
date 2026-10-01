from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_asset_processing import (
    AssetPlanError,
    compile_invalidation_plan,
    compile_processing_plan,
)


def digest(char: str) -> str:
    return "sha256:" + char * 64


def case():
    sources = [
        {
            "asset_key": "mesh.source",
            "content_digest": digest("a"),
            "media_type": "model/gltf+json",
            "rights_state": "CLEARED",
            "provenance_ref": "fixture:mesh",
        },
        {
            "asset_key": "texture.source",
            "content_digest": digest("b"),
            "media_type": "image/png",
            "rights_state": "CLEARED",
            "provenance_ref": "fixture:texture",
        },
    ]
    jobs = [
        {
            "job_key": "texture.optimize",
            "input_keys": ["texture.source"],
            "recipe": {"id": "texture.optimize", "version": "1", "parameters": {"quality": 90}},
            "outputs": [{"asset_key": "texture.product", "media_type": "image/ktx2"}],
        },
        {
            "job_key": "material.pack",
            "input_keys": ["mesh.source", "texture.product"],
            "recipe": {"id": "material.pack", "version": "2", "parameters": {"pbr": True}},
            "outputs": [{"asset_key": "material.product", "media_type": "application/x-fa3-material"}],
        },
    ]
    edges = [
        {"consumer_key": "material.product", "dependency_key": "texture.source", "kind": "REFERENCE"},
        {"consumer_key": "mesh.source", "dependency_key": "missing.optional", "kind": "OPTIONAL"},
    ]
    return sources, edges, jobs


class AssetProcessingTests(unittest.TestCase):
    def test_canonical_profile_contract_and_shared_binding_match(self):
        import json
        profile = json.loads((ROOT / "canonical/profiles/FA3-SHARED-ASSET-PROCESSING-001.json").read_text())
        contracts = json.loads((ROOT / "canonical/contracts/FA3-SHARED-ASSET-PROCESSING-CONTRACTS-001.json").read_text())
        links = json.loads((ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json").read_text())
        self.assertEqual(profile["capability_bindings"], contracts["capability_bindings"])
        self.assertEqual(profile["capability_count"], 175)
        self.assertFalse(profile["new_capability"])
        shared = next(x for x in links["shared_capabilities"] if x["id"] == "FA3-SHARED-ASSET-PROCESSING-001")
        self.assertNotIn("capability_ids", shared["fa3_bindings"])
        self.assertEqual(shared["current_host_impact"]["classification"], "NO_RUNTIME_IMPACT")
        self.assertIn("fa3.video-editor", shared["consumer_applications"])
        self.assertIn("fa3.ai-module-factory", shared["consumer_applications"])

    def test_plan_is_deterministic_and_non_executing(self):
        sources, edges, jobs = case()
        a = compile_processing_plan(
            project_namespace="project:test",
            source_assets=sources,
            dependency_edges=edges,
            jobs=jobs,
        )
        b = compile_processing_plan(
            project_namespace="project:test",
            source_assets=list(reversed(sources)),
            dependency_edges=list(reversed(edges)),
            jobs=list(reversed(jobs)),
        )
        self.assertEqual(a["plan_digest"], b["plan_digest"])
        self.assertFalse(a["execution_authorized"])
        self.assertFalse(a["file_transform_execution"])
        self.assertFalse(a["network_access_required"])
        self.assertEqual(a["job_build_order"], ["texture.optimize", "material.pack"])
        self.assertEqual(
            a["unresolved_optional_dependencies"],
            [{"consumer_key": "mesh.source", "dependency_key": "missing.optional", "kind": "OPTIONAL"}],
        )

    def test_logical_identity_stable_but_version_changes(self):
        sources, edges, jobs = case()
        a = compile_processing_plan(project_namespace="project:test", source_assets=sources, dependency_edges=edges, jobs=jobs)
        changed = deepcopy(sources)
        changed[1]["content_digest"] = digest("c")
        b = compile_processing_plan(project_namespace="project:test", source_assets=changed, dependency_edges=edges, jobs=jobs)
        by_a = {x["asset_key"]: x for x in a["assets"]}
        by_b = {x["asset_key"]: x for x in b["assets"]}
        self.assertEqual(by_a["texture.source"]["logical_id"], by_b["texture.source"]["logical_id"])
        self.assertNotEqual(by_a["texture.source"]["version_id"], by_b["texture.source"]["version_id"])
        self.assertNotEqual(by_a["texture.product"]["version_id"], by_b["texture.product"]["version_id"])
        self.assertNotEqual(by_a["material.product"]["version_id"], by_b["material.product"]["version_id"])

    def test_transitive_build_state_changes_downstream_version(self):
        sources, _, jobs = case()
        jobs = [{
            "job_key": "mesh.package",
            "input_keys": ["mesh.source"],
            "recipe": {"id": "mesh.package", "version": "1", "parameters": {}},
            "outputs": [{"asset_key": "mesh.product", "media_type": "model/gltf-binary"}],
        }]
        edges = [{"consumer_key": "mesh.source", "dependency_key": "texture.source", "kind": "BUILD"}]
        a = compile_processing_plan(project_namespace="project:test", source_assets=sources, dependency_edges=edges, jobs=jobs)
        changed = deepcopy(sources)
        changed[1]["content_digest"] = digest("c")
        b = compile_processing_plan(project_namespace="project:test", source_assets=changed, dependency_edges=edges, jobs=jobs)
        by_a = {x["asset_key"]: x for x in a["assets"]}
        by_b = {x["asset_key"]: x for x in b["assets"]}
        self.assertEqual(by_a["mesh.source"]["version_id"], by_b["mesh.source"]["version_id"])
        self.assertNotEqual(by_a["mesh.source"]["build_state_id"], by_b["mesh.source"]["build_state_id"])
        self.assertNotEqual(by_a["mesh.product"]["version_id"], by_b["mesh.product"]["version_id"])

    def test_transitive_invalidation_uses_build_edges_only(self):
        sources, edges, jobs = case()
        plan = compile_processing_plan(project_namespace="project:test", source_assets=sources, dependency_edges=edges, jobs=jobs)
        inv = compile_invalidation_plan(plan, ["texture.source"])
        self.assertEqual(
            inv["affected_asset_keys"],
            ["material.product", "texture.product", "texture.source"],
        )
        self.assertEqual(inv["affected_job_keys"], ["material.pack", "texture.optimize"])
        self.assertFalse(inv["automatic_rebuild_authorized"])

    def test_reference_cycle_is_allowed(self):
        sources, _, jobs = case()
        edges = [
            {"consumer_key": "mesh.source", "dependency_key": "texture.source", "kind": "REFERENCE"},
            {"consumer_key": "texture.source", "dependency_key": "mesh.source", "kind": "REFERENCE"},
        ]
        plan = compile_processing_plan(project_namespace="project:test", source_assets=sources, dependency_edges=edges, jobs=jobs)
        self.assertEqual(len(plan["reference_dependencies"]), 2)

    def test_build_cycle_fails_closed(self):
        sources = [{
            "asset_key": "seed",
            "content_digest": digest("d"),
            "media_type": "application/octet-stream",
            "rights_state": "CLEARED",
            "provenance_ref": "fixture:seed",
        }]
        jobs = [
            {
                "job_key": "a",
                "input_keys": ["out.b"],
                "recipe": {"id": "a", "version": "1", "parameters": {}},
                "outputs": [{"asset_key": "out.a", "media_type": "application/x-a"}],
            },
            {
                "job_key": "b",
                "input_keys": ["out.a"],
                "recipe": {"id": "b", "version": "1", "parameters": {}},
                "outputs": [{"asset_key": "out.b", "media_type": "application/x-b"}],
            },
        ]
        with self.assertRaisesRegex(AssetPlanError, "cycle"):
            compile_processing_plan(project_namespace="project:test", source_assets=sources, jobs=jobs)

    def test_missing_required_dependency_fails_closed(self):
        sources, _, jobs = case()
        edges = [{"consumer_key": "mesh.source", "dependency_key": "missing", "kind": "BUILD"}]
        with self.assertRaisesRegex(AssetPlanError, "required dependency unknown"):
            compile_processing_plan(project_namespace="project:test", source_assets=sources, dependency_edges=edges, jobs=jobs)

    def test_uncleared_rights_block_execution_eligibility(self):
        sources, edges, jobs = case()
        sources[1]["rights_state"] = "REFERENCE_ONLY"
        plan = compile_processing_plan(project_namespace="project:test", source_assets=sources, dependency_edges=edges, jobs=jobs)
        by_job = {x["job_key"]: x for x in plan["jobs"]}
        self.assertFalse(by_job["texture.optimize"]["execution_eligible_if_executor_admitted"])
        self.assertFalse(by_job["material.pack"]["execution_eligible_if_executor_admitted"])

    def test_arbitrary_executable_recipe_payload_is_forbidden(self):
        sources, edges, jobs = case()
        jobs[0]["recipe"]["parameters"]["command"] = "ffmpeg -i input output"
        with self.assertRaisesRegex(AssetPlanError, "executable payload"):
            compile_processing_plan(project_namespace="project:test", source_assets=sources, dependency_edges=edges, jobs=jobs)


if __name__ == "__main__":
    unittest.main()
