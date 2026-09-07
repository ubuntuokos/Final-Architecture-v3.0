from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import fa3_sillytavern_kde_gate as stkde


ROOT = Path(__file__).resolve().parents[1]


class SillyTavernKdeGateTests(unittest.TestCase):
    def _copy_root(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for name in ("canonical", "evidence", "deployment", "bin", "docs"):
            shutil.copytree(ROOT / name, root / name)
        return temporary, root

    @staticmethod
    def _write(path: Path, value):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def test_all_24_positive_negative_regressions_pass(self):
        cases = stkde.regression_cases()
        self.assertEqual(24, len(cases))
        self.assertEqual(24, len({case["rule"] for case in cases}))
        self.assertTrue(all(case["positive"] and case["negative_refusal"] for case in cases))

    def test_full_canonical_gate_passes(self):
        report = stkde.gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual((24, 24), (report["regressions"]["passed"], report["regressions"]["total"]))
        self.assertEqual("PASS", report["deployment"]["result"])
        self.assertFalse(report["current_host_runtime_promotion_claimed"])

    def test_immutable_tuple_rejects_floating_release(self):
        provider = json.loads((ROOT / stkde.PATHS["provider"]).read_text(encoding="utf-8"))
        value = provider["immutable_component_tuple"]
        self.assertTrue(stkde.immutable_component_tuple_valid(value))
        self.assertFalse(stkde.immutable_component_tuple_valid({**value, "release": "latest"}))

    def test_fixed_port_is_not_canonical(self):
        self.assertTrue(stkde.endpoint_valid(loopback=True, event_derived=True, fixed_port=False))
        self.assertFalse(stkde.endpoint_valid(loopback=True, event_derived=False, fixed_port=True))

    def test_second_wrapper_and_no_sandbox_are_rejected(self):
        self.assertTrue(stkde.desktop_valid(wayland=True, no_sandbox=False, second_wrapper=False, fixed_gpu=False))
        self.assertFalse(stkde.desktop_valid(wayland=True, no_sandbox=True, second_wrapper=True, fixed_gpu=False))

    def test_prompt_and_percentage_routing_are_rejected(self):
        self.assertTrue(stkde.model_valid(existing_router=True, prompt_keyword=False, percentage_router=False, direct_runtime=False))
        self.assertFalse(stkde.model_valid(existing_router=True, prompt_keyword=True, percentage_router=True, direct_runtime=False))

    def test_fake_sandbox_and_free_shell_are_rejected(self):
        self.assertTrue(stkde.tool_valid(central_gateway=True, free_shell=False, fake_sandbox=False, privileged=False, side_effect_human_gate=True))
        self.assertFalse(stkde.tool_valid(central_gateway=True, free_shell=True, fake_sandbox=True, privileged=False, side_effect_human_gate=True))

    def test_runtime_npm_install_drift_fails_closed(self):
        temporary, root = self._copy_root()
        try:
            path = root / "deployment/sillytavern-kde/bin/sillytavern-kde-launch"
            path.write_text(path.read_text(encoding="utf-8") + "\nnpm ci\n", encoding="utf-8")
            report = stkde.deployment_check(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "SILLYKDE-DEP-002" for item in report["findings"]))
        finally:
            temporary.cleanup()

    def test_provider_authority_drift_fails_closed(self):
        temporary, root = self._copy_root()
        try:
            path = root / stkde.PATHS["provider"]
            value = json.loads(path.read_text(encoding="utf-8"))
            value["architectural_authority"] = True
            self._write(path, value)
            report = stkde.gate(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "SILLYKDE-REF-004" for item in report["findings"]))
        finally:
            temporary.cleanup()

    def test_reference_evidence_cannot_claim_current_host_runtime(self):
        evidence = json.loads((ROOT / stkde.PATHS["evidence"]).read_text(encoding="utf-8"))
        self.assertEqual("PASS", evidence["status"])
        self.assertEqual("NOT_CLAIMED", evidence["current_host_runtime_evidence"])
        self.assertFalse(evidence["current_host_runtime_promotion_claimed"])
        self.assertFalse(evidence["production_provider_admission_claimed"])


if __name__ == "__main__":
    unittest.main()
