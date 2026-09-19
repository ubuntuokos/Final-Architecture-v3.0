import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_kde_secret_service_reference_diagnostics import (
    _boolean_state,
    _config_diagnostics,
    collect_kde_secret_service_reference_diagnostics,
)


class KdeSecretServiceReferenceDiagnosticsTests(unittest.TestCase):
    def test_boolean_state_is_bounded_and_explicit(self):
        self.assertEqual(_boolean_state("true"), "TRUE")
        self.assertEqual(_boolean_state("OFF"), "FALSE")
        self.assertEqual(_boolean_state(None), "UNSET")
        self.assertEqual(_boolean_state("maybe"), "INVALID")

    def test_kwalletrc_reads_only_two_non_secret_flags(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            cfg = home / ".config" / "kwalletrc"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(
                "[KSecretD]\n"
                "Enabled=false\n"
                "SecretSentinel=DO_NOT_LEAK\n"
                "[org.freedesktop.secrets]\n"
                "apiEnabled=true\n"
                "[Wallet]\n"
                "Default Wallet=DO_NOT_LEAK_EITHER\n",
                encoding="utf-8",
            )
            report = _config_diagnostics({"HOME": str(home)})
            encoded = json.dumps(report, sort_keys=True)
            self.assertEqual(report["file_status"], "READABLE")
            self.assertEqual(report["ksecret_backend_enabled"], "FALSE")
            self.assertEqual(report["standard_secret_service_api_enabled"], "TRUE")
            self.assertNotIn("DO_NOT_LEAK", encoded)
            self.assertNotIn("Default Wallet", encoded)
            self.assertFalse(report["authoritative_for_pass"])

    def test_kwalletrc_symlink_is_rejected_without_reading_target(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            config = home / ".config"
            config.mkdir(parents=True)
            target = home / "target.ini"
            target.write_text("[KSecretD]\nEnabled=true\n", encoding="utf-8")
            (config / "kwalletrc").symlink_to(target)
            report = _config_diagnostics({"HOME": str(home)})
            self.assertEqual(report["file_status"], "REJECTED_SYMLINK")
            self.assertEqual(report["ksecret_backend_enabled"], "UNSET")

    @patch("fa3_kde_secret_service_reference_diagnostics.shutil.which", return_value="/usr/bin/busctl")
    @patch("fa3_kde_secret_service_reference_diagnostics.subprocess.run")
    def test_dbus_diagnostics_return_only_requested_target_states(self, run, _which):
        def fake(argv, **kwargs):
            if "NameHasOwner" in argv:
                name = argv[-1]
                return Mock(returncode=0, stdout=f"b {'true' if name == 'org.kde.secretservicecompat' else 'false'}\n", stderr="")
            if "ListActivatableNames" in argv:
                return Mock(
                    returncode=0,
                    stdout='as 3 "org.freedesktop.secrets" "org.kde.secretservicecompat" "org.example.Unrelated"\n',
                    stderr="",
                )
            raise AssertionError(argv)
        run.side_effect = fake
        report = collect_kde_secret_service_reference_diagnostics(
            {
                "HOME": "/nonexistent",
                "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
            },
            alias="org.kde.secretservicecompat",
        )
        owners = report["dbus"]["owners"]
        activatable = report["dbus"]["activatable"]["targets"]
        self.assertEqual(set(owners), {"org.freedesktop.secrets", "org.kde.secretservicecompat"})
        self.assertFalse(owners["org.freedesktop.secrets"]["has_owner"])
        self.assertTrue(owners["org.kde.secretservicecompat"]["has_owner"])
        self.assertEqual(set(activatable), {"org.freedesktop.secrets", "org.kde.secretservicecompat"})
        self.assertTrue(activatable["org.freedesktop.secrets"])
        self.assertTrue(activatable["org.kde.secretservicecompat"])
        self.assertNotIn("org.example.Unrelated", json.dumps(report))
        self.assertFalse(report["authoritative_for_pass"])
        self.assertFalse(report["mutation_performed"])
        self.assertFalse(report["secret_material_read"])


if __name__ == "__main__":
    unittest.main()
