import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_skill_fabric_gate import gate,good_package,good_use_receipt,package_admission_allowed,skill_use_allowed
from fa3_skill_execution_closure import good_execution_binding,good_execution_receipt,execution_binding_allowed,execution_receipt_allowed
class SkillFabricGateTests(unittest.TestCase):
    def test_gate(self):
        r=gate(ROOT);self.assertEqual(r["result"],"PASS");self.assertGreaterEqual(r["regressions"]["total"],45)
    def test_valid_package_and_use(self):
        self.assertTrue(package_admission_allowed(good_package()));self.assertTrue(skill_use_allowed(good_use_receipt()))
    def test_v13_package_requirements_fail_closed(self):
        p=good_package();p.pop("interface");self.assertFalse(package_admission_allowed(p))
        p=good_package();p["context_budget"]["references_used_tokens"]=p["context_budget"]["references_max_tokens"]+1;self.assertFalse(package_admission_allowed(p))
        p=good_package();p["activation_preview"]["side_effects_performed"]=True;self.assertFalse(package_admission_allowed(p))
    def test_execution_closure_positive(self):
        b=good_execution_binding();r=good_execution_receipt()
        self.assertTrue(execution_binding_allowed(b));self.assertTrue(execution_receipt_allowed(b,r))
    def test_execution_closure_bypasses_fail_closed(self):
        b=good_execution_binding();b["bypass"]["direct_model_provider"]=True;self.assertFalse(execution_binding_allowed(b))
        b=good_execution_binding();b["runtime"]["unsandboxed_execution"]=True;self.assertFalse(execution_binding_allowed(b))
        b=good_execution_binding();b["safety"]["coexistence_result"]="PENDING";self.assertFalse(execution_binding_allowed(b))
    def test_execution_receipt_requires_cleanup_and_physical_truth(self):
        b=good_execution_binding();r=good_execution_receipt();r["cleanup"]["worker_gone"]=False;self.assertFalse(execution_receipt_allowed(b,r))
        r=good_execution_receipt();r["current_host"].update({"claim":True,"status":"CURRENT_HOST_PASS","physical_evidence_ref":None});self.assertFalse(execution_receipt_allowed(b,r))
if __name__=="__main__":unittest.main()
