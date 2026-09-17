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
    assert p['admission_gate'] == 'AUDACITY_AI_ABI_COMPATIBILITY_GATE'
    assert p['failure_policy'].startswith('fail-closed')

def test_openvino_cannot_capture_authority():
    p = load('canonical/providers/FA3-PROVIDER-AUDACITY-OPENVINO-001.json')
    constraints = ' '.join(p['authority_constraints'])
    assert 'SHALL NOT become global AI runtime authority' in constraints
    assert 'SHALL NOT become STT authority' in constraints
    assert 'Host Resource Broker' in constraints

def test_contract_requires_provenance_and_compatibility():
    c = load('canonical/contracts/FA3-AUDIO-EDIT-CONTRACTS-001.json')
    result = c['contracts']['AudioEditAIResult']['required']
    assert {'provider_identity','model_identity','parameters','provenance'} <= set(result)
    admission = c['contracts']['AudacityAICompatibilityAdmission']
    assert admission['failure'] == 'disable OpenVINO provider only'
