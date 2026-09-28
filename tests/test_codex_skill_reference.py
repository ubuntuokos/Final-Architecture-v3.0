from __future__ import annotations
import json, shutil, tempfile, unittest
from dataclasses import replace
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import fa3_codex_adapter as codex
import fa3_developer_agent_coordination as dac
import tests.test_skill_signed_authority as signed
from fa3_codex_skill_reference import run_ci_skill_reference_e2e, build_reference_fixture
from fa3_skill_task_projection import SkillTaskPreflight

class CodexSkillConsumerTests(unittest.TestCase):
    def test_real_bytes_reach_fake_binary(self):
        report=run_ci_skill_reference_e2e()
        self.assertEqual(report["result"],"PASS",report)
        self.assertTrue(report["real_skill_bytes_consumed"])
        self.assertTrue(report["synthetic_codex_binary"])
        self.assertFalse(report["current_host_production_claim"])

    def test_reference_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory(prefix="fa3-codex-skill-negative-") as td:
            base=Path(td);repo=base/"repo";codex._init_repo(repo)
            fake=base/"codex";codex._write_fake_codex(fake)
            preflight,tasks=build_reference_fixture(base)
            runner=dac.Coordinator(repo,base/"control")
            with self.assertRaises(dac.CoordinationDenied):
                runner.run(tasks,codex.CodexAdapter(fake,timeout_seconds=60),
                           skill_preflight=preflight)
            self.assertEqual((repo/"work/a.txt").read_text(),"baseline\n")
            self.assertFalse((base/"control/results/CODEX-CI-A.json").exists())

    @unittest.skipUnless(shutil.which("openssl"),"openssl required")
    def test_real_signed_claims_reach_existing_codex_adapter(self):
        fixture=signed.SignedSkillAuthorityTests(
            methodName="test_full_signed_production_path_with_real_fixture_worker")
        fixture.setUp()
        try:
            binding,language,verifier=fixture._signed_binding()
            preflight=SkillTaskPreflight(
                {"example":binding},language,fixture.root,authority_verifier=verifier)
            fake=fixture.root/"codex";codex._write_fake_codex(fake)
            repo=fixture.root/"codex-repo";codex._init_repo(repo)
            task=replace(fixture.task,provider_id=codex.PROVIDER_ID)
            other=dac.AgentTask("TASK-2","agent-2",codex.PROVIDER_ID,
                                "work/b.txt","plain\n")
            result=dac.Coordinator(repo,fixture.root/"codex-control").run(
                [task,other],codex.CodexAdapter(fake,timeout_seconds=60),
                skill_preflight=preflight)
            self.assertEqual(result["status"],"PASS",result)
            row=json.loads((fixture.root/"codex-control/results/TASK-1.json").read_text())
            self.assertEqual(row["verified_skill_ids"],["example"])
            self.assertEqual(row["skill_evidence_scope"],
                             "PKI_AND_SECURITY_GOVERNANCE_SIGNED")
            self.assertIn("reasoning",row["event_summary"]["item_types"])
        finally:
            fixture.doCleanups()

if __name__=="__main__": unittest.main()
