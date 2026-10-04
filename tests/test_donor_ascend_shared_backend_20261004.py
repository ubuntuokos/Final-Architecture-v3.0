"""FIFO-waiting Ascend shared-backend donor intake."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-ASCEND-SHARED-BACKEND-2026-10-04.json"

EXPECTED_URLS = [
    "https://github.com/Ascend/pytorch",
    "https://github.com/Ascend/torchair",
    "https://github.com/triton-lang/triton-ascend",
    "https://github.com/Ascend/triton-ascend",
    "https://github.com/vllm-project/vllm-ascend",
    "https://github.com/Ascend/samples",
    "https://github.com/microsoft/onnxruntime",
    "https://www.hiascend.com/document/detail/en/CANNCommunityEdition/910/index/index.html",
]

EXPECTED_IDS = {
    "FA3-DONOR-ASCEND-PYTORCH-001",
    "FA3-DONOR-ASCEND-TORCHAIR-001",
    "FA3-DONOR-TRITON-LANG-TRITON-ASCEND-001",
    "FA3-DONOR-ASCEND-TRITON-ASCEND-LEGACY-001",
    "FA3-DONOR-VLLM-ASCEND-001",
    "FA3-DONOR-ASCEND-SAMPLES-001",
    "FA3-DONOR-MICROSOFT-ONNXRUNTIME-001",
    "FA3-DONOR-HUAWEI-CANN-DOCS-910-001",
}


class WaitingAscendDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))

    def test_delta_is_bound_to_verified_parent(self):
        d = self.delta
        self.assertEqual(d["schema"], "fa3.donor-intake-delta.v1")
        self.assertEqual(
            d["parent_main"],
            "b5052f6595a3fdad84ed7a06e6276f8af5a8dcd8",
        )
        self.assertEqual(
            d["parent_registry_blob_sha"],
            "1362d75186c6da74e5cf947fdf0b8867d462636a",
        )
        self.assertEqual(d["parent_entry_count"], 1427)
        self.assertFalse(d["canonical_registry_materialized"])
        self.assertTrue(d["waiting_queue_only"])

    def test_exact_processed_source_set_is_preserved(self):
        d = self.delta
        self.assertEqual(d["submitted_url_count"], 8)
        self.assertEqual(d["submitted_urls"], EXPECTED_URLS)
        self.assertEqual(d["unique_source_count"], 8)
        self.assertEqual(d["new_source_count"], 8)
        self.assertEqual(d["proposed_entry_count"], 1435)
        self.assertIn("OWNER_APPROVED_IMPLEMENTATION_PLAN_EXCEPTION", d["approval_mode"])

    def test_planned_identities_are_complete_and_unique(self):
        ids = {row["donor_id"] for row in self.delta["canonical_identities"]}
        self.assertEqual(ids, EXPECTED_IDS)
        keys = [row["normalized_key"] for row in self.delta["canonical_identities"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_triton_legacy_source_is_superseded_only(self):
        rows = {row["donor_id"]: row for row in self.delta["canonical_identities"]}
        legacy = rows["FA3-DONOR-ASCEND-TRITON-ASCEND-LEGACY-001"]
        self.assertEqual(legacy["status"], "SUPERSEDED")
        self.assertEqual(legacy["mode"], "MIGRATION_PROVENANCE_ONLY")
        self.assertEqual(
            legacy["superseded_by"],
            "FA3-DONOR-TRITON-LANG-TRITON-ASCEND-001",
        )

    def test_cann_is_external_reference_not_bundled_runtime(self):
        rows = {row["donor_id"]: row for row in self.delta["canonical_identities"]}
        cann = rows["FA3-DONOR-HUAWEI-CANN-DOCS-910-001"]
        self.assertEqual(cann["kind"], "VENDOR_DOCUMENTATION")
        self.assertEqual(cann["mode"], "EXTERNAL_RUNTIME_DOCUMENTATION")
        self.assertEqual(cann["source_copying"], "REFERENCE_ONLY")
        self.assertIn("BLOCKED", cann["runtime_bundling"])
        self.assertFalse(self.delta["boundaries"]["cann_bundling_authorized"])

    def test_pending_records_are_not_prematurely_canonical(self):
        current_ids = {e["donor_id"] for e in self.registry["entries"]}
        self.assertTrue(EXPECTED_IDS.isdisjoint(current_ids))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.registry["entries"]))
        self.assertEqual(len(self.registry["entries"]), 1427)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.delta["boundaries"]["canonical_planning_visibility"])

    def test_no_implementation_or_runtime_admission(self):
        b = self.delta["boundaries"]
        for key in (
            "automatic_fetch",
            "automatic_install",
            "automatic_activation",
            "automatic_code_import",
            "automatic_dependency",
            "automatic_provider_admission",
            "automatic_model_selection",
            "usage_edge_created",
            "capability_count_change",
            "authority_change",
            "runtime_change",
            "current_host_pass_claimed",
            "canonical_planning_visibility",
            "cann_bundling_authorized",
        ):
            self.assertFalse(b[key])
        self.assertEqual(self.delta["capability_baseline"], 175)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)
        self.assertEqual(self.delta["usage_edges_created"], 0)

    def test_fifo_state_is_explicit(self):
        d = self.delta
        self.assertEqual(d["max_active_donor_intakes"], 5)
        self.assertEqual(d["observed_active_window"], [651, 657, 663, 664, 671])
        self.assertEqual(d["canonical_plan_exception_policy_pr"], 701)
        self.assertIn("FIFO_WAITING", d["expected_initial_state"])


if __name__ == "__main__":
    unittest.main()
