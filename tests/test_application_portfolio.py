from __future__ import annotations
import json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_application_portfolio import validate,resolve,reconcile_records
from fa3_release_baseline import load_active_release_baseline
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c):
  c.r=ROOT;c.p=json.loads((c.r/"canonical/FA3-APPLICATION-PORTFOLIO-001.json").read_text());c.l=json.loads((c.r/"canonical/FA3-OPERATING-LEVEL-MODEL-001.json").read_text());c.e=json.loads((c.r/"canonical/FA3-ENTITLEMENT-POLICY-001.json").read_text());c.c=json.loads((c.r/"canonical/FA3-PRODUCT-CATALOG-001.json").read_text());c.d=json.loads((c.r/"canonical/FA3-APPLICATION-DEPENDENCY-REGISTRY-001.json").read_text())
 def test_validation(s):s.assertEqual(validate(s.r),[])
 def test_baseline(s):
  b=load_active_release_baseline(s.r).capability_count;s.assertEqual(s.p["capability_count"],b);s.assertEqual(s.l["capability_count"],b);s.assertEqual(b,175)
 def test_story_render(s):
  x=resolve(s.r,["fa3.story-screenplay","fa3.render-manager"]);s.assertEqual(x["operating_level"],"PROFESSIONAL");s.assertIn("fa3.platform.3d-core",x["platform_dependencies"]);s.assertNotIn("fa3.threed-dcc-studio",x["applications"])
 def test_one_app_enterprise(s):s.assertEqual(resolve(s.r,["fa3.story-screenplay"],"ENTERPRISE")["applications"],["fa3.story-screenplay"])
 def test_lan_requirement(s):
  x=resolve(s.r,["fa3.story-screenplay"],operational_requirements=["LAN_DISTRIBUTED_EXECUTION"]);s.assertEqual(x["operating_level"],"STUDIO");s.assertEqual(x["applications"],["fa3.story-screenplay"])
 def test_unknown_requirement(s):
  with s.assertRaisesRegex(ValueError,"UNKNOWN_OPERATIONAL_REQUIREMENT"):resolve(s.r,["fa3.story-screenplay"],operational_requirements=["MAGIC_SCALE"])
 def test_tier_no_apps(s):s.assertTrue(s.e["rules"]["higher_operating_level_does_not_grant_apps"])
 def test_bundles_optional(s):s.assertTrue(all(x["optional"] for x in s.c["bundles"]))
 def test_optional_addons(s):
  rows=s.c["optional_addons"];s.assertEqual({x["class"] for x in rows},{"ENGINE","PROVIDER","CAPACITY","SUPPORT"});s.assertTrue(all(x["optional"] and not x["authority"] and not x["runtime_activation_grant"] and not x["grants_application_entitlement"] for x in rows))
 def test_authorities(s):
  b=s.e["authority_boundaries"];s.assertEqual(b["security"],"FA3-AUTH-SECURITY-GOV-001");s.assertEqual(b["license_rights"],"FA3-LICENSE-RIGHTS-001");s.assertEqual(b["host_resources"],"FA3-AUTH-HOST-RESOURCE-BROKER-001");s.assertEqual(b["model_provider_routing"],"FA3-AUTH-MODEL-ROUTER-001");s.assertTrue(s.e["rules"]["entitlement_may_restrict_but_never_override_authority"])
 def test_dependency_separation(s):
  r=s.d["rules"];s.assertTrue(r["runtime_dependency_is_not_application_entitlement"]);s.assertTrue(r["application_entitlement_is_never_technical_dependency"]);s.assertTrue(r["restricted_donor_may_not_be_sole_required_dependency"])
 def test_below_min(s):
  with s.assertRaisesRegex(ValueError,"APPLICATION_BELOW_MINIMUM_OPERATING_LEVEL"):resolve(s.r,["fa3.render-manager"],"PERSONAL")
 def test_external_catalog(s):
  ids={a["application_id"] for a in s.p["applications"]};x=json.loads((s.r/"canonical/FA3-AI-STUDIO-APP-CATALOG-001.json").read_text());s.assertTrue(all("studio."+a["id"] in ids for a in x["applications"]))
 def test_family_placement(s):
  pf=json.loads((s.r/"canonical/FA3-PRODUCT-FAMILY-REGISTRY-001.json").read_text());placed={x["application_id"] for x in pf["application_placements"]};s.assertTrue(all(a["application_id"] in placed for a in s.p["applications"]))
 def test_dependencies_explicit(s):s.assertEqual({a["application_id"] for a in s.p["applications"]},set(s.d["application_dependencies"]))
 def test_bundle_projection(s):
  e={}
  for b in s.c["bundles"]:
   for aid in b["applications"]:e.setdefault(aid,[]).append(b["id"])
  for a in s.p["applications"]:s.assertEqual(sorted(a["available_in_bundles"]),sorted(e.get(a["application_id"],[])))
 def test_existing_markers(s):
  for a in s.p["applications"]:
   if a["application_class"] in {"INTERNAL_APPLICATION","SYSTEM_APPLICATION","COMPANION_APPLICATION"} and a["portfolio_state"]=="EXISTING":s.assertTrue(a.get("implementation_markers"),a["application_id"])
 def test_lifecycle_separate(s):
  l=json.loads((s.r/"canonical/FA3-APP-LIFECYCLE-001.json").read_text());s.assertEqual(s.p["provisioning_lifecycle_ref"],"FA3-APP-LIFECYCLE-001");s.assertEqual(l["states"],["AVAILABLE","READY_TO_INSTALL","INSTALLING","INSTALLED","INCOMPATIBLE","RECIPE_REQUIRED","ERROR"]);s.assertTrue(set(s.p["portfolio_states"]).isdisjoint(l["states"]))
 def test_incremental(s):
  a={"applications":[{"application_id":"a","portfolio_state":"PLANNED"},{"application_id":"b","portfolio_state":"EXISTING"}]};b={"applications":[{"application_id":"a","portfolio_state":"IN_PROGRESS"},{"application_id":"c","portfolio_state":"FUTURE"}]};k={(e["application_id"],e["change"]) for e in reconcile_records(a,b)};s.assertEqual(k,{("a","PORTFOLIO_STATE_CHANGED"),("b","REMOVED"),("c","ADDED")})
 def test_control_center_projection(s):
  c=(s.r/"apps/fa3-control-center/src/ProductEntitlementService.cpp").read_text();q=(s.r/"apps/fa3-control-center/qml/ProductEntitlementsPage.qml").read_text();s.assertIn('levels.value(QStringLiteral("order")).toList()',c);s.assertIn('catalog.value(QStringLiteral("bundles")).toList()',c);s.assertIn("optionalAddons",q)
 def test_cli(s):
  p=subprocess.run([sys.executable,str(s.r/"src/fa3_application_portfolio.py"),"--check"],cwd=s.r,text=True,capture_output=True);s.assertEqual(p.returncode,0,p.stdout+p.stderr)
  p=subprocess.run([sys.executable,str(s.r/"src/fa3_application_portfolio.py"),"--apps","fa3.story-screenplay","--requirement","LAN_DISTRIBUTED_EXECUTION"],cwd=s.r,text=True,capture_output=True);s.assertEqual(p.returncode,0,p.stdout+p.stderr);s.assertIn('"STUDIO"',p.stdout)
 def test_product_gate(s):
  p=subprocess.run([sys.executable,str(s.r/"src/fa3_product_entitlement_gate.py")],cwd=s.r,text=True,capture_output=True);s.assertEqual(p.returncode,0,p.stdout+p.stderr)
if __name__=="__main__":unittest.main()
