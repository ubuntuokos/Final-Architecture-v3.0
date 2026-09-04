from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("gate", ROOT/"src/fa3_openvid_gate.py")
gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)

def test_regressions_all_pass():
    cases=gate.regression_cases()
    assert len(cases)==18
    assert all(c["result"]=="PASS" for c in cases)

def test_runtime_admission_fail_closed_for_noncommercial_license():
    good={"license_compatible_with_intended_deployment":True,"separate_license_or_independent_implementation":True,"immutable_source_pin":True,"contract_conformance_pass":True,"current_host_e2e_pass":True}
    assert gate.runtime_admission_allowed(good)
    assert not gate.runtime_admission_allowed({**good,"license_compatible_with_intended_deployment":False})
    assert not gate.runtime_admission_allowed({**good,"separate_license_or_independent_implementation":False})

def test_export_fallback_order_and_bounds():
    good={"backend_order":["HARDWARE_ACCELERATED_NATIVE_OR_WEB_CODECS","SOFTWARE_ENCODER","WASM_FALLBACK"],"bounded_memory":True,"fallbacks_observable":True,"direct_to_disk_preferred":True}
    assert gate.export_plan_allowed(good)
    assert not gate.export_plan_allowed({**good,"bounded_memory":False})
    assert not gate.export_plan_allowed({**good,"backend_order":["SOFTWARE_ENCODER","WASM_FALLBACK"]})

def test_full_canonical_gate_passes():
    report=gate.gate(ROOT)
    assert report["status"]=="PASS", report
    assert report["finding_count"]==0
    assert report["capability_count_after"]==143
    assert report["current_host_runtime_promotion_claimed"] is False
