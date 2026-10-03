from __future__ import annotations
import json,subprocess,sys,unittest
from pathlib import Path
from src.fa3_application_portfolio import validate,resolve
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c):
  c.r=Path(__file__).resolve().parents[1];c.p=json.loads((c.r/"canonical/FA3-APPLICATION-PORTFOLIO-001.json").read_text());c.l=json.loads((c.r/"canonical/FA3-OPERATING-LEVEL-MODEL-001.json").read_text());c.e=json.loads((c.r/"canonical/FA3-ENTITLEMENT-POLICY-001.json").read_text());c.c=json.loads((c.r/"canonical/FA3-PRODUCT-CATALOG-001.json").read_text())
 def test_validation(s):s.assertEqual(validate(s.r),[])
 def test_baseline(s):s.assertEqual(s.p["capability_count"],175);s.assertEqual(s.l["capability_count"],175)
 def test_story_render(s):
  x=resolve(s.r,["fa3.story-screenplay","fa3.render-manager"]);s.assertEqual(x["operating_level"],"PROFESSIONAL");s.assertIn("fa3.platform.3d-core",x["platform_dependencies"]);s.assertNotIn("fa3.threed-dcc-studio",x["applications"])
 def test_one_app_enterprise(s):s.assertEqual(resolve(s.r,["fa3.story-screenplay"],"ENTERPRISE")["applications"],["fa3.story-screenplay"])
 def test_tier_no_apps(s):s.assertTrue(s.e["rules"]["higher_operating_level_does_not_grant_apps"])
 def test_bundles_optional(s):s.assertTrue(all(x["optional"] for x in s.c["bundles"]))
 def test_below_min(s):
  with s.assertRaisesRegex(ValueError,"APPLICATION_BELOW_MINIMUM_OPERATING_LEVEL"):resolve(s.r,["fa3.render-manager"],"PERSONAL")
 def test_lifecycle_separate(s):s.assertEqual(s.p["provisioning_lifecycle_ref"],"FA3-APP-LIFECYCLE-001")
 def test_cli(s):
  p=subprocess.run([sys.executable,str(s.r/"src/fa3_application_portfolio.py"),"--check"],cwd=s.r,text=True,capture_output=True);s.assertEqual(p.returncode,0,p.stdout+p.stderr)
if __name__=="__main__":unittest.main()
