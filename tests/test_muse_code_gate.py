import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_muse_code_gate as m


class MuseCodeGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence", root / "evidence")
        return td, root

    def _write(self, path: Path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        report = m.gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["regressions"]["passed"], 20)
        self.assertEqual(report["regressions"]["total"], 20)
        self.assertEqual(report["authority_scan"]["result"], "PASS")
        self.assertFalse(report["runtime_provider_required"])
        self.assertFalse(report["current_host_provider_runtime_evidence"])

    def test_regression_matrix_is_20_of_20(self):
        report = m.run_regressions()
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual((report["passed"], report["total"]), (20, 20))
        self.assertEqual(len({case["rule_id"] for case in report["cases"]}), 20)

    def test_duplicate_or_non_monotonic_event_sequence_is_rejected(self):
        self.assertFalse(
            m.append_only_sequence_valid(
                [
                    {"event_id": "e1", "seq": 1},
                    {"event_id": "e1", "seq": 2},
                ]
            )
        )
        self.assertFalse(
            m.append_only_sequence_valid(
                [
                    {"event_id": "e1", "seq": 1},
                    {"event_id": "e2", "seq": 3},
                ]
            )
        )

    def test_gated_mutation_without_prior_approval_is_rejected(self):
        events = [
            {
                "event_type": "EDIT_OR_MUTATION",
                "event_id": "m1",
                "seq": 1,
                "mutation_id": "mut1",
                "approval_required": True,
                "approval_id": "ap1",
            }
        ]
        self.assertFalse(m.approval_precedes_mutation_valid(events, mutation_id="mut1"))

    def test_replay_side_effect_reexecution_is_rejected(self):
        self.assertFalse(
            m.replay_without_side_effect_reexecution_valid(
                reconstructs_from_committed_events=True,
                external_side_effects_enabled=True,
            )
        )
        self.assertFalse(
            m.external_side_effect_idempotency_valid(
                is_external_side_effect=True,
                idempotency_key=None,
                replay_action="APPLY",
            )
        )

    def test_subagent_capability_expansion_is_rejected(self):
        self.assertFalse(
            m.subagent_capability_narrowing_valid(
                parent_capabilities={"read"},
                child_capabilities={"read", "edit"},
                child_authority_expansion=False,
            )
        )

    def test_restart_cannot_auto_approve_pending_action(self):
        self.assertFalse(
            m.pending_approval_resume_valid(
                before_restart="PENDING",
                after_restart="APPROVED",
            )
        )

    def test_secret_bearing_event_is_rejected(self):
        self.assertFalse(
            m.secret_redaction_valid(
                persisted_event={"event_id": "e1", "api_key": "x"},
                redacted=False,
            )
        )

    def test_provider_authority_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/providers/FA3-PROVIDER-MUSE-CODE-001.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["architectural_authority"] = True
            self._write(path, obj)
            report = m.gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(
                any(x["code"] in {"MUSE-AUTH-001", "MUSE-REF-002"} for x in report["authority_scan"]["findings"] + report["reference"]["findings"])
            )
        finally:
            td.cleanup()

    def test_direct_authority_assignment_is_rejected_by_global_scan(self):
        td, root = self._copy_root()
        try:
            self._write(
                root / "canonical/muse-code-authority-escalation.json",
                {
                    "schema": "fa3.test.v1",
                    "id": "TEST",
                    "workflow_authority": m.PROVIDER_ID,
                },
            )
            report = m.scan_canonical_authority_assignments(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "MUSE-AUTH-002" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_global_policy_binding_is_required(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/enforcement-policy.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["mandatory_reference_gates"] = [
                gate for gate in obj["mandatory_reference_gates"] if gate != m.GATE_ID
            ]
            self._write(path, obj)
            report = m.gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "MUSE-REF-009" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_reference_evidence_does_not_claim_current_host_promotion(self):
        evidence = json.loads(
            (ROOT / "evidence/reference/muse-code-ci-2026-09-01.json").read_text(encoding="utf-8")
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertFalse(evidence["current_host_provider_runtime_evidence"])
        self.assertFalse(evidence["current_host_runtime_promotion_claim"])
        self.assertFalse(evidence["production_provider_admission_claim"])


if __name__ == "__main__":
    unittest.main()
