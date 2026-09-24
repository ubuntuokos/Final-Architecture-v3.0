from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_gui_current_host import (  # noqa: E402
    gui_desktop_runtime_scoped_admission,
    qpa_for_session,
    safe_child_environment,
)
from fa3_gui_current_host_gate import gate, validate_receipt  # noqa: E402


def good_receipt() -> dict:
    checks = {
        "github_actions_context": True,
        "repository_binding_exact": True,
        "source_commit_binding_exact": True,
        "runner_class_exact": True,
        "non_root_runner": True,
        "active_local_graphical_session": True,
        "supported_session_type": True,
        "display_endpoint_proven": True,
        "desktop_runtime_scope_admission_pass": True,
        "same_source_binary_present": True,
        "explicit_native_qpa": True,
        "offscreen_or_minimal_forbidden": True,
        "webengine_sandbox_override_absent": True,
        "real_gui_process_started": True,
        "process_survived_smoke_window": True,
        "smoke_window_minimum_5s": True,
        "probe_cleanup_completed": True,
        "fatal_qt_startup_marker_absent": True,
    }
    return {
        "schema": "fa3.gui-current-host-receipt.v1",
        "evidence_id": "EVID-FA3-GUI-CURRENT-HOST-001",
        "gate_id": "FA3-GUI-CURRENT-HOST-GATESET-001",
        "conformance_id": "FA3-GUI-RUNTIME-CONFORMANCE-001",
        "result": "PASS",
        "fail_closed": True,
        "source_binding": {
            "github_actions": True,
            "repository": "ubuntuokos/Final-Architecture-v3.0",
            "repository_exact": True,
            "source_commit": "a" * 40,
            "source_commit_exact": True,
        },
        "host": {
            "runner_class": "fa3-current-host",
            "fingerprint_sha256": "sha256:" + "b" * 64,
        },
        "session": {
            "type": "wayland",
            "active_local_graphical_session_proven": True,
            "runtime_dir_proven": True,
            "user_bus_socket_proven": True,
            "display_endpoint_proven": True,
            "qpa_platform": "wayland",
        },
        "desktop_admission": {
            "result": "FAIL",
            "mode": "LOCAL_GUI",
            "capabilities": {
                "linux_host": "PASS",
                "xdg_runtime": "PASS",
                "dbus_session": "PASS",
                "uri_open": "PASS",
                "secret_backend": "FAIL",
                "local_gui_session": "PASS",
            },
        },
        "desktop_runtime_scope": {
            "result": "PASS",
            "full_desktop_admission_result": "FAIL",
            "full_desktop_required_failures": ["secret_backend"],
            "secret_backend_status": "FAIL",
            "secret_backend_used_for_gui_runtime_admission": False,
            "secrets_authority_owner": "CAP-003",
            "scope_semantics": "GUI_PROCESS_RUNTIME_PROOF_NOT_SECRET_BACKEND_ADMISSION",
        },
        "build": {"status": "PASS", "binary_sha256": "c" * 64},
        "launch": {
            "attempted": True,
            "qpa_platform": "wayland",
            "process_alive_after_smoke": True,
            "observed_runtime_seconds": 8.0,
            "terminated_by_probe": True,
            "cleanup_completed": True,
            "fatal_qt_startup_marker_absent": True,
        },
        "security": {
            "root_execution": False,
            "sudo_or_pkexec_used": False,
            "package_install_or_network_fetch_used": False,
            "webengine_sandbox_disabled": False,
            "offscreen_or_minimal_platform_used": False,
            "secret_material_recorded": False,
            "secret_backend_promoted_by_gui_receipt": False,
        },
        "checks": checks,
        "capability_count": 143,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "gui_runtime_promotion_eligible": True,
        "current_host_runtime_promotion_claimed": True,
        "global_fa3_promotion_claim": False,
    }


