import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT / path).read_text())

def test_audacity_profile_is_non_authoritative_projection():
    p = load('canonical/profiles/FA3-AUDIO-EDIT-001.json')
    assert p['status'] == 'CANONICAL'
    assert p['new_capability'] is False
    assert p['new_architectural_authority'] is False
    assert p['subprofile_of'] == 'FA3-AUDIO-001'

def test_openvino_is_optional_and_fail_closed():
    p = load('canonical/providers/FA3-PROVIDER-AUDACITY-OPENVINO-001.json')
    assert p['requirement'] == 'OPTIONAL'
    assert p['pattern_source_strength'] == 'STRONG'
    assert p['admission_gate'] == 'AUDACITY_AI_ABI_AND_RESOURCE_ADMISSION_GATE'
    assert p['failure_policy'].startswith('fail-closed')

def test_openvino_cannot_capture_authority():
    p = load('canonical/providers/FA3-PROVIDER-AUDACITY-OPENVINO-001.json')
    constraints = ' '.join(p['authority_constraints'])
    assert 'SHALL NOT become global AI runtime authority' in constraints
    assert 'SHALL NOT become STT authority' in constraints
    assert 'Host Resource Broker' in constraints
    assert 'FA3-ACCEL-GUARD-001' in constraints

def test_post_audit_cpu_only_does_not_require_accelerator():
    h = load('canonical/hardware/FA3-AUDACITY-OPENVINO-HARDWARE-PROJECTION-001.json')
    s = h['semantics']
    assert s['resource_envelope'] == 'WORKLOAD_DERIVED'
    assert s['cpu_only_execution'] == 'VALID_WITHOUT_ACCELERATOR_DISCOVERY_OR_LEASE'
    assert s['fixed_cpu_gpu_npu_numa_values'] == 'FORBIDDEN'
    assert s['implicit_accelerator_fallback'] == 'FORBIDDEN'

def test_post_audit_accelerator_requires_hardware_authorities():
    h = load('canonical/hardware/FA3-AUDACITY-OPENVINO-HARDWARE-PROJECTION-001.json')
    assert h['authority'] == 'FA3-AUTH-HOST-RESOURCE-BROKER-001'
    assert h['semantics']['accelerator_execution'] == 'REQUIRES_HRB_LEASE_AND_FA3-ACCEL-GUARD-001_RECONCILIATION'

def test_contract_requires_provenance_and_admission_receipt():
    c = load('canonical/contracts/FA3-AUDIO-EDIT-CONTRACTS-001.json')
    result = c['contracts']['AudioEditAIResult']['required']
    assert {'provider_identity','model_identity','parameters','provenance','admission_receipt'} <= set(result)
    admission = c['contracts']['AudacityAICompatibilityAdmission']
    assert admission['failure'] == 'deny affected provider workload only'
    assert 'hrb_lease' in admission['accelerator_fields_required_only_when_accelerator_requested']
    assert 'accelerator_guard_reconciliation' in admission['accelerator_fields_required_only_when_accelerator_requested']
