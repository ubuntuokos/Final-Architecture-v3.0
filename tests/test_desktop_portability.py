import json
import tempfile
import unittest
from pathlib import Path
import shutil
import sys
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_desktop_admission import (
    BASE_ID,
    CAPABILITY_COUNT,
    GATE_ID,
    PLASMA_ID,
    canonical_check,
    classify_desktop,
    collect_runtime_probes,
    discover_current_user_session_environment,
    _reference_secret_service_activation_aliases,
    _secret_service_probe,
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

    def test_secret_backend_report_preserves_standard_verification_evidence(self):
        probes = {
            **FULL_PROBES,
            "secret_service_live_name": True,
            "secret_service_standard_interface": True,
            "secret_service_standard_name_verified": True,
            "secret_service_dbus_activation_attempted": True,
            "secret_service_reference_activation_attempted": True,
            "secret_service_compatibility_endpoint_verified": True,
        }
        report = evaluate_desktop(self._env("KDE", "wayland"), probes, require_gui=True)
        evidence = report["secret_backend_evidence"]
        self.assertTrue(evidence["standard_name_verified"])
        self.assertTrue(evidence["standard_interface_verified"])
        self.assertTrue(evidence["reference_activation_attempted"])
        self.assertTrue(evidence["compatibility_endpoint_verified_diagnostic_only"])

    def test_headless_is_valid_when_gui_not_required(self):
        report = evaluate_desktop({}, {key: False for key in FULL_PROBES}, require_gui=False)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["mode"], "HEADLESS_COMPATIBLE")

    @patch("fa3_desktop_admission.os.getuid", return_value=1000)
    @patch("fa3_desktop_admission._safe_runtime_dir", return_value=Path("/run/user/1000"))
    @patch("fa3_desktop_admission._owned_socket", return_value=True)
    @patch(
        "fa3_desktop_admission._systemd_user_environment_snapshot",
        return_value={"WAYLAND_DISPLAY": "wayland-0"},
    )
    @patch(
        "fa3_desktop_admission._loginctl_session_properties",
        return_value={
            "Id": "2",
            "User": "1000",
            "Type": "wayland",
            "Remote": "no",
            "Active": "yes",
            "Desktop": "",
        },
    )
    @patch(
        "fa3_desktop_admission._user_bus_names",
        return_value={
            "org.kde.KWin",
            "org.kde.plasmashell",
            "org.freedesktop.portal.Desktop",
            "org.freedesktop.secrets",
        },
    )
    def test_current_user_session_discovery_reconstructs_only_proven_session(
        self,
        _bus,
        _session,
        _systemd,
        _socket,
        _runtime,
        _uid,
    ):
        discovered = discover_current_user_session_environment({})
        env = discovered["environment"]
        evidence = discovered["evidence"]
        self.assertEqual(env["XDG_RUNTIME_DIR"], "/run/user/1000")
        self.assertEqual(env["DBUS_SESSION_BUS_ADDRESS"], "unix:path=/run/user/1000/bus")
        self.assertEqual(env["XDG_SESSION_TYPE"], "wayland")
        self.assertEqual(env["WAYLAND_DISPLAY"], "wayland-0")
        self.assertEqual(env["XDG_CURRENT_DESKTOP"], "KDE")
        self.assertTrue(evidence["active_local_graphical_session_proven"])
        self.assertTrue(evidence["kde_bus_identity_proven"])
        self.assertTrue(evidence["portal_bus_identity_proven"])
        self.assertTrue(evidence["secret_service_bus_identity_proven"])
        self.assertEqual(evidence["desktop_class"], "KDE_PLASMA")

    @patch("fa3_desktop_admission.os.getuid", return_value=1000)
    @patch("fa3_desktop_admission._safe_runtime_dir", return_value=Path("/run/user/1000"))
    @patch("fa3_desktop_admission._owned_socket", return_value=True)
    @patch("fa3_desktop_admission._systemd_user_environment_snapshot", return_value={})
    @patch("fa3_desktop_admission._loginctl_session_properties", return_value={})
    @patch("fa3_desktop_admission._user_bus_names", return_value=set())
    def test_session_discovery_does_not_invent_graphical_session(
        self,
        _bus,
        _session,
        _systemd,
        _socket,
        _runtime,
        _uid,
    ):
        discovered = discover_current_user_session_environment({})
        env = discovered["environment"]
        self.assertNotIn("XDG_SESSION_TYPE", env)
        self.assertNotIn("XDG_CURRENT_DESKTOP", env)
        report = evaluate_desktop(env, {**FULL_PROBES, "secret_service": True}, require_gui=True)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["capabilities"]["local_gui_session"], "FAIL")

    def test_runtime_dbus_probes_use_supplied_session_environment(self):
        env = self._env("KDE", "wayland")
        seen = []

        def probe(name, supplied):
            seen.append((name, supplied.get("DBUS_SESSION_BUS_ADDRESS")))
            return True

        verified = Mock(
            returncode=0,
            stdout="<node><interface name='org.freedesktop.Secret.Service'><method name='OpenSession'/></interface></node>",
            stderr="",
        )
        with (
            patch("fa3_desktop_admission._dbus_name_present", side_effect=probe),
            patch("fa3_desktop_admission._secret_service_introspect", return_value=verified),
        ):
            probes = collect_runtime_probes(env)
        self.assertTrue(probes["portal"])
        self.assertTrue(probes["secret_service"])
        self.assertTrue(probes["secret_service_live_name"])
        self.assertTrue(probes["secret_service_standard_interface"])
        self.assertEqual(probes["secret_service_introspection_format"], "BUSCTL_XML_INTERFACE")
        self.assertFalse(probes["secret_service_dbus_activation_attempted"])
        self.assertEqual(
            seen,
            [
                ("org.freedesktop.portal.Desktop", env["DBUS_SESSION_BUS_ADDRESS"]),
                ("org.freedesktop.secrets", env["DBUS_SESSION_BUS_ADDRESS"]),
            ],
        )

    @patch("fa3_desktop_admission.shutil.which", return_value="/usr/bin/busctl")
    @patch("fa3_desktop_admission._dbus_name_present", return_value=False)
    @patch("fa3_desktop_admission.subprocess.run")
    def test_secret_service_standard_introspection_may_activate_provider(
        self,
        run,
        _present,
        _which,
    ):
        run.return_value.returncode = 0
        run.return_value.stdout = "org.freedesktop.Secret.Service interface - -\n"
        run.return_value.stderr = ""
        env = self._env("KDE", "wayland")
        probe = _secret_service_probe(env)
        self.assertTrue(probe["available"])
        self.assertTrue(probe["live_name"])
        self.assertTrue(probe["standard_interface"])
        self.assertEqual(probe["introspection_format"], "BUSCTL_XML_INTERFACE")
        self.assertTrue(probe["dbus_activation_attempted"])
        argv = run.call_args.args[0]
        self.assertEqual(
            argv,
            [
                "/usr/bin/busctl",
                "--user",
                "--xml-interface",
                "introspect",
                "org.freedesktop.secrets",
                "/org/freedesktop/secrets",
            ],
        )
        self.assertEqual(
            run.call_args.kwargs["env"]["DBUS_SESSION_BUS_ADDRESS"],
            env["DBUS_SESSION_BUS_ADDRESS"],
        )

    @patch("fa3_desktop_admission._reference_secret_service_activation_aliases", return_value=["org.example.SecretCompat"])
    @patch("fa3_desktop_admission.shutil.which", return_value="/usr/bin/busctl")
    @patch("fa3_desktop_admission._dbus_name_present", return_value=False)
    @patch("fa3_desktop_admission.subprocess.run")
    def test_compatibility_endpoint_is_diagnostic_only_without_standard_name(
        self,
        run,
        _present,
        _which,
        _aliases,
    ):
        run.side_effect = [
            Mock(returncode=1, stdout="", stderr="standard name not activatable"),
            Mock(returncode=0, stdout="<node><interface name='org.freedesktop.Secret.Service'><method name='OpenSession'/></interface></node>", stderr=""),
            Mock(returncode=1, stdout="", stderr="standard name still unavailable"),
        ]
        env = self._env("KDE", "wayland")
        probe = _secret_service_probe(env)
        self.assertFalse(probe["available"])
        self.assertTrue(probe["reference_activation_attempted"])
        self.assertTrue(probe["compatibility_endpoint_verified"])
        self.assertFalse(probe["standard_interface"])
        self.assertFalse(probe["standard_name_verified"])
        self.assertFalse(probe["live_name"])
        self.assertEqual(run.call_args_list[1].args[0][3], "org.example.SecretCompat")
        self.assertEqual(run.call_args_list[2].args[0][3], "org.freedesktop.secrets")

    @patch("fa3_desktop_admission._reference_secret_service_activation_aliases", return_value=["org.example.SecretCompat"])
    @patch("fa3_desktop_admission.shutil.which", return_value="/usr/bin/busctl")
    @patch("fa3_desktop_admission._dbus_name_present", return_value=False)
    @patch("fa3_desktop_admission.subprocess.run")
    def test_activation_hint_may_start_standard_service_without_alias_interface(
        self,
        run,
        _present,
        _which,
        _aliases,
    ):
        run.side_effect = [
            Mock(returncode=1, stdout="", stderr="standard name initially unavailable"),
            Mock(returncode=1, stdout="", stderr="activation alias exposes no standard object"),
            Mock(returncode=0, stdout="<node><interface name='org.freedesktop.Secret.Service'><method name='OpenSession'/></interface></node>", stderr=""),
        ]
        env = self._env("KDE", "wayland")
        probe = _secret_service_probe(env)
        self.assertTrue(probe["available"])
        self.assertTrue(probe["reference_activation_attempted"])
        self.assertFalse(probe["compatibility_endpoint_verified"])
        self.assertTrue(probe["standard_interface"])
        self.assertTrue(probe["standard_name_verified"])
        self.assertTrue(probe["live_name"])

    @patch("fa3_desktop_admission._reference_secret_service_activation_aliases", return_value=["org.example.SecretCompat"])
    @patch("fa3_desktop_admission.shutil.which", return_value="/usr/bin/busctl")
    @patch("fa3_desktop_admission._dbus_name_present", return_value=False)
    @patch("fa3_desktop_admission.subprocess.run")
    def test_mapped_compatibility_endpoint_without_standard_interface_fails(
        self,
        run,
        _present,
        _which,
        _aliases,
    ):
        run.side_effect = [
            Mock(returncode=1, stdout="", stderr="standard name not activatable"),
            Mock(returncode=0, stdout="<node><interface name='org.example.PrivateWallet'><method name='Open'/></interface></node>", stderr=""),
            Mock(returncode=1, stdout="", stderr="standard name still unavailable"),
        ]
        env = self._env("KDE", "wayland")
        probe = _secret_service_probe(env)
        self.assertFalse(probe["available"])
        self.assertTrue(probe["reference_activation_attempted"])
        self.assertFalse(probe["compatibility_endpoint_verified"])
        self.assertFalse(probe["standard_interface"])

    def test_plasma_reference_activation_hint_is_non_authoritative(self):
        env = self._env("KDE", "wayland")
        aliases = _reference_secret_service_activation_aliases(env)
        self.assertEqual(aliases, ["org.kde.secretservicecompat"])
        plasma = json.loads((ROOT / "canonical/FA3-DESKTOP-PLASMA-001.json").read_text(encoding="utf-8"))
        activation = plasma["secret_service_activation"]
        self.assertEqual(activation["mode"], "REFERENCE_PROVIDER_COMPATIBILITY_ACTIVATION_HINT")
        self.assertFalse(activation["core_requirement"])
        self.assertFalse(activation["architectural_authority"])
        self.assertTrue(activation["standard_interface_required"])
        self.assertTrue(activation["standard_bus_name_required"])
        self.assertTrue(activation["compatibility_bus_name_allowed"])
        self.assertTrue(activation["compatibility_endpoint_diagnostic_only"])
        self.assertEqual(
            activation["activation_alias_semantics"],
            "ACTIVATION_ONLY_NO_CAPABILITY_OR_INTERFACE_AUTHORITY",
        )
        self.assertEqual(activation["preferred_standard_bus_name"], "org.freedesktop.secrets")
        self.assertEqual(activation["object_path"], "/org/freedesktop/secrets")
        self.assertEqual(activation["interface"], "org.freedesktop.Secret.Service")
        self.assertEqual(_reference_secret_service_activation_aliases(self._env("GNOME", "wayland")), [])

    @patch("fa3_desktop_admission._reference_secret_service_activation_aliases", return_value=[])
    @patch("fa3_desktop_admission.shutil.which", return_value="/usr/bin/busctl")
    @patch("fa3_desktop_admission._dbus_name_present", return_value=True)
    @patch("fa3_desktop_admission.subprocess.run")
    def test_live_standard_name_without_standard_interface_fails_closed(
        self,
        run,
        _present,
        _which,
        _aliases,
    ):
        run.return_value = Mock(returncode=1, stdout="", stderr="standard interface missing")
        probe = _secret_service_probe(self._env("KDE", "wayland"))
        self.assertFalse(probe["available"])
        self.assertFalse(probe["standard_interface"])
        self.assertFalse(probe["standard_name_verified"])

    @patch("fa3_desktop_admission._reference_secret_service_activation_aliases", return_value=[])
    @patch("fa3_desktop_admission.shutil.which", return_value="/usr/bin/busctl")
    @patch("fa3_desktop_admission._dbus_name_present", return_value=True)
    @patch("fa3_desktop_admission.subprocess.run")
    def test_human_readable_filtered_table_is_not_interface_identity_proof(
        self,
        run,
        _present,
        _which,
        _aliases,
    ):
        run.return_value = Mock(
            returncode=0,
            stdout=".OpenSession method sv (vo) - -\n.SearchItems method a{ss} aoao - -\n",
            stderr="",
        )
        probe = _secret_service_probe(self._env("KDE", "wayland"))
        self.assertFalse(probe["available"])
        self.assertFalse(probe["standard_interface"])
        self.assertFalse(probe["standard_name_verified"])

    @patch("fa3_desktop_admission._reference_secret_service_activation_aliases", return_value=[])
    @patch("fa3_desktop_admission.shutil.which", return_value="/usr/bin/busctl")
    @patch("fa3_desktop_admission._dbus_name_present", return_value=True)
    @patch("fa3_desktop_admission.subprocess.run")
    def test_malformed_introspection_xml_fails_closed(
        self,
        run,
        _present,
        _which,
        _aliases,
    ):
        run.return_value = Mock(returncode=0, stdout="<node><interface", stderr="")
        probe = _secret_service_probe(self._env("KDE", "wayland"))
        self.assertFalse(probe["available"])
        self.assertFalse(probe["standard_interface"])

    @patch("fa3_desktop_admission.shutil.which", return_value="/usr/bin/busctl")
    @patch("fa3_desktop_admission._dbus_name_present", return_value=False)
    @patch("fa3_desktop_admission.subprocess.run")
    def test_secret_service_activation_failure_remains_fail_closed(
        self,
        run,
        _present,
        _which,
    ):
        run.return_value.returncode = 1
        run.return_value.stdout = ""
        run.return_value.stderr = "service unavailable"
        env = self._env("KDE", "wayland")
        probe = _secret_service_probe(env)
        self.assertFalse(probe["available"])
        self.assertTrue(probe["dbus_activation_attempted"])
        probes = {**FULL_PROBES, "secret_service": probe["available"], "fa3_vault": False}
        report = evaluate_desktop(env, probes, require_gui=True)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["capabilities"]["secret_backend"], "FAIL")

    def test_secret_service_probe_remains_provider_neutral(self):
        text = (ROOT / "src/fa3_desktop_admission.py").read_text(encoding="utf-8")
        self.assertIn("org.freedesktop.secrets", text)
        self.assertIn("org.freedesktop.Secret.Service", text)
        for forbidden in ("kwallet-query", "kwalletd6", "ksecretd", "org.kde.KWallet"):
            self.assertNotIn(forbidden, text)

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
