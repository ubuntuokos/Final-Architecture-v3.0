import importlib.util
import json
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SPEC = importlib.util.spec_from_file_location("fa3_audacity_mcp_gate", ROOT / "src/fa3_audacity_mcp_gate.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

class AudacityMCPGateTests(unittest.TestCase):
    def test_audacity_mcp_gate_passes(self):
        report = MOD.gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertFalse(report["runtime_promotion_claim"])
        self.assertTrue(all(x["result"] == "PASS" for x in report["checks"]))

    def test_upstream_installer_is_forbidden_in_managed_mode(self):
        p = load("canonical/providers/FA3-PROVIDER-AUDACITY-MCP-001.json")
        self.assertEqual(p["fa3_adapter_policy"]["upstream_installer_execution_in_fa3_managed_mode"], "FORBIDDEN")
        self.assertEqual(p["fa3_adapter_policy"]["host_config_mutation"], "DENY")

    def test_audacity4_fails_closed_for_legacy_provider(self):
        p = load("canonical/providers/FA3-PROVIDER-AUDACITY-MCP-001.json")
        self.assertEqual(p["runtime_activation"]["audacity_4"], "NOT_ADMITTED_BY_THIS_PROVIDER")
        self.assertEqual(p["fa3_adapter_policy"]["unsupported_interface_behavior"], "FAIL_CLOSED_NO_GUI_CLICK_FALLBACK")

    def test_cap175_software_coexistence_is_explicit(self):
        p = load("canonical/providers/FA3-PROVIDER-AUDACITY-MCP-001.json")
        c = p["software_coexistence"]
        self.assertFalse(c["requires_upstream_uninstall"])
        self.assertFalse(c["global_environment_mutation"])
        self.assertFalse(c["claims_default_port"])
        self.assertFalse(c["writes_other_client_configuration"])

    def test_hardware_audit_cpu_only_and_zero_to_n_accelerators(self):
        c = load("canonical/contracts/FA3-AUDACITY-MCP-CONTRACTS-001.json")
        h = c["hardware_audit"]
        self.assertTrue(h["cpu_only_required"])
        self.assertEqual(h["accelerator_cardinality"], "0..N")
        self.assertEqual(h["fixed_cpu_gpu_npu_numa_values"], "FORBIDDEN")

    def test_dsp_model_router_boundary_is_precise(self):
        p = load("canonical/providers/FA3-PROVIDER-AUDACITY-DSP-REFERENCE-001.json")
        self.assertEqual(p["execution_policy"]["model_router_required"], "WHEN_OPERATION_USES_A_ROUTED_AI_MODEL")
        self.assertTrue(p["execution_policy"]["deterministic_non_model_dsp_may_execute_without_model_router"])

    def test_global_gate_registry_and_policy_binding(self):
        registry = load("canonical/FA3-GATE-REGISTRY-001.json")
        policy = load("canonical/enforcement-policy.json")
        self.assertIn("FA3-AUDACITY-MCP-GATESET-001", registry["mandatory_reference_gates"])
        self.assertEqual(registry["mandatory_reference_gates"], policy["mandatory_reference_gates"])
        self.assertEqual(policy["audacity_mcp_gate_id"], "FA3-AUDACITY-MCP-GATESET-001")
        self.assertFalse(policy["audacity_mcp_current_host_runtime_promotion_claim"])

    def test_cap124_evidence_registry_binds_materialization_decision_without_promotion(self):
        registry = load("evidence/evidence-registry.json")
        cap124 = next(x for x in registry["records"] if x["subject_id"] == "CAP-124")
        self.assertIn("FA3-DEC-AUDACITY-MCP-2026-09-28", cap124["source_decision_ids"])
        self.assertEqual(cap124["status"], "PENDING_CURRENT_HOST")
        rec = registry["audacity_mcp_reconciliation"]
        self.assertEqual(rec["gate_id"], "FA3-AUDACITY-MCP-GATESET-001")
        self.assertFalse(rec["current_host_runtime_promotion_claim"])
        self.assertFalse(rec["production_provider_admission"])

    def test_canonical_gate_record_is_p0_fail_closed(self):
        gate = load("canonical/FA3-GATE-AUDACITY-MCP-001.json")
        self.assertEqual(gate["enforcement_id"], "FA3-AUDACITY-MCP-GATESET-001")
        self.assertEqual(gate["priority"], "P0")
        self.assertTrue(gate["fail_closed"])
        self.assertFalse(gate["static_pass_promotes_runtime"])

if __name__ == "__main__":
    unittest.main()
