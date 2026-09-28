from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_mcp_day1_telemetry import ReceiptTelemetry, summarize  # noqa: E402
from fa3_mcp_gateway import Adapter, McpGateway  # noqa: E402


def gateway(observer):
    registry = {
        "schema": "fa3.mcp.capability-registry.v1",
        "profile": "FA3-MCP-CURRENT-HOST-001",
        "authority": "FA3-AUTH-MCP-GATEWAY-001",
        "policy_authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
        "capabilities": [{
            "capability_id": "fa3.test.echo",
            "risk_class": "R0",
            "approval": "policy",
            "hrb_required": False,
            "providers": [{
                "provider_id": "FA3-PROVIDER-TEST-001",
                "adapter_id": "fa3.adapter.test.echo",
                "state": "CONNECTED",
                "priority": 1,
            }],
        }],
    }
    obj = McpGateway(registry, receipt_observer=observer)
    obj.register_adapter(Adapter("fa3.adapter.test.echo", "FA3-PROVIDER-TEST-001", lambda args: {"echo": args}))
    return obj


def request():
    return {
        "actor_id": "operator",
        "client_id": "test-client",
        "session_id": "ctx-1",
        "capability_id": "fa3.test.echo",
        "arguments": {"value": 7},
        "policy_decision": {
            "authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
            "decision_id": "opaque-policy-identifier",
            "capability_id": "fa3.test.echo",
            "status": "ALLOW",
        },
    }


class McpDay1TelemetryTests(unittest.TestCase):
    def test_success_and_deny_are_recorded_without_payload_or_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "private" / "events.jsonl"
            gw = gateway(ReceiptTelemetry(path))
            payload = request()
            payload["arguments"] = {"hidden_token": "NEVER-LOG-THIS"}
            self.assertEqual("success", gw.invoke(payload)["result_status"])
            payload = request()
            payload["capability_id"] = "secret-as-unregistered-capability"
            self.assertEqual("UNKNOWN_CAPABILITY", gw.invoke(payload)["reason_code"])
            raw = path.read_text(encoding="utf-8")
            for secret in ("NEVER-LOG-THIS", "secret-as-unregistered-capability", "opaque-policy-identifier", "operator", "ctx-1"):
                self.assertNotIn(secret, raw)
            rows = [json.loads(line) for line in raw.splitlines()]
            self.assertEqual(["success", "denied"], [r["result_status"] for r in rows])
            self.assertEqual("REDACTED", rows[-1]["capability_id"])
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            report = summarize(path, now=time.time())
            self.assertEqual((2, 1, 1), (report["events"], report["success"], report["denied"]))
            self.assertFalse(report["global_promotion_claim"])

    def test_unknown_identity_does_not_log_attacker_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            gw = gateway(ReceiptTelemetry(path))
            payload = request()
            payload.pop("actor_id")
            payload["capability_id"] = "never-log-this-capability"
            self.assertEqual("UNKNOWN_IDENTITY", gw.invoke(payload)["reason_code"])
            self.assertEqual("REDACTED", json.loads(path.read_text())["capability_id"])

    def test_telemetry_failure_does_not_respond_with_false_success(self):
        def broken_observer(_receipt):
            raise OSError("I/O unavailable")
        with self.assertRaises(OSError):
            gateway(broken_observer).invoke(request())

    def test_rejects_world_readable_log_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text("")
            os.chmod(path, 0o644)
            gw = gateway(ReceiptTelemetry(path))
            with self.assertRaises(PermissionError):
                gw.invoke(request())
            with self.assertRaises(PermissionError):
                summarize(path)
            path.unlink()
            actual = Path(tmp) / "actual.jsonl"
            actual.write_text("")
            path.symlink_to(actual)
            with self.assertRaises(OSError):
                gw.invoke(request())

    def test_corrupt_rows_fail_and_empty_window_does_not_claim_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text('{"schema":"wrong"}\n')
            os.chmod(path, 0o600)
            with self.assertRaises(ValueError):
                summarize(path)
            path.write_text("")
            report = summarize(path)
            self.assertEqual(0, report["events"])
            self.assertEqual("OBSERVATION_ONLY", report["status"])
            self.assertIsNone(report["p95_duration_ms"])


if __name__ == "__main__":
    unittest.main()
