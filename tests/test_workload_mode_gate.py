import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_workload_mode_gate import GATESET_ID,MANDATORY_PROFILES,gate

class WorkloadModeTests(unittest.TestCase):
    def test_static_gate(self):
        r=gate(ROOT)
        self.assertEqual("PASS",r["result"],r["findings"])
        self.assertEqual(0,r["capability_delta"])
        self.assertEqual(0,r["authority_delta"])
        self.assertFalse(r["current_host_runtime_promotion_claim"])

    def test_mandatory_all_profiles_and_no_bypass(self):
        row=json.loads((ROOT/"canonical/FA3-MANDATORY-CORE-COMPONENTS-001.json").read_text())
        self.assertTrue(MANDATORY_PROFILES.issubset(set(row["profiles"])))
        comp=next(x for x in row["components"] if x["id"]=="workload-mode")
        self.assertFalse(comp["optional"])
        self.assertFalse(comp["bypassable"])
        self.assertTrue(comp["required_for_all_profiles"])

    def test_fa3_hrb_authority_is_preserved(self):
        row=json.loads((ROOT/"canonical/profiles/FA3-WORKLOAD-MODE-FRAMEWORK-001.json").read_text())
        self.assertEqual("FA3-AUTH-HOST-RESOURCE-BROKER-001",row["authority"]["when_fa3_present"])
        self.assertTrue(row["authority"]["fa3_parallel_resource_authority_forbidden"])

    def test_global_indicator_is_real_backed_and_accessible(self):
        main=(ROOT/"apps/fa3-control-center/qml/Main.qml").read_text()
        indicator=(ROOT/"apps/fa3-control-center/qml/WorkloadModeIndicator.qml").read_text()
        service=(ROOT/"apps/fa3-control-center/src/WorkloadModeStateService.cpp").read_text()
        self.assertIn("WorkloadModeIndicator {",main)
        self.assertIn("stateProvider: fa3WorkloadMode",main)
        self.assertIn("Accessible.name",indicator)
        self.assertIn("StateChanged",service)
        self.assertIn("QDBusInterface",service)

    def test_no_physical_runtime_overclaim(self):
        mat=json.loads((ROOT/"canonical/materialization/FA3-WORKLOAD-MODE-MATERIALIZATION-001.json").read_text())
        self.assertFalse(mat["current_host_runtime_promotion_claim"])
        self.assertTrue(mat["deferred_physical_scope"])

if __name__=="__main__":
    unittest.main()
