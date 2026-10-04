import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_donor_readiness import (
    MAX_ACTIVE_CANONICAL_REGISTRY_MUTATION_PRS,
    MAX_ACTIVE_DONOR_INTAKES,
    batch_manifest_coverage,
)

REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
MANIFEST = ROOT / "canonical/deltas/CFA3-DONOR-BACKLOG-CONSOLIDATION-2026-10-04.json"
DECISION = ROOT / "canonical/decisions/CFA3-DEC-DONOR-INTAKE-BATCH-ACCELERATION-2026-10-04.json"
CONTRACT = ROOT / "canonical/contracts/FA3-DONOR-CHAT-INGEST-001.json"
POLICY = ROOT / "canonical/enforcement-policy.json"


class DonorBatchAccelerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_exact_backlog_union_and_baseline(self):
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(len(self.registry["entries"]), 1512)
        self.assertEqual(self.registry["backfill"]["entry_count"], 1512)
        self.assertEqual(self.manifest["parent_entry_count"], 1427)
        self.assertEqual(self.manifest["new_source_count"], 85)
        self.assertEqual(self.manifest["resulting_entry_count"], 1512)
        self.assertEqual(self.manifest["capability_delta"], 0)
        self.assertEqual(self.manifest["authority_delta"], 0)
        self.assertEqual(sum(x["contribution"] for x in self.manifest["source_prs"]), 85)
        self.assertEqual(len(self.manifest["source_prs"]), 15)

    def test_materialized_identities_are_unique_and_present(self):
        entries = self.registry["entries"]
        ids = [x["donor_id"] for x in entries]
        keys = [x["source"]["normalized_key"] for x in entries]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(keys), len(set(keys)))
        materialized = self.manifest["materialized"]
        self.assertEqual(len(materialized), 85)
        registry_ids = set(ids)
        registry_keys = set(keys)
        for row in materialized:
            self.assertIn(row["donor_id"], registry_ids)
            self.assertIn(row["normalized_key"], registry_keys)

    def test_exact_head_batch_coverage(self):
        pending = [
            {"number": row["pr"], "head_sha": row["head"], "intake": True}
            for row in self.manifest["source_prs"]
        ]
        pending.append({"number": 999999, "head_sha": "f" * 40, "intake": True})
        covered, missing = batch_manifest_coverage(ROOT, pending, 999999)
        self.assertEqual(missing, [])
        self.assertEqual(set(covered), {x["pr"] for x in self.manifest["source_prs"]})
        pending[0]["head_sha"] = "0" * 40
        _, mismatch = batch_manifest_coverage(ROOT, pending, 999999)
        self.assertEqual(mismatch, [self.manifest["source_prs"][0]["pr"]])

    def test_single_writer_batch_policy_is_canonical(self):
        self.assertEqual(MAX_ACTIVE_DONOR_INTAKES, 5)
        self.assertEqual(MAX_ACTIVE_CANONICAL_REGISTRY_MUTATION_PRS, 1)
        self.assertEqual(self.contract["max_active_canonical_registry_mutation_prs"], 1)
        self.assertTrue(self.contract["append_to_existing_open_batch_when_available"])
        serial = self.policy["donor_registry_serialization"]
        self.assertEqual(serial["max_active_canonical_registry_mutation_prs"], 1)
        self.assertEqual(serial["canonical_registry_mutation_mode"], "SINGLE_WRITER_BATCH")
        self.assertEqual(self.decision["rules"]["full_protected_gate_run_scope"], "FINAL_BATCH_HEAD_ONLY")

    def test_stale_pr_payload_is_not_admitted(self):
        stale = self.manifest["stale_branch_policy"]
        self.assertFalse(stale["direct_merge_or_rebase_of_superseded_source_prs"])
        self.assertTrue(stale["exact_head_history_preserved"])
        self.assertTrue(stale["donor_delta_only_rehydration"])
        self.assertFalse(stale["non_donor_payload_admitted"])


if __name__ == "__main__":
    unittest.main()
