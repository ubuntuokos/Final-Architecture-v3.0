from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("openvid_gate",ROOT/"src/fa3_openvid_gate.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class OpenVidGateTests(unittest.TestCase):
    def test_new_positive_and_negative_regressions(self):
        cases=gate.regression_cases()
        self.assertEqual(len(cases),20)
        self.assertTrue(all(c["result"]=="PASS" and c["positive"] and c["negative_refusal"] for c in cases))
    def test_upstream_runtime_stays_fail_closed(self):
        good={k:True for k in ("license_compatible_with_intended_deployment",
              "separate_license_or_independent_implementation","immutable_source_pin",
              "contract_conformance_pass","current_host_e2e_pass")}
        self.assertTrue(gate.runtime_admission_allowed(good))
        for key in good:
            self.assertFalse(gate.runtime_admission_allowed({**good,key:False}))
    def test_editable_roundtrip_rejects_flatten(self):
        good={"project_format":".fa3openvid","editable_reference":True,"round_trip":True,"auto_flatten":False}
        self.assertTrue(gate.project_handoff_allowed(good))
        for key in good:
            self.assertFalse(gate.project_handoff_allowed({**good,key:None}))
    def test_cpu_only_baseline_and_bounded_fallbacks(self):
        good={"backend_order":["CPU_ONLY_BASELINE","HRB_ADMITTED_ACCELERATOR_OPTIONAL","SOFTWARE_ENCODER","WASM_FALLBACK_BOUNDED"],
              "bounded_memory":True,"fallbacks_observable":True,"direct_to_disk_preferred":True}
        self.assertTrue(gate.export_plan_allowed(good))
        for key in good:
            self.assertFalse(gate.export_plan_allowed({**good,key:None}))
    def test_complete_canonical_gate(self):
        result=gate.gate(ROOT)
        self.assertEqual(result["status"],"PASS",result["findings"])
        self.assertEqual(result["capability_count_after"],175)
        self.assertFalse(result["current_host_runtime_promotion_claimed"])
    def test_canonical_mutation_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for path in gate.PATHS.values():
                (root/path).parent.mkdir(parents=True,exist_ok=True)
                (root/path).write_bytes((ROOT/path).read_bytes())
            path=root/gate.PATHS["c"]
            data=json.loads(path.read_text(encoding="utf-8"))
            data["fast_compose_application"]["auto_flatten"]=True
            data["authority_boundaries"]["full_nle"]="CFA3_OPENVID_SHARED"
            path.write_text(json.dumps(data),encoding="utf-8")
            result=gate.gate(root)
            self.assertEqual(result["status"],"FAIL")
            self.assertTrue(any(f["code"]=="OPENVID-SHARED-ROUNDTRIP" for f in result["findings"]))

if __name__=="__main__":
    unittest.main()
