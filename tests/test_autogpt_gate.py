import json,shutil,tempfile,unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import fa3_autogpt_gate as a

class AutoGPTGateTests(unittest.TestCase):
 def _copy(self):
  td=tempfile.TemporaryDirectory();root=Path(td.name);shutil.copytree(ROOT/"canonical",root/"canonical");return td,root
 def _write(self,p,o): p.write_text(json.dumps(o,indent=2)+"\n",encoding="utf-8")
 def test_baseline_gate_passes(self):
  r=a.gate(ROOT);self.assertEqual(r["result"],"PASS",r);self.assertEqual((r["regressions"]["passed"],r["regressions"]["total"]),(17,17));self.assertEqual(r["authority_scan"]["result"],"PASS");self.assertFalse(r["runtime_provider_required"])
 def test_regression_matrix_17_of_17(self):
  r=a.run_regressions();self.assertEqual(r["result"],"PASS",r);self.assertEqual((r["passed"],r["total"]),(17,17))
 def test_graph_authorization_is_not_transitive(self):
  self.assertFalse(a.graph_node_authorization_valid(graph_authorized=True,node_authorized=False,capability_admitted=True))
 def test_delegated_capability_escalation_denied(self):
  self.assertFalse(a.delegated_capabilities_valid(["read"],["read","write"]))
 def test_credential_scope_widening_denied(self):
  self.assertFalse(a.credential_scope_narrowing_valid(["a"],["a"],["a"],["a","b"]))
 def test_trigger_without_authorization_denied(self):
  self.assertFalse(a.trigger_execution_valid(trigger_or_schedule_fired=True,authorization_admitted=False,capability_admitted=True))
 def test_marketplace_adoption_not_trust(self):
  self.assertFalse(a.marketplace_admission_valid(adopted=True,artifact_trust_pass=False,policy_admitted=True))
 def test_platform_license_requires_explicit_admission(self):
  self.assertFalse(a.license_admission_valid(component="autogpt_platform",explicit_license_admission=False))
  self.assertTrue(a.license_admission_valid(component="classic",explicit_license_admission=False))
 def test_floating_master_denied(self):
  self.assertFalse(a.immutable_reference_valid(ref="master",commit_sha=None))
  self.assertTrue(a.immutable_reference_valid(ref=a.REFERENCE_RELEASE,commit_sha=a.REFERENCE_RELEASE_COMMIT))
 def test_authority_assignment_scan_fails_closed(self):
  td,root=self._copy()
  try:
   self._write(root/"canonical"/"autogpt-escalation.json",{"schema":"fa3.test.v1","id":"T","provider_id":a.PROVIDER_ID,"model_routing_authority":a.PROVIDER_ID})
   self.assertEqual(a.scan_canonical_authority_assignments(root)["result"],"FAIL")
  finally: td.cleanup()
 def test_provider_authority_drift_denied(self):
  td,root=self._copy()
  try:
   p=root/"canonical/providers/FA3-PROVIDER-AUTOGPT-001.json";o=json.loads(p.read_text());o["architectural_authority"]=True;self._write(p,o)
   self.assertEqual(a.gate(root)["result"],"FAIL")
  finally: td.cleanup()
 def test_policy_binding_required(self):
  td,root=self._copy()
  try:
   p=root/"canonical/enforcement-policy.json";o=json.loads(p.read_text());o["mandatory_reference_gates"]=[x for x in o["mandatory_reference_gates"] if x!=a.GATE_ID];self._write(p,o)
   r=a.gate(root);self.assertEqual(r["result"],"FAIL");self.assertTrue(any(x["code"]=="AUTOGPT-REF-007" for x in r["reference"]["findings"]))
  finally: td.cleanup()
 def test_runtime_admission_is_fail_closed_and_not_promoted(self):
  o=json.loads((ROOT/"canonical/autogpt-runtime-admission.json").read_text());self.assertEqual(o["status"],"NOT_ADMITTED");self.assertTrue(o["fail_closed"]);self.assertTrue(o["current_host_evidence_required"]);self.assertTrue(o["license_admission_required"])
 def test_reference_is_not_promotion_evidence(self):
  o=json.loads((ROOT/"canonical/references/FA3-AUTOGPT-UPSTREAM-REFERENCE-2026-08-30.json").read_text());self.assertFalse(o["promotion_evidence"]);self.assertFalse(o["floating_master_allowed_as_promotion_evidence"]);self.assertEqual(o["latest_release_commit"],a.REFERENCE_RELEASE_COMMIT)
if __name__=="__main__": unittest.main()
