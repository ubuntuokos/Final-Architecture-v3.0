import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
import fa3_model_artifact_security_gate as g

class ModelArtifactSecurityGateTests(unittest.TestCase):
    def test_canonical_gate_passes(self):
        r=g.gate(ROOT)
        self.assertEqual("PASS",r["result"],r)
        self.assertEqual(g.GATE_ID,r["gate_id"])
        self.assertEqual(len(g.RULES),r["regression_cases"])
        self.assertEqual(143,r["capability_count"])
        self.assertFalse(r["current_host_runtime_promotion_claim"])

    def test_exact_regression_corpus_passes(self):
        r=g.run_regressions()
        self.assertEqual("PASS",r["result"],r)
        self.assertEqual(len(g.RULES),r["passed"])
        self.assertEqual(g.RULES,[x["invariant"] for x in r["cases"]])

    def test_safetensors_still_requires_security_admission(self):
        r=g._base_receipt(); self.assertTrue(g.admission_valid(r))
        r["artifact"]["trusted_because_safe_format"]=True
        self.assertFalse(g.admission_valid(r))

    def test_pickle_requires_three_specialist_scanners(self):
        r=g._base_receipt("LLM",dangerous=True); self.assertTrue(g.admission_valid(r))
        r["scanners"]=[x for x in r["scanners"] if x["scanner_id"]!="fickling"]
        self.assertFalse(g.admission_valid(r))

    def test_scanner_error_and_skip_fail_closed(self):
        for status in ("ERROR","INCOMPLETE","SKIPPED","UNSUPPORTED"):
            r=g._base_receipt(); next(x for x in r["scanners"] if x["scanner_id"]=="modelaudit")["status"]=status
            self.assertFalse(g.admission_valid(r),status)

    def test_unpinned_remote_code_denied(self):
        r=g._base_receipt(); r["remote_code"]={"enabled":True,"exception":{"policy_authority":"FA3-AUTH-SECURITY-GOV-001","immutable_code_revision":"latest","code_sha256":"a"*64,"static_code_security_evidence":True,"network_denied_isolated_first_load":True,"policy_decision_id":"P1"}}
        self.assertFalse(g.admission_valid(r))

    def test_isolated_first_load_is_mandatory(self):
        r=g._base_receipt(); r["isolated_first_load"]["network_egress"]=True
        self.assertFalse(g.admission_valid(r))

    def test_garak_required_for_llm(self):
        r=g._base_receipt("LLM"); self.assertTrue(g.admission_valid(r))
        next(x for x in r["scanners"] if x["scanner_id"]=="garak")["status"]="SKIPPED"
        self.assertFalse(g.admission_valid(r))

    def test_scanner_cannot_be_promotion_authority(self):
        r=g._base_receipt(); r["security_attestation"]["scanner_output_is_authority"]=True
        self.assertFalse(g.admission_valid(r))

    def test_runtime_store_bypass_forbidden(self):
        r=g._base_receipt(); r["promotion"]["direct_runtime_store_download_bypass"]=True
        self.assertFalse(g.admission_valid(r))

    def test_reference_mutation_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in ("canonical","evidence"): shutil.copytree(ROOT/rel,root/rel)
            p=root/"canonical/model-artifact-security-enforcement.json"
            obj=json.loads(p.read_text()); obj["scanner_pass_is_promotion_authority"]=True; p.write_text(json.dumps(obj))
            rr=g.reference_check(root)
            self.assertEqual("FAIL",rr["result"])
            self.assertTrue(any(x["code"]=="MODEL-SEC-REF-015" for x in rr["findings"]))

if __name__=="__main__": unittest.main()
