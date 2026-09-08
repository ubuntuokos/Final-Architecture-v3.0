import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fa3_xcmd_current_host import *


def good_receipt():
    return {
      "schema":"fa3.xcmd-current-host-receipt.v1","provider_id":PROVIDER_ID,"gate_id":GATE_ID,
      "candidate":{"tag":TAG,"commit":COMMIT,"tree":TREE},
      "source":{"commit_revalidated":True,"tree_revalidated":True},
      "caller":{"identity":"github:actor"},"request_id":"run:1","workspace_id":"ws:1","capability_scope":[CAPABILITY],
      "policy":{"authorization_authority":"FA3-AUTH-SECURITY-GOV-001","tool_mediation_authority":"FA3-AUTH-MCP-GATEWAY-001"},
      "runner":{"labels":["self-hosted","linux","x64","fa3-current-host"]},
      "execution":{"root_execution":False,"direct_remote_eval":False,"self_update":False,"host_shell_startup_unchanged":True,"resident_provider_processes_after":0},
      "ci_fixture":False,"result_status":PASS_STATUS
    }

class ReceiptTests(unittest.TestCase):
    def test_positive(self): self.assertTrue(receipt_valid(good_receipt()))
    def test_floating_or_wrong_commit_denied(self):
        r=good_receipt(); r["candidate"]["commit"]="X"; self.assertFalse(receipt_valid(r))
    def test_wrong_tree_denied(self):
        r=good_receipt(); r["candidate"]["tree"]="0"*40; self.assertFalse(receipt_valid(r))
    def test_missing_caller_denied(self):
        r=good_receipt(); r["caller"]["identity"]=""; self.assertFalse(receipt_valid(r))
    def test_wrong_capability_denied(self):
        r=good_receipt(); r["capability_scope"]=["CAP-001"]; self.assertFalse(receipt_valid(r))
    def test_wrong_policy_authority_denied(self):
        r=good_receipt(); r["policy"]["authorization_authority"]="XCMD"; self.assertFalse(receipt_valid(r))
    def test_wrong_tool_mediation_denied(self):
        r=good_receipt(); r["policy"]["tool_mediation_authority"]="XCMD"; self.assertFalse(receipt_valid(r))
    def test_root_execution_denied(self):
        r=good_receipt(); r["execution"]["root_execution"]=True; self.assertFalse(receipt_valid(r))
    def test_remote_eval_denied(self):
        r=good_receipt(); r["execution"]["direct_remote_eval"]=True; self.assertFalse(receipt_valid(r))
    def test_self_update_denied(self):
        r=good_receipt(); r["execution"]["self_update"]=True; self.assertFalse(receipt_valid(r))
    def test_shell_startup_mutation_denied(self):
        r=good_receipt(); r["execution"]["host_shell_startup_unchanged"]=False; self.assertFalse(receipt_valid(r))
    def test_resident_process_denied(self):
        r=good_receipt(); r["execution"]["resident_provider_processes_after"]=1; self.assertFalse(receipt_valid(r))
    def test_fixture_cannot_claim_pass(self):
        r=good_receipt(); r["ci_fixture"]=True; self.assertFalse(receipt_valid(r))
    def test_missing_runner_label_denied(self):
        r=good_receipt(); r["runner"]["labels"]=["self-hosted","linux","x64"]; self.assertFalse(receipt_valid(r))
    def test_source_revalidation_required(self):
        r=good_receipt(); r["source"]["tree_revalidated"]=False; self.assertFalse(receipt_valid(r))

if __name__ == "__main__": unittest.main()
