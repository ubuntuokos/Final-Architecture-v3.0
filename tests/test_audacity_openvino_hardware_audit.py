import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def load(p): return json.loads((ROOT / p).read_text())

def test_no_fixed_hardware_or_implicit_accelerator():
    h = load('canonical/hardware/FA3-AUDACITY-OPENVINO-HARDWARE-PROJECTION-001.json')['semantics']
    assert h['fixed_cpu_gpu_npu_numa_values'] == 'FORBIDDEN'
    assert h['implicit_accelerator_fallback'] == 'FORBIDDEN'
    assert h['display_gpu_is_compute_entitlement'] is False

def test_cpu_only_negative_accelerator_assurance():
    h = load('canonical/hardware/FA3-AUDACITY-OPENVINO-HARDWARE-PROJECTION-001.json')['semantics']
    assert h['cpu_only_execution'] == 'VALID_WITHOUT_ACCELERATOR_DISCOVERY_OR_LEASE'

def test_accelerator_positive_authority_chain():
    h = load('canonical/hardware/FA3-AUDACITY-OPENVINO-HARDWARE-PROJECTION-001.json')
    assert h['authority'] == 'FA3-AUTH-HOST-RESOURCE-BROKER-001'
    assert 'HRB_LEASE' in h['semantics']['accelerator_execution']
    assert 'ACCEL-GUARD' in h['semantics']['accelerator_execution']

def test_provider_disable_does_not_break_editor():
    h = load('canonical/hardware/FA3-AUDACITY-OPENVINO-HARDWARE-PROJECTION-001.json')
    assert h['failure_policy'] == 'FAIL_CLOSED_FOR_PROVIDER_EXECUTION_WITHOUT_DEGRADING_BASE_AUDACITY'
