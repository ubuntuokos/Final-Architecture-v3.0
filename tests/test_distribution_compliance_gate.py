import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_distribution_compliance_gate import gate,good_external_descriptor,good_native_descriptor,release_bundle_allowed,declared_distribution_records
class DistributionComplianceTests(unittest.TestCase):
    def test_gate(self):self.assertEqual(gate(ROOT)["result"],"PASS")
    def test_valid_external_and_native_bundle(self):
        self.assertTrue(release_bundle_allowed(good_external_descriptor()));self.assertTrue(release_bundle_allowed(good_native_descriptor()))
    def test_all_distribution_declared_records_are_registered(self):
        registry=__import__("json").loads((ROOT/"canonical/distribution-registry.json").read_text())
        ids={r["subject_id"] for r in registry["records"]}
        declared=declared_distribution_records(ROOT)
        self.assertGreaterEqual(len(declared),12)
        self.assertTrue(all(r["subject_id"] in ids for r in declared))
if __name__=="__main__":unittest.main()
