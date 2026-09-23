import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fa3_plasma_secret_service_diagnostic import (
    ALIAS,
    STANDARD,
    STANDARD_INTERFACE,
    _dbus_activation_descriptors,
    _introspection_diagnostic,
    _name_owner_diagnostic,
    _parse_kde_bool,
    _redact_unique_names,
    _systemd_show_fields,
    _systemd_user_mask_origins,
    _systemd_user_service_diagnostic,
    collect_plasma_secret_service_diagnostic,
)


class PlasmaSecretServiceDiagnosticTests(unittest.TestCase):
    def test_kde_boolean_parser_is_fail_safe(self):
        self.assertEqual(_parse_kde_bool("false", True), (False, "EXPLICIT_CONFIG"))
        self.assertEqual(_parse_kde_bool("true", False), (True, "EXPLICIT_CONFIG"))
        self.assertEqual(
            _parse_kde_bool("unexpected", True),
            (True, "INVALID_CONFIG_FALLBACK_TO_UPSTREAM_DEFAULT"),
        )

    def test_unique_name_redaction_preserves_shape_not_live_owner(self):
        redacted = _redact_unique_names('s ":1.247"')
        self.assertEqual(redacted, 's "<UNIQUE_NAME>"')
        self.assertNotIn(":1.247", redacted)

    @patch("fa3_plasma_secret_service_diagnostic._run_busctl")
    def test_live_alias_owner_is_parsed_without_promoting_raw_output(self, run_busctl):
        run_busctl.return_value = subprocess.CompletedProcess(
            args=["busctl"],
            returncode=0,
            stdout='s ":1.247"\n',
            stderr="",
        )
        report = _name_owner_diagnostic(
            {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"},
            ALIAS,
            live_names={ALIAS},
        )
        self.assertTrue(report["queried"])
        self.assertTrue(report["owner_parse_ok"])
        self.assertEqual(report["unique_owner"], ":1.247")
        self.assertEqual(report["stdout_shape"], 's "<UNIQUE_NAME>"')
        self.assertNotIn(":1.247", report["stdout_shape"])

    @patch("fa3_plasma_secret_service_diagnostic._run_busctl")
    def test_unquoted_busctl_owner_shape_is_accepted(self, run_busctl):
        run_busctl.return_value = subprocess.CompletedProcess(
            args=["busctl"],
            returncode=0,
            stdout="s :1.88\n",
            stderr="",
        )
        report = _name_owner_diagnostic(
            {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"},
            ALIAS,
            live_names={ALIAS},
        )
        self.assertTrue(report["owner_parse_ok"])
        self.assertEqual(report["unique_owner"], ":1.88")

    @patch("fa3_plasma_secret_service_diagnostic._run_busctl")
    def test_introspection_records_only_interface_metadata(self, run_busctl):
        xml = (
            '<node>'
            '<interface name="org.freedesktop.DBus.Introspectable"/>'
            f'<interface name="{STANDARD_INTERFACE}">'
            '<method name="OpenSession"/>'
            '</interface>'
            '</node>'
        )
        run_busctl.return_value = subprocess.CompletedProcess(
            args=["busctl"],
            returncode=0,
            stdout=xml,
            stderr="",
        )
        report = _introspection_diagnostic(
            {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"},
            ALIAS,
            target_live=True,
        )
        self.assertTrue(report["xml_parse_ok"])
        self.assertTrue(report["standard_interface_present"])
        self.assertIn(STANDARD_INTERFACE, report["interface_names"])
        self.assertNotIn("OpenSession", repr(report))

    def test_systemd_show_parser_emits_only_whitelisted_non_secret_fields(self):
        parsed = _systemd_show_fields(
            "LoadState=loaded\n"
            "ActiveState=failed\n"
            "SubState=failed\n"
            "Result=exit-code\n"
            "ExecMainCode=1\n"
            "ExecMainStatus=2\n"
            "NRestarts=3\n"
            "Environment=SECRET=DO_NOT_LEAK\n"
            "ExecStart={ path=/usr/bin/ksecretd ; argv[]=/usr/bin/ksecretd --token DO_NOT_LEAK ; }\n"
        )
        self.assertEqual(parsed["LoadState"], "loaded")
        self.assertEqual(parsed["ActiveState"], "failed")
        self.assertEqual(parsed["SubState"], "failed")
        self.assertEqual(parsed["Result"], "exit-code")
        self.assertEqual(parsed["ExecMainCode"], 1)
        self.assertEqual(parsed["ExecMainStatus"], 2)
        self.assertEqual(parsed["NRestarts"], 3)
        self.assertNotIn("Environment", parsed)
        self.assertNotIn("ExecStart", parsed)
        self.assertNotIn("DO_NOT_LEAK", repr(parsed))

    @patch("fa3_plasma_secret_service_diagnostic._activation_search_roots")
    def test_dbus_activation_descriptor_redacts_exec_arguments(self, roots):
        with tempfile.TemporaryDirectory() as td:
            service_root = Path(td) / "dbus-1" / "services"
            service_root.mkdir(parents=True)
            (service_root / "org.kde.secretservicecompat.service").write_text(
                "[D-BUS Service]\n"
                "Name=org.kde.secretservicecompat\n"
                "SystemdService=plasma-ksecretd.service\n"
                "Exec=/usr/libexec/ksecretd --token DO_NOT_LEAK --password SECRET\n",
                encoding="utf-8",
            )
            roots.return_value = [("TEST", service_root)]
            rows = _dbus_activation_descriptors({})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], ALIAS)
        self.assertEqual(rows[0]["systemd_service"], "plasma-ksecretd.service")
        self.assertEqual(rows[0]["exec_basename"], "ksecretd")
        self.assertFalse(rows[0]["exec_arguments_emitted"])
        self.assertNotIn("DO_NOT_LEAK", repr(rows))
        self.assertNotIn("--password", repr(rows))

    @patch("fa3_plasma_secret_service_diagnostic._systemd_unit_search_roots")
    def test_mask_origin_classifies_user_mask_without_emitting_paths_or_targets(self, roots):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            user = base / "user"
            admin = base / "admin"
            vendor = base / "vendor"
            user.mkdir()
            admin.mkdir()
            vendor.mkdir()
            (user / "kwalletd6.service").symlink_to("/dev/null")
            (vendor / "kwalletd6.service").write_text(
                "[Service]\nExecStart=/usr/bin/kwalletd6 --token DO_NOT_LEAK\n",
                encoding="utf-8",
            )
            (admin / "plasma-kwallet-pam.service").symlink_to("/dev/null")
            roots.return_value = [
                ("USER_CONFIG", user),
                ("ADMIN", admin),
                ("VENDOR", vendor),
            ]
            report = _systemd_user_mask_origins(
                {"HOME": "/home/private-user"},
                ["kwalletd6.service", "plasma-kwallet-pam.service"],
            )
        by_unit = {row["unit"]: row for row in report["units"]}
        self.assertEqual(by_unit["kwalletd6.service"]["effective_mask_origin"], "USER_CONFIG")
        self.assertEqual(by_unit["kwalletd6.service"]["masking_scopes"], ["USER_CONFIG"])
        self.assertEqual(by_unit["plasma-kwallet-pam.service"]["effective_mask_origin"], "ADMIN")
        self.assertFalse(report["paths_emitted"])
        self.assertFalse(report["symlink_targets_emitted"])
        self.assertFalse(report["unit_contents_read"])
        self.assertNotIn("/home/private-user", repr(report))
        self.assertNotIn(str(base), repr(report))
        self.assertNotIn("DO_NOT_LEAK", repr(report))
        self.assertNotIn("/dev/null", repr(report))

    @patch("fa3_plasma_secret_service_diagnostic._systemd_unit_search_roots")
    def test_mask_origin_does_not_treat_regular_vendor_unit_as_mask(self, roots):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.mkdir(exist_ok=True)
            (root / "kwalletd6.service").write_text("[Service]\n", encoding="utf-8")
            roots.return_value = [("VENDOR", root)]
            report = _systemd_user_mask_origins({}, ["kwalletd6.service"])
        row = report["units"][0]
        self.assertIsNone(row["effective_mask_origin"])
        self.assertEqual(row["masking_scopes"], [])
        self.assertEqual(row["entries"][0]["entry_type"], "REGULAR_FILE")
        self.assertFalse(row["entries"][0]["is_dev_null_mask"])

    @patch("fa3_plasma_secret_service_diagnostic._run_systemctl_user")
    def test_systemd_user_diagnostic_reports_service_state_without_journal_or_argv(self, run_systemctl):
        def fake(_env, argv, **_kwargs):
            if argv[0] == "list-units":
                return subprocess.CompletedProcess(
                    args=["systemctl"], returncode=0,
                    stdout="plasma-ksecretd.service loaded failed failed KDE Secret Service\n",
                    stderr="",
                )
            if argv[0] == "list-unit-files":
                return subprocess.CompletedProcess(
                    args=["systemctl"], returncode=0,
                    stdout="plasma-ksecretd.service enabled enabled\n",
                    stderr="",
                )
            if argv[0] == "show":
                return subprocess.CompletedProcess(
                    args=["systemctl"], returncode=0,
                    stdout=(
                        "LoadState=loaded\nActiveState=failed\nSubState=failed\n"
                        "Result=exit-code\nExecMainCode=1\nExecMainStatus=1\n"
                        "UnitFileState=enabled\nNRestarts=2\n"
                        "Environment=TOKEN=DO_NOT_LEAK\n"
                    ),
                    stderr="",
                )
            raise AssertionError(argv)

        run_systemctl.side_effect = fake
        report = _systemd_user_service_diagnostic(
            {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"},
            [{"systemd_service": "plasma-ksecretd.service"}],
        )
        self.assertTrue(report["queried"])
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["units"][0]["ActiveState"], "failed")
        self.assertEqual(report["units"][0]["ExecMainStatus"], 1)
        self.assertFalse(report["raw_journal_collected"])
        self.assertFalse(report["process_argv_collected"])
        self.assertFalse(report["environment_collected"])
        self.assertIn("mask_origins", report)
        self.assertFalse(report["mask_origins"]["paths_emitted"])
        self.assertFalse(report["mask_origins"]["symlink_targets_emitted"])
        self.assertFalse(report["mask_origins"]["unit_contents_read"])
        self.assertNotIn("DO_NOT_LEAK", repr(report))
        self.assertNotIn("Environment", repr(report))

    @patch("fa3_plasma_secret_service_diagnostic._name_owner_diagnostic")
    @patch("fa3_plasma_secret_service_diagnostic._introspection_diagnostic")
    @patch("fa3_plasma_secret_service_diagnostic._user_bus_names", return_value=set())
    @patch("fa3_plasma_secret_service_diagnostic.shutil.which")
    def test_explicit_disabled_state_is_reported_without_secret_content(
        self, which, _names, introspect, owner
    ):
        which.side_effect = lambda name: "/usr/bin/ksecretd" if name == "ksecretd" else None
        owner.return_value = {
            "queried": False,
            "reason": "WELL_KNOWN_NAME_NOT_LIVE",
            "returncode": None,
            "owner_parse_ok": False,
            "unique_owner": None,
            "stdout_shape": None,
        }
        introspect.return_value = {
            "queried": False,
            "returncode": None,
            "xml_parse_ok": False,
            "standard_interface_present": False,
            "interface_names": [],
            "stderr_summary": "",
        }
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            config = home / ".config"
            config.mkdir()
            (config / "kwalletrc").write_text(
                "[KSecretD]\nEnabled=false\n"
                "[org.freedesktop.secrets]\napiEnabled=true\n"
                "[Wallet]\nPassword=DO_NOT_LEAK\n",
                encoding="utf-8",
            )
            report = collect_plasma_secret_service_diagnostic(
                {"HOME": str(home), "DBUS_SESSION_BUS_ADDRESS": "unix:path=/tmp/fake"}
            )
        self.assertTrue(report["read_only"])
        self.assertFalse(report["secret_values_read"])
        self.assertFalse(report["secret_values_emitted"])
        self.assertEqual(report["admission_effect"], "NONE_DIAGNOSTIC_ONLY")
        self.assertEqual(report["promotion_effect"], "NONE_DIAGNOSTIC_ONLY")
        self.assertTrue(report["ksecretd_binary_present"])
        self.assertFalse(report["ksecretd_enabled_effective"])
        self.assertTrue(report["fdo_secrets_api_enabled_effective"])
        self.assertNotIn("DO_NOT_LEAK", repr(report))
        self.assertNotIn("Password", repr(report))

    @patch("fa3_plasma_secret_service_diagnostic._name_owner_diagnostic")
    @patch("fa3_plasma_secret_service_diagnostic._introspection_diagnostic")
    @patch(
        "fa3_plasma_secret_service_diagnostic._user_bus_names",
        return_value={ALIAS},
    )
    @patch(
        "fa3_plasma_secret_service_diagnostic.shutil.which",
        return_value="/usr/bin/ksecretd",
    )
    def test_absent_config_uses_upstream_enabled_defaults(
        self, _which, _names, introspect, owner
    ):
        owner.side_effect = [
            {
                "queried": True,
                "reason": None,
                "returncode": 0,
                "owner_parse_ok": True,
                "unique_owner": ":1.9",
                "stdout_shape": 's "<UNIQUE_NAME>"',
            },
            {
                "queried": False,
                "reason": "WELL_KNOWN_NAME_NOT_LIVE",
                "returncode": None,
                "owner_parse_ok": False,
                "unique_owner": None,
                "stdout_shape": None,
            },
        ]
        introspect.return_value = {
            "queried": True,
            "returncode": 0,
            "xml_parse_ok": True,
            "standard_interface_present": True,
            "interface_names": [STANDARD_INTERFACE],
            "stderr_summary": "",
        }
        with tempfile.TemporaryDirectory() as td:
            report = collect_plasma_secret_service_diagnostic({"HOME": td})
        self.assertFalse(report["config_file_present"])
        self.assertTrue(report["ksecretd_enabled_effective"])
        self.assertEqual(report["ksecretd_enabled_source"], "UPSTREAM_DEFAULT")
        self.assertTrue(report["fdo_secrets_api_enabled_effective"])
        self.assertTrue(report["reference_alias_live"])
        self.assertFalse(report["standard_secret_service_live"])
        self.assertEqual(report["reference_alias_owner"]["unique_owner"], ":1.9")
        self.assertTrue(report["reference_alias_introspection"]["standard_interface_present"])
        self.assertTrue(report["reference_owner_introspection"]["standard_interface_present"])
        self.assertEqual(report["admission_effect"], "NONE_DIAGNOSTIC_ONLY")
        self.assertEqual(report["promotion_effect"], "NONE_DIAGNOSTIC_ONLY")


if __name__ == "__main__":
    unittest.main()
