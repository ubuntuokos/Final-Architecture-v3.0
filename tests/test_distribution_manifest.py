import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_distribution_manifest import build_manifest
class DistributionManifestTests(unittest.TestCase):
    def test_excluded_reference_does_not_create_notice(self):
        m=build_manifest([{"subject_id":"x","class":"REFERENCE_ONLY","release_bundle_status":"EXCLUDED"}]);self.assertEqual(m["included"],[]);self.assertEqual(m["third_party_notices"],[])
if __name__=="__main__":unittest.main()