class GuiCurrentHostTests(unittest.TestCase):
    def test_qpa_mapping_is_native_only(self):
        self.assertEqual(qpa_for_session("wayland"), "wayland")
        self.assertEqual(qpa_for_session("x11"), "xcb")
        self.assertIsNone(qpa_for_session("headless"))

    def test_safe_child_environment_removes_sandbox_override_and_secrets(self):
        env = safe_child_environment({
            "PATH": "/usr/bin",
            "HOME": "/home/user",
            "XDG_SESSION_TYPE": "wayland",
            "WAYLAND_DISPLAY": "wayland-0",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
            "QTWEBENGINE_DISABLE_SANDBOX": "1",
            "GITHUB_TOKEN": "secret",
            "API_KEY": "secret",
        })
        self.assertEqual(env["QT_QPA_PLATFORM"], "wayland")
        self.assertNotIn("QTWEBENGINE_DISABLE_SANDBOX", env)
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("API_KEY", env)

    def test_valid_receipt_passes(self):
        self.assertEqual(validate_receipt(good_receipt()), [])

    def test_gui_scoped_admission_allows_only_secret_backend_full_failure(self):
        report = {
            "result": "FAIL",
            "desktop": {"desktop": "KDE_PLASMA"},
            "session": {"type": "wayland"},
            "capabilities": {
                "linux_host": "PASS",
                "xdg_runtime": "PASS",
                "dbus_session": "PASS",
                "uri_open": "PASS",
                "secret_backend": "FAIL",
                "local_gui_session": "PASS",
            },
        }
        evidence = {
            "active_local_graphical_session_proven": True,
            "runtime_dir_proven": True,
            "user_bus_socket_proven": True,
        }
        scoped = gui_desktop_runtime_scoped_admission(report, evidence)
        self.assertEqual(scoped["result"], "PASS")
        self.assertEqual(scoped["full_desktop_required_failures"], ["secret_backend"])
        self.assertEqual(scoped["secret_backend_status"], "FAIL")
        self.assertFalse(scoped["secret_backend_used_for_gui_runtime_admission"])
        self.assertEqual(scoped["secrets_authority_owner"], "CAP-003")

    def test_gui_scoped_admission_rejects_non_secret_desktop_failure(self):
        report = {
            "result": "FAIL",
            "desktop": {"desktop": "GENERIC_XDG"},
            "session": {"type": "x11"},
            "capabilities": {
                "linux_host": "PASS",
                "xdg_runtime": "PASS",
                "dbus_session": "FAIL",
                "uri_open": "PASS",
                "secret_backend": "FAIL",
                "local_gui_session": "PASS",
            },
        }
        evidence = {
            "active_local_graphical_session_proven": True,
            "runtime_dir_proven": True,
            "user_bus_socket_proven": True,
        }
        scoped = gui_desktop_runtime_scoped_admission(report, evidence)
        self.assertEqual(scoped["result"], "FAIL")
        self.assertIn("dbus_session", scoped["failed_checks"])
        self.assertIn("full_desktop_failure:dbus_session", scoped["failed_checks"])

    def test_receipt_cannot_turn_secret_backend_into_gui_owned_promotion(self):
        receipt = good_receipt()
        receipt["security"]["secret_backend_promoted_by_gui_receipt"] = True
        receipt["desktop_runtime_scope"]["secret_backend_used_for_gui_runtime_admission"] = True
        errors = validate_receipt(receipt)
        self.assertTrue(any("Secret Backend" in item for item in errors))

    def test_offscreen_or_global_promotion_claim_fails(self):
        receipt = good_receipt()
        receipt["session"]["qpa_platform"] = "offscreen"
        receipt["launch"]["qpa_platform"] = "offscreen"
        receipt["global_fa3_promotion_claim"] = True
        errors = validate_receipt(receipt)
        self.assertTrue(any("QPA" in item for item in errors))
        self.assertTrue(any("global FA3 promotion" in item for item in errors))

    def test_short_or_crashed_smoke_fails(self):
        receipt = good_receipt()
        receipt["launch"]["observed_runtime_seconds"] = 1.0
        receipt["launch"]["process_alive_after_smoke"] = False
        receipt["checks"]["process_survived_smoke_window"] = False
        receipt["checks"]["smoke_window_minimum_5s"] = False
        self.assertTrue(validate_receipt(receipt))

    def test_repository_materialization_gate_passes_while_runtime_pending(self):
        result = gate(ROOT)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["runtime_evidence_status"], "PENDING_CURRENT_HOST")

    def test_workflow_is_current_host_bounded_and_non_mutating(self):
        text = (ROOT / ".github/workflows/fa3-gui-current-host.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "runs-on: [self-hosted, linux, x64, fa3-current-host]",
            text,
        )
        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            text,
        )
        for token in ("sudo ", "pkexec ", "apt-get ", "curl ", "wget "):
            self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
