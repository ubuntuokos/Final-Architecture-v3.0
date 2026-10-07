from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_application_handoff import can_dispatch_effect, correlate, validate_handoff


class ApplicationHandoffTests(unittest.TestCase):
    def request(self) -> dict:
        return {
            "message_id": "msg:1",
            "kind": "OPERATION_REQUEST",
            "source_application": "fa3.story-screenplay",
            "target_application": "fa3.video-editor",
            "correlation_id": "corr:scene-24",
            "operation_ref": "video.sequence.import_story_scene",
            "work_context_ref": "context:scene-24",
            "capability_grant_ref": "grant:handoff-1",
            "provenance_refs": ["journal:msg-1"],
            "handoff_is_authorization": False,
            "sender_expands_receiver_scope": False,
        }

    def test_handoff_does_not_authorize_by_itself(self) -> None:
        value = self.request()
        self.assertTrue(validate_handoff(value).ok)
        self.assertFalse(can_dispatch_effect(value, grant_valid=False, uaf_action_resolved=True))
        self.assertTrue(can_dispatch_effect(value, grant_valid=True, uaf_action_resolved=True))

    def test_sender_cannot_expand_receiver_scope(self) -> None:
        value = self.request()
        value["sender_expands_receiver_scope"] = True
        self.assertFalse(validate_handoff(value).ok)

    def test_artifact_handoff_requires_provenance(self) -> None:
        value = self.request()
        value["kind"] = "ARTIFACT_HANDOFF"
        value["artifact_refs"] = ["artifact:story-scene-24"]
        value["provenance_preserved"] = False
        self.assertFalse(validate_handoff(value).ok)
        value["provenance_preserved"] = True
        self.assertTrue(validate_handoff(value).ok)

    def test_intermediate_result_not_canonical_commit(self) -> None:
        value = self.request()
        value["kind"] = "INTERMEDIATE_RESULT"
        value["canonical_commit"] = True
        self.assertFalse(validate_handoff(value).ok)

    def test_correlation(self) -> None:
        a = self.request()
        b = dict(a, message_id="msg:2")
        c = dict(a, message_id="msg:3", correlation_id="other")
        self.assertEqual(len(correlate([a, b, c], "corr:scene-24")), 2)


if __name__ == "__main__":
    unittest.main()
