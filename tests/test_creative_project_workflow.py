from __future__ import annotations
import unittest
from fa3_creative_project_workflow import CreativeProjectError, build_timeline_projection_plan, plan_scoped_revision, project_context_slice, validate_project_state

def sample_project():
    return {
      "schema":"fa3.creative-project-state.v1","project_id":"film-1",
      "nodes":[
        {"id":"spec","type":"PROJECT_SPEC"},{"id":"shot-1","type":"SHOT","order":1},{"id":"asset-1","type":"ASSET"},{"id":"timeline-1","type":"TIMELINE_SEGMENT"},
        {"id":"shot-2","type":"SHOT","order":2},{"id":"asset-2","type":"ASSET"}],
      "edges":[
        {"from":"shot-1","to":"asset-1","type":"DERIVED_FROM","invalidate_on_revision":True},
        {"from":"asset-1","to":"timeline-1","type":"EDIT_SOURCE","invalidate_on_revision":True},
        {"from":"shot-2","to":"asset-2","type":"DERIVED_FROM","invalidate_on_revision":True},
        {"from":"spec","to":"shot-1","type":"PROVIDES_CONTEXT","invalidate_on_revision":False}],
      "documents":[
        {"id":"user-spec","origin":"USER","editable":True,"scope":["*"]},
        {"id":"ai-notes","origin":"AI","editable":True,"scope":["shot-1"],"provenance_ref":"prov:ai:1"},
        {"id":"ref","origin":"IMPORTED_REFERENCE","editable":False,"scope":["shot-2"]}],
      "constraints":[{"id":"identity:hero","hard":True}]}

class CreativeProjectWorkflowTests(unittest.TestCase):
    def test_valid_project(self):
        self.assertEqual(validate_project_state(sample_project())["result"],"PASS")
    def test_scoped_revision_preserves_unrelated(self):
        plan=plan_scoped_revision(sample_project(),["shot-1"])
        self.assertEqual(plan["affected_node_ids"],["asset-1","shot-1","timeline-1"])
        self.assertIn("shot-2",plan["preserved_node_ids"]); self.assertIn("asset-2",plan["preserved_node_ids"])
        self.assertFalse(plan["execution_authorized"])
    def test_locked_node_requires_approval(self):
        p=sample_project(); next(x for x in p["nodes"] if x["id"]=="asset-1")["human_approved"]=True
        plan=plan_scoped_revision(p,["shot-1"]); self.assertTrue(plan["approval_required"]); self.assertEqual(plan["approval_boundary_node_ids"],["asset-1"])
    def test_context_slice_is_bounded(self):
        p=sample_project(); context=project_context_slice(p,plan_scoped_revision(p,["shot-1"]))
        self.assertEqual([d["id"] for d in context["documents"]],["user-spec","ai-notes"]); self.assertFalse(context["global_corpus_auto_injection"])
    def test_imported_reference_must_be_read_only(self):
        p=sample_project(); next(x for x in p["documents"] if x["id"]=="ref")["editable"]=True
        with self.assertRaises(CreativeProjectError): validate_project_state(p)
    def test_unknown_changed_node_fails_closed(self):
        with self.assertRaises(CreativeProjectError): plan_scoped_revision(sample_project(),["missing"])
    def test_timeline_projection_no_direct_native_mutation(self):
        plan=build_timeline_projection_plan(sample_project())
        self.assertEqual(plan["ordered_shot_ids"],["shot-1","shot-2"]); self.assertEqual(plan["canonical_interchange"],"OpenTimelineIO")
        self.assertFalse(plan["direct_native_project_mutation"]); self.assertTrue(plan["fa3_video_editor_command_bus_required_for_native_commit"])

if __name__=="__main__": unittest.main()
