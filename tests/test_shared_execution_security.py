import unittest
from src.fa3_shared_execution_security import policy_subset, proof_allows_execution, security_level_satisfies, executable_identity_valid, execution_admitted

class SharedExecutionSecurityTests(unittest.TestCase):
    def test_policy_narrowing(self):
        self.assertTrue(policy_subset(["read"],["read","write"]))
        self.assertFalse(policy_subset(["read","network"],["read","write"]))
    def test_unproven_never_passes_when_proof_required(self):
        self.assertTrue(proof_allows_execution("PROVED",proof_required=True))
        self.assertFalse(proof_allows_execution("UNPROVEN",proof_required=True))
        self.assertFalse(proof_allows_execution("DENIED",proof_required=False))
    def test_security_level_no_silent_downgrade(self):
        self.assertTrue(security_level_satisfies(minimum="EXEC-SEC-L3",observed="EXEC-SEC-L4"))
        self.assertFalse(security_level_satisfies(minimum="EXEC-SEC-L3",observed="EXEC-SEC-L2"))
    def test_executable_digest_binding(self):
        self.assertTrue(executable_identity_valid(expected_sha256="a",observed_sha256="a"))
        self.assertFalse(executable_identity_valid(expected_sha256="a",observed_sha256="b"))
    def test_enforcer_loss_and_policy_expansion_fail_closed(self):
        common=dict(authorized_policy=["read"],requested_policy=["read"],proof_state="PROVED",proof_required=True,minimum_security_level="EXEC-SEC-L3",observed_security_level="EXEC-SEC-L3",authorization_valid=True,lease_valid=True,executable_digest_valid=True,enforcer_available=True)
        self.assertTrue(execution_admitted(**common))
        self.assertFalse(execution_admitted(**{**common,"enforcer_available":False}))
        self.assertFalse(execution_admitted(**{**common,"requested_policy":["read","network"]}))
if __name__=="__main__": unittest.main()
