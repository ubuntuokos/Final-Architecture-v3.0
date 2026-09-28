import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_pr_watch_reference_e2e import fixture_e2e
from fa3_pr_watch_reference_checker import verify_fixture,EXPECTED
from fa3_developer_agent_coordination import _init_fixture_repo

class ReferenceE2ETests(unittest.TestCase):
    def test_real_isolated_worker_and_independent_checker(self):
        report=fixture_e2e()
        self.assertEqual("CI_REFERENCE_PASS_NOT_PRODUCTION",report["status"])
        self.assertEqual("PASS",report["checker"]["status"])
        self.assertEqual(2,report["worker_count"])
        self.assertTrue(report["separate_checker_process"])
        self.assertFalse(report["current_host_production_admitted"])

    def test_forced_base_as_integration_commit_denied(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/"repo";_init_fixture_repo(repo,{p:v.decode() for p,v in EXPECTED.items()})
            base=subprocess.run(["git","-C",str(repo),"rev-parse","HEAD"],
                capture_output=True,text=True,check=True).stdout.strip()
            x=verify_fixture(repo,base,base,hashlib.sha256(b"fixture").hexdigest())
            self.assertEqual("FAIL",x["status"])
            self.assertFalse(x["canonical_evidence_verified"])

    def test_tampered_fixture_workspace_denied(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/"repo";_init_fixture_repo(repo,{p:v.decode() for p,v in EXPECTED.items()})
            base=subprocess.run(["git","-C",str(repo),"rev-parse","HEAD"],
                capture_output=True,text=True,check=True).stdout.strip()
            (repo/"work/tests.txt").write_text("untrusted override\n")
            x=verify_fixture(repo,base,base,hashlib.sha256(b"fixture").hexdigest())
            self.assertEqual("FAIL",x["status"])

    def test_missing_repository_and_digest_fail(self):
        with tempfile.TemporaryDirectory() as td:
            x=verify_fixture(Path(td),"not-sha","not-sha","invalid")
            self.assertEqual("FAIL",x["status"])
            self.assertFalse(x["canonical_evidence_verified"])

if __name__=="__main__":unittest.main()
