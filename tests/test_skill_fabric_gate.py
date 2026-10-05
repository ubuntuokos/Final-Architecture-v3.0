import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_skill_fabric_gate import gate,good_package,good_use_receipt,package_admission_allowed,skill_use_allowed
class SkillFabricGateTests(unittest.TestCase):
    def test_gate(self):
        r=gate(ROOT);self.assertEqual(r["result"],"PASS");self.assertGreaterEqual(r["regressions"]["total"],45)
    def test_valid_package_and_use(self):
        self.assertTrue(package_admission_allowed(good_package()));self.assertTrue(skill_use_allowed(good_use_receipt()))
    def test_v13_package_requirements_fail_closed(self):
        p=good_package();p.pop("interface");self.assertFalse(package_admission_allowed(p))
        p=good_package();p["context_budget"]["references_used_tokens"]=p["context_budget"]["references_max_tokens"]+1;self.assertFalse(package_admission_allowed(p))
        p=good_package();p["activation_preview"]["side_effects_performed"]=True;self.assertFalse(package_admission_allowed(p))
if __name__=="__main__":unittest.main()
