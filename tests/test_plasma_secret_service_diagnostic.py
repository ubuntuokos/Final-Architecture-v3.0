import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fa3_plasma_secret_service_diagnostic import (
    ALIAS,
    STANDARD,
    STANDARD_INTERFACE,
    _introspection_diagnostic,
    _name_owner_diagnostic,
    _parse_kde_bool,
    _redact_unique_names,
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
