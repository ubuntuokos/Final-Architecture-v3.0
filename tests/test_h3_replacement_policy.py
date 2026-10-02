import json
import unittest
from pathlib import Path
from fa3_h3_replacement_gate import gate
from fa3_release_baseline import module_active_capability_count

ROOT=Path(__file__).resolve().parents[1]
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))

class H3ReplacementPolicyTests(unittest.TestCase):
    def test_h3_retired_and_removed(self):
        h3=load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        profile=load("canonical/profiles/FA3-VIDEO-001.json")
        video=load("canonical/video-enforcement.json")
        self.assertEqual(h3["status"],"RETIRED_REFERENCE_ONLY")
        self.assertTrue(h3["runtime_execution_forbidden"])
        self.assertNotIn(h3["id"],profile["providers"])
        self.assertNotIn(h3["id"],video["provider_ids"])

    def test_v2_chain_reuses_existing_authorities(self):
        p=load("canonical/h3-replacement-enforcement.json")
        chain=p["replacement"]["mandatory_execution_chain"]
        for item in ("FA3-AUTH-MODEL-ROUTER-001","FA3-WORKLOAD-MODE-CONTRACTS-001","FA3-AUTH-HOST-RESOURCE-BROKER-001","FA3-VIDEO-PROVIDER-LIFECYCLE-BACKEND-CACHE-CONTRACTS-001","HrbResourceLeaseSetProjection"):
            self.assertIn(item,chain)
        self.assertEqual(module_active_capability_count(__file__),175)
        self.assertEqual(p["capability_delta"],0)
        self.assertEqual(p["authority_delta"],0)

    def test_published_1354_donor_snapshot_and_usage_edges(self):
        a=load("canonical/assessments/FA3-H3-REPLACEMENT-REUSE-ASSESSMENT-001.json")
        self.assertEqual(a["donor_planning_snapshot"]["donor_registry_entry_count"],1354)
        self.assertEqual(a["donor_planning_snapshot"]["donor_registry_blob_sha"],"804786e96c66ef6c4397b1471e52a6594473bb20")
        self.assertEqual(len(a["adopted_pattern_donors"]),4)
        links=load("canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
        ids={r["id"] for r in links["donor_usage_records"]}
        for row in a["adopted_pattern_donors"]:
            self.assertIn(row["usage_edge_id"],ids)

    def test_static_gate(self):
        r=gate(ROOT)
        self.assertEqual(r["result"],"PASS",r["errors"])
        self.assertFalse(r["current_host_runtime_claim"])

if __name__=="__main__": unittest.main()
