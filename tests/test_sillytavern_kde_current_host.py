from __future__ import annotations

import copy
import unittest
from pathlib import Path

import fa3_sillytavern_kde_current_host as current_host


ROOT = Path(__file__).resolve().parents[1]


def pass_receipt():
    return {
        "schema": "fa3.sillytavern-kde-current-host-receipt.v1",
        "provider_id": current_host.PROVIDER_ID,
        "gate_id": current_host.GATE_ID,
        "conformance_id": current_host.CONFORMANCE_ID,
        "result_status": current_host.PASS_STATUS,
        "capability_scope": [current_host.CAPABILITY],
        "ci_fixture": False,
        "runner": {"labels": sorted(current_host.RUNNER_LABELS)},
        "candidate": {"release": current_host.RELEASE, "commit": current_host.COMMIT},
        "source": {
            "commit_revalidated": True,
            "root_lock_revalidated": True,
            "root_npmrc_revalidated": True,
            "electron_entry_revalidated": True,
            "electron_lock_revalidated": True,
        },
        "runtime": {
            "node_major": 24,
            "root_dependencies_prepared": True,
            "electron_dependencies_prepared": True,
            "normal_launch_dependency_mutation": False,
        },
        "session": {
            "xdg_session_type": "wayland",
            "wayland_socket_exists": True,
            "graphical_session_active": True,
        },
        "process": {
            "ozone_wayland_present": True,
            "no_sandbox_present": False,
        },
        "network": {
            "fixed_port_assumed": False,
            "all_service_listeners_loopback": True,
            "ui_probe_sillytavern": True,
        },
        "negative": {"invalid_source_refused": True},
        "authority": {
            "model_router_preserved": True,
            "mcp_gateway_preserved": True,
            "memory_authority_preserved": True,
            "hrb_preserved": True,
        },
        "stop": {"clean_stop": True, "resident_provider_processes_after": 0},
        "rollback": {"uninstall_pass": True, "reinstall_pass": True, "service_inactive_after": True},
    }


class SillyTavernKdeCurrentHostTests(unittest.TestCase):
    def test_static_materialization_passes(self):
        report = current_host.static_check(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertTrue(all(report["checks"].values()))

    def test_synthetic_valid_receipt_shape_passes_verifier(self):
        self.assertTrue(current_host.receipt_valid(pass_receipt()))

    def test_ci_fixture_cannot_claim_production_pass(self):
        receipt = pass_receipt()
        receipt["ci_fixture"] = True
        self.assertFalse(current_host.receipt_valid(receipt))

    def test_runner_label_bypass_fails_closed(self):
        receipt = pass_receipt()
        receipt["runner"]["labels"] = ["self-hosted", "linux", "x64"]
        self.assertFalse(current_host.receipt_valid(receipt))

    def test_non_wayland_receipt_fails_closed(self):
        receipt = pass_receipt()
        receipt["session"]["xdg_session_type"] = "x11"
        self.assertFalse(current_host.receipt_valid(receipt))

    def test_fixed_port_assumption_fails_closed(self):
        receipt = pass_receipt()
        receipt["network"]["fixed_port_assumed"] = True
        self.assertFalse(current_host.receipt_valid(receipt))

    def test_invalid_source_negative_test_is_mandatory(self):
        receipt = pass_receipt()
        receipt["negative"]["invalid_source_refused"] = False
        self.assertFalse(current_host.receipt_valid(receipt))

    def test_clean_stop_and_rollback_are_mandatory(self):
        receipt = pass_receipt()
        receipt["stop"]["resident_provider_processes_after"] = 1
        receipt["rollback"]["reinstall_pass"] = False
        self.assertFalse(current_host.receipt_valid(receipt))

    def test_root_dependency_identity_is_mandatory(self):
        receipt = pass_receipt()
        receipt["source"]["root_lock_revalidated"] = False
        self.assertFalse(current_host.receipt_valid(receipt))


if __name__ == "__main__":
    unittest.main()
