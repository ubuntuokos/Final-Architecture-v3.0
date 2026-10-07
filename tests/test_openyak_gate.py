from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import fa3_openyak_gate as openyak


ROOT = Path(__file__).resolve().parents[1]


class OpenYakGateTests(unittest.TestCase):
    def _copy_root(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence", root / "evidence")
        return temporary, root

    @staticmethod
    def _write(path: Path, value):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def test_all_24_positive_negative_regressions_pass(self):
        cases = openyak.regression_cases()
        self.assertEqual(24, len(cases))
        self.assertEqual(24, len({case["rule"] for case in cases}))
        self.assertTrue(all(case["positive"] and case["negative_refusal"] for case in cases))

    def test_full_canonical_gate_passes(self):
        report = openyak.gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual((24, 24), (report["regressions"]["passed"], report["regressions"]["total"]))
        self.assertEqual("PASS", report["authority_scan"]["result"])
        self.assertFalse(report["current_host_runtime_promotion_claimed"])

    def test_model_route_rejects_direct_ollama(self):
        self.assertFalse(openyak.model_route_valid(
            route="FA3_LITELLM_OPENAI_COMPATIBLE_ENDPOINT_ONLY",
            managed_ollama=False,
            direct_ollama=True,
            silent_fallback=False,
        ))

    def test_workspace_rejects_unbounded_or_host_specific_root(self):
        self.assertFalse(openyak.workspace_scope_valid(bounded=False, root_kind="FILESYSTEM_ROOT", host_specific_constant=False))
        self.assertFalse(openyak.workspace_scope_valid(bounded=True, root_kind="USER_SELECTED_PROJECT_DIRECTORY", host_specific_constant=True))

    def test_permission_ceiling_rejects_automatic_mutation(self):
        actions = {
            "bounded_read": "ALLOW", "workspace_mutation": "ALLOW", "shell": "ASK",
            "privileged_command": "DENY", "system_path_mutation": "DENY", "credential_access": "DENY",
            "model_store_mutation": "DENY", "direct_data_plane": "DENY",
        }
        self.assertFalse(openyak.permission_ceiling_valid(actions))

    def test_backend_rejects_wildcard_listener(self):
        self.assertFalse(openyak.backend_boundary_valid(host="0.0.0.0", local_session_auth=True, remote_access=False))

    def test_provider_authority_drift_fails_closed(self):
        temporary, root = self._copy_root()
        try:
            path = root / openyak.PATHS["provider"]
            value = json.loads(path.read_text(encoding="utf-8"))
            value["architectural_authority"] = True
            self._write(path, value)
            report = openyak.gate(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "OPENYAK-REF-004" for item in report["findings"]))
        finally:
            temporary.cleanup()

    def test_direct_authority_assignment_fails_closed(self):
        temporary, root = self._copy_root()
        try:
            path = root / "canonical/openyak-authority-escalation.json"
            self._write(path, {"schema": "fa3.test.v1", "workflow_authority": openyak.PROVIDER_ID})
            report = openyak.scan_authority_assignments(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "OPENYAK-AUTH-001" for item in report["findings"]))
        finally:
            temporary.cleanup()

    def test_reference_evidence_cannot_claim_current_host_runtime(self):
        evidence = json.loads((ROOT / openyak.PATHS["evidence"]).read_text(encoding="utf-8"))
        self.assertEqual("PASS", evidence["status"])
        self.assertEqual("NOT_CLAIMED", evidence["current_host_runtime_evidence"])
        self.assertFalse(evidence["current_host_runtime_promotion_claimed"])
        self.assertFalse(evidence["production_provider_admission_claimed"])


if __name__ == "__main__":
    unittest.main()
