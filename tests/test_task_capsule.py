from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_task_capsule import promotion_eligible, speculative_result_can_commit, validate_capsule


class TaskCapsuleTests(unittest.TestCase):
    def capsule(self) -> dict:
        return {
            "capsule_id": "capsule:weekly-cost-dashboard",
            "application_id": "fa3.finance",
            "objective": "Build weekly production cost dashboard",
            "blueprint_ref": "blueprint:dashboard",
            "workload_task_ref": "workload:1",
            "workspace_ref": "workspace:film-a",
            "capability_grant_ref": "grant:1",
            "work_context_ref": "context:1",
            "lifecycle_state": "READY",
            "provenance_refs": ["journal:1"],
            "owns_application_authority": False,
            "owns_project_truth": False,
            "owns_task_truth": False,
            "owns_permission_authority": False,
            "owns_durable_workflow_authority": False,
            "capability_scope_expansion": False,
            "direct_tool_bypass": False,
            "embedded_secret_values": False,
        }

    def test_capsule_is_non_authoritative_composition(self) -> None:
        self.assertTrue(validate_capsule(self.capsule()).ok)

    def test_capsule_cannot_expand_permission_scope(self) -> None:
        value = self.capsule()
        value["capability_scope_expansion"] = True
        self.assertFalse(validate_capsule(value).ok)

    def test_speculative_result_needs_explicit_commit_path(self) -> None:
        self.assertFalse(speculative_result_can_commit(
            approval_satisfied=False, uaf_authorized=True, canonical_target_authorized=True
        ))
        self.assertTrue(speculative_result_can_commit(
            approval_satisfied=True, uaf_authorized=True, canonical_target_authorized=True
        ))

    def test_promotion_requires_all_reviews(self) -> None:
        review = {
            "functional_reuse": True,
            "security": True,
            "license_rights": True,
            "capability_compatibility": True,
            "gui_compatibility": True,
            "application_compatibility_propagation": True,
            "test_and_rollback": True,
        }
        self.assertTrue(promotion_eligible(review, "APPLICATION"))
        review["security"] = False
        self.assertFalse(promotion_eligible(review, "APPLICATION"))


if __name__ == "__main__":
    unittest.main()
