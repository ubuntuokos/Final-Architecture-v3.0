from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_munder_difflin_executable_gate as g
import fa3_munder_difflin_gate as wrapper


class MunderDifflinExecutableGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        return td, root

    def test_exact_20_case_matrix_passes(self):
        report = g.run_regressions()
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["passed"], 20)
        self.assertEqual(report["total"], 20)
        self.assertTrue(report["case_ids_exact"])
        self.assertEqual([case["case_id"] for case in report["cases"]], g.CASE_IDS)
        self.assertTrue(all(case["status"] == "PASS" for case in report["cases"]))

    def test_canonical_executable_gate_passes(self):
        report = g.gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["gate_id"], "FA3-GATE-MUNDER-DIFFLIN-001")
        self.assertEqual(report["gateset_id"], "FA3-MUNDER-DIFFLIN-GATESET-001")
        self.assertFalse(report["current_host_provider_runtime_claim"])

    def test_wrapper_requires_executable_gate_pass(self):
        report = wrapper.gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["executable_gate"]["gate_id"], g.EXECUTABLE_GATE_ID)
        self.assertEqual(report["executable_gate"]["regressions"]["passed"], 20)

    def test_workspace_escape_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "safe").mkdir()
            self.assertEqual(
                g.resolve_workspace_path(root, "safe/file.txt"),
                (root / "safe/file.txt").resolve(strict=False),
            )
            with self.assertRaises(g.GateDenied):
                g.resolve_workspace_path(root, "../outside.txt")

    def test_symlink_escape_is_denied(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "root"
            outside = Path(td) / "outside"
            root.mkdir()
            outside.mkdir()
            os.symlink(outside, root / "link")
            with self.assertRaises(g.GateDenied):
                g.resolve_workspace_path(root, "link/secret.txt")

    def test_duplicate_message_is_noop_and_cursors_are_independent(self):
        a = g.ConsumerState()
        b = g.ConsumerState()
        self.assertEqual(a.consume("m1", 0), "PROCESS")
        self.assertEqual(a.consume("m1", 0), "NOOP")
        self.assertTrue(g.cursor_isolation_valid(a, b))
        self.assertEqual(a.cursor, 1)
        self.assertEqual(b.cursor, 0)
        self.assertNotIn("m1", b.processed)

    def test_renderer_direct_host_access_is_denied(self):
        self.assertTrue(
            g.renderer_host_call_allowed(
                direct_node_access=False,
                through_typed_broker=True,
                capability_scoped=True,
            )
        )
        self.assertFalse(
            g.renderer_host_call_allowed(
                direct_node_access=True,
                through_typed_broker=False,
                capability_scoped=False,
            )
        )

    def test_sensitive_and_unknown_telemetry_are_denied(self):
        self.assertTrue(g.telemetry_valid({"event": "agent.completed", "provider": "codex"}))
        self.assertFalse(g.telemetry_valid({"event": "agent.completed", "token": "secret"}))
        self.assertFalse(g.telemetry_valid({"event": "agent.completed", "free_form": "x"}))

    def test_provider_failure_is_isolated(self):
        result = g.orchestrator_survives_provider_failure(
            {
                "a": lambda: "PASS",
                "b": lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                "c": lambda: "PASS",
            }
        )
        self.assertEqual(result, {"a": "PASS", "b": "FAILED_ISOLATED", "c": "PASS"})

    def test_planned_or_verified_state_cannot_be_faked(self):
        self.assertFalse(
            g.capability_state_valid(
                "IMPLEMENTED",
                implementation_present=False,
                executable_evidence=True,
            )
        )
        self.assertFalse(
            g.capability_state_valid(
                "VERIFIED",
                implementation_present=True,
                executable_evidence=False,
            )
        )

    def test_canonical_case_set_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/FA3-GATE-MUNDER-DIFFLIN-001.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["case_ids"] = obj["case_ids"][:-1]
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = g.gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "MD-CANON-002" for x in report["canonical"]["findings"]))
        finally:
            td.cleanup()

    def test_global_policy_binding_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/enforcement-policy.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["munder_difflin_executable_gate_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = g.gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "MD-CANON-004" for x in report["canonical"]["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
