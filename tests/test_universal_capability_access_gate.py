import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from fa3_universal_capability_access_gate import classify_donor,evaluate_usage,gate
ROOT=Path(__file__).resolve().parents[1]
class UniversalCapabilityAccessTests(unittest.TestCase):
 def test_current_repository_gate_audits_every_donor(self):
  r=gate(ROOT); self.assertEqual(r["result"],"PASS",r); self.assertEqual(r["registry_entry_count"],r["audited_record_count"]); self.assertEqual(r["capability_count"],175); self.assertFalse(r["physical_current_host_pass_claimed"])
 def test_classes(self):
  self.assertEqual(classify_donor({"source":{"kind":"GITHUB_REPOSITORY"},"license":{"declared":"Custom","status":"NONCOMMERCIAL_RESEARCH_ONLY"}}),"RESTRICTED_REFERENCE")
  self.assertEqual(classify_donor({"source":{"kind":"GITHUB_REPOSITORY"},"license":{"declared":"UNKNOWN","status":"UNVERIFIED"}}),"UNVERIFIED_REFERENCE_ONLY")
  self.assertEqual(classify_donor({"source":{"kind":"GITHUB_TOPIC"},"license":{"declared":"NOT_APPLICABLE","status":"COLLECTION_INDEX"},"donor_modes":["DISCOVERY_INDEX"]}),"DISCOVERY_INDEX")
 def test_restricted_nonmaterial_allowed(self): self.assertEqual(evaluate_usage({"id":"U1","usage_kind":"ARCHITECTURE_PATTERN"},"RESTRICTED_REFERENCE"),[])
 def test_restricted_material_requires_substitute(self):
  self.assertTrue(evaluate_usage({"id":"U2","usage_kind":"RUNTIME_DEPENDENCY"},"RESTRICTED_REFERENCE"))
  u={"id":"U3","usage_kind":"RUNTIME_DEPENDENCY","universal_access":{"classification":"OPTIONAL_RESTRICTED_WITH_GLOBAL_SUBSTITUTE","global_substitute_refs":["FA3-NATIVE"],"rights_evidence_refs":["rights:x"],"restriction_circumvention_forbidden":True}}
  self.assertEqual(evaluate_usage(u,"RESTRICTED_REFERENCE"),[])
 def test_unknown_and_discovery_material_fail(self):
  u={"id":"U4","usage_kind":"CODE_REUSE","universal_access":{"rights_evidence_refs":["x"]}}; self.assertTrue(evaluate_usage(u,"UNVERIFIED_REFERENCE_ONLY")); self.assertTrue(evaluate_usage(u,"DISCOVERY_INDEX"))
 def test_global_material_needs_rights(self):
  u={"id":"U5","usage_kind":"CODE_REUSE"}; self.assertTrue(evaluate_usage(u,"GLOBAL_CONDITIONAL_REUSE")); u["universal_access"]={"rights_evidence_refs":["rights:x"]}; self.assertEqual(evaluate_usage(u,"GLOBAL_CONDITIONAL_REUSE"),[])
if __name__=="__main__": unittest.main()
