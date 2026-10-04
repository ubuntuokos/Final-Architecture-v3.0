from __future__ import annotations
import hashlib,json,tempfile,unittest
from pathlib import Path
from fa3_current_host_base_admission import admitted_state,build_candidate
class T(unittest.TestCase):
 def test_full_candidate_and_admitted_state(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td); (r/"reports").mkdir(); (r/"acceptance").mkdir(); (r/"evidence").mkdir()
   (r/".fa3-current-host/global-closure/host").mkdir(parents=True)
   payloads={
    "reports/current-host-evidence-audit.json":{"runtime_closure":"PASS","registry_pass_count":175,"registry_pending_count":0,"qualified_current_host_receipt_count":175},
    "acceptance/acceptance-report.json":{"status":"DENIED","criteria_passed":0,"criteria_total":19},
    "reports/current-host-capability-test-bundle-assembler.json":{"bundles_materialized":175},
    "reports/current-host-capability-attestation-producer.json":{"attestations_materialized":175},
    "reports/current-host-capability-handoff.json":{"receipts_materialized":175},
    "evidence/evidence-registry.json":{"canonical_capability_count":175},
    ".fa3-current-host/global-closure/host/host-fingerprint.json":{"host":"physical"},
   }
   for p,v in payloads.items():(r/p).write_text(json.dumps(v))
   c=build_candidate(r,"a"*40,"123"); self.assertEqual("FULL_175_525_PHYSICAL_PASS",c["status"])
   self.assertEqual(64,len(c["base_release_digest"]))
   s=admitted_state(c); self.assertEqual("CURRENT_HOST_BASE_ADMITTED",s["status"]); self.assertEqual(525,s["obligation_count"])
 def test_incomplete_full_closure_cannot_admit(self):
  bad={"schema":"fa3.current-host-base-admission-candidate.v1","status":"FULL_175_525_PHYSICAL_PASS","capability_count":175,"obligation_count":525,
       "release_acceptance_status":"DENIED","release_acceptance_criteria_passed":0,"release_acceptance_criteria_total":19,"release_acceptance_gates_current_host_base":False,"positive_negative_rollback_complete":False,
       "bundles_receipts_attestations_complete":True,"synthetic_current_host_pass":False,"source_commit":"a"*40,
       "base_release_digest":"b"*64,"host_fingerprint_sha256":"c"*64}
  with self.assertRaises(ValueError): admitted_state(bad)
if __name__=="__main__":unittest.main()
