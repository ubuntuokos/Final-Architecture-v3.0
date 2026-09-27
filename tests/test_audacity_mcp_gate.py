import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fa3_audacity_mcp_gate", ROOT / "src/fa3_audacity_mcp_gate.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def test_audacity_mcp_gate_passes():
    report = MOD.gate(ROOT)
    assert report["result"] == "PASS"
    assert report["runtime_promotion_claim"] is False
    assert all(x["result"] == "PASS" for x in report["checks"])

def test_upstream_installer_is_forbidden_in_managed_mode():
    p = load("canonical/providers/FA3-PROVIDER-AUDACITY-MCP-001.json")
    assert p["fa3_adapter_policy"]["upstream_installer_execution_in_fa3_managed_mode"] == "FORBIDDEN"
    assert p["fa3_adapter_policy"]["host_config_mutation"] == "DENY"

def test_audacity4_fails_closed_for_legacy_provider():
    p = load("canonical/providers/FA3-PROVIDER-AUDACITY-MCP-001.json")
    assert p["runtime_activation"]["audacity_4"] == "NOT_ADMITTED_BY_THIS_PROVIDER"
    assert p["fa3_adapter_policy"]["unsupported_interface_behavior"] == "FAIL_CLOSED_NO_GUI_CLICK_FALLBACK"

def test_cap175_software_coexistence_is_explicit():
    p = load("canonical/providers/FA3-PROVIDER-AUDACITY-MCP-001.json")
    c = p["software_coexistence"]
    assert c["requires_upstream_uninstall"] is False
    assert c["global_environment_mutation"] is False
    assert c["claims_default_port"] is False
    assert c["writes_other_client_configuration"] is False

def test_hardware_audit_cpu_only_and_zero_to_n_accelerators():
    c = load("canonical/contracts/FA3-AUDACITY-MCP-CONTRACTS-001.json")
    h = c["hardware_audit"]
    assert h["cpu_only_required"] is True
    assert h["accelerator_cardinality"] == "0..N"
    assert h["fixed_cpu_gpu_npu_numa_values"] == "FORBIDDEN"

def test_dsp_model_router_boundary_is_precise():
    p = load("canonical/providers/FA3-PROVIDER-AUDACITY-DSP-REFERENCE-001.json")
    assert p["execution_policy"]["model_router_required"] == "WHEN_OPERATION_USES_A_ROUTED_AI_MODEL"
    assert p["execution_policy"]["deterministic_non_model_dsp_may_execute_without_model_router"] is True
