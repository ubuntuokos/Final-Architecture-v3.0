import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_distribution_adoption_gate import validate_record,canonical_registration
class DistributionAdoptionGateTests(unittest.TestCase):
    def test_reference_only_is_excluded(self):
        self.assertEqual(validate_record({"distribution_class":"REFERENCE_ONLY","product_bundle_allowed":False}),[])
    def test_reference_only_included_fails(self):
        self.assertTrue(validate_record({"distribution":{"class":"REFERENCE_ONLY","release_bundle_status":"INCLUDED"}}))
    def test_external_redistributable_needs_basis(self):
        self.assertTrue(validate_record({"distribution":{"class":"EXTERNAL_REDISTRIBUTABLE","release_bundle_status":"EXCLUDED"}}))
    def test_external_redistributable_with_basis_passes(self):
        self.assertEqual(validate_record({"distribution":{"class":"EXTERNAL_REDISTRIBUTABLE","classification_basis":"MIT_LICENSE","release_bundle_status":"EXCLUDED"}}),[])
    def test_new_external_record_requires_registry_entry(self):
        row={"id":"X","distribution":{"class":"USER_LOCAL_EXTERNAL","release_bundle_status":"EXCLUDED"}}
        self.assertTrue(canonical_registration(row,{"records":[]}))
        self.assertEqual(canonical_registration(row,{"records":[{"subject_id":"X","class":"USER_LOCAL_EXTERNAL","release_bundle_status":"EXCLUDED"}]}),[])
    def test_registry_class_mismatch_fails(self):
        row={"id":"X","distribution":{"class":"REFERENCE_ONLY","release_bundle_status":"EXCLUDED"}}
        self.assertTrue(canonical_registration(row,{"records":[{"subject_id":"X","class":"USER_LOCAL_EXTERNAL","release_bundle_status":"EXCLUDED"}]}))
if __name__=="__main__":unittest.main()
