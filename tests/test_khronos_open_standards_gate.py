import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_khronos_open_standards_gate import EXPECTED,EXPECTED_BUILD_DEPS,gate
from fa3_khronos_adapters import load_registry
class KhronosOpenStandardsTests(unittest.TestCase):
 def test_static_gate(self):
  r=gate(ROOT);self.assertEqual("PASS",r["result"],r["findings"]);self.assertEqual(0,r["capability_delta"]);self.assertEqual(0,r["authority_delta"]);self.assertFalse(r["current_host_runtime_promotion_claim"])
 def test_pin_inventory(self):
  self.assertEqual(15,len(EXPECTED));self.assertEqual(4,len(EXPECTED_BUILD_DEPS))
 def test_adapter_registry_non_authoritative(self):
  r=load_registry(ROOT);self.assertTrue(r["adapters"]);self.assertTrue(all(x["authority"] is False for x in r["adapters"]))
 def test_dedicated_current_host_executes_physical_cap083_proof(self):
  text=(ROOT/".github/workflows/fa3-khronos-current-host.yml").read_text(encoding="utf-8")
  self.assertIn("src/fa3_current_host_capability_qualification_constituent_orchestrator.py --root . --execute --subjects CAP-083",text)
  self.assertIn("src/fa3_current_host_capability_test_orchestrator.py --root . --execute --subjects CAP-083",text)
  self.assertIn("src/fa3_current_host_capability_test_bundle.py --root .",text)
  self.assertIn("src/fa3_current_host_capability_attest.py --root .",text)
  self.assertIn("src/fa3_current_host_capability_handoff.py --root .",text)
  self.assertIn("src/fa3_current_host_evidence_audit.py --root . --apply-reconciliation",text)
  self.assertIn("Assert physical CAP-083 proof payloads and receipt",text)
  self.assertIn("evidence/receipts/capabilities/CAP-083.json",text)
  self.assertIn("evidence/evidence-registry.json",text)
  self.assertIn('cap83.get("runtime_conformance") != "CURRENT_HOST_EVIDENCE_PASS"',text)
  for path in (
   "src/fa3_cap083_khronos_current_host.py",
   "src/fa3_khronos_open_standards_gate.py",
   "src/fa3_current_host_capability_qualification_constituent_orchestrator.py",
   "src/fa3_current_host_capability_test_qualification_audit.py",
   "src/fa3_current_host_capability_qualification_constituent_producer_audit.py",
   "src/fa3_current_host_capability_test_executor_audit.py",
   "src/fa3_current_host_capability_test_orchestrator.py",
   "src/fa3_current_host_capability_test_qualifier.py",
   "src/fa3_current_host_capability_test_bundle.py",
   "src/fa3_current_host_capability_attest.py",
   "src/fa3_current_host_capability_handoff.py",
   "src/fa3_current_host_evidence_audit.py",
   "canonical/current-host-capability-proof-recipes.json",
   "canonical/current-host-capability-qualification-constituent-producers.json",
   "canonical/current-host-capability-test-qualifications.json",
   "canonical/current-host-capability-test-executors.json",
   "evidence/evidence-registry.json",
   "evidence/collect-current-host.sh",
   "tests/test_khronos_open_standards_gate.py",
   "tests/test_cap083_khronos_current_host.py",
  ):
   self.assertIn(f"'{path}'",text)
  self.assertIn("  push:\n    branches: [main]\n",text)
  self.assertIn("  pull_request:\n",text)
  self.assertIn("  workflow_dispatch:\n",text)
if __name__=="__main__":unittest.main()
