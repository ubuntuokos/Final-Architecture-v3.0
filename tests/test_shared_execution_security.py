"""Shared Execution Security canonical and semantics regressions."""
import json
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_shared_execution_security import DENIED,PROVED,UNPROVEN,credential_projection_valid,execution_admitted,prove_policy
from fa3_shared_execution_security_gate import gate

class SharedExecutionSecurityTests(unittest.TestCase):
    def test_gate_passes(self):
        self.assertEqual(gate(ROOT)["result"],"PASS")

    def test_policy_narrowing_and_unproven(self):
        b={"filesystem":["workspace:rw"],"network":["github.com"],"process":["python"],"mcp":["read_file"],"credentials":["lease"]}
        self.assertEqual(prove_policy(b,b),PROVED)
        self.assertEqual(prove_policy({**b,"network":["github.com","bad.invalid"]},b),DENIED)
        self.assertEqual(prove_policy(b,b,supported=False),UNPROVEN)

    def test_fail_closed_execution(self):
        base=dict(proof_state=PROVED,proof_required=True,executable_digest_matches=True,policy_revision_matches=True,
                  approval_valid=True,resource_leases_valid=True,secret_leases_valid=True,
                  actual_assurance="EXEC-SEC-L4",minimum_assurance="EXEC-SEC-L3",enforcer_alive=True)
        self.assertTrue(execution_admitted(**base))
        self.assertFalse(execution_admitted(**{**base,"proof_state":UNPROVEN}))
        self.assertFalse(execution_admitted(**{**base,"executable_digest_matches":False}))
        self.assertFalse(execution_admitted(**{**base,"enforcer_alive":False}))

    def test_raw_secret_exposure_denied(self):
        self.assertTrue(credential_projection_valid(raw_secret_exposed=False,endpoint_bound=True,operation_bound=True,lease_valid=True))
        self.assertFalse(credential_projection_valid(raw_secret_exposed=True,endpoint_bound=True,operation_bound=True,lease_valid=True))

    def test_openshell_usage_edge_is_pattern_only(self):
        d=json.loads((ROOT/"canonical/FA3-APPLICATION-DONOR-LINKS-001.json").read_text())
        u=[x for x in d["donor_usage_records"] if x["id"]=="FA3-USAGE-NVIDIA-OPENSHELL-EXECUTION-SECURITY-001"]
        self.assertEqual(len(u),1)
        self.assertEqual(u[0]["usage_kind"],"ARCHITECTURE_PATTERN")
        self.assertEqual(u[0]["current_host_impact"]["classification"],"RUNTIME_REQUALIFICATION_REQUIRED")

if __name__=="__main__": unittest.main()
