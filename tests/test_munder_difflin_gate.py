import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import fa3_munder_difflin_gate as m


class MunderDifflinGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        return td, root

    def _write(self, path: Path, obj):
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        r = m.gate(ROOT)
        self.assertEqual(r["result"], "PASS", r)
        self.assertEqual(r["regressions"]["passed"], 16)
        self.assertEqual(r["regressions"]["total"], 16)
        self.assertEqual(r["authority_scan"]["result"], "PASS")
        self.assertFalse(r["runtime_provider_required"])

    def test_regression_matrix_16_of_16(self):
        r = m.run_regressions()
        self.assertEqual(r["result"], "PASS", r)
        self.assertEqual((r["passed"], r["total"]), (16, 16))

    def test_duplicate_message_is_idempotent_noop(self):
        self.assertEqual(
            m.message_consumption_action(
                message_id="m1", processed_ids={"m1"}, independent_cursor=True
            ),
            "NOOP",
        )

    def test_concurrent_workspace_collision_denied(self):
        self.assertFalse(
            m.concurrent_workspace_isolation_valid(
                mutating_agents=["a", "b"],
                workspace_by_agent={"a": "shared", "b": "shared"},
            )
        )

    def test_sensitive_freeform_telemetry_denied(self):
        self.assertFalse(
            m.telemetry_allowlist_valid(
                properties={"provider": "codex", "prompt": "secret"},
                allowed_properties={"provider", "app_version"},
                sensitive_properties={"prompt", "path", "repo", "secret"},
                free_form_allowed=True,
            )
        )

    def test_transition_without_exercised_hop_is_not_evidence(self):
        self.assertFalse(
            m.transition_evidence_valid(
                mechanism_present=True,
                transition_exercised=False,
                evidence_status="PASS",
            )
        )

    def test_authority_assignment_scan_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical" / "munder-authority-escalation.json"
            self._write(
                p,
                {
                    "schema": "fa3.test.v1",
                    "id": "TEST",
                    "workflow_authority": m.PROVIDER_ID,
                },
            )
            r = m.scan_canonical_authority_assignments(root)
            self.assertEqual(r["result"], "FAIL")
            self.assertTrue(any(x["code"] == "MUNDER-AUTH-002" for x in r["findings"]))
        finally:
            td.cleanup()

    def test_provider_authority_drift_denied(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/providers/FA3-PROVIDER-MUNDER-DIFFLIN-001.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["architectural_authority"] = True
            self._write(p, obj)
            self.assertEqual(m.gate(root)["result"], "FAIL")
        finally:
            td.cleanup()

    def test_global_policy_binding_required(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/enforcement-policy.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["mandatory_reference_gates"] = [
                x for x in obj["mandatory_reference_gates"] if x != m.GATE_ID
            ]
            self._write(p, obj)
            r = m.gate(root)
            self.assertEqual(r["result"], "FAIL")
            self.assertTrue(any(x["code"] == "MUNDER-REF-006" for x in r["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_reference_is_not_runtime_promotion_evidence(self):
        ref = json.loads(
            (ROOT / "canonical/references/FA3-MUNDER-DIFFLIN-UPSTREAM-REFERENCE-2026-08-30.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(ref["promotion_evidence"])
        self.assertFalse(ref["floating_main_allowed_as_promotion_evidence"])
        self.assertEqual(ref["security_support_scope"], "MAIN_ONLY_EARLY_PROTOTYPE")


if __name__ == "__main__":
    unittest.main()
