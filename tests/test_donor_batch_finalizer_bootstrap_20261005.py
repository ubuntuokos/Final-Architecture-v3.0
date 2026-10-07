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
    REGISTRY,
    _candidate_manifest_paths,
    _published_batch_decision,
    is_donor_intake_pr,
    validate_batch_finalizer,
)

class DonorBatchFinalizerBootstrapTests(unittest.TestCase):
    def test_cfa3_batch_manifest_is_governed_metadata_not_a_standalone_intake_slot(self):
        path = "canonical/deltas/CFA3-DONOR-BACKLOG-CONSOLIDATION-2026-10-04.json"
        self.assertNotIn("canonical/deltas/CFA3-DONOR-", DONOR_DELTA_PREFIXES)
        self.assertFalse(is_donor_intake_pr({"title": "batch metadata"}, [{"filename": path}]))

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
        self.assertIn("finalizer=order[0]", text)
        self.assertIn("refreshed_finalizer=refreshed_order[0] if refreshed_order else None", text)

    def test_batch_approval_is_loaded_only_from_published_tree(self):
        decision = _published_batch_decision(ROOT)
        self.assertIsInstance(decision, dict)
        self.assertEqual(decision["id"], "CFA3-DEC-DONOR-INTAKE-BATCH-ACCELERATION-2026-10-04")
        self.assertTrue(decision["explicit_user_approval"])

    def test_missing_candidate_registry_blob_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_rel = "canonical/deltas/CFA3-DONOR-BACKLOG-CONSOLIDATION-2026-10-04.json"
            (root / "canonical/deltas").mkdir(parents=True)
            (root / "canonical/decisions").mkdir(parents=True)
            (root / REGISTRY).write_text("{}", encoding="utf-8")
            (root / BATCH_DECISION).write_text(
                json.dumps({
                    "id": "CFA3-DEC-DONOR-INTAKE-BATCH-ACCELERATION-2026-10-04",
                    "status": "APPROVED",
                    "explicit_user_approval": True,
                    "rules": {
                        "canonical_mutation_mode": "ROLLING_BATCH_SINGLE_WRITER",
                        "max_active_canonical_registry_mutation_prs": 1,
                    },
                }),
                encoding="utf-8",
            )
            (root / manifest_rel).write_text(
                json.dumps({
                    "batch_role": BATCH_ROLE,
                    "batch_finalizer_pr": 705,
                    "decision_ref": BATCH_DECISION,
                    "status": "MATERIALIZED_PENDING_EXACT_HEAD_GATES",
                    "capability_baseline": 175,
                    "capability_delta": 0,
                    "authority_delta": 0,
                    "source_prs": [{"pr": 651, "head": "a" * 40, "contribution": 0}],
                    "new_source_count": 0,
                    "resulting_registry_blob_sha": "b" * 40,
                }),
                encoding="utf-8",
            )
            pending = [
                {"number": 651, "head_sha": "a" * 40, "registry_mutation": False},
                {"number": 705, "head_sha": "c" * 40, "registry_mutation": True},
            ]
            candidate = {
                "number": 705,
                "head_sha": "c" * 40,
                "registry_mutation": True,
                "file_paths": [manifest_rel],
            }
            result = validate_batch_finalizer(
                root,
                pending,
                candidate,
                {"count": 0, "registry": {"entries": []}},
                require_complete=False,
            )
            self.assertIn(
                "PROOF_UNAVAILABLE:BATCH_CANDIDATE_REGISTRY_BLOB:705",
                result["findings"],
            )

    def test_closed_historical_source_pr_is_accepted_by_exact_head(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_rel = "canonical/deltas/CFA3-DONOR-HISTORICAL-SOURCE-TEST.json"
            (root / "canonical/deltas").mkdir(parents=True)
            (root / "canonical/decisions").mkdir(parents=True)
            (root / REGISTRY).write_text("{}", encoding="utf-8")
            (root / BATCH_DECISION).write_text(
                json.dumps({
                    "id": "CFA3-DEC-DONOR-INTAKE-BATCH-ACCELERATION-2026-10-04",
                    "status": "APPROVED",
                    "explicit_user_approval": True,
                    "rules": {
                        "canonical_mutation_mode": "ROLLING_BATCH_SINGLE_WRITER",
                        "max_active_canonical_registry_mutation_prs": 1,
                    },
                }), encoding="utf-8")
            (root / manifest_rel).write_text(
                json.dumps({
                    "batch_role": BATCH_ROLE,
                    "batch_finalizer_pr": 727,
                    "decision_ref": BATCH_DECISION,
                    "status": "MATERIALIZED_PENDING_EXACT_HEAD_GATES",
                    "capability_baseline": 175,
                    "capability_delta": 0,
                    "authority_delta": 0,
                    "source_prs": [{"pr": 726, "head": "a" * 40, "contribution": 1}],
                    "new_source_count": 1,
                    "resulting_registry_blob_sha": "b" * 40,
                }), encoding="utf-8")
            pending = [{"number": 727, "head_sha": "c" * 40, "registry_mutation": True}]
            candidate = {
                "number": 727, "head_sha": "c" * 40, "registry_mutation": True,
                "registry_blob_sha": "b" * 40, "file_paths": [manifest_rel],
            }
            def fake_get(path):
                if path.endswith("/pulls/726"):
                    return {"state": "closed", "merged_at": "2026-10-06T10:15:08Z",
                            "head": {"sha": "a" * 40}}
                raise AssertionError(path)
            result = validate_batch_finalizer(
                root, pending, candidate, {"count": 0, "registry": {"entries": []}},
                get=fake_get, require_complete=False)
            self.assertNotIn("BATCH_SOURCE_PR_NOT_OPEN:726", result["findings"])
            self.assertNotIn("PROOF_UNAVAILABLE:BATCH_SOURCE_PR:726", result["findings"])
            self.assertNotIn("BATCH_SOURCE_HEAD_MISMATCH:726", result["findings"])

    def test_revalidation_refuses_blocked_gate_results(self):
        text = (ROOT / ".github/workflows/fa3-donor-intake-revalidation.yml").read_text()
        self.assertIn('report.get("result")=="BLOCKED"', text)
        self.assertIn('refreshed.get("result")=="BLOCKED"', text)

    def test_revalidation_does_not_fail_batch_covered_source_prs(self):
        text = (ROOT / ".github/workflows/fa3-donor-intake-revalidation.yml").read_text()
        self.assertIn('covered=set(report.get("batch_covered_prs") or [])', text)
        self.assertIn('number == finalizer or number in covered', text)
        self.assertIn('leaving its existing checks untouched', text)

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
