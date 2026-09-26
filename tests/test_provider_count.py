import json, tempfile, unittest
from pathlib import Path
from fa3_provider_count import derive

class ProviderCountTests(unittest.TestCase):
    def test_count_is_derived_not_fixed(self):
        td=tempfile.TemporaryDirectory()
        try:
            root=Path(td.name)
            d=root/"canonical/providers"
            d.mkdir(parents=True)
            for n in (1,2,3):
                (d/f"p{n}.json").write_text(json.dumps({"id":f"FA3-PROVIDER-TEST-{n:03d}"}))
            r=derive(root)
            self.assertEqual(r["provider_count"],3)
            self.assertFalse(r["provider_count_fixed"])
            self.assertTrue(r["capability_count_fixed"])
            self.assertEqual(r["capability_count"],175)
        finally:
            td.cleanup()

    def test_new_provider_increases_count_automatically(self):
        td=tempfile.TemporaryDirectory()
        try:
            root=Path(td.name)
            d=root/"canonical/providers"
            d.mkdir(parents=True)
            (d/"a.json").write_text(json.dumps({"id":"FA3-PROVIDER-A-001"}))
            self.assertEqual(derive(root)["provider_count"],1)
            (d/"b.json").write_text(json.dumps({"id":"FA3-PROVIDER-B-001"}))
            self.assertEqual(derive(root)["provider_count"],2)
        finally:
            td.cleanup()

if __name__=="__main__":
    unittest.main()
