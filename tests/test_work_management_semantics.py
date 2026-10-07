from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_work_management_semantics import canonical_path, validate_check_in, validate_entity


class WorkManagementSemanticTests(unittest.TestCase):
    def test_goal_project_task_hierarchy(self) -> None:
        project = {
            "canonical_id": "project:film-a",
            "kind": "PROJECT",
            "title": "Film A",
            "state": "ACTIVE",
            "project_workspace_scope": "workspace:film-a",
            "provenance_refs": ["journal:1"],
        }
        task = {
            "canonical_id": "task:scene-24",
            "kind": "TASK",
            "title": "Scene 24 rewrite",
            "state": "OPEN",
            "project_workspace_scope": "workspace:film-a",
            "provenance_refs": ["journal:2"],
            "parent_ref": "project:film-a",
        }
        self.assertTrue(validate_entity(project).ok)
        self.assertTrue(validate_entity(task, project).ok)

    def test_provider_identity_cannot_be_canonical(self) -> None:
        entity = {
            "canonical_id": "task:1",
            "kind": "TASK",
            "title": "Task",
            "state": "OPEN",
            "project_workspace_scope": "workspace:1",
            "provenance_refs": [],
            "provider_owns_canonical_identity": True,
        }
        result = validate_entity(entity)
        self.assertFalse(result.ok)
        self.assertIn("provider_canonical_identity_forbidden", result.findings)

    def test_checkin_source_truth(self) -> None:
        value = {
            "canonical_check_in_id": "checkin:1",
            "subject_ref": "project:film-a",
            "status": "ON_TRACK",
            "completed_since_last": ["scene layout"],
            "next_actions": ["lighting"],
            "blockers": [],
            "risks": [],
            "decisions_needed": [],
            "actor_identity": "user:1",
            "timestamp": "2026-10-05T15:00:00Z",
            "provenance_refs": ["journal:3"],
            "ai_summary_is_source_truth": False,
        }
        self.assertTrue(validate_check_in(value).ok)
        value["ai_summary_is_source_truth"] = True
        self.assertFalse(validate_check_in(value).ok)

    def test_canonical_path_order(self) -> None:
        self.assertEqual(
            canonical_path(goal="goal:1", production="prod:1", project="project:1", task="task:1"),
            ["goal:1", "prod:1", "project:1", "task:1"],
        )


if __name__ == "__main__":
    unittest.main()
