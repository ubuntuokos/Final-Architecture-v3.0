import importlib.util,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
SPEC=importlib.util.spec_from_file_location("fa3_binary_analysis_gate",ROOT/"src/fa3_binary_analysis_gate.py")
MOD=importlib.util.module_from_spec(SPEC); assert SPEC.loader is not None; SPEC.loader.exec_module(MOD)
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class BinaryAnalysisGateTests(unittest.TestCase):
 def test_gate(self):
  r=MOD.gate(ROOT); self.assertEqual(r["result"],"PASS"); self.assertFalse(r["runtime_promotion_claim"]); self.assertEqual(len(r["checks"]),20)
 def test_reference_only_pin(self):
  r=load("canonical/references/FA3-REVERSE-SKILLS-UPSTREAM-REFERENCE-2026-09-28.json"); self.assertEqual(r["observed_commit"],"a2baa31c58a3567977188414da68c8c842057152"); self.assertEqual(r["distribution_class"],"REFERENCE_ONLY"); self.assertFalse(r["runtime_dependency"])
 def test_license_fail_closed(self):
  r=load("canonical/references/FA3-REVERSE-SKILLS-UPSTREAM-REFERENCE-2026-09-28.json"); self.assertFalse(r["license_review"]["root_license_file_observed"]); self.assertEqual(r["license_review"]["status"],"INCOMPLETE_FAIL_CLOSED")
 def test_bundled_executable_blocked(self):
  e=load("canonical/references/FA3-REVERSE-SKILLS-UPSTREAM-REFERENCE-2026-09-28.json")["bundled_executables"][0]; self.assertEqual(e["path"],"skills/rev-dex-dumper/panda-dex-dumper"); self.assertEqual(e["disposition"],"BLOCKED_FROM_FA3_RUNTIME_MATERIALIZATION")
 def test_ir_provider_neutral(self):
  r=load("canonical/contracts/FA3-BINARY-ANALYSIS-IR-CONTRACTS-001.json"); self.assertTrue(r["provider_neutral"]); self.assertTrue(r["cross_provider_rules"]["canonical_core_must_not_require_ida_ghidra_rizin_radare2_binary_ninja_or_other_specific_backend"])
 def test_untrusted_content(self):
  c=load("canonical/contracts/FA3-BINARY-ANALYSIS-CONTRACTS-001.json"); self.assertTrue(c["analyzed_content_security"]["analyzed_content_must_not_become_system_instruction"]); self.assertTrue(c["analyzed_content_security"]["prompt_injection_adversarial_eval_required"])
 def test_model_and_fallback(self):
  c=load("canonical/contracts/FA3-BINARY-ANALYSIS-CONTRACTS-001.json"); self.assertEqual(c["provider_discovery"]["silent_fallback"],"FORBIDDEN"); self.assertTrue(c["model_policy"]["model_backed_reasoning_requires_model_router"])
 def test_emulation_safety(self):
  e=load("canonical/contracts/FA3-BINARY-ANALYSIS-CONTRACTS-001.json")["emulation_safety"]; self.assertEqual(e["network_default"],"DENY"); self.assertEqual(e["host_filesystem_default"],"DENY"); self.assertEqual(e["host_syscall_passthrough_default"],"DENY")
 def test_hardware_coexistence(self):
  c=load("canonical/contracts/FA3-BINARY-ANALYSIS-CONTRACTS-001.json"); self.assertTrue(c["hardware_audit"]["cpu_only_required"]); self.assertEqual(c["hardware_audit"]["accelerator_cardinality"],"0..N"); self.assertFalse(c["coexistence"]["host_global_config_mutation"])
if __name__=="__main__": unittest.main()
