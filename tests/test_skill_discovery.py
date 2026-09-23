import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_skill_discovery import fingerprint,eligible_skill_ids
class SkillDiscoveryTests(unittest.TestCase):
    def test_read_only_stack_fingerprint_and_eligibility(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/"package.json").write_text(json.dumps({"dependencies":{"react":"1","next":"1"}}));(p/"src").mkdir();(p/"src"/"a.tsx").write_text("export default 1")
            fp=fingerprint(p);self.assertFalse(fp["execution_performed"]);self.assertFalse(fp["network_used"]);self.assertIn("typescript",fp["languages"]);self.assertIn("react",fp["frameworks"]);self.assertIn("nextjs",fp["frameworks"])
            recs=[{"skill_id":"react-x","admission_status":"ADMITTED","eligibility":{"frameworks":["react"]}},{"skill_id":"vue-x","admission_status":"ADMITTED","eligibility":{"frameworks":["vue"]}},{"skill_id":"unadmitted","admission_status":"PENDING","eligibility":{"frameworks":["react"]}}]
            self.assertEqual(eligible_skill_ids(fp,recs),["react-x"])
if __name__=="__main__":unittest.main()
