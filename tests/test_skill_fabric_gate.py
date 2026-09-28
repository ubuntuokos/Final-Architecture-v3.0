import copy,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_skill_fabric_gate import gate,good_package,good_use_receipt,package_admission_allowed,skill_use_allowed,native_snapshot_findings
class SkillFabricGateTests(unittest.TestCase):
    def test_gate(self):
        r=gate(ROOT);self.assertEqual(r["result"],"PASS");self.assertGreaterEqual(r["regressions"]["total"],45)
    def test_valid_package_and_use(self):
        self.assertTrue(package_admission_allowed(good_package()));self.assertTrue(skill_use_allowed(good_use_receipt()))
    def test_v13_package_requirements_fail_closed(self):
        p=good_package();p.pop("interface");self.assertFalse(package_admission_allowed(p))
        p=good_package();p["context_budget"]["references_used_tokens"]=p["context_budget"]["references_max_tokens"]+1;self.assertFalse(package_admission_allowed(p))
        p=good_package();p["activation_preview"]["side_effects_performed"]=True;self.assertFalse(package_admission_allowed(p))
    def test_native_skill_hashes_and_tamper_denial(self):
        self.assertEqual(native_snapshot_findings(ROOT), [])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "canonical").mkdir()
            shutil.copy2(ROOT / "canonical/skill-registry.json", root / "canonical/skill-registry.json")
            shutil.copytree(ROOT / "skills", root / "skills")
            self.assertEqual(native_snapshot_findings(root), [])
            target = root / "skills/fa3-quality-ui/SKILL.md"
            target.write_bytes(target.read_bytes() + b"\nunauthorized-change\n")
            self.assertTrue(any("fa3-quality-ui" in finding
                                for finding in native_snapshot_findings(root)))

if __name__=="__main__":unittest.main()
