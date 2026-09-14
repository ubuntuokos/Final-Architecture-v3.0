from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fa3_audit_chain import AuditChainError, append_event, read_jsonl, verify_records
from fa3_blackhole_admission import AdmissionDenied, validate_request
from fa3_blackhole_runtime_gate import current_host_gate, reference_gate


class AuditChainTests(unittest.TestCase):
    def test_valid_chain_passes_and_tampering_fails(self) -> None:
        key = "ab" * 32
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "audit.jsonl"
            append_event(path, {"kind": "one"}, key)
            append_event(path, {"kind": "two"}, key)
            report = verify_records(read_jsonl(path), key)
            self.assertEqual(report["result"], "PASS")
            self.assertEqual(report["records"], 2)

            records = read_jsonl(path)
            records[0]["event"]["kind"] = "tampered"
            with self.assertRaises(AuditChainError):
                verify_records(records, key)

    def test_short_audit_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(AuditChainError):
                append_event(Path(td) / "audit.jsonl", {"kind": "denied"}, "aa")


class AdmissionTests(unittest.TestCase):
    def _payload(self) -> dict:
        return {
            "input_media": "/data/raw/source.mov",
            "output_dir": "/data/processed/job-1",
            "hrb_lease_id": "lease-1",
            "resource_profile": {
                "cpu_threads": 8,
                "ram_mb": 8192,
                "vram_mb": 4096,
                "gpu_devices": ["GPU-example"],
                "virtual_profile": {"cu": 4, "tu": 2},
            },
        }

    def _lease(self, expires_at: datetime) -> dict:
        return {
            "schema": "fa3.hrb-blackhole-lease.v1",
            "lease_id": "lease-1",
            "workload_id": "FA3-BLACKHOLE-API-001",
            "status": "ACTIVE",
            "expires_at": expires_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "resources": {
                "cpu_threads": 16,
                "ram_mb": 16384,
                "vram_mb": 8192,
                "gpu_devices": ["GPU-example"],
            },
            "virtual_limits": {"cu": 8, "tu": 4},
        }

    def test_valid_hrb_lease_is_admitted(self) -> None:
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "lease-1.json").write_text(json.dumps(self._lease(now + timedelta(hours=1))), encoding="utf-8")
            result = validate_request(self._payload(), root, now=now)
            self.assertEqual(result["result"], "PASS")

    def test_expired_hrb_lease_is_fail_closed(self) -> None:
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "lease-1.json").write_text(json.dumps(self._lease(now - timedelta(seconds=1))), encoding="utf-8")
            with self.assertRaises(AdmissionDenied) as ctx:
                validate_request(self._payload(), root, now=now)
            self.assertEqual(ctx.exception.code, "HRB_LEASE_EXPIRED")

    def test_cu_tu_overcommit_is_denied(self) -> None:
        now = datetime.now(timezone.utc)
        payload = self._payload()
        payload["resource_profile"]["virtual_profile"]["cu"] = 64
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "lease-1.json").write_text(json.dumps(self._lease(now + timedelta(hours=1))), encoding="utf-8")
            with self.assertRaises(AdmissionDenied) as ctx:
                validate_request(payload, root, now=now)
            self.assertEqual(ctx.exception.code, "VIRTUAL_PROFILE_EXCEEDED")


class RuntimeGateTests(unittest.TestCase):
    def test_repository_reference_gate_passes(self) -> None:
        root = Path(__file__).resolve().parents[1]
        report = reference_gate(root)
        self.assertEqual(report["result"], "PASS", report.get("findings"))

    def test_current_host_gate_blocks_without_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = current_host_gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertFalse(report["blackhole_component_promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
