"""FA3 donor readiness negative and source-identity regressions."""
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from fa3_donor_readiness import (inspect_registry,pending_prs,gate,is_donor_pr,
    is_donor_intake_pr,REGISTRY,REJECTION_AUDIT,git_blob_sha)

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
    audit=root/REJECTION_AUDIT;audit.parent.mkdir(parents=True,exist_ok=True)
    audit.write_text(json.dumps({"id":"FA3-DONOR-REJECTION-AUDIT-001","entries":[]}))
    return t,root,p
class Tests(unittest.TestCase):
    def test_real_repository_invariants(self):
        r=inspect_registry(Path(__file__).resolve().parents[1])
        self.assertEqual(r["findings"],[])
        self.assertGreaterEqual(r["count"],1059)
    def test_rejected_donor_cannot_remain_in_active_registry(self):
        t,root,p=fixture()
        with t:
            d=json.loads(p.read_text());d["entries"][0]["status"]="REJECTED"
            p.write_text(json.dumps(d))
            findings=inspect_registry(root)["findings"]
            self.assertTrue(any(x.startswith("INVALID_STATUS:") for x in findings))

    def test_rejected_donor_reentry_requires_verified_safe_evidence(self):
        t,root,p=fixture()
        with t:
            row=json.loads(p.read_text())["entries"][0]
            audit=root/REJECTION_AUDIT
            audit.write_text(json.dumps({
                "id":"FA3-DONOR-REJECTION-AUDIT-001",
                "entries":[{"donor":row}]
            }))
            findings=inspect_registry(root)["findings"]
            self.assertTrue(any(
                x.startswith("REJECTED_DONOR_REENTRY_WITHOUT_VERIFIED_SAFE_EVIDENCE:")
                for x in findings))
            d=json.loads(p.read_text())
            d["entries"][0]["security_reentry_evidence"]={
                "status":"VERIFIED_SAFE",
                "evidence_refs":["canonical/evidence/example.json"]
            }
            p.write_text(json.dumps(d))
            self.assertEqual(inspect_registry(root)["findings"],[])

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
    def test_maintenance_exempt_from_application_preflights_and_live_pr_scan(self):
        t,root,_=fixture()
        with t:
            def forbidden_live_scan(_):
                self.fail("maintenance must not require application preflight or live PR scan")
            x=gate(root,"maintenance",get=forbidden_live_scan,
                   assessment=None,plan=None,approval=None,pr_number=None)
            self.assertEqual(x["result"],"MAINTENANCE_INTEGRITY_PASS")
            self.assertEqual(x["pending_prs"],None)
            self.assertFalse(x["planning_allowed"])
            self.assertFalse(x["execution_allowed"])
            self.assertFalse(x["finalization_allowed"])

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
            ".github/workflows/fa3-permanent-enforcement.yml",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(is_donor_pr({"title": "Generic media feature"},
                                            [{"filename": path}]))
        self.assertFalse(is_donor_pr(
            {"title": "Generic media feature"},
            [{"filename": "canonical/assessments/FA3-MEDIA-REUSE-ASSESSMENT-001.json"}]))
        self.assertTrue(is_donor_pr({"title": "Donor source review"}, []))

    def test_governance_and_reference_only_prs_do_not_claim_intake(self):
        governance = [{"filename":"src/fa3_donor_readiness.py"},
                      {"filename":"docs/donor-repair/DONOR_READINESS.md"},
                      {"filename":".github/workflows/fa3-donor-serialization.yml"}]
        reference_only = [{"filename":"canonical/references/FA3-OLD-DONOR-REFERENCE.json"}]
        self.assertTrue(is_donor_pr({"title":"Donor governance correction"},governance))
        self.assertFalse(is_donor_intake_pr({"title":"Donor governance correction"},governance))
        self.assertTrue(is_donor_pr({"title":"Generic feature"},reference_only))
        self.assertFalse(is_donor_intake_pr({"title":"Generic feature"},reference_only))
        self.assertTrue(is_donor_intake_pr({"title":"Generic feature"},[{"filename":REGISTRY}]))
        self.assertTrue(is_donor_intake_pr({"title":"Generic feature"},
            [{"filename":"canonical/deltas/FA3-DONOR-NEW-SOURCES.json"}]))
        with self.assertRaises(ValueError):
            is_donor_intake_pr({"title":"Unknown"},[{"filename":None}])

    def test_governance_pr_does_not_block_new_intake_or_steal_slot(self):
        t,root,_=fixture()
        with t:
            def get(s):
                if "/branches/main" in s:
                    return {"commit":{"sha":"a"*40}}
                if "pulls?state=open" in s:
                    return [
                        {"number":547,"title":"Donor governance correction",
                         "head":{"sha":"b"*40}},
                        {"number":548,"title":"Donor: owner-marked links",
                         "head":{"sha":"c"*40}},
                    ]
                if "/pulls/547/files?" in s:
                    return [{"filename":"src/fa3_donor_readiness.py"},
                            {"filename":"docs/donor-repair/DONOR_READINESS.md"}]
                if "/pulls/548/files?" in s:
                    return [{"filename":REGISTRY}]
                raise AssertionError(s)
            allowed=gate(root,"intake",get=get,pr_number=548)
            self.assertEqual(allowed["result"],"EXCLUSIVE_DONOR_INTAKE_READY")
            self.assertEqual(allowed["active_donor_pr"],548)
            self.assertEqual([p["number"] for p in allowed["pending_intake_prs"]],[548])
            self.assertEqual([p["number"] for p in allowed["pending_prs"]],[547,548])
            blocked=gate(root,"intake",get=get,pr_number=547)
            self.assertEqual(blocked["result"],"BLOCKED")
            self.assertEqual(blocked["active_donor_pr"],548)

    def test_policy_only_open_pr_allows_initial_unclaimed_intake(self):
        t,root,_=fixture()
        with t:
            def get(s):
                if "/branches/main" in s:
                    return {"commit":{"sha":"a"*40}}
                if "pulls?state=open" in s:
                    return [{"number":547,"title":"Donor: policy only",
                             "head":{"sha":"b"*40}}]
                if "/pulls/547/files?" in s:
                    return [{"filename":"src/fa3_donor_readiness.py"}]
                raise AssertionError(s)
            ready=gate(root,"intake",get=get)
            self.assertEqual(ready["result"],"EXCLUSIVE_DONOR_INTAKE_READY")
            self.assertIsNone(ready["active_donor_pr"])
            self.assertEqual(ready["pending_intake_prs"],[])
            denied=gate(root,"intake",get=get,pr_number=547)
            self.assertIn("INTAKE_PR_NOT_OPEN_OR_NOT_DONOR",denied["findings"])

    def test_expansion_removal_and_sync_all_count_as_donor_maintenance(self):
        operations = [
            ("expansion", REGISTRY, "added"),
            ("removal", REGISTRY, "removed"),
            ("sync", "canonical/FA3-APPLICATION-DONOR-LINKS-001.json", "modified"),
            ("sync-source-key", "canonical/deltas/FA3-DONOR-MEDIA-INTAKE-2026-09-29.json", "modified"),
            ("sync-history", "docs/donor-repair/RECONCILIATION.md", "modified"),
        ]
        for operation, path, status in operations:
            with self.subTest(operation=operation, path=path):
                self.assertTrue(is_donor_pr({"title": "Generic metadata update"},
                                            [{"filename": path, "status": status}]))

    def test_explicit_historical_heads_exempt_without_weakening_new_work(self):
        from fa3_donor_readiness import EXEMPT_HISTORICAL_HEADS
        head=EXEMPT_HISTORICAL_HEADS[24]
        def get(url):
            if "pulls?state=open" in url:
                return [{"number":24,"title":"Historical donor PR","head":{"sha":head}},
                        {"number":31,"title":"Historical donor PR changed","head":{"sha":"f"*40}},
                        {"number":999,"title":"New donor PR","head":{"sha":"a"*40}}]
            if "/pulls/" in url and "/files?" in url:
                return [{"filename":REGISTRY}]
            raise AssertionError(url)
        self.assertEqual([x["number"] for x in pending_prs(get)],[31,999])

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
    def test_pending_edit_allows_published_main_for_planning_preflight(self):
        t,root,p=fixture()
        with t:
            def get(s):
                if "/branches/main" in s:return {"commit":{"sha":"a"*40}}
                if "pulls?state=open" in s:return [{"number":8,"title":"New editor",
                                                     "head":{"sha":"a"*40}}]
                if "/pulls/8/files?" in s:return [{"filename":REGISTRY}]
                if "/contents/"+REGISTRY in s:return {"sha":git_blob_sha(p.read_bytes())}
                return []
            x=gate(root,"status",get=get)
            self.assertEqual(x["result"],"READY_FOR_SEPARATE_FA3_ADMISSION_GATES")
            self.assertEqual(x["registry_snapshot"],"PUBLISHED_MAIN_ONLY")
            self.assertEqual(x["pending_prs"][0]["number"],8)
            self.assertNotIn("PENDING_DONOR_MAINTENANCE",x["findings"])
            self.assertFalse(x["planning_allowed"])

    def test_second_conversation_intake_waits_for_oldest_donor_pr(self):
        t,root,p=fixture()
        with t:
            def get(s):
                if "/branches/main" in s:return {"commit":{"sha":"a"*40}}
                if "pulls?state=open" in s:return [
                    {"number":8,"title":"donor intake from conversation A",
                     "head":{"sha":"a"*40}},
                    {"number":9,"title":"donor intake from conversation B",
                     "head":{"sha":"b"*40}}]
                if "/pulls/" in s and "/files?" in s:return [{"filename":REGISTRY}]
                raise AssertionError(s)
            first=gate(root,"intake",get=get,pr_number=8)
            self.assertEqual(first["result"],"EXCLUSIVE_DONOR_INTAKE_READY")
            second=gate(root,"intake",get=get,pr_number=9)
            self.assertEqual(second["result"],"BLOCKED")
            self.assertEqual(second["active_donor_pr"],8)
            self.assertIn("DONOR_INTAKE_IN_PROGRESS_WAIT_FOR_COMPLETION",
                          second["findings"])
            unclaimed=gate(root,"intake",get=get)
            self.assertEqual(unclaimed["result"],"BLOCKED")

    def test_intake_without_live_inventory_is_fail_closed(self):
        t,root,p=fixture()
        with t:
            self.assertEqual(gate(root,"intake",pr_number=10)["result"],"BLOCKED")

    def test_intake_pr_must_be_open_and_classified_donor(self):
        t,root,p=fixture()
        with t:
            def get(s):
                if "/branches/main" in s:return {"commit":{"sha":"a"*40}}
                return []
            x=gate(root,"intake",get=get,pr_number=10)
            self.assertIn("INTAKE_PR_NOT_OPEN_OR_NOT_DONOR",x["findings"])

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
