from src.fa3_extension_boundary_gate import ExtensionBoundaryError, validate_extension


def test_capability_neutral_extension_passes():
    report = validate_extension({
        "existing_capability_ids": ["CAP-001"],
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "device_selection_authority": False,
        "model_routing_authority": False,
        "runtime_evidence_ref": "evidence/reference/runtime.json",
        "security_evidence_ref": "evidence/reference/security.json",
    })
    assert report["classification"] == "CAPABILITY_NEUTRAL"
    assert report["result"] == "PASS"


def test_new_authority_forces_capability_changing_and_reconciliation():
    report = validate_extension({
        "new_architectural_authority": True,
        "release_baseline_change_ref": "decision",
        "capability_reconciliation_ref": "cap-reg",
        "authority_reconciliation_ref": "auth-reg",
        "canonical_decision_ref": "decision",
    })
    assert report["classification"] == "CAPABILITY_CHANGING"
    assert report["result"] == "PASS"


def test_neutral_extension_cannot_own_routing_authority():
    report = validate_extension({
        "existing_capability_ids": ["CAP-001"],
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "device_selection_authority": False,
        "model_routing_authority": True,
        "runtime_evidence_ref": "runtime",
        "security_evidence_ref": "security",
    })
    assert report["result"] == "FAIL"


def test_unclassified_extension_fails_closed():
    try:
        validate_extension({})
    except ExtensionBoundaryError:
        return
    raise AssertionError("unclassified extension must fail closed")
