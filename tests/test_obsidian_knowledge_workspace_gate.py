import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_obsidian_knowledge_workspace_gate as obsidian


class ObsidianKnowledgeWorkspaceGateTests(unittest.TestCase):
    def _copy(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence", root / "evidence")
        return temporary, root

    def test_baseline_gate_passes(self):
        report = obsidian.gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual((32, 32), (report["regressions"]["passed"], report["regressions"]["total"]))
        self.assertFalse(report["current_host_runtime_promotion_claim"])
        self.assertFalse(report["local_rest_mcp_adapter_admitted"])

    def test_all_positive_and_negative_regressions_pass(self):
        report = obsidian.run_regressions()
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(32, len({case["rule_id"] for case in report["cases"]}))

    def test_draft_private_and_missing_metadata_fail_closed(self):
        good = {"id": "n-1", "type": "architecture", "status": "approved", "owner": "human", "visibility": "agent-read", "index": True, "source": "human", "created": "2026-09-07", "updated": "2026-09-07", "tags": []}
        self.assertTrue(obsidian.index_admission_valid(good))
        self.assertFalse(obsidian.index_admission_valid({**good, "status": "draft"}))
        self.assertFalse(obsidian.index_admission_valid({**good, "visibility": "private"}))
        del good["id"]
        self.assertFalse(obsidian.index_admission_valid(good))

    def test_direct_agent_routes_and_symlink_escape_fail_closed(self):
        self.assertFalse(obsidian.retrieval_valid("DIRECT_OBSIDIAN_MCP", False, True, True))
        self.assertFalse(obsidian.retrieval_valid("DIRECT_FILESYSTEM", True, False, True))
        self.assertFalse(obsidian.vault_scope_valid(True, True, True, "APPROVED_VAULT_ROOT"))

    def test_unreviewed_or_conflicting_mutation_fails_closed(self):
        args = dict(staging="_agent-inbox/<proposal_id>/", human_review=True, receipt=True, compare_and_swap=True, destructive_default="DENY")
        self.assertTrue(obsidian.mutation_valid(**args))
        self.assertFalse(obsidian.mutation_valid(**{**args, "human_review": False}))
        self.assertFalse(obsidian.mutation_valid(**{**args, "compare_and_swap": False}))
        self.assertFalse(obsidian.mutation_valid(**{**args, "destructive_default": "ALLOW"}))

    def test_plugin_requires_separate_acceptance_verified_tls_and_gateway(self):
        self.assertTrue(obsidian.plugin_valid(False, True, True, True, False, True, False))
        self.assertTrue(obsidian.plugin_valid(True, True, True, True, False, True, False))
        self.assertFalse(obsidian.plugin_valid(True, False, True, True, False, True, False))
        self.assertFalse(obsidian.plugin_valid(True, True, True, False, True, True, False))
        self.assertFalse(obsidian.plugin_valid(True, True, True, True, False, False, True))

    def test_provider_authority_drift_fails(self):
        temporary, root = self._copy()
        try:
            path = root / obsidian.PATHS["desktop_provider"]
            value = json.loads(path.read_text())
            value["architectural_authority"] = True
            path.write_text(json.dumps(value))
            self.assertEqual("FAIL", obsidian.gate(root)["result"])
        finally:
            temporary.cleanup()

    def test_runtime_claim_without_e2e_is_rejected(self):
        self.assertTrue(obsidian.promotion_valid(True, False, False))
        self.assertFalse(obsidian.promotion_valid(True, False, True))


if __name__ == "__main__":
    unittest.main()
