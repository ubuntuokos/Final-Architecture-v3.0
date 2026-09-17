import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT / p).read_text())

def test_hardware_projection_negative_assurance():
    h = load('canonical/hardware/FA3-AUDACITY-OPENVINO-HARDWARE-PROJECTION-001.json')['semantics']
    assert h['resource_envelope'] == 'WORKLOAD_DERIVED'
    assert h['cpu_only_execution'] == 'VALID_WITHOUT_ACCELERATOR_DISCOVERY_OR_LEASE'
    assert h['fixed_cpu_gpu_npu_numa_values'] == 'FORBIDDEN'
    assert h['implicit_accelerator_fallback'] == 'FORBIDDEN'
    assert h['display_gpu_is_compute_entitlement'] is False

def test_accelerator_authority_chain():
    h = load('canonical/hardware/FA3-AUDACITY-OPENVINO-HARDWARE-PROJECTION-001.json')
    assert h['authority'] == 'FA3-AUTH-HOST-RESOURCE-BROKER-001'
    assert h['semantics']['accelerator_execution'] == 'REQUIRES_HRB_LEASE_AND_FA3-ACCEL-GUARD-001_RECONCILIATION'

def test_gate_has_positive_negative_and_rollback_cases():
    g = load('canonical/contracts/FA3-AUDACITY-OPENVINO-HARDWARE-AUDIT-GATE-001.json')
    assert 'CPU_ONLY_NO_ACCELERATOR_LEASE' in g['positive_cases']
    assert 'ACCELERATOR_WITH_HRB_LEASE_AND_GUARD' in g['positive_cases']
    assert 'ACCELERATOR_WITHOUT_HRB_LEASE' in g['negative_cases']
    assert 'SILENT_DEVICE_OR_PROVIDER_FALLBACK' in g['negative_cases']
    assert g['rollback_case'] == 'PROVIDER_DISABLED_BASE_AUDACITY_REMAINS_FUNCTIONAL'

def test_provider_disable_does_not_break_editor():
    h = load('canonical/hardware/FA3-AUDACITY-OPENVINO-HARDWARE-PROJECTION-001.json')
    assert h['failure_policy'] == 'FAIL_CLOSED_FOR_PROVIDER_EXECUTION_WITHOUT_DEGRADING_BASE_AUDACITY'
