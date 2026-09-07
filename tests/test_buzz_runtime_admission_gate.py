import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_buzz_runtime_admission import AdmissionDenied, mutation_proposal, resolve_workspace_target
from fa3_buzz_runtime_admission_gate import CAPABILITY_COUNT, GATE_ID, P0_RULES, gate, regression_check

class BuzzRuntimeAdmissionGateTests(unittest.TestCase):
    def _copy_root(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        for rel in ("canonical","evidence/reference","src","tests","bin",".github/workflows","docs"):
            src=ROOT/rel
            if src.exists(): shutil.copytree(src,root/rel)
        return td,root
    def _load(self,root,rel): return json.loads((root/rel).read_text(encoding="utf-8"))
    def _write(self,root,rel,obj):
        path=root/rel; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    def test_baseline_gate_passes(self):
        report=gate(ROOT); self.assertEqual(report["result"],"PASS"); self.assertEqual(report["gate_id"],GATE_ID); self.assertEqual(report["regressions"]["passed"],26); self.assertEqual(report["p0_rule_count"],22); self.assertEqual(report["p0_rules"],P0_RULES); self.assertFalse(report["current_host_production_evidence"]); self.assertEqual(report["runtime_status"],"NOT_ADMITTED_PENDING_CURRENT_HOST"); self.assertEqual(report["capability_count"],CAPABILITY_COUNT)
    def test_regression_suite_is_exactly_26_of_26(self):
        report=regression_check(); self.assertEqual(report["result"],"PASS"); self.assertEqual(report["passed"],26); self.assertEqual(report["total"],26)
    def test_raw_buzz_dev_mcp_direct_route_is_denied(self):
        from fa3_buzz_runtime_admission import validate_runtime_route
        with self.assertRaises(AdmissionDenied): validate_runtime_route({"mcp_authority":"FA3-AUTH-MCP-GATEWAY-001","fa3_wrapper":True,"direct_buzz_dev_mcp":True,"workspace_containment":True,"capability_narrowing":True})
    def test_symlink_escape_is_denied(self):
        with tempfile.TemporaryDirectory() as td,tempfile.TemporaryDirectory() as outside:
            root=Path(td); outside_root=Path(outside); (outside_root/"secret").write_text("no",encoding="utf-8"); (root/"link").symlink_to(outside_root,target_is_directory=True)
            with self.assertRaises(AdmissionDenied): resolve_workspace_target(root,"link/secret")
    def test_diff_is_proposed_before_apply(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); target=root/"x.txt"; target.write_text("before\n",encoding="utf-8"); proposal=mutation_proposal(root,"x.txt",old_text="before",new_text="after"); self.assertTrue(proposal["proposed_diff"]); self.assertFalse(proposal["applied"]); self.assertEqual(target.read_text(encoding="utf-8"),"before\n")
    def test_provider_authority_escalation_fails(self):
        td,root=self._copy_root()
        try:
            rel="canonical/providers/FA3-PROVIDER-BUZZ-001.json"; obj=self._load(root,rel); obj["architectural_authority"]=True; self._write(root,rel,obj); self.assertEqual(gate(root)["result"],"FAIL")
        finally: td.cleanup()
    def test_raw_dev_mcp_policy_drift_fails(self):
        td,root=self._copy_root()
        try:
            rel="canonical/contracts/FA3-BUZZ-RUNTIME-ADMISSION-CONTRACTS-001.json"; obj=self._load(root,rel); obj["mcp_and_tool_boundary"]["raw_buzz_dev_mcp_direct_host_tool_provider"]="ALLOW"; self._write(root,rel,obj); self.assertEqual(gate(root)["result"],"FAIL")
        finally: td.cleanup()
    def test_document_only_current_host_promotion_fails(self):
        td,root=self._copy_root()
        try:
            rel="evidence/reference/buzz-runtime-admission-ci-2026-09-07.json"; obj=self._load(root,rel); obj["current_host_production_evidence"]=True; obj["current_host_runtime_status"]="CURRENT_HOST_PRODUCTION_E2E_PASS"; self._write(root,rel,obj); self.assertEqual(gate(root)["result"],"FAIL")
        finally: td.cleanup()
    def test_parent_binding_drift_fails(self):
        td,root=self._copy_root()
        try:
            rel="canonical/buzz-enforcement.json"; obj=self._load(root,rel); obj["child_gates"]=[]; self._write(root,rel,obj); self.assertEqual(gate(root)["result"],"FAIL")
        finally: td.cleanup()
    def test_permanent_workflow_binding_drift_fails(self):
        td,root=self._copy_root()
        try:
            path=root/".github/workflows/fa3-buzz-runtime-admission.yml"; path.write_text("name: broken\n",encoding="utf-8"); self.assertEqual(gate(root)["result"],"FAIL")
        finally: td.cleanup()
if __name__=="__main__": unittest.main()
