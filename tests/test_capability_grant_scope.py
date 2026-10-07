from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_capability_grant_scope import authorize, subgrant_is_subset, validate_grant


class CapabilityGrantScopeTests(unittest.TestCase):
    def grant(self) -> dict:
        return {
            "grant_id": "grant:1",
            "actor_identity": "agent:assistant",
            "operations": ["story.scene.read", "story.scene.update"],
            "resource_scope": ["story:episode-4"],
            "project_workspace_scope": ["project:ep4"],
            "delegator_identity": "user:1",
            "valid_from": "2026-10-05T10:00:00Z",
            "expires_at": "2026-10-05T18:00:00Z",
            "approval_binding": "REQUIRED",
            "budget_envelope": {"max_tool_calls": 20, "max_runtime_seconds": 600},
            "provenance_refs": ["journal:grant-1"],
            "actor_inherits_full_delegator_authority": False,
        }

    def test_scoped_operation_allows_with_approval(self) -> None:
        result = authorize(
            self.grant(),
            actor_identity="agent:assistant",
            operation="story.scene.update",
            resource="story:episode-4",
            project_workspace="project:ep4",
            now=datetime(2026, 10, 5, 12, tzinfo=timezone.utc),
            approval_satisfied=True,
        )
        self.assertTrue(result.allowed)

    def test_out_of_scope_resource_denied(self) -> None:
        result = authorize(
            self.grant(),
            actor_identity="agent:assistant",
            operation="story.scene.update",
            resource="finance:payments",
            project_workspace="project:ep4",
            now=datetime(2026, 10, 5, 12, tzinfo=timezone.utc),
            approval_satisfied=True,
        )
        self.assertFalse(result.allowed)

    def test_required_approval_denied_until_satisfied(self) -> None:
        result = authorize(
            self.grant(),
            actor_identity="agent:assistant",
            operation="story.scene.read",
            resource="story:episode-4",
            project_workspace="project:ep4",
            now=datetime(2026, 10, 5, 12, tzinfo=timezone.utc),
        )
        self.assertEqual(result.reason, "approval_required")

    def test_expired_grant_denied(self) -> None:
        result = authorize(
            self.grant(),
            actor_identity="agent:assistant",
            operation="story.scene.read",
            resource="story:episode-4",
            project_workspace="project:ep4",
            now=datetime(2026, 10, 6, 12, tzinfo=timezone.utc),
            approval_satisfied=True,
        )
        self.assertFalse(result.allowed)

    def test_subgrant_must_be_subset(self) -> None:
        parent = self.grant()
        child = self.grant()
        child["operations"] = ["story.scene.read"]
        self.assertTrue(subgrant_is_subset(parent, child))
        child["operations"] = ["project.delete"]
        self.assertFalse(subgrant_is_subset(parent, child))

    def test_full_user_authority_inheritance_is_invalid(self) -> None:
        grant = self.grant()
        grant["actor_inherits_full_delegator_authority"] = True
        self.assertIn("full_authority_inheritance_forbidden", validate_grant(grant))


if __name__ == "__main__":
    unittest.main()
