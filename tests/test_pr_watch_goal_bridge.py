"""PR Watch -> existing Goal/Workforce/AgentWorkload and evidence integration tests."""
import hashlib
import hmac
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from fa3_pr_watch import ProjectionStore, normalize_webhook, preview_goal_plan, preview_evidence, PRWatchDenied
from test_goal_execution_foundation import fixture, task, preflight, evidence

SECRET = b"FA3-test-exact-source-secret-bridge"
HEAD = "c" * 40


class GoalBridgeTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.store = ProjectionStore(Path(td.name) / "pr-watch")
        raw = json.dumps({
            "action": "opened",
            "repository": {"full_name": "ubuntuokos/Final-Architecture-v3.0"},
            "sender": {"login": "developer"},
            "pull_request": {
                "number": 10, "updated_at": "2026-09-28T18:00:00Z", "title": "Authorized fixture",
                "head": {"sha": HEAD}, "base": {"sha": "f" * 40},
            },
        }).encode()
        sig = "sha256=" + hmac.new(SECRET, raw, hashlib.sha256).hexdigest()
        self.event = normalize_webhook(raw, signature=sig, secret=SECRET,
                                       event_type="pull_request", delivery_id="bridge-test")
        self.store.ingest(self.event)
        self.item = self.store.operator_projection()["items"][0]
        self.p = {**preflight(), "source_sha": HEAD,
                  "repository_scope": "ubuntuokos/Final-Architecture-v3.0"}

    def test_exact_sha_proposal_routes_through_existing_workforce(self):
        result = preview_goal_plan(ROOT, self.item, fixture(), [task()], self.p)
        self.assertEqual("fa3.pr-watch-plan-preview.v1", result["schema"])
        self.assertFalse(result["authority"])
        self.assertFalse(result["execution_performed"])
        route = result["proposal"]["steps"][0]["design_route"]
        self.assertEqual("FA3-SPECIALIST-DURABLE-LIFECYCLE-001", route["specialist_id"])
        self.assertEqual("PENDING_EXISTING_AUTHORITIES",
                         result["proposal"]["steps"][0]["runtime_admission"])

    def test_forged_scope_or_moved_sha_blocks_plan(self):
        for changed in ({"source_sha": "a" * 40},
                        {"repository_scope": "attacker/different"}):
            with self.subTest(changed=changed):
                with self.assertRaises(PRWatchDenied):
                    preview_goal_plan(ROOT, self.item, fixture(), [task()], {**self.p, **changed})

    def test_independent_evidence_is_still_only_gate_candidate(self):
        incomplete = preview_evidence(fixture(), [])
        self.assertEqual("INCOMPLETE_OR_BLOCKED", incomplete["status"])
        candidate = preview_evidence(fixture(), evidence())
        self.assertEqual("CANONICAL_GATE_REQUIRED", candidate["status"])
        self.assertFalse(candidate["verification_claim"])
        self.assertTrue(candidate["canonical_gate_required"])


if __name__ == "__main__":
    unittest.main()
