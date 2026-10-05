import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_donor_readiness import (
    BATCH_DECISION,
    BATCH_ROLE,
    DONOR_DELTA_PREFIXES,
    _candidate_manifest_paths,
)

class DonorBatchFinalizerBootstrapTests(unittest.TestCase):
    def test_cfa3_batch_delta_prefix_is_recognized(self):
        self.assertIn("canonical/deltas/CFA3-DONOR-", DONOR_DELTA_PREFIXES)

    def test_known_non_batch_pr_never_falls_back_to_local_batch_manifest(self):
        candidate = {
            "number": 671,
            "file_paths": [
                "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
                "canonical/deltas/FA3-DONOR-PHRESHOS-ORG-2026-10-04.json",
            ],
        }
        self.assertEqual(_candidate_manifest_paths(ROOT, candidate), [])

    def test_batch_candidate_uses_its_declared_cfa3_manifest(self):
        path = "canonical/deltas/CFA3-DONOR-BACKLOG-CONSOLIDATION-2026-10-04.json"
        self.assertEqual(_candidate_manifest_paths(ROOT, {"number": 705, "file_paths": [path]}), [path])

    def test_cross_pr_revalidation_is_batch_aware_on_published_main(self):
        text = (ROOT / ".github/workflows/fa3-donor-intake-revalidation.yml").read_text()
        self.assertIn("'canonical/deltas/CFA3-DONOR-*'", text)
        self.assertIn('gate(Path(".").resolve(),"intake",token=token)', text)
        self.assertIn("batch finalizer", text.lower())

    def test_bootstrap_has_no_registry_materialization(self):
        decision = json.loads((ROOT / "canonical/decisions/CFA3-DEC-DONOR-BATCH-FINALIZER-BOOTSTRAP-2026-10-05.json").read_text())
        self.assertFalse(decision["scope"]["donor_registry_mutation"])
        self.assertEqual(decision["scope"]["donor_entry_delta"], 0)
        self.assertEqual(decision["scope"]["capability_baseline"], 175)
        self.assertEqual(decision["scope"]["authority_delta"], 0)
        self.assertEqual(BATCH_DECISION, "canonical/decisions/CFA3-DEC-DONOR-INTAKE-BATCH-ACCELERATION-2026-10-04.json")
        self.assertEqual(BATCH_ROLE, "CANONICAL_ROLLING_BATCH_FINALIZER")

if __name__ == "__main__":
    unittest.main()
