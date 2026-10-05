import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_donor_readiness import (
    MAX_ACTIVE_CANONICAL_REGISTRY_MUTATION_PRS,
    MAX_ACTIVE_DONOR_INTAKES,
    _candidate_manifest_paths,
    batch_manifest_coverage,
    git_blob_sha,
    inspect_registry,
    validate_batch_finalizer,
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
        self.assertEqual(len(self.registry["entries"]), 1548)
        self.assertEqual(self.registry["backfill"]["entry_count"], 1548)
        self.assertEqual(self.manifest["parent_entry_count"], 1427)
        self.assertEqual(self.manifest["new_source_count"], 121)
        self.assertEqual(self.manifest["resulting_entry_count"], 1548)
        self.assertEqual(self.manifest["capability_delta"], 0)
        self.assertEqual(self.manifest["authority_delta"], 0)
        self.assertEqual(sum(x["contribution"] for x in self.manifest["source_prs"]), 121)
        self.assertEqual(len(self.manifest["source_prs"]), 18)

    def test_materialized_identities_are_unique_and_present(self):
        entries = self.registry["entries"]
        ids = [x["donor_id"] for x in entries]
        keys = [x["source"]["normalized_key"] for x in entries]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(keys), len(set(keys)))
        materialized = self.manifest["materialized"]
        self.assertEqual(len(materialized), 121)
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

    def test_live_queue_stale_dedup_and_existing_enrichment(self):
        reconciled = self.manifest["reconciled_existing_identities"]
        self.assertEqual(len(reconciled), 7)
        by_key = {x["source"]["normalized_key"]: x for x in self.registry["entries"]}
        self.assertEqual(by_key["github:microsoft/onnxruntime"]["donor_id"], "FA3-DONOR-MICROSOFT-ONNX-RUNTIME-001")
        self.assertEqual(by_key["github:microsoft/onnxruntime"]["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(by_key["github:microsoft/directxshadercompiler"]["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(by_key["github:doitsujin/dxvk"]["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(by_key["github:microsoft/directxtex"]["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(by_key["github:microsoft/directx-headers"]["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(by_key["github:opencomputeproject/opennetworklinux"]["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(next(x for x in self.manifest["source_prs"] if x["pr"] == 706)["head"], "dd62e05810f1212a8489f4aa7cb2e033a801766d")
        self.assertEqual(next(x for x in self.manifest["source_prs"] if x["pr"] == 707)["head"], "af8cd23982e27fdda0cc315ffd9e1186459f532f")
        self.assertEqual(by_key["github:gpuopen-librariesandsdks"]["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(by_key["github:intel/intel-graphics-compiler"]["status"], "ACCEPTED_REFERENCE")

    def test_batch_finalizer_manifest_is_exactly_bound(self):
        self.assertEqual(self.manifest["batch_role"], "CANONICAL_ROLLING_BATCH_FINALIZER")
        self.assertEqual(self.manifest["batch_finalizer_pr"], 705)
        self.assertEqual(
            self.manifest["decision_ref"],
            "canonical/decisions/CFA3-DEC-DONOR-INTAKE-BATCH-ACCELERATION-2026-10-04.json",
        )
        candidate = {
            "number": 705,
            "head_sha": "b" * 40,
            "head_repo_full_name": "ubuntuokos/Final-Architecture-v3.0",
            "file_paths": [
                "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
                "canonical/deltas/CFA3-DONOR-BACKLOG-CONSOLIDATION-2026-10-04.json",
            ],
            "registry_blob_sha": git_blob_sha(REGISTRY.read_bytes()),
            "registry_mutation": True,
            "intake": True,
        }
        pending = [
            {
                "number": row["pr"],
                "head_sha": row["head"],
                "registry_mutation": True,
                "intake": True,
            }
            for row in self.manifest["source_prs"]
        ] + [candidate]
        check = validate_batch_finalizer(
            ROOT, pending, candidate, inspect_registry(ROOT), require_complete=True
        )
        self.assertEqual(check["findings"], [])
        bad = dict(candidate)
        bad["registry_blob_sha"] = "f" * 40
        broken = validate_batch_finalizer(
            ROOT, pending[:-1] + [bad], bad, inspect_registry(ROOT), require_complete=True
        )
        self.assertIn("BATCH_RESULTING_REGISTRY_BLOB_MISMATCH", broken["findings"])

    def test_known_non_batch_candidate_never_falls_back_to_local_batch_manifest(self):
        candidate = {
            "number": 651,
            "file_paths": [
                "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
                "canonical/deltas/FA3-DONOR-EXAMPLE-2026-10-04.json",
            ],
        }
        self.assertEqual(_candidate_manifest_paths(ROOT, candidate), [])
        local_only = _candidate_manifest_paths(ROOT, {"number": 705})
        self.assertIn(
            "canonical/deltas/CFA3-DONOR-BACKLOG-CONSOLIDATION-2026-10-04.json",
            local_only,
        )

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
