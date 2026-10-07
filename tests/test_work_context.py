from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_work_context import project_for_application, to_os_event_enrichment, validate_work_context


class WorkContextTests(unittest.TestCase):
    def context(self) -> dict:
        return {
            "context_id": "context:1",
            "application_id": "fa3.story-screenplay",
            "project_workspace_scope": "project:film-a",
            "production_ref": "production:film-a",
            "project_ref": "project:film-a",
            "workstream_ref": "workstream:writing",
            "milestone_ref": "milestone:script-lock",
            "task_ref": "task:scene-24",
            "workflow_ref": "workflow:rewrite",
            "asset_refs": ["asset:scene-24"],
            "artifact_refs": [],
            "approval_refs": [],
            "provenance_refs": ["journal:1"],
            "owns_project_truth": False,
            "owns_task_truth": False,
            "agent_scope_expansion": False,
        }

    def test_context_is_reference_projection(self) -> None:
        self.assertTrue(validate_work_context(self.context()).ok)

    def test_shadow_project_authority_is_forbidden(self) -> None:
        value = self.context()
        value["owns_project_truth"] = True
        self.assertFalse(validate_work_context(value).ok)

    def test_application_projection_is_minimized(self) -> None:
        result = project_for_application(self.context(), {"project_ref", "task_ref"})
        self.assertIn("project_ref", result)
        self.assertIn("task_ref", result)
        self.assertNotIn("production_ref", result)

    def test_os_event_mapping_keeps_journal_outer_authority(self) -> None:
        event = to_os_event_enrichment(
            self.context(), action="work-context.open", subject_kind="task", subject_ref="task:scene-24"
        )
        self.assertEqual(event["capture_policy_id"], "FA3-OS-POLICY-001")
        self.assertEqual(event["workstream_id"], "workstream:writing")
        self.assertNotIn("canonical_event_id", event)


if __name__ == "__main__":
    unittest.main()
