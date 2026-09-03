import json,shutil,tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import fa3_video_provider_lifecycle_gate as v

class VideoProviderLifecycleGateTests(unittest.TestCase):
    def _copy(self):
        td=tempfile.TemporaryDirectory();r=Path(td.name)
        shutil.copytree(ROOT/"canonical",r/"canonical")
        shutil.copytree(ROOT/"evidence",r/"evidence")
        return td,r
    def test_baseline_gate_passes(self):
        r=v.gate(ROOT)
        self.assertEqual("PASS",r["result"],r)
        self.assertEqual((30,30),(r["regressions"]["passed"],r["regressions"]["total"]))
    def test_all_30_regressions_are_unique(self):
        r=v.run_regressions()
        self.assertEqual("PASS",r["result"],r)
        self.assertEqual(30,len({x["rule_id"] for x in r["cases"]}))
    def test_backend_and_fallback_fail_closed(self):
        self.assertFalse(v.backend_match_valid("cuda","cpu"))
        self.assertFalse(v.fallback_valid(False,False,True))
        self.assertFalse(v.accelerator_valid(False,None,None,True))
    def test_cache_invalidation_fail_closed(self):
        self.assertFalse(v.cache_invalidation_valid(True,False,False))
        self.assertFalse(v.cache_scope_valid(None,None,True))
        self.assertFalse(v.cache_recompute_valid(True,True,False))
    def test_open_sora_license_drift_blocks(self):
        self.assertTrue(v.open_sora_license_valid("MIT","Apache",True))
        self.assertFalse(v.open_sora_license_valid("MIT","Apache",False))
    def test_helios_low_vram_requires_host_preflight(self):
        self.assertTrue(v.low_vram_preflight_valid("~6GB",True,True,True))
        self.assertFalse(v.low_vram_preflight_valid("~6GB",False,False,False))
    def test_runtime_claim_without_evidence_fails(self):
        self.assertFalse(v.promotion_valid(False,False,False,False,False,False,True))
    def test_authority_drift_fails(self):
        td,r=self._copy()
        try:
            p=r/v.PATHS["helios"];o=json.loads(p.read_text());o["architectural_authority"]=True;p.write_text(json.dumps(o))
            self.assertEqual("FAIL",v.gate(r)["result"])
        finally: td.cleanup()
    def test_reference_evidence_is_not_runtime_promotion(self):
        e=json.loads((ROOT/v.PATHS["evidence"]).read_text())
        self.assertEqual("PASS",e["status"])
        self.assertFalse(e["current_host_provider_runtime_evidence"])
        self.assertFalse(e["production_provider_admission_claim"])

if __name__=="__main__": unittest.main()
