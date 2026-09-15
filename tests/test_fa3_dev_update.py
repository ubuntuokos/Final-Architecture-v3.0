from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fa3_dev_mode
import fa3_dev_update_gate
import fa3_update_fabric


class DevUpdateCanonicalTests(unittest.TestCase):
    def test_canonical_gate_passes(self) -> None:
        result = fa3_dev_update_gate.check()
        self.assertEqual(result["status"], "PASS", result["blocking_findings"])
        self.assertEqual(result["capability_count"], 143)
        self.assertEqual(result["capability_delta"], 0)
        self.assertEqual(result["authority_delta"], 0)

    def test_index_manifest_is_deterministic_and_non_self_referential(self) -> None:
        first = fa3_dev_mode.build_index_manifest()
        second = fa3_dev_mode.build_index_manifest()
        self.assertEqual(first["manifest_digest"], second["manifest_digest"])
        paths = {item["path"] for item in first["artifacts"]}
        self.assertNotIn("evidence/development/current/artifact-manifest.json", paths)
        self.assertNotIn("evidence/development/current/receipt.json", paths)

    def test_low_risk_os_security_update_can_auto_install(self) -> None:
        result = fa3_update_fabric.classify({
            "id": "openssl-security",
            "class": "OS_MANAGED",
            "security_update": True,
            "impact": "QUICK",
        })
        self.assertTrue(result["auto_install"])
        self.assertFalse(result["host_critical"])

    def test_host_critical_security_update_is_staged_not_blindly_installed(self) -> None:
        result = fa3_update_fabric.classify({
            "id": "nvidia-driver-security",
            "class": "HOST_CRITICAL",
            "security_update": True,
            "impact": "HOST_CRITICAL",
        })
        self.assertFalse(result["auto_install"])
        self.assertTrue(result["stage"])
        self.assertTrue(result["user_activation_required"])

    def test_model_download_never_implicit(self) -> None:
        result = fa3_update_fabric.classify({
            "id": "model-v2",
            "class": "MODEL",
            "large_model_download": True,
        })
        self.assertFalse(result["auto_install"])
        self.assertTrue(result["user_activation_required"])

    def test_restart_now_is_deferred_when_protected_workload_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td)
            restart_state = state_dir / "restart-required.json"
            with mock.patch.object(fa3_update_fabric, "STATE_DIR", state_dir), mock.patch.object(
                fa3_update_fabric, "RESTART_STATE", restart_state
            ):
                fa3_update_fabric.set_restart_required("host", ["kernel"], ["render"])
                state = fa3_update_fabric.choose_restart("RESTART_NOW", ["render"], None)
                self.assertEqual(state["state"], "DEFERRED")
                self.assertEqual(state["action"], "POSTPONE_AND_NOTIFY")
                self.assertFalse(state["resolved"])

    def test_when_idle_safe_is_ready_when_no_workload_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td)
            restart_state = state_dir / "restart-required.json"
            with mock.patch.object(fa3_update_fabric, "STATE_DIR", state_dir), mock.patch.object(
                fa3_update_fabric, "RESTART_STATE", restart_state
            ):
                fa3_update_fabric.set_restart_required("service", ["ollama"], [])
                state = fa3_update_fabric.choose_restart("WHEN_IDLE_SAFE", [], None)
                self.assertEqual(state["state"], "READY_TO_RESTART")
                self.assertEqual(state["action"], "RESTART_ALLOWED")

    def test_update_all_remains_disabled(self) -> None:
        policy = json.loads((fa3_update_fabric.ROOT / "config/fa3-update-policy.json").read_text())
        self.assertFalse(policy["allow_blind_update_all"])
        self.assertTrue(policy["allow_check_all"])


if __name__ == "__main__":
    unittest.main()
