import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_integration_broker as b
import fa3_integration_broker_gate as g


class IntegrationBrokerTests(unittest.TestCase):
    def _proposal(self):
        proposal = {
            "schema": b.PROPOSAL_SCHEMA,
            "proposal_id": "prop-20260919-123",
            "origin_agent": "FA3-PROVIDER-TEST-001",
            "context": {
                "task_scope": "test",
                "target_capability": "CAP-028",
                "base_commit": "a" * 40,
                "declared_write_set": ["docs/x.txt"],
                "test_plan": ["static gate"],
            },
            "approval_state": {
                "status": b.APPROVED,
                "approved_by": "human",
                "approved_at": "2026-09-19T00:00:00Z",
                "approved_base_sha": "a" * 40,
                "proposal_digest_sha256": "sha256:" + "0" * 64,
            },
            "mutations": [{
                "file_path": "docs/x.txt",
                "diff": "diff --git a/docs/x.txt b/docs/x.txt\n--- a/docs/x.txt\n+++ b/docs/x.txt\n@@ -1 +1 @@\n-a\n+b\n",
            }],
            "circuit_breaker_limits": {
                "max_execution_seconds": 300,
                "max_file_mutations": 1,
            },
        }
        proposal["approval_state"]["proposal_digest_sha256"] = b.proposal_digest(proposal)
        return proposal

    def test_digest_binds_approved_content(self):
        proposal = self._proposal()
        self.assertTrue(b.validate_approval(proposal)[0])
        proposal["context"]["task_scope"] = "tampered"
        self.assertFalse(b.validate_approval(proposal)[0])

    def test_protected_gate_self_modification_denied(self):
        self.assertTrue(b.protected_path("bin/fa3-enforce"))
        self.assertTrue(b.protected_path("canonical/schemas/agent-task-proposal.v1.json"))
        self.assertFalse(b.protected_path("docs/allowed.md"))

    def test_patch_path_must_equal_declared_path(self):
        proposal = self._proposal()
        proposal["mutations"][0]["file_path"] = "docs/y.txt"
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(b.IntegrationDenied):
                b.validate_mutations(Path(td), proposal)

    def test_path_traversal_denied(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(b.IntegrationDenied):
                b.normalize_repo_path(Path(td), "../escape")

    def test_reference_e2e_passes_and_keeps_proposal_immutable(self):
        report = g.run_reference_e2e()
        self.assertEqual("PASS", report["result"], report)
        self.assertTrue(report["positive_flow"]["pr_ready"])
        self.assertTrue(report["positive_flow"]["main_unchanged"])
        self.assertTrue(report["positive_flow"]["proposal_immutable"])
        self.assertTrue(all(report["negative_cases"].values()))

    def test_global_gate_passes(self):
        report = g.gate(ROOT)
        self.assertEqual("PASS", report["result"], report)


if __name__ == "__main__":
    unittest.main()
