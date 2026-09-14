import json
import tempfile
import unittest
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_desktop_admission import (
    BASE_ID,
    CAPABILITY_COUNT,
    GATE_ID,
    PLASMA_ID,
    canonical_check,
    classify_desktop,
    evaluate_desktop,
    regression_check,
    self_test,
)


FULL_PROBES = {
    "linux_host": True,
    "xdg_runtime": True,
    "dbus_session": True,
    "portal": True,
    "secret_service": True,
    "fa3_vault": False,
    "uri_open": True,
    "notifications": True,
    "clipboard": True,
    "power_inhibit": True,
    "system_tray": True,
    "global_shortcuts": True,
    "screen_capture_portal": True,
}


class DesktopPortabilityTests(unittest.TestCase):
    def _env(self, desktop="KDE", session="wayland"):
        env = {
            "XDG_CURRENT_DESKTOP": desktop,
            "XDG_SESSION_TYPE": session,
            "XDG_RUNTIME_DIR": "/run/user/1000",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        }
        if session == "x11":
            env["DISPLAY"] = ":0"
        else:
            env["WAYLAND_DISPLAY"] = "wayland-0"
        return env

    def test_repository_self_test_passes(self):
        report = self_test(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["gate_id"], GATE_ID)
        self.assertEqual(report["capability_count"], CAPABILITY_COUNT)
        self.assertFalse(report["current_host_production_evidence"])

    def test_canonical_profiles_are_bound(self):
        report = canonical_check(ROOT)
        self.assertEqual(report["result"], "PASS")
        base = json.loads((ROOT / "canonical/FA3-DESKTOP-BASE-001.json").read_text(encoding="utf-8"))
        plasma = json.loads((ROOT / "canonical/FA3-DESKTOP-PLASMA-001.json").read_text(encoding="utf-8"))
        gate = json.loads((ROOT / "canonical/FA3-GATE-DESKTOP-PORTABILITY-001.json").read_text(encoding="utf-8"))
        self.assertEqual(base["id"], BASE_ID)
        self.assertEqual(plasma["id"], PLASMA_ID)
        self.assertEqual(plasma["base_profile"], BASE_ID)
        self.assertEqual(gate["base_profile"], BASE_ID)
        self.assertEqual(gate["reference_profile"], PLASMA_ID)
        self.assertEqual(base["new_capabilities"], 0)
        self.assertEqual(plasma["new_capabilities"], 0)
        self.assertEqual(gate["new_capabilities"], 0)

    def test_plasma_wayland_is_tier_1_reference(self):
        report = evaluate_desktop(self._env("KDE", "wayland"), FULL_PROBES, require_gui=True)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["desktop"]["desktop"], "KDE_PLASMA")
        self.assertEqual(report["desktop"]["tier"], 1)
        self.assertEqual(report["session"]["support"], "PREFERRED")

    def test_cosmic_is_tier_2_and_optional_features_do_not_fail(self):
        probes = {**FULL_PROBES, "system_tray": False, "global_shortcuts": False}
        report = evaluate_desktop(self._env("COSMIC", "wayland"), probes, require_gui=True)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["desktop"]["desktop"], "COSMIC")
        self.assertEqual(report["desktop"]["tier"], 2)
        self.assertEqual(report["capabilities"]["system_tray"], "LIMITED")
        self.assertEqual(report["capabilities"]["global_shortcuts"], "LIMITED")

    def test_gnome_cinnamon_xfce_lxqt_are_supported_targets(self):
        for desktop in ("GNOME", "Cinnamon", "XFCE", "LXQt"):
            with self.subTest(desktop=desktop):
                profile = classify_desktop(self._env(desktop))
                self.assertEqual(profile["tier"], 2)
                self.assertEqual(profile["support"], "SUPPORTED_TARGET")

    def test_x11_is_compatibility_not_failure(self):
        report = evaluate_desktop(self._env("GNOME", "x11"), {**FULL_PROBES, "portal": False}, require_gui=True)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["session"]["support"], "SUPPORTED_COMPATIBILITY")
        self.assertEqual(report["capabilities"]["xdg_desktop_portal"], "LIMITED")

    def test_missing_required_dbus_fails_closed(self):
        probes = {**FULL_PROBES, "dbus_session": False}
        report = evaluate_desktop(self._env("XFCE", "x11"), probes, require_gui=True)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["capabilities"]["dbus_session"], "FAIL")

    def test_fa3_vault_is_valid_secret_backend_fallback(self):
        probes = {**FULL_PROBES, "secret_service": False, "fa3_vault": True}
        report = evaluate_desktop(self._env("LXQt", "wayland"), probes, require_gui=True)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["capabilities"]["secret_backend"], "PASS")

    def test_missing_all_secret_backends_fails_closed(self):
        probes = {**FULL_PROBES, "secret_service": False, "fa3_vault": False}
        report = evaluate_desktop(self._env("COSMIC", "wayland"), probes, require_gui=True)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["capabilities"]["secret_backend"], "FAIL")

    def test_headless_is_valid_when_gui_not_required(self):
        report = evaluate_desktop({}, {key: False for key in FULL_PROBES}, require_gui=False)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["mode"], "HEADLESS_COMPATIBLE")

    def test_headless_fails_when_gui_is_required(self):
        report = evaluate_desktop({}, {key: False for key in FULL_PROBES}, require_gui=True)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["capabilities"]["local_gui_session"], "FAIL")

    def test_regression_suite_is_complete(self):
        report = regression_check()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], report["total"])
        self.assertEqual(report["total"], 6)

    def test_policy_drift_fails_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "canonical").mkdir(parents=True)
            for name in (
                "FA3-DESKTOP-BASE-001.json",
                "FA3-DESKTOP-PLASMA-001.json",
                "FA3-GATE-DESKTOP-PORTABILITY-001.json",
            ):
                shutil.copy2(ROOT / "canonical" / name, root / "canonical" / name)
            base_path = root / "canonical/FA3-DESKTOP-BASE-001.json"
            base = json.loads(base_path.read_text(encoding="utf-8"))
            base["policy"]["plasma_is_reference_not_core_dependency"] = False
            base_path.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
            self.assertEqual(canonical_check(root)["result"], "FAIL")


if __name__ == "__main__":
    unittest.main()
