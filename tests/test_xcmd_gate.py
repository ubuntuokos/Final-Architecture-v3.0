import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import fa3_xcmd_gate as x

class XCmdGateTests(unittest.TestCase):
    def _copy_root(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        shutil.copytree(ROOT/"canonical",root/"canonical")
        return td,root
    def _write(self,p,obj):
        p.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    def test_baseline_gate_passes(self):
        r=x.gate(ROOT); self.assertEqual(r["result"],"PASS",r)
        self.assertEqual(r["regressions"]["passed"],12)
        self.assertEqual(r["authority_scan"]["result"],"PASS")
    def test_regression_matrix_12_of_12(self):
        r=x.run_regressions(); self.assertEqual(r["result"],"PASS",r)
        self.assertEqual((r["passed"],r["total"]),(12,12))
    def test_direct_remote_eval_denied(self):
        self.assertFalse(x.network_to_shell_allowed(downloaded_from_network=True,materialized=False,
            immutable_identity=False,integrity_verified=False,provenance_verified=False,
            policy_admitted=False,direct_eval_or_pipe=True))
    def test_floating_x_denied(self):
        self.assertFalse(x.immutable_reference_valid(ref="X",commit_sha=None))
        self.assertTrue(x.immutable_reference_valid(ref=x.REFERENCE_RELEASE,commit_sha=x.REFERENCE_COMMIT))
    def test_curated_package_is_not_trusted_by_curation_alone(self):
        self.assertFalse(x.package_trust_valid(curated=True,integrity_verified=False,
            provenance_verified=False,license_admitted=False,policy_admitted=False))
    def test_agent_shell_bypass_denied(self):
        self.assertFalse(x.agent_shell_execution_valid(caller_identity="agent",workspace_id="",
            capability_scope=["shell.*"],tool_mediation_authority="XCMD",policy_authority="XCMD",policy_admitted=True))
    def test_project_context_cannot_grant_authority(self):
        self.assertFalse(x.project_context_valid(trust_class="TRUSTED_POLICY",grants_authority=True))
    def test_self_update_floating_production_denied(self):
        self.assertFalse(x.self_update_allowed(production=True,explicit_external_authorization=False,
            immutable_target=False,post_change_evidence=False,floating_upgrade=True))
    def test_global_mutation_without_external_authorization_denied(self):
        self.assertFalse(x.global_host_mutation_allowed(global_mutation=True,external_authorization=False,change_evidence=False))
    def test_xcmd_authority_assignment_scan_fails_closed(self):
        td,root=self._copy_root()
        try:
            p=root/"canonical"/"xcmd-escalation.json"
            self._write(p,{"schema":"fa3.test.v1","id":"T","model_routing_authority":x.PROVIDER_ID})
            self.assertEqual(x.scan_canonical_authority_assignments(root)["result"],"FAIL")
        finally: td.cleanup()
    def test_provider_authority_drift_denied(self):
        td,root=self._copy_root()
        try:
            p=root/"canonical/providers/FA3-PROVIDER-XCMD-001.json"; o=json.loads(p.read_text())
            o["architectural_authority"]=True; self._write(p,o)
            self.assertEqual(x.gate(root)["result"],"FAIL")
        finally: td.cleanup()
    def test_policy_binding_required(self):
        td,root=self._copy_root()
        try:
            p=root/"canonical/enforcement-policy.json"; o=json.loads(p.read_text())
            o["mandatory_reference_gates"]=[]; self._write(p,o); r=x.gate(root)
            self.assertEqual(r["result"],"FAIL")
            self.assertTrue(any(f["code"]=="XCMD-REF-011" for f in r["reference"]["findings"]))
        finally: td.cleanup()
    def test_execution_evidence_requires_artifact_identity(self):
        e={"caller_identity":"a","request_id":"r","workspace_id":"w","capability_scope":["tool"],
           "policy_decision_id":"p","result_status":"PASS"}
        self.assertFalse(x.execution_evidence_valid(e))

if __name__=="__main__":
    unittest.main()
