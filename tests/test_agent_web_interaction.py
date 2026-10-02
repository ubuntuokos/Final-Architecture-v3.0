from __future__ import annotations
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_agent_web_interaction_gate import gate

class AgentWebInteractionTests(unittest.TestCase):
 def test_canonical_gate_passes(self):
  r=gate(ROOT); self.assertEqual(r["result"],"PASS",r["findings"]); self.assertEqual(r["capability_count"],175)
 def test_three_rails_and_no_silent_fallback(self):
  p=json.loads((ROOT/"canonical/profiles/FA3-SHARED-AGENT-WEB-INTERACTION-001.json").read_text())
  self.assertEqual(set(p["execution_rails"]),{"NATIVE_AGENT_CONTRACT","SEMANTIC_HTTP_BRIDGE","BROWSER_VISUAL"})
  self.assertIn("NO_SILENT_RAIL_FALLBACK",p["invariants"])
 def test_non_delegable_human_boundary_is_explicit(self):
  c=json.loads((ROOT/"canonical/contracts/FA3-SHARED-AGENT-WEB-INTERACTION-CONTRACTS-001.json").read_text())
  self.assertEqual(c["required_semantics"]["human_only_commitment"],"NON_DELEGABLE_ACTION_ABSENT_FROM_AGENT_EXECUTABLE_SURFACE")
 def test_attempt_receipt_cannot_claim_native_authority(self):
  c=json.loads((ROOT/"canonical/contracts/FA3-SHARED-AGENT-WEB-INTERACTION-CONTRACTS-001.json").read_text())
  self.assertIn("NO_ATTEMPT_RECEIPT_AS_AUTHORITATIVE_SITE_RECEIPT",c["invariants"])
if __name__=="__main__": unittest.main()
