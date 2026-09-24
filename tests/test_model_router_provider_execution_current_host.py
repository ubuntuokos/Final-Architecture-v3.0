import json, tempfile, unittest
from pathlib import Path
from fa3_model_router_provider_execution_current_host_gate import REQUIRED_CHECKS

class CurrentHostReceiptContractTests(unittest.TestCase):
    def test_required_matrix_contains_rollback_and_negative_boundaries(self):
        self.assertIn("rollback_pass",REQUIRED_CHECKS)
        self.assertIn("unadmitted_provider_denied_pass",REQUIRED_CHECKS)
        self.assertIn("cross_provider_silent_fallback_denied_pass",REQUIRED_CHECKS)
        self.assertIn("raw_secret_absent_from_evidence_pass",REQUIRED_CHECKS)
    def test_no_mock_semantic_in_required_checks(self):
        self.assertFalse(any("mock" in name or "synthetic" in name for name in REQUIRED_CHECKS))
if __name__=="__main__": unittest.main()
