from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("gate", ROOT/"src/fa3_openvid_gate.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class OpenVidGateTests(unittest.TestCase):
    def test_regressions_all_pass(self):
        cases=gate.regression_cases()
        self.assertEqual(len(cases),18)
        self.assertTrue(all(c["result"]=="PASS" for c in cases))

    def test_runtime_admission_fail_closed_for_noncommercial_license(self):
        good={"license_compatible_with_intended_deployment":True,"separate_license_or_independent_implementation":True,"immutable_source_pin":True,"contract_conformance_pass":True,"current_host_e2e_pass":True}
        self.assertTrue(gate.runtime_admission_allowed(good))
        self.assertFalse(gate.runtime_admission_allowed({**good,"license_compatible_with_intended_deployment":False}))
        self.assertFalse(gate.runtime_admission_allowed({**good,"separate_license_or_independent_implementation":False}))

    def test_export_fallback_order_and_bounds(self):
        good={"backend_order":["HARDWARE_ACCELERATED_NATIVE_OR_WEB_CODECS","SOFTWARE_ENCODER","WASM_FALLBACK"],"bounded_memory":True,"fallbacks_observable":True,"direct_to_disk_preferred":True}
        self.assertTrue(gate.export_plan_allowed(good))
        self.assertFalse(gate.export_plan_allowed({**good,"bounded_memory":False}))
        self.assertFalse(gate.export_plan_allowed({**good,"backend_order":["SOFTWARE_ENCODER","WASM_FALLBACK"]}))

    def test_full_canonical_gate_passes(self):
        report=gate.gate(ROOT)
        self.assertEqual(report["status"],"PASS",report)
        self.assertEqual(report["finding_count"],0)
        self.assertEqual(report["capability_count_after"],143)
        self.assertFalse(report["current_host_runtime_promotion_claimed"])

if __name__=="__main__":
    unittest.main()
