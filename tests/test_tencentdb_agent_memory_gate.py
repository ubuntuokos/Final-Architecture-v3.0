import json,shutil,tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
import fa3_tencentdb_agent_memory_gate as t
class TencentDBAgentMemoryGateTests(unittest.TestCase):
 def _copy(self):
  td=tempfile.TemporaryDirectory();r=Path(td.name);shutil.copytree(ROOT/"canonical",r/"canonical");shutil.copytree(ROOT/"evidence",r/"evidence");return td,r
 def test_baseline_gate_passes(self):
  r=t.gate(ROOT);self.assertEqual("PASS",r["result"],r);self.assertEqual((30,30),(r["regressions"]["passed"],r["regressions"]["total"]))
 def test_all_30_regressions(self):
  r=t.run_regressions();self.assertEqual("PASS",r["result"],r);self.assertEqual(30,len({x["rule_id"] for x in r["cases"]}))
 def test_binding_scope_consent_fail_closed(self):
  self.assertFalse(t.binding_valid(False,True,True));self.assertFalse(t.scope_valid(None,False));self.assertFalse(t.durable_write_valid(True,False,True))
 def test_admin_and_ssrf_fail_closed(self):
  self.assertFalse(t.admin_auth_valid(True,False));self.assertFalse(t.empty_admin_key_valid(True,False,True));self.assertFalse(t.ssrf_valid(False,False,False,True))
 def test_license_and_hardware_fail_closed(self):
  self.assertFalse(t.license_valid(True,True,False));self.assertFalse(t.hrb_valid(False,False,True,True));self.assertFalse(t.accelerator_valid(False,False,None,None,True))
 def test_runtime_claim_blocked(self): self.assertFalse(t.promotion_valid(False,False,False,True))
 def test_provider_authority_drift_fails(self):
  td,r=self._copy()
  try:
   p=r/t.PATHS["provider"];o=json.loads(p.read_text());o["architectural_authority"]=True;p.write_text(json.dumps(o));self.assertEqual("FAIL",t.gate(r)["result"])
  finally:td.cleanup()
 def test_reference_evidence_not_runtime(self):
  e=json.loads((ROOT/t.PATHS["evidence"]).read_text());self.assertEqual("PASS",e["status"]);self.assertFalse(e["security_runtime_admission_pass"]);self.assertFalse(e["license_runtime_admission_pass"]);self.assertFalse(e["current_host_provider_runtime_evidence"])
if __name__=="__main__":unittest.main()
