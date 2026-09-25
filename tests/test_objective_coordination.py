from __future__ import annotations

import copy
import unittest

from fa3_objective_coordination import CoordinationContractError, compile_snapshot, deduplicate_events


def fixture():
    return {
        "schema": "fa3.objective-coordination.v1",
        "objective_id": "OBJ-001",
        "title": "Create a short video",
        "authority": False,
        "trace_context": {"correlation_id": "corr-001", "causation_id": "user-request-001"},
        "nodes": [
            {"node_id": "story", "kind": "WORK_ITEM", "state": "COMPLETED"},
            {"node_id": "voice", "kind": "WORKFLOW", "state": "PENDING"},
            {"node_id": "edit", "kind": "WORKFLOW", "state": "PENDING"},
        ],
        "dependencies": [
            {"upstream": "story", "downstream": "voice", "relation": "REQUIRES"},
            {"upstream": "voice", "downstream": "edit", "relation": "HANDOFF_AFTER"},
        ],
        "handoffs": [{
            "handoff_id": "voice-edit", "source_node": "voice", "target_node": "edit", "state": "PLANNED",
            "artifact_refs": ["artifact://audio/narration"], "provenance_refs": ["journal://event/voice-001"],
        }],
        "blockers": [],
    }


class ObjectiveCoordinationTests(unittest.TestCase):
    def test_ready_and_blocked_projection(self):
        result = compile_snapshot(fixture())
        self.assertEqual(result["ready_node_ids"], ["voice"])
        self.assertEqual(result["blocked_node_ids"], ["edit"])
        self.assertEqual(result["objective_state"], "ACTIVE")
        self.assertFalse(result["authority"])

    def test_cycle_fails_closed(self):
        payload = fixture()
        payload["dependencies"].append({"upstream": "edit", "downstream": "story", "relation": "REQUIRES"})
        with self.assertRaises(CoordinationContractError):
            compile_snapshot(payload)

    def test_authority_claim_fails_closed(self):
        payload = fixture()
        payload["allocate_resources"] = True
        with self.assertRaises(CoordinationContractError):
            compile_snapshot(payload)

    def test_missing_handoff_provenance_fails_closed(self):
        payload = fixture()
        payload["handoffs"][0]["provenance_refs"] = []
        with self.assertRaises(CoordinationContractError):
            compile_snapshot(payload)

    def test_received_handoff_still_waits_for_upstream_execution(self):
        payload = fixture()
        payload["handoffs"][0]["state"] = "RECEIVED"
        result = compile_snapshot(payload)
        self.assertNotIn("edit", result["ready_node_ids"])
        self.assertIn("edit", result["blocked_node_ids"])

    def test_downstream_becomes_ready_when_upstream_completed_and_handoff_received(self):
        payload = fixture()
        payload["nodes"][1]["state"] = "COMPLETED"
        payload["handoffs"][0]["state"] = "RECEIVED"
        result = compile_snapshot(payload)
        self.assertEqual(result["ready_node_ids"], ["edit"])

    def test_explicit_human_blocker(self):
        payload = fixture()
        payload["blockers"].append({
            "blocker_id": "approval-1", "target_node": "voice", "kind": "HUMAN_APPROVAL",
            "state": "OPEN", "reason": "voice approval required",
        })
        result = compile_snapshot(payload)
        self.assertNotIn("voice", result["ready_node_ids"])
        self.assertIn("voice", result["blocked_node_ids"])

    def test_identical_event_replay_is_noop(self):
        event = {
            "event_id": "evt-1", "event_type": "WORK_ITEM_OBSERVED", "correlation_id": "corr-001",
            "causation_id": "req-001", "source_ref": "work-item://1", "payload": {"state": "COMPLETED"},
        }
        result = deduplicate_events([event, copy.deepcopy(event)])
        self.assertEqual(len(result.accepted), 1)
        self.assertEqual(result.replayed_event_ids, ("evt-1",))

    def test_event_id_payload_mismatch_fails_closed(self):
        event = {
            "event_id": "evt-1", "event_type": "WORK_ITEM_OBSERVED", "correlation_id": "corr-001",
            "causation_id": None, "source_ref": "work-item://1", "payload": {"state": "COMPLETED"},
        }
        changed = copy.deepcopy(event)
        changed["payload"]["state"] = "FAILED"
        with self.assertRaises(CoordinationContractError):
            deduplicate_events([event, changed])


if __name__ == "__main__":
    unittest.main()
