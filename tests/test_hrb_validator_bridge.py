from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "libexec/fa3-host-resource-broker-validate-root.py"
CLIENT_PATH = ROOT / "libexec/fa3-host-resource-broker-validator.sh"
INSTALLER_PATH = ROOT / "bin/fa3-install-hrb-validator-bridge.sh"
COLLECTOR_PATH = ROOT / "evidence/collect-resource-admission-current-host.py"
ENFORCEMENT_PATH = ROOT / "canonical/resource-admission-current-host-enforcement.json"

spec = importlib.util.spec_from_file_location("fa3_hrb_validator_root", HELPER_PATH)
assert spec and spec.loader
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class HRBValidatorBridgeTests(unittest.TestCase):
    def valid_lease(self) -> dict:
        return {
            "schema": helper.LEASE_SCHEMA,
            "lease_id": "fixture",
            "issuer": "FA3-HOST-RESOURCE-BROKER-001",
        }

    def test_owned_regular_0600_json_is_accepted_for_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lease.json"
            raw = json.dumps(self.valid_lease()).encode()
            path.write_bytes(raw)
            path.chmod(0o600)
            self.assertEqual(helper.read_candidate(str(path), os.getuid()), raw)

    def test_relative_path_is_rejected(self) -> None:
        with self.assertRaises(helper.BridgeError):
            helper.read_candidate("relative.json", os.getuid())

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real.json"
            real.write_text(json.dumps(self.valid_lease()), encoding="utf-8")
            real.chmod(0o600)
            link = Path(tmp) / "lease.json"
            link.symlink_to(real)
            with self.assertRaises(helper.BridgeError):
                helper.read_candidate(str(link), os.getuid())

    def test_group_writable_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lease.json"
            path.write_text(json.dumps(self.valid_lease()), encoding="utf-8")
            path.chmod(0o620)
            with self.assertRaises(helper.BridgeError):
                helper.read_candidate(str(path), os.getuid())

    def test_schema_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lease.json"
            path.write_text('{"schema":"wrong"}', encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaises(helper.BridgeError):
                helper.read_candidate(str(path), os.getuid())

    def test_client_uses_noninteractive_sudo_and_never_names_hmac_key(self) -> None:
        text = CLIENT_PATH.read_text(encoding="utf-8")
        self.assertIn("sudo -n", text)
        self.assertNotIn("lease-hmac.key", text)

    def test_installer_keeps_secret_root_only_and_uses_visudo(self) -> None:
        text = INSTALLER_PATH.read_text(encoding="utf-8")
        self.assertIn("visudo -cf", text)
        self.assertIn("SECRET_ACCESS: ROOT_ONLY", text)
        self.assertNotIn("chmod 644", text)
        self.assertNotIn("chmod 640", text)

    def test_collector_default_is_privilege_separated_validator(self) -> None:
        text = COLLECTOR_PATH.read_text(encoding="utf-8")
        self.assertIn(
            'BROKER_DEFAULT = "/usr/local/bin/fa3-host-resource-broker-validator"',
            text,
        )

    def test_canonical_validation_command_uses_bridge(self) -> None:
        enforcement = json.loads(ENFORCEMENT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            enforcement["broker_validation_command"],
            [
                "/usr/local/bin/fa3-host-resource-broker-validator",
                "validate-lease",
                "{lease}",
            ],
        )
        self.assertTrue(enforcement["secret_boundary"]["hmac_key_root_only"])
        self.assertFalse(enforcement["secret_boundary"]["collector_secret_access"])


if __name__ == "__main__":
    unittest.main()
