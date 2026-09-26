import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_model_manager_gate import (
    CAPABILITY_COUNT,CAPABILITY_IDS,CANONICAL_STORE_ID,GATE_ID,PROFILE_ID,RULES,
    gate,reference_check,run_regressions,scan_canonical_authority_assignments,
)

class ModelManagerGateTests(unittest.TestCase):
    def _copy_root(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        for name in ("canonical","evidence"): shutil.copytree(ROOT/name,root/name)
        return td,root
    def _write(self,path,obj):
        path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    def test_baseline_gate_passes(self):
        report=gate(ROOT)
        self.assertEqual("PASS",report["result"],report)
        self.assertEqual(GATE_ID,report["gate_id"])
        self.assertEqual(PROFILE_ID,report["profile_id"])
        self.assertEqual(CANONICAL_STORE_ID,report["canonical_store_id"])
        self.assertEqual(list(CAPABILITY_IDS),report["capability_bindings"])
        self.assertEqual(CAPABILITY_COUNT,report["capability_count"])
        self.assertFalse(report["current_host_runtime_promotion_claim"])
    def test_exact_seventeen_regressions_pass(self):
        report=run_regressions()
        self.assertEqual("PASS",report["result"])
        self.assertEqual(17,report["passed"])
        self.assertEqual(17,report["total"])
        self.assertEqual(list(RULES),[x["invariant"] for x in report["cases"]])
    def test_canonical_store_cannot_become_architectural_authority(self):
        td,root=self._copy_root()
        try:
            self._write(root/"canonical/model-manager-authority-mutation.json",{"id":"TEST-MUTATION","model_routing_authority":CANONICAL_STORE_ID})
            scan=scan_canonical_authority_assignments(root)
            self.assertEqual("FAIL",scan["result"])
            self.assertTrue(any(x["code"]=="MODEL-MGR-AUTH-001" for x in scan["findings"]))
        finally: td.cleanup()
    def test_policy_rule_drift_fails_closed(self):
        td,root=self._copy_root()
        try:
            p=root/"canonical/enforcement-policy.json"; obj=json.loads(p.read_text(encoding="utf-8"))
            obj["model_manager_mandatory_p0_rules"]=obj["model_manager_mandatory_p0_rules"][:-1]; self._write(p,obj)
            report=reference_check(root)
            self.assertEqual("FAIL",report["result"])
            self.assertTrue(any(x["code"]=="MODEL-MGR-REF-016" for x in report["findings"]))
        finally: td.cleanup()
    def test_evidence_registry_binding_missing_fails_closed(self):
        td,root=self._copy_root()
        try:
            p=root/"evidence/evidence-registry.json"; obj=json.loads(p.read_text(encoding="utf-8"))
            rec=next(x for x in obj["records"] if x["subject_id"]=="CAP-005")
            rec["evidence_artifacts"]=[x for x in rec["evidence_artifacts"] if "model-manager" not in x]; self._write(p,obj)
            report=reference_check(root)
            self.assertEqual("FAIL",report["result"])
            self.assertTrue(any(x["code"]=="MODEL-MGR-REF-018" for x in report["findings"]))
        finally: td.cleanup()
    def test_projection_reconciliation_missing_fails_closed(self):
        td,root=self._copy_root()
        try:
            p=root/"canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"; obj=json.loads(p.read_text(encoding="utf-8"))
            obj.pop("model_manager_reconciliation",None); self._write(p,obj)
            report=reference_check(root)
            self.assertEqual("FAIL",report["result"])
            self.assertTrue(any(x["code"]=="MODEL-MGR-REF-019" for x in report["findings"]))
        finally: td.cleanup()

if __name__=="__main__": unittest.main()
