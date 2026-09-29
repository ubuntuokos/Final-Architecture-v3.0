"""FA3 donor readiness negative and source-identity regressions."""
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from fa3_donor_readiness import inspect_registry,pending_prs,gate,is_donor_pr,REGISTRY,git_blob_sha

def source():
    v={"donor_id":"FA3-DONOR-X-001","source":{"normalized_key":"github:x/y"},
       "status":"CANDIDATE"}
    for k in ("authority","automatic_selection","automatic_fetch","automatic_install",
              "automatic_activation","automatic_dependency","automatic_code_import",
              "automatic_provider_admission","automatic_model_selection"):v[k]=False
    return v
def fixture():
    t=tempfile.TemporaryDirectory();root=Path(t.name);p=root/REGISTRY;p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"id":"FA3-DONOR-REFERENCE-REGISTRY-001",
       "capability_count":175,"backfill":{"entry_count":1},"entries":[source()]}))
    return t,root,p
class Tests(unittest.TestCase):
    def test_real_repository_invariants(self):
        r=inspect_registry(Path(__file__).resolve().parents[1])
        self.assertEqual(r["findings"],[])
        self.assertGreaterEqual(r["count"],1059)
    def test_duplicate_fails(self):
        t,root,p=fixture()
        with t:
            d=json.loads(p.read_text());d["entries"].append(source());d["backfill"]["entry_count"]=2
            p.write_text(json.dumps(d))
            self.assertEqual(gate(root,"maintenance")["result"],"BLOCKED")
    def test_maintenance_cannot_promote(self):
        t,root,p=fixture()
        with t:
            r=gate(root,"maintenance")
            self.assertEqual(r["result"],"MAINTENANCE_INTEGRITY_PASS")
            self.assertFalse(r["planning_allowed"])
    def test_no_live_proof_fails_closed(self):
        t,root,p=fixture()
        with t:self.assertEqual(gate(root,"status")["result"],"BLOCKED")
    def test_hidden_donor_reference_or_delta_edit_blocks(self):
        paths = [
            "canonical/references/FA3-AUTOM8AI-DONOR-REFERENCE-2026-09-28.json",
            "canonical/deltas/FA3-DONOR-MEDIA-INTAKE-2026-09-29.json",
            "docs/donor-new-upstream-2026-09-29.md",
            "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
            "src/fa3_application_donor_index.py",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(is_donor_pr({"title": "Generic media feature"},
                                            [{"filename": path}]))
        self.assertFalse(is_donor_pr(
            {"title": "Generic media feature"},
            [{"filename": "canonical/assessments/FA3-MEDIA-REUSE-ASSESSMENT-001.json"}]))
        self.assertTrue(is_donor_pr({"title": "Donor source review"}, []))

    def test_hidden_reference_in_live_scan(self):
        def get(url):
            if "pulls?state=open" in url:
                return [{"number": 435, "title": "Generic Media Studio",
                         "head": {"sha": "a" * 40}}]
            if "/pulls/435/files?" in url:
                return [{"filename": "canonical/references/FA3-AUTOM8AI-DONOR-REFERENCE-2026-09-28.json"}]
            raise AssertionError(url)
        self.assertEqual([r["number"] for r in pending_prs(get)], [435])

    def test_hidden_registry_edit_is_found(self):
        def get(s):
            if "pulls?state=open" in s:return [{"number":8,"title":"New editor",
                                                "head":{"sha":"a"*40}}]
            if "/pulls/8/files?" in s:return [{"filename":REGISTRY}]
            raise AssertionError(s)
        self.assertEqual([p["number"] for p in pending_prs(get)],[8])
    def test_pending_edit_denies_planning(self):
        t,root,p=fixture()
        with t:
            def get(s):
                if "/branches/main" in s:return {"commit":{"sha":"a"*40}}
                if "pulls?state=open" in s:return [{"number":8,"title":"New editor",
                                                     "head":{"sha":"a"*40}}]
                if "/pulls/8/files?" in s:return [{"filename":REGISTRY}]
            x=gate(root,"status",get=get)
            self.assertIn("PENDING_DONOR_MAINTENANCE",x["findings"])
    def test_zero_pending_does_not_allow_adoption_or_promotion(self):
        t,root,p=fixture()
        with t:
            def get(s):
                if "/branches/main" in s:return {"commit":{"sha":"a"*40}}
                if "/contents/"+REGISTRY in s:return {"sha":git_blob_sha(p.read_bytes())}
                return []
            x=gate(root,"status",get=get)
            self.assertEqual(x["result"],"READY_FOR_SEPARATE_FA3_ADMISSION_GATES")
            self.assertFalse(x["planning_allowed"])
            self.assertFalse(x["finalization_allowed"])
            self.assertIn("DONOR_ASSESSMENT_REQUIRED",gate(root,"entry",get=get)["findings"])
    def test_stale_main_snapshot_blocks_even_with_no_pending_prs(self):
        t,root,p=fixture()
        with t:
            def get(s):
                if "/branches/main" in s:return {"commit":{"sha":"a"*40}}
                if "/contents/"+REGISTRY in s:return {"sha":"b"*40}
                return []
            x=gate(root,"entry",get=get)
            self.assertEqual(x["result"],"BLOCKED")
            self.assertIn("STALE_CANONICAL_DONOR_SNAPSHOT",x["findings"])
            self.assertFalse(x["planning_allowed"])
    def test_missing_main_blob_fails_closed(self):
        t,root,p=fixture()
        with t:
            def get(s):
                if "/branches/main" in s:return {"commit":{"sha":"a"*40}}
                if "/contents/"+REGISTRY in s:return {}
                return []
            x=gate(root,"status",get=get)
            self.assertEqual(x["result"],"BLOCKED")
            self.assertTrue(any("PROOF_UNAVAILABLE:" in f for f in x["findings"]))
if __name__=="__main__":unittest.main()
