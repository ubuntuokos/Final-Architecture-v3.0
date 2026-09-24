import json, tempfile, unittest
from pathlib import Path
from fa3_model_router_provider_execution_current_host_gate import REQUIRED_CHECKS

ROOT=Path(__file__).resolve().parents[1]

class CurrentHostReceiptContractTests(unittest.TestCase):
    def test_required_matrix_contains_rollback_and_negative_boundaries(self):
        self.assertIn("rollback_pass",REQUIRED_CHECKS)
        self.assertIn("unadmitted_provider_denied_pass",REQUIRED_CHECKS)
        self.assertIn("cross_provider_silent_fallback_denied_pass",REQUIRED_CHECKS)
        self.assertIn("raw_secret_absent_from_evidence_pass",REQUIRED_CHECKS)
        self.assertIn("credential_authentication_enforced_pass",REQUIRED_CHECKS)
    def test_no_mock_semantic_in_required_checks(self):
        self.assertFalse(any("mock" in name or "synthetic" in name for name in REQUIRED_CHECKS))
    def test_real_producer_and_two_credential_contract_are_materialized(self):
        producer=(ROOT/"bin/fa3-model-router-provider-execution-current-host.py").read_text(encoding="utf-8")
        schema=json.loads((ROOT/"canonical/contracts/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-CONFIG-001.schema.json").read_text(encoding="utf-8"))
        self.assertIn("receipt_proves_provider",producer)
        self.assertIn("fa3-secretctl",producer)
        self.assertIn("credential_authentication_enforced",producer)
        self.assertEqual(schema["properties"]["credentials"]["minItems"],2)
if __name__=="__main__": unittest.main()
