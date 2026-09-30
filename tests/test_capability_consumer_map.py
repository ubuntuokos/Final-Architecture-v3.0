from __future__ import annotations
import json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from fa3_capability_consumer_map import build_map
FILES=["canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json","canonical/FA3-APPLICATION-DONOR-LINKS-001.json","canonical/FA3-AI-STUDIO-APP-CATALOG-001.json","canonical/FA3-GUI-SURFACE-REGISTRY-001.json","canonical/profiles/FA3-EXTERNAL-LLM-CATALOG-001.json"]
def fixture(root):
 for rel in FILES:
  dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes((ROOT/rel).read_bytes())
class CapabilityConsumerMapTests(unittest.TestCase):
 def test_empty_current_graph_is_valid(self): self.assertEqual(build_map(ROOT)["validation"]["result"],"PASS")
 def test_canonical_binding_and_reverse_views(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); fixture(root); links=json.loads((root/FILES[1]).read_text()); donor=json.loads((root/FILES[0]).read_text())["entries"][0]["donor_id"]
   links["donor_usage_records"]=[{"id":"FA3-USAGE-CAPMAP-TEST-001","application_id":"fa3.quickclip","donor_id":donor,"donor_capability_key":"provider-discovery","usage_kind":"CAPABILITY_PATTERN","status":"ACTIVE","fa3_bindings":{"profile_ids":["FA3-EXTERNAL-LLM-CATALOG-001"],"contract_ids":[],"authority_ids":["FA3-AUTH-MODEL-ROUTER-001"],"shared_module_ids":[]},"consumers":[{"kind":"SHARED_MODULE","id":"FA3-EXTERNAL-LLM-CATALOG-001","relationship":"DIRECT"}],"current_host_impact":{"classification":"NO_RUNTIME_IMPACT"}}]; (root/FILES[1]).write_text(json.dumps(links))
   r=build_map(root); self.assertEqual(r["validation"]["result"],"PASS",r["validation"]["findings"]); e=r["edges"][0]; self.assertEqual(e["fa3_bindings"]["capability_ids"],["CAP-005","CAP-140"]); self.assertIn(e["id"],r["views"]["by_consumer"]["APPLICATION:fa3.quickclip"]); self.assertIn(e["id"],r["views"]["by_capability"]["CAP-140"])
 def test_manual_capability_binding_fails_closed(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); fixture(root); links=json.loads((root/FILES[1]).read_text()); donor=json.loads((root/FILES[0]).read_text())["entries"][0]["donor_id"]; links["donor_usage_records"]=[{"id":"BAD","application_id":"fa3.quickclip","donor_id":donor,"usage_kind":"CAPABILITY_PATTERN","status":"ACTIVE","fa3_bindings":{"profile_ids":["FA3-EXTERNAL-LLM-CATALOG-001"],"capability_ids":["CAP-140"]}}]; (root/FILES[1]).write_text(json.dumps(links)); self.assertIn("MANUAL_CAPABILITY_BINDING_FORBIDDEN",{x["code"] for x in build_map(root)["validation"]["findings"]})
if __name__=="__main__": unittest.main()
