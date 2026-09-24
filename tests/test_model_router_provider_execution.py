import unittest
from src.fa3_model_router_provider_execution import CredentialCandidate, ExecutionDenied, choose_credential, rebind_action, protocol_projection_status, execution_receipt
from src.fa3_model_router_provider_execution_gate import regressions

class ProviderExecutionTests(unittest.TestCase):
    def test_regression_matrix(self): self.assertEqual(regressions()["result"],"PASS")
    def test_session_affinity(self):
        rows=[CredentialCandidate("p","secretref:p/a","HEALTHY",True),CredentialCandidate("p","secretref:p/b","HEALTHY",True)]
        self.assertEqual(choose_credential(rows,provider_id="p",session_credential_ref="secretref:p/b").credential_ref,"secretref:p/b")
    def test_unadmitted_provider_is_not_eligible(self):
        with self.assertRaises(ExecutionDenied): choose_credential([CredentialCandidate("p","secretref:p/a","HEALTHY",False)],provider_id="p")
    def test_cross_provider_requires_router(self): self.assertEqual(rebind_action("QUOTA",False),"MODEL_ROUTER_REEVALUATION_REQUIRED")
    def test_security_schema_loss_fails_closed(self): self.assertEqual(protocol_projection_status(unsupported_fields={"pattern"},security_relevant_fields={"pattern"}),"UNSUPPORTED_FAIL_CLOSED")
    def test_receipt_redacts_reference(self):
        r=execution_receipt(CredentialCandidate("p","secretref:p/a","HEALTHY",True),logical_route="x",physical_model="y",selection_reason="z")
        self.assertNotIn("credential_ref",r); self.assertFalse(r["raw_credential_present"])
if __name__=="__main__": unittest.main()
