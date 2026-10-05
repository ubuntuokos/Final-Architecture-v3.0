from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_application_runtime_lifecycle import can_transition, evaluate_transition, runtime_states


class ApplicationRuntimeLifecycleTests(unittest.TestCase):
    def base(self, current: str, requested: str) -> dict:
        return {
            "application_id": "fa3.story-screenplay",
            "current_state": current,
            "requested_state": requested,
            "actor_identity": "user:1",
            "operation_ref": "application.lifecycle.transition",
            "authorization_decision": "ALLOW",
            "source_revision": "rev:1",
            "provenance_refs": ["journal:1"],
        }

    def test_existing_installed_state_enters_runtime_lifecycle(self) -> None:
        self.assertTrue(can_transition("INSTALLED", "READY"))
        self.assertTrue(can_transition("INSTALLED", "CONFIGURING"))

    def test_running_suspend_requires_declared_support(self) -> None:
        request = self.base("RUNNING", "SUSPENDING")
        self.assertTrue(evaluate_transition(request).allowed)
        request = self.base("SUSPENDING", "SUSPENDED")
        request["suspend_supported"] = False
        self.assertFalse(evaluate_transition(request).allowed)
        request["suspend_supported"] = True
        self.assertTrue(evaluate_transition(request).allowed)

    def test_resume_requires_fresh_resource_admission(self) -> None:
        request = self.base("SUSPENDED", "RESUMING")
        request["runtime_resources_required"] = True
        request["fresh_resource_admission"] = False
        self.assertFalse(evaluate_transition(request).allowed)
        request["fresh_resource_admission"] = True
        self.assertTrue(evaluate_transition(request).allowed)

    def test_update_cannot_promote_without_evidence(self) -> None:
        request = self.base("UPDATING", "READY")
        self.assertFalse(evaluate_transition(request).allowed)
        request["update_evidence_pass"] = True
        self.assertTrue(evaluate_transition(request).allowed)

    def test_invalid_transition_fails_closed(self) -> None:
        self.assertFalse(evaluate_transition(self.base("RUNNING", "READY")).allowed)

    def test_expected_runtime_states_exist(self) -> None:
        for state in ("RUNNING", "SUSPENDED", "STOPPED", "ROLLING_BACK", "REMOVED", "FAILED"):
            self.assertIn(state, runtime_states())


if __name__ == "__main__":
    unittest.main()
