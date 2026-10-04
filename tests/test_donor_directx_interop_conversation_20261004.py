"""FIFO-waiting DirectX/Linux interoperability donor intake."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-DIRECTX-INTEROP-CONVERSATION-2026-10-04.json"

EXISTING = {
    "FA3-DONOR-MICROSOFT-DIRECTXSHADERCOMPILER-001",
    "FA3-DONOR-DOITSUJIN-DXVK-001",
    "FA3-DONOR-MICROSOFT-DIRECTXTEX-001",
    "FA3-DONOR-MICROSOFT-DIRECTX-HEADERS-001",
}

NEW = {
    "FA3-DONOR-MICROSOFT-DIRECTXTK-001",
    "FA3-DONOR-EDUAPPS-CDG-OPENDX-001",
    "FA3-DONOR-MICROSOFT-DIRECTXTK12-001",
    "FA3-DONOR-MICROSOFT-DIRECTX-LINUX-WSL-ARTICLE-001",
    "FA3-DONOR-MICROSOFT-DIRECTML-001",
    "FA3-DONOR-OPENRA-ORG-001",
}


class WaitingDirectXInteropDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))

    def test_verified_parent_and_waiting_state(self):
        d = self.delta
        self.assertEqual(d["parent_main"], "b5052f6595a3fdad84ed7a06e6276f8af5a8dcd8")
        self.assertEqual(d["parent_registry_blob_sha"], "1362d75186c6da74e5cf947fdf0b8867d462636a")
        self.assertEqual(d["parent_entry_count"], 1427)
        self.assertFalse(d["canonical_registry_materialized"])
        self.assertTrue(d["waiting_queue_only"])

    def test_exact_owner_marked_batch_is_preserved(self):
        d = self.delta
        self.assertEqual(d["submitted_url_count"], 10)
        self.assertEqual(len(d["submitted_urls"]), 10)
        self.assertEqual(len(set(d["submitted_urls"])), 10)
        self.assertEqual(d["matched_existing_count"], 4)
        self.assertEqual(d["new_source_count"], 6)
        self.assertEqual(d["proposed_entry_count_after_slot_reconciliation"], 1433)
        self.assertIn("OWNER_EXPLICIT_DONORNAK_BATCH", d["approval_mode"])

    def test_existing_records_are_not_duplicated(self):
        current_ids = {e["donor_id"] for e in self.registry["entries"]}
        self.assertTrue(EXISTING.issubset(current_ids))
        matches = {e["donor_id"] for e in self.delta["existing_matches"]}
        self.assertEqual(matches, EXISTING)
        self.assertTrue(all(e["no_duplicate_record"] for e in self.delta["existing_matches"]))

    def test_new_records_are_not_prematurely_canonical(self):
        current_ids = {e["donor_id"] for e in self.registry["entries"]}
        planned = {e["donor_id"] for e in self.delta["planned_new_identities"]}
        self.assertEqual(planned, NEW)
        self.assertTrue(NEW.isdisjoint(current_ids))
        self.assertFalse(self.delta["boundaries"]["canonical_planning_visibility_for_new_sources"])

    def test_openra_is_discovery_index_only(self):
        rows = {e["donor_id"]: e for e in self.delta["planned_new_identities"]}
        row = rows["FA3-DONOR-OPENRA-ORG-001"]
        self.assertEqual(row["kind"], "GITHUB_ORGANIZATION")
        self.assertEqual(row["mode"], "DISCOVERY_INDEX")
        self.assertFalse(row["recursive_child_admission"])

    def test_runtime_and_authority_boundaries(self):
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
            "canonical_planning_visibility_for_new_sources",
            "application_local_directx_core_allowed",
            "vendor_specific_duplicate_directx_core_allowed",
        ):
            self.assertFalse(b[key])
        self.assertEqual(self.delta["capability_baseline"], 175)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)
        self.assertEqual(self.delta["usage_edges_created"], 0)

    def test_fifo_window_is_explicit(self):
        d = self.delta
        self.assertEqual(d["max_active_donor_intakes"], 5)
        self.assertEqual(d["observed_active_window"], [651, 657, 663, 664, 671])
        self.assertIn(704, d["observed_waiting_ahead"])
        self.assertIn("FIFO_WAITING", d["expected_initial_state"])

    def test_registry_count_integrity(self):
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.registry["entries"]))
        self.assertEqual(len(self.registry["entries"]), 1427)
        self.assertEqual(self.registry["capability_count"], 175)


if __name__ == "__main__":
    unittest.main()
