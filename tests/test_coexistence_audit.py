import json, tempfile, unittest
from pathlib import Path
from fa3_coexistence_audit import audit

class CoexistenceAuditTests(unittest.TestCase):
    def fixture(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        (root/"canonical/decisions").mkdir(parents=True)
        (root/"canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json").write_text("{\"schema\":\"fa3.release-capability-baseline.v1\",\"id\":\"FA3-RELEASE-CAPABILITY-BASELINE-001\",\"baseline_semantics\":\"RELEASE_SCOPED\",\"current_release\":\"test/v3.1.0\",\"current_release_capability_count\":175,\"release_baselines\":[{\"release\":\"test/v3.1.0\",\"capability_count\":175,\"status\":\"ACTIVE_BASELINE\"}]}")
        (root/"canonical/intents").mkdir()
        (root/"canonical/providers").mkdir()
        (root/"canonical/coexistence/footprints").mkdir(parents=True)
        (root/"deployment/x").mkdir(parents=True)
        (root/"canonical/FA3-COEXISTENCE-POLICY-001.json").write_text(json.dumps({"capability_count":175,"capability_delta":0,"authority_delta":0}))
        (root/"canonical/decisions/FA3-DEC-SOFTWARE-COEXISTENCE-2026-09-26.json").write_text(json.dumps({"capability_count":175,"truth_boundary":{"static_pass_is_current_host_pass":False,"physical_current_host_evidence_required_for_runtime_pass":True}}))
        return td,root
    def test_detects_unnamespaced_service(self):
        td,root=self.fixture()
        try:
            (root/"deployment/x/upstream.service").write_text("[Service]\nExecStart=/bin/true\n")
            r=audit(root)
            self.assertEqual(r["static_result"],"FAIL")
            self.assertTrue(any(x["code"]=="COEX-020" for x in r["findings"]))
            self.assertEqual(r["capability_count"],175)
            self.assertFalse(r["runtime_promotion_claim"])
        finally: td.cleanup()
    def test_static_pass_never_promotes_runtime(self):
        td,root=self.fixture()
        try:
            r=audit(root)
            self.assertEqual(r["static_result"],"PASS")
            self.assertEqual(r["current_host_status"],"PENDING_CURRENT_HOST")
            self.assertFalse(r["runtime_promotion_claim"])
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main()
