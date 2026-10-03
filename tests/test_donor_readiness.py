"""FA3 donor readiness negative and source-identity regressions."""
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import fa3_donor_readiness as readiness
from fa3_donor_readiness import (inspect_registry,pending_prs,gate,is_donor_pr,
    is_donor_intake_pr,effective_donor_intake_pr,donor_intake_workload,
    MAX_ACTIVE_DONOR_INTAKES,REGISTRY,REJECTION_AUDIT,git_blob_sha,planning_snapshot_findings)

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
            self.assertEqual(allowed["result"],"DONOR_INTAKE_READY_TO_FINALIZE")
            self.assertEqual(allowed["active_donor_pr"],548)
            self.assertEqual(allowed["active_donor_prs"],[548])
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
            self.assertEqual(ready["result"],"DONOR_INTAKE_SLOT_AVAILABLE")
            self.assertIsNone(ready["active_donor_pr"])
            self.assertEqual(ready["pending_intake_prs"],[])
            self.assertEqual(ready["available_intake_slots"],MAX_ACTIVE_DONOR_INTAKES)
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

    def test_stale_base_byte_identical_donor_file_does_not_steal_intake_slot(self):
        donor_sha="a"*40
        files=[{"filename":REGISTRY,"sha":donor_sha}]
        def get(url):
            if "/contents/"+REGISTRY in url:
                return {"sha":donor_sha}
            raise AssertionError(url)
        self.assertTrue(is_donor_intake_pr({"title":"stale current-host"},files))
        self.assertFalse(effective_donor_intake_pr(
            {"title":"stale current-host","head":{"sha":"b"*40}},files,get))

    def test_real_donor_delta_still_claims_intake_slot(self):
        files=[{"filename":REGISTRY,"sha":"b"*40}]
        def get(url):
            if "/contents/"+REGISTRY in url:
                return {"sha":"a"*40}
            raise AssertionError(url)
        self.assertTrue(effective_donor_intake_pr(
            {"title":"Donor intake","head":{"sha":"c"*40}},files,get))

    def test_stale_base_pr_remains_visible_but_not_pending_intake(self):
        donor_sha="a"*40
        def get(url):
            if "pulls?state=open" in url:
                return [{"number":559,"title":"Current Host stale base",
                         "head":{"sha":"b"*40}}]
            if "/pulls/559/files?" in url:
                return [{"filename":REGISTRY,"sha":donor_sha}]
            if "/contents/"+REGISTRY in url:
                return {"sha":donor_sha}
            raise AssertionError(url)
        rows=pending_prs(get)
        self.assertEqual([r["number"] for r in rows],[559])
        self.assertFalse(rows[0]["intake"])

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

    def test_active_intakes_finalize_by_size_then_fifo(self):
        t,root,p=fixture()
        with t:
            def get(s):
                if "/branches/main" in s:return {"commit":{"sha":"a"*40}}
                if "pulls?state=open" in s:return [
                    {"number":8,"title":"large donor intake","head":{"sha":"a"*40}},
                    {"number":9,"title":"small donor intake A","head":{"sha":"b"*40}},
                    {"number":10,"title":"small donor intake B","head":{"sha":"c"*40}}]
                if "/pulls/8/files?" in s:return [{"filename":REGISTRY,"changes":50}]
                if "/pulls/9/files?" in s:return [{"filename":REGISTRY,"changes":5}]
                if "/pulls/10/files?" in s:return [{"filename":REGISTRY,"changes":5}]
                raise AssertionError(s)
            small=gate(root,"intake",get=get,pr_number=9)
            self.assertEqual(small["result"],"DONOR_INTAKE_READY_TO_FINALIZE")
            self.assertEqual(small["finalization_order"],[9,10,8])
            self.assertEqual(small["intake_workload_units"],5)
            tied=gate(root,"intake",get=get,pr_number=10)
            self.assertEqual(tied["result"],"BLOCKED")
            self.assertEqual(tied["next_finalizable_donor_pr"],9)
            self.assertIn("DONOR_INTAKE_ACTIVE_WAIT_FOR_SMALLER_FINALIZATION",
                          tied["findings"])
            large=gate(root,"intake",get=get,pr_number=8)
            self.assertEqual(large["result"],"BLOCKED")
            unclaimed=gate(root,"intake",get=get)
            self.assertEqual(unclaimed["result"],"DONOR_INTAKE_SLOT_AVAILABLE")
            self.assertEqual(unclaimed["available_intake_slots"],2)

    def test_rolling_five_slot_window_refills_from_fifo_wait_queue(self):
        t,root,p=fixture()
        with t:
            state={"include_first":True}
            def open_prs():
                nums=[20,21,22,23,24,25] if state["include_first"] else [21,22,23,24,25]
                return [{"number":n,"title":"donor intake","head":{"sha":str(n)[-1]*40}}
                        for n in nums]
            def get(s):
                if "/branches/main" in s:return {"commit":{"sha":"a"*40}}
                if "pulls?state=open" in s:return open_prs()
                if "/pulls/" in s and "/files?" in s:
                    n=int(s.split("/pulls/")[1].split("/")[0])
                    return [{"filename":REGISTRY,"changes":n-19}]
                raise AssertionError(s)
            sixth=gate(root,"intake",get=get,pr_number=25)
            self.assertEqual(sixth["result"],"BLOCKED")
            self.assertEqual(sixth["active_donor_prs"],[20,21,22,23,24])
            self.assertEqual(sixth["waiting_donor_prs"],[25])
            self.assertIn("DONOR_INTAKE_ACTIVE_WINDOW_FULL_WAIT_FOR_SLOT",
                          sixth["findings"])
            state["include_first"]=False
            refilled=gate(root,"intake",get=get,pr_number=25)
            self.assertEqual(refilled["active_donor_prs"],[21,22,23,24,25])
            self.assertEqual(refilled["waiting_donor_prs"],[])
            self.assertNotIn("DONOR_INTAKE_ACTIVE_WINDOW_FULL_WAIT_FOR_SLOT",
                             refilled["findings"])
            self.assertIn("DONOR_INTAKE_ACTIVE_WAIT_FOR_SMALLER_FINALIZATION",
                          refilled["findings"])

    def test_owner_approved_active_intake_limit_is_five(self):
        self.assertEqual(MAX_ACTIVE_DONOR_INTAKES,5)

    def test_intake_workload_uses_canonical_mutation_stats_only(self):
        files=[
            {"filename":REGISTRY,"changes":7},
            {"filename":"canonical/deltas/FA3-DONOR-X.json","additions":3,"deletions":2},
            {"filename":"docs/donor-x.md","changes":1000},
        ]
        self.assertEqual(donor_intake_workload(files),12)
        self.assertEqual(donor_intake_workload([{"filename":REGISTRY}]),1)

    def test_stale_base_files_are_excluded_from_live_workload(self):
        stale_delta="canonical/deltas/FA3-DONOR-STALE.json"
        def get(url):
            if "pulls?state=open" in url:
                return [{"number":77,"title":"Donor intake",
                         "head":{"sha":"d"*40,"ref":"fa3/donor-77",
                                 "repo":{"full_name":"ubuntuokos/Final-Architecture-v3.0"}}}]
            if "/pulls/77/files?" in url:
                return [
                    {"filename":REGISTRY,"sha":"b"*40,"changes":7},
                    {"filename":stale_delta,"sha":"c"*40,"changes":500},
                ]
            if "/contents/"+REGISTRY in url:
                return {"sha":"a"*40}
            if "/contents/"+stale_delta in url:
                return {"sha":"c"*40}
            raise AssertionError(url)
        row=pending_prs(get)[0]
        self.assertTrue(row["intake"])
        self.assertEqual(row["workload_units"],7)
        self.assertEqual(row["head_ref"],"fa3/donor-77")
        self.assertEqual(row["head_repo_full_name"],"ubuntuokos/Final-Architecture-v3.0")

    def test_cli_ready_results_return_success(self):
        for result in ("DONOR_INTAKE_SLOT_AVAILABLE","DONOR_INTAKE_READY_TO_FINALIZE"):
            with self.subTest(result=result), \
                 patch.object(readiness,"gate",return_value={"result":result}), \
                 patch.object(sys,"argv",["fa3_donor_readiness.py"]):
                self.assertEqual(readiness.main(),0)

    def test_cross_pr_revalidation_and_operator_docs_match_rolling_window(self):
        root=Path(__file__).resolve().parents[1]
        workflow=(root/".github/workflows/fa3-donor-serialization.yml").read_text()
        guide=(root/"docs/donor-repair/DONOR_READINESS.md").read_text()
        self.assertIn("pull_request_target:",workflow)
        self.assertIn("actions: write",workflow)
        self.assertIn("checks: write",workflow)
        self.assertIn("canonical-regression / P0",workflow)
        self.assertIn("fa3-permanent-enforcement.yml/dispatches",workflow)
        self.assertNotIn("A second intake remains BLOCKED",guide)

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
    def test_planning_snapshot_must_match_live_published_main(self):
        reg={"id":"FA3-DONOR-REFERENCE-REGISTRY-001","entries":[source()]}
        row={"donor_planning_snapshot":{
            "published_main_commit":"a"*40,
            "donor_registry_id":reg["id"],
            "donor_registry_blob_sha":"b"*40,
            "donor_registry_sha256":"c"*64,
            "donor_registry_entry_count":1}}
        self.assertEqual(planning_snapshot_findings(row,"c"*64,reg,"a"*40,"b"*40),[])
        stale=planning_snapshot_findings(row,"c"*64,reg,"d"*40,"b"*40)
        self.assertIn("DONOR_PLANNING_SNAPSHOT_MISMATCH:published_main_commit",stale)

if __name__=="__main__":unittest.main()
