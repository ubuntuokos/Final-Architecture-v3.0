from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import fa3_lynxhub_gate as lynxhub


ROOT = Path(__file__).resolve().parents[1]


class LynxHubGateTests(unittest.TestCase):
    def _copy_root(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence", root / "evidence")
        shutil.copytree(ROOT / "deployment", root / "deployment")
        shutil.copytree(ROOT / "bin", root / "bin")
        shutil.copytree(ROOT / "docs", root / "docs")
        return temporary, root

    @staticmethod
    def _write(path: Path, value):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def test_all_28_positive_negative_regressions_pass(self):
        cases = lynxhub.regression_cases()
        self.assertEqual(28, len(cases))
        self.assertEqual(28, len({case["rule"] for case in cases}))
        self.assertTrue(all(case["positive"] and case["negative_refusal"] for case in cases))

    def test_full_canonical_gate_passes(self):
        report = lynxhub.gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual((28, 28), (report["regressions"]["passed"], report["regressions"]["total"]))
        self.assertEqual("PASS", report["deployment"]["result"])
        self.assertEqual("PASS", report["authority_scan"]["result"])
        self.assertFalse(report["current_host_runtime_promotion_claimed"])

    def test_debian_tuple_rejects_floating_branch(self):
        value = {
            "repository": "TheLynxHub/LynxHub",
            "release": lynxhub.PINNED_VERSION,
            "commit": "master",
            "license": "AGPL-3.0",
            "debian_package": lynxhub.PINNED_DEB,
            "debian_package_sha256": lynxhub.PINNED_DEB_SHA256,
            "debian_package_name": "lynxhub",
            "debian_package_version": "3.5.8",
            "installed_executable": "/opt/LynxHub/lynxhub",
        }
        self.assertFalse(lynxhub.immutable_component_tuple_valid(value))

    def test_action_wrapper_rejects_direct_mcp_or_privilege(self):
        self.assertFalse(lynxhub.action_valid(
            versioned=True,
            fixed_id=True,
            free_shell=False,
            eval_used=False,
            privileged=True,
            direct_mcp=True,
            direct_ollama=False,
            secret_access=False,
        ))

    def test_browser_route_rejects_external_url(self):
        self.assertTrue(lynxhub.url_valid("http://127.0.0.1:3000", approved=True))
        self.assertFalse(lynxhub.url_valid("https://example.com", approved=True))

    def test_lifecycle_rejects_parallel_autostart(self):
        self.assertFalse(lynxhub.lifecycle_valid(
            user_session=True,
            on_demand=True,
            service="lynxhub.service",
            target="ai-creative-ops.target",
            duplicate_autostart=True,
            transient_parallel=True,
        ))

    def test_provider_authority_drift_fails_closed(self):
        temporary, root = self._copy_root()
        try:
            path = root / lynxhub.PATHS["provider"]
            value = json.loads(path.read_text(encoding="utf-8"))
            value["architectural_authority"] = True
            self._write(path, value)
            report = lynxhub.gate(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "LYNXHUB-REF-004" for item in report["findings"]))
        finally:
            temporary.cleanup()

    def test_no_sandbox_launch_drift_fails_closed(self):
        temporary, root = self._copy_root()
        try:
            path = root / "deployment/lynxhub/bin/lynxhub-launch"
            path.write_text(path.read_text(encoding="utf-8") + "\n/opt/LynxHub/lynxhub --no-sandbox\n", encoding="utf-8")
            report = lynxhub.deployment_check(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "LYNXHUB-DEP-003" for item in report["findings"]))
        finally:
            temporary.cleanup()

    def test_direct_authority_assignment_fails_closed(self):
        temporary, root = self._copy_root()
        try:
            path = root / "canonical/lynxhub-authority-escalation.json"
            self._write(path, {"schema": "fa3.test.v1", "workflow_authority": lynxhub.PROVIDER_ID})
            report = lynxhub.scan_authority_assignments(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "LYNXHUB-AUTH-001" for item in report["findings"]))
        finally:
            temporary.cleanup()

    def test_reference_evidence_cannot_claim_current_host_runtime(self):
        evidence = json.loads((ROOT / lynxhub.PATHS["evidence"]).read_text(encoding="utf-8"))
        self.assertEqual("PASS", evidence["status"])
        self.assertEqual("NOT_CLAIMED", evidence["current_host_runtime_evidence"])
        self.assertFalse(evidence["current_host_runtime_promotion_claimed"])
        self.assertFalse(evidence["production_provider_admission_claimed"])


if __name__ == "__main__":
    unittest.main()
