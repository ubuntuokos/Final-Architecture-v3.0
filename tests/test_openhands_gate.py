import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import fa3_openhands_gate as o

class OpenHandsGateTests(unittest.TestCase):
    def _copy_root(self):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        shutil.copytree(ROOT/"canonical",root/"canonical")
        shutil.copytree(ROOT/"evidence",root/"evidence")
        return td,root

    def _write(self,path,obj):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")

    def test_baseline_gate_passes(self):
        report=o.gate(ROOT)
        self.assertEqual("PASS",report["result"],report)
        self.assertEqual((20,20),(report["regressions"]["passed"],report["regressions"]["total"]))
        self.assertEqual("PASS",report["authority_scan"]["result"])
        self.assertEqual(
            "PENDING_REAL_CURRENT_HOST_EXECUTION",
            report["current_host_provider_runtime_evidence"],
        )

    def test_all_20_positive_negative_regressions_pass(self):
        report=o.run_regressions()
        self.assertEqual("PASS",report["result"],report)
        self.assertEqual(20,len({case["rule_id"] for case in report["cases"]}))
        self.assertTrue(all(case["positive_case"] and case["negative_case"] for case in report["cases"]))

    def test_direct_execute_tool_bypass_denied(self):
        self.assertFalse(o.direct_execute_tool_valid(api="conversation.execute_tool",canonical_mediated=False))

    def test_unisolated_local_execution_without_admission_denied(self):
        self.assertFalse(o.local_unisolated_admission_valid(local_unisolated=True,explicit_admission=False,bounded_scope=False))

    def test_raw_secret_persistence_denied(self):
        self.assertFalse(o.secret_persistence_valid(raw_secret_values=["token"],secret_reference_handles=[],redacted=False))

    def test_floating_component_tuple_denied(self):
        bad={"commit":"main","openhands-sdk":"1.44.1","openhands-agent-server":"1.44.1","openhands-tools":"1.44.1","openhands-workspace":"1.44.1"}
        self.assertFalse(o.component_tuple_valid(bad))

    def test_provider_authority_drift_fails_closed(self):
        td,root=self._copy_root()
        try:
            path=root/o.PATHS["provider"]
            obj=json.loads(path.read_text(encoding="utf-8"))
            obj["architectural_authority"]=True
            self._write(path,obj)
            report=o.gate(root)
            self.assertEqual("FAIL",report["result"])
        finally:
            td.cleanup()

    def test_direct_authority_assignment_rejected_by_global_scan(self):
        td,root=self._copy_root()
        try:
            self._write(root/"canonical/openhands-authority-escalation.json",{"schema":"fa3.test.v1","workflow_authority":o.PROVIDER_ID})
            report=o.scan_canonical_authority_assignments(root)
            self.assertEqual("FAIL",report["result"])
            self.assertTrue(any(x["code"]=="OPENHANDS-AUTH-001" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_global_policy_binding_required(self):
        td,root=self._copy_root()
        try:
            path=root/o.PATHS["policy"]
            obj=json.loads(path.read_text(encoding="utf-8"))
            obj["mandatory_reference_gates"]=[x for x in obj["mandatory_reference_gates"] if x!=o.GATE_ID]
            self._write(path,obj)
            report=o.gate(root)
            self.assertEqual("FAIL",report["result"])
            self.assertTrue(any(x["code"]=="OPENHANDS-REF-011" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_reference_evidence_cannot_claim_current_host(self):
        evidence=json.loads((ROOT/o.PATHS["evidence"]).read_text(encoding="utf-8"))
        self.assertEqual("PASS",evidence["status"])
        self.assertFalse(evidence["current_host_provider_runtime_evidence"])
        self.assertFalse(evidence["current_host_runtime_promotion_claim"])
        self.assertFalse(evidence["production_provider_admission_claim"])

if __name__=="__main__":
    unittest.main()
