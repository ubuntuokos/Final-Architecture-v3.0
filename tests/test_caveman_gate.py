import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import fa3_caveman_gate as c

class CavemanGateTests(unittest.TestCase):
    def test_baseline_gate_passes(self):
        r=c.gate(ROOT)
        self.assertEqual(r["result"],"PASS",r)
        self.assertEqual((r["regressions"]["passed"],r["regressions"]["total"]),(15,15))
        self.assertEqual(r["authority_scan"]["result"],"PASS")
        self.assertEqual(r["current_host_runtime_evidence"],"NOT_CLAIMED")

    def test_regression_matrix(self):
        r=c.run_regressions()
        self.assertEqual(r["result"],"PASS",r)
        self.assertEqual((r["passed"],r["total"]),(15,15))

    def test_recovery_required_for_lossy(self):
        self.assertFalse(c.recovery_before_lossy_valid(lossy=True,recovery_persisted=False,recovery_handle=None,source_hash="h"))

    def test_original_is_immutable(self):
        self.assertFalse(c.canonical_original_preserved_valid(source_mutated=True))

    def test_failure_is_exact_passthrough(self):
        self.assertFalse(c.failure_passthrough_valid(transform_status="ERROR",input_payload=b"abc",output_payload=b"ab"))

    def test_benefit_threshold(self):
        self.assertFalse(c.measurable_benefit_valid(token_before=1000,token_after=999))

    def test_quality_gate(self):
        self.assertFalse(c.quality_gate_valid(lossy=True,semantic_fidelity_pass=True,task_success_pass=False))

    def test_measurement_class(self):
        self.assertFalse(c.measurement_provenance_valid(evidence_class="INFERRED",claimed_verified=True,provider_receipt_present=False))

    def test_baseline_before_active_mode(self):
        self.assertFalse(c.record_before_optimize_valid(mode="ACTIVE",baseline_recorded=False))

    def test_unknown_transform_passthrough(self):
        self.assertFalse(c.unsupported_no_transform_valid(supported=False,output_equals_input=False))

    def test_recovery_lineage(self):
        self.assertFalse(c.lineage_valid(source_artifact_id="a",source_sha256="h",projection_artifact_id="p",recovery_source_sha256="x",lossy=True))

    def test_recovery_storage_hardening(self):
        self.assertFalse(c.recovery_storage_valid(classification="SENSITIVE",file_mode=0o644,canonical_path_validated=True,symlink_rejected=True,retention_bounded=True,secret_policy_declared=True))

    def test_resource_bounds(self):
        self.assertFalse(c.bounded_resources_valid(input_bytes=129,max_input_bytes=128,recovery_bytes=1,max_recovery_bytes=128,retention_days=1,max_retention_days=30))

    def test_cache_classification(self):
        self.assertFalse(c.cache_classification_valid("UNKNOWN"))

    def test_semantic_rollback(self):
        self.assertFalse(c.semantic_rollback_valid(fidelity_pass=False,rollback_available=True,rolled_back=False))

    def test_telemetry_requires_authorization(self):
        self.assertFalse(c.telemetry_default_valid(explicitly_authorized=False,enabled=True))

if __name__=="__main__":
    unittest.main()
