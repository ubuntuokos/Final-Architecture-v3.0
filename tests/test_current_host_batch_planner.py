from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fa3_current_host_batch_planner import TEST_KINDS, build_plan

ROOT = Path(__file__).resolve().parents[1]


class TestCurrentHostBatchPlanner(unittest.TestCase):
    def test_plan_preserves_175_x_3_materialized_definition_model(self):
        report = build_plan(ROOT, batch_size=5)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["capability_count"], 175)
        self.assertEqual(report["required_test_kinds_per_capability"], 3)
        self.assertEqual(report["required_test_obligation_count"], 525)
        self.assertEqual(
            report["materialized_obligation_count"] + report["pending_obligation_count"],
            525,
        )
        self.assertEqual(
            report["fully_materialized_capability_count"] + report["pending_materialization_capability_count"],
            175,
        )
        self.assertEqual(report["materialized_obligation_count"], 525)
        self.assertEqual(report["pending_obligation_count"], 0)
        self.assertEqual(report["fully_materialized_capability_count"], 175)
        self.assertEqual(report["pending_materialization_capability_count"], 0)
        self.assertEqual(report["registry_integrity"], "PASS")
        self.assertEqual(len(report["registry_sha256"]), 3)
        self.assertEqual(len(report["execution_ready_selection_sha256"]), 64)
        self.assertIsNone(report["next_materialization_batch"])
        self.assertEqual(report["materialization_batches"], [])

    def test_execution_ready_requires_all_three_registration_layers(self):
        report = build_plan(ROOT, batch_size=5)
        ready = set(report["execution_ready_capabilities"])
        for capability in report["capabilities"]:
            kinds = capability["obligations"]
            self.assertEqual({row["test_kind"] for row in kinds}, set(TEST_KINDS))
            complete = all(
                row["executor_registered"]
                and row["qualification_registered"]
                and row["producer_registered"]
                and row["materialized"]
                for row in kinds
            )
            self.assertEqual(capability["capability_id"] in ready, complete)

    def test_duplicate_registry_obligation_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            paths = [
                "evidence/evidence-registry.json",
                "canonical/current-host-capability-test-executors.json",
                "canonical/current-host-capability-test-qualifications.json",
                "canonical/current-host-capability-qualification-constituent-producers.json",
            ]
            for rel in paths:
                src = ROOT / rel
                dst = temp_root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            executor_path = temp_root / "canonical/current-host-capability-test-executors.json"
            data = json.loads(executor_path.read_text(encoding="utf-8"))
            data["entries"].append(dict(data["entries"][0]))
            executor_path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate obligation key"):
                build_plan(temp_root, batch_size=5)

    def test_batches_are_deterministic_and_non_promoting(self):
        report = build_plan(ROOT, batch_size=5)
        inv = report["invariants"]
        self.assertIs(inv["synthetic_current_host_pass_allowed"], False)
        self.assertIs(inv["materialized_executor_implies_runtime_pass"], False)
        self.assertIs(inv["batch_completion_implies_global_promotion"], False)
        self.assertIs(inv["global_promotion_claim"], False)
        self.assertIs(inv["duplicate_obligation_keys_allowed"], False)
        self.assertIs(inv["cross_registry_qualification_binding_required"], True)
        self.assertIs(inv["batch_selection_digest_required"], True)
        self.assertTrue(all(len(row["selection_sha256"]) == 64 for row in report["execution_batches"]))
        self.assertTrue(all(len(row["capabilities"]) <= 5 for row in report["execution_batches"]))
        self.assertTrue(all(len(row["capabilities"]) <= 5 for row in report["materialization_batches"]))


if __name__ == "__main__":
    unittest.main()
