from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fa3_opencut_gate import (
    PATHS,
    PINNED_COMMIT,
    gate,
    operation_allowed,
    regression_cases,
    runtime_admission_allowed,
)

ROOT = Path(__file__).resolve().parents[1]


class OpenCutGateTests(unittest.TestCase):
    def test_canonical_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(15, report["regression_count"])
        self.assertEqual("NOT_CLAIMED", report["current_host_runtime_evidence"])

    def test_all_positive_negative_regressions_pass(self):
        cases = regression_cases()
        self.assertEqual(15, len(cases))
        self.assertTrue(all(case["positive"] for case in cases))
        self.assertTrue(all(case["negative_refusal"] for case in cases))

    def test_ui_automation_is_not_primary_mutation_boundary(self):
        operation = {
            "schema": "fa3.structured-timeline-operation.v1",
            "operation": "timeline.insert",
            "project_identity": "sha256:before",
            "idempotency_key": "op-1",
            "transport": "UI_MOUSE_KEYBOARD",
            "destructive": False,
        }
        self.assertFalse(operation_allowed(operation))

    def test_destructive_operation_without_approval_fails_closed(self):
        operation = {
            "schema": "fa3.structured-timeline-operation.v1",
            "operation": "timeline.delete",
            "project_identity": "sha256:before",
            "idempotency_key": "op-2",
            "transport": "TYPED_ADAPTER",
            "destructive": True,
            "dry_run": True,
            "diff_present": True,
            "provenance_present": True,
            "audit_present": True,
            "approval_id": "",
        }
        self.assertFalse(operation_allowed(operation))

    def test_floating_main_cannot_be_runtime_admitted(self):
        descriptor = {
            "source_revision": "main",
            "dependency_lock_identity": "sha256:lock",
            "capability_compatibility_matrix": "sha256:matrix",
            "adapter_conformance_pass": True,
            "current_host_e2e_pass": True,
            "stable_interfaces": {
                "editor_api": True,
                "mcp": True,
                "headless": True,
                "plugins": True,
                "scripting": True,
            },
        }
        self.assertNotEqual(PINNED_COMMIT, descriptor["source_revision"])
        self.assertFalse(runtime_admission_allowed(descriptor))

    def test_provider_authority_escalation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "reports", "__pycache__"))
            path = dst / PATHS["provider"]
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["architectural_authority"] = True
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = gate(dst)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "OPENCUT-REF-005" for item in report["findings"]))

    def test_stable_api_claim_without_observation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "reports", "__pycache__"))
            path = dst / PATHS["reference"]
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["observed_tree"]["stable_mcp_server_surface_observed"] = True
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = gate(dst)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "OPENCUT-REF-006" for item in report["findings"]))

    def test_cfa3_native_fast_edit_scope_and_otio_interchange(self):
        profile = json.loads((ROOT / PATHS["profile"]).read_text(encoding="utf-8"))
        contract = json.loads((ROOT / PATHS["contract"]).read_text(encoding="utf-8"))
        decision = json.loads((ROOT / PATHS["decision"]).read_text(encoding="utf-8"))
        provider = json.loads((ROOT / PATHS["provider"]).read_text(encoding="utf-8"))
        policy = json.loads((ROOT / PATHS["policy"]).read_text(encoding="utf-8"))
        enforcement = json.loads((ROOT / PATHS["enforcement"]).read_text(encoding="utf-8"))
        app = profile["opencut_application"]
        self.assertEqual("FAST_EDIT_QUICKCLIP", app["role"])
        self.assertEqual(".fa3clip", app["project_format"])
        self.assertEqual(["STANDALONE", "WEBDESIGN_EMBEDDED"], app["delivery_modes"])
        self.assertFalse(app["professional_nle"])
        self.assertFalse(app["advanced_motion_engine"])
        self.assertEqual("CFA3_NATIVE_PROJECT_STATE", contract["canonical_timeline_ir"])
        self.assertEqual("OpenTimelineIO", contract["interchange_ir"])
        self.assertEqual([], contract["required_adapter_families"])
        self.assertIn("KdenliveAdapter", contract["optional_adapter_families"])
        self.assertEqual("CFA3_VIDEO_EDITOR_SOLE_FULL_EDIT", profile["authority_boundaries"]["human_finishing_nle"])
        self.assertEqual("UPSTREAM_REFERENCE_ONLY", provider["classification"][0])
        self.assertEqual(enforcement["rules"], policy["opencut_mandatory_p0_rules"])
        self.assertEqual("CFA3_NATIVE_OPENCUT_FAST_EDIT_APPLICATION_SHARED_PROGRAMMABLE_VIDEO_EDITING_FABRIC", decision["decision"])
        self.assertEqual("KDENLIVE_REMAINS_PRIMARY_HUMAN_FINISHING_NLE", decision["historical_decision"]["original"]["mandatory_rules"][10])

    def test_old_full_nle_authority_rule_cannot_be_restored(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "reports", "__pycache__"))
            path = dst / PATHS["policy"]
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["opencut_mandatory_p0_rules"][10] = "KDENLIVE_REMAINS_PRIMARY_HUMAN_FINISHING_NLE"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = gate(dst)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "OPENCUT-REF-008" for item in report["findings"]))

    def test_otio_as_project_authority_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "reports", "__pycache__"))
            path = dst / PATHS["contract"]
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["canonical_timeline_ir"] = "OpenTimelineIO"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = gate(dst)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "OPENCUT-REF-004" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
