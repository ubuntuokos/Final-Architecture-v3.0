import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fa3_plasma_secret_service_diagnostic import (
    _parse_kde_bool,
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

    @patch("fa3_plasma_secret_service_diagnostic._user_bus_names", return_value=set())
    @patch("fa3_plasma_secret_service_diagnostic.shutil.which")
    def test_explicit_disabled_state_is_reported_without_secret_content(self, which, _names):
        which.side_effect = lambda name: "/usr/bin/ksecretd" if name == "ksecretd" else None
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
        self.assertTrue(report["ksecretd_binary_present"])
        self.assertFalse(report["ksecretd_enabled_effective"])
        self.assertTrue(report["fdo_secrets_api_enabled_effective"])
        self.assertNotIn("DO_NOT_LEAK", repr(report))
        self.assertNotIn("Password", repr(report))

    @patch("fa3_plasma_secret_service_diagnostic._user_bus_names", return_value={"org.kde.secretservicecompat"})
    @patch("fa3_plasma_secret_service_diagnostic.shutil.which", return_value="/usr/bin/ksecretd")
    def test_absent_config_uses_upstream_enabled_defaults(self, _which, _names):
        with tempfile.TemporaryDirectory() as td:
            report = collect_plasma_secret_service_diagnostic({"HOME": td})
        self.assertFalse(report["config_file_present"])
        self.assertTrue(report["ksecretd_enabled_effective"])
        self.assertEqual(report["ksecretd_enabled_source"], "UPSTREAM_DEFAULT")
        self.assertTrue(report["fdo_secrets_api_enabled_effective"])
        self.assertTrue(report["reference_alias_live"])


if __name__ == "__main__":
    unittest.main()
