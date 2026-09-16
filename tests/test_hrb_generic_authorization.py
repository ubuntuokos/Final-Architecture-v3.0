from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
AUTHORIZE_HELPER = ROOT / "libexec/fa3-host-resource-broker-authorize-root.py"
VALIDATE_HELPER = ROOT / "libexec/fa3-host-resource-broker-validate-root.py"
GENERIC_COLLECTOR = ROOT / "evidence/collect-resource-admission-current-host-generic.py"
AUTHORIZE_CLIENT = ROOT / "libexec/fa3-host-resource-broker-authorizer.sh"
VALIDATE_CLIENT = ROOT / "libexec/fa3-host-resource-broker-validator.sh"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


authorizer = load_module("fa3_hrb_authorizer_root", AUTHORIZE_HELPER)
validator = load_module("fa3_hrb_validator_root_generic", VALIDATE_HELPER)
collector = load_module("fa3_hrb_generic_collector", GENERIC_COLLECTOR)


class HRBGenericAuthorizationTests(unittest.TestCase):
    def workload(self) -> dict:
        return {
            "schema": authorizer.WORKLOAD_SCHEMA,
            "workload_id": "cpu-test",
            "requirements": [
                {"metric": "cpu.physical_cores", "operator": ">=", "value": 8},
                {"metric": "memory.total_gib", "operator": ">=", "value": 16},
            ],
        }

    def authorization(self, *, now: int = 1000, key: bytes = b"k" * 32) -> dict:
        return authorizer.issue_authorization(
            self.workload(),
            {"cpu.physical_cores": 16.0, "memory.total_gib": 64.0, "numa.nodes": 2.0},
            key,
            host="test-host",
            now_epoch=now,
            ttl_seconds=300,
            nonce="fixture-nonce",
        )

    def test_generic_authorization_is_hrb_signed_and_valid(self) -> None:
        key = b"k" * 32
        record = self.authorization(key=key)
        self.assertEqual(record["schema"], validator.AUTH_SCHEMA)
        self.assertEqual(record["authority"], validator.AUTHORITY)
        self.assertEqual(record["requested_resource_classes"], ["cpu", "memory"])
        self.assertTrue(validator.validate_generic_authorization(
            json.dumps(record).encode(), key=key, now_epoch=1001, host="test-host"
        ))

    def test_wrong_key_and_expired_record_fail_closed(self) -> None:
        record = self.authorization()
        raw = json.dumps(record).encode()
        self.assertFalse(validator.validate_generic_authorization(raw, key=b"x" * 32, now_epoch=1001, host="test-host"))
        self.assertFalse(validator.validate_generic_authorization(raw, key=b"k" * 32, now_epoch=1301, host="test-host"))

    def test_generic_authorizer_rejects_accelerator_requirement(self) -> None:
        workload = self.workload()
        workload["requirements"].append({"metric": "gpu.vram_gib", "operator": ">=", "value": 1})
        with self.assertRaises(authorizer.AuthorizationError):
            authorizer.issue_authorization(
                workload,
                {"cpu.physical_cores": 16.0, "memory.total_gib": 64.0, "numa.nodes": 2.0},
                b"k" * 32,
                host="test-host",
                now_epoch=1000,
                nonce="fixture-nonce",
            )

    def test_unsatisfied_cpu_requirement_is_rejected(self) -> None:
        workload = self.workload()
        workload["requirements"][0]["value"] = 32
        with self.assertRaises(authorizer.AuthorizationError):
            authorizer.issue_authorization(
                workload,
                {"cpu.physical_cores": 16.0, "memory.total_gib": 64.0, "numa.nodes": 2.0},
                b"k" * 32,
                host="test-host",
                now_epoch=1000,
                nonce="fixture-nonce",
            )

    def test_collector_requires_exact_workload_and_resource_class_binding(self) -> None:
        record = self.authorization(now=1000)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "authorization.json"
            broker = Path(tmp) / "validator"
            path.write_text(json.dumps(record), encoding="utf-8")
            broker.write_text("fixture", encoding="utf-8")
            with mock.patch.object(collector, "_run", return_value=(0, "VALID\n", "")):
                _, errors = collector.validate_authorization(
                    path, str(broker), self.workload(), ["cpu", "memory"], host="test-host", now_epoch=1001
                )
                self.assertEqual(errors, [])
                _, errors = collector.validate_authorization(
                    path, str(broker), self.workload(), ["cpu"], host="test-host", now_epoch=1001
                )
                self.assertIn("AUTHORIZATION_RESOURCE_CLASS_MISMATCH", errors)

    def test_non_root_clients_do_not_name_or_read_hmac_key(self) -> None:
        for path in (AUTHORIZE_CLIENT, VALIDATE_CLIENT, GENERIC_COLLECTOR):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("lease-hmac.key", text)
        self.assertIn("sudo -n", AUTHORIZE_CLIENT.read_text(encoding="utf-8"))
        self.assertIn("validate-authorization", VALIDATE_CLIENT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
