from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from fa3_os_context_policy import (
    AuthorizationError,
    authorized_retrieve,
    effective_events,
    selective_erase,
    validate_gateway_authorization,
)
from fa3_os_current_host_gate import REQUIRED_EVIDENCE_FLAGS, _evidence_valid, _repo_head
from fa3_os_runtime import ingest_event, read_journal_events

ROOT = Path(__file__).resolve().parents[1]


def valid_request(artifact_id: str = "ART-TEST") -> dict:
    return {
        "source_kind": "FA3_NATIVE",
        "capture_kind": "APPLICATION_EVENT",
        "action": "FILE_SAVE",
        "subject": {"kind": "FILE", "reference": "/projects/test/shot.png"},
        "application_id": "Krita",
        "project_id": "TEST-PROJECT",
        "session_id": "TEST-SESSION",
        "workstream_id": "TEST-WORKSTREAM",
        "artifact_id": artifact_id,
        "provenance": {"source_class": "FA3_NATIVE", "source_reference": "test"},
        "confidence": 1.0,
        "tags": ["test"],
    }


def valid_authorization() -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "schema": "fa3.gateway-authorization-receipt.v1",
        "issuer": "central-mcp-gateway",
        "decision": "ALLOW",
        "capability": "FA3_OS_CONTEXT_READ",
        "policy_id": "FA3-OS-POLICY-001",
        "request_id": "REQ-TEST",
        "actor": "TEST-ACTOR",
        "purpose": "current-host regression",
        "issued_at": (now - dt.timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "expires_at": (now + dt.timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
        "gateway_runtime_admitted": True,
        "scope": {"project_ids": ["TEST-PROJECT"], "workstream_ids": ["TEST-WORKSTREAM"]},
    }


class Fa3OsContextPolicyTests(unittest.TestCase):
    def test_selective_erasure_is_append_only_and_hides_event_from_effective_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "active.jsonl"
            receipt = ingest_event(valid_request(), journal)
            event_id = receipt["event_id"]
            erase = selective_erase(
                journal,
                scope={"kind": "artifact", "value": "ART-TEST"},
                actor="TEST-ACTOR",
                reason="test erasure",
            )
            self.assertEqual(erase["matched_event_count"], 1)
            raw = read_journal_events(journal)
            self.assertTrue(any(row.get("id") == event_id for row in raw))
            self.assertTrue(any(row.get("event_type") == "TOMBSTONE" and row.get("target_event_id") == event_id for row in raw))
            self.assertFalse(any(row.get("id") == event_id for row in effective_events(journal)))

    def test_authorized_retrieval_is_gateway_gated_and_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "active.jsonl"
            event_id = ingest_event(valid_request(), journal)["event_id"]
            result = authorized_retrieve(
                journal,
                authorization=valid_authorization(),
                project_id="TEST-PROJECT",
                workstream_id="TEST-WORKSTREAM",
            )
            self.assertEqual(result["result"], "PASS")
            self.assertIn(event_id, result["source_event_refs"])
            audit_id = result["audit_event_id"]
            raw = read_journal_events(journal)
            self.assertTrue(any(row.get("id") == audit_id and row.get("event_type") == "AUDIT" for row in raw))

    def test_expired_or_non_admitted_gateway_receipt_fails_closed(self) -> None:
        expired = valid_authorization()
        expired["expires_at"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        with self.assertRaises(AuthorizationError):
            validate_gateway_authorization(expired)
        not_admitted = valid_authorization()
        not_admitted["gateway_runtime_admitted"] = False
        with self.assertRaises(AuthorizationError):
            validate_gateway_authorization(not_admitted)


class Fa3OsCurrentHostGateEvidenceTests(unittest.TestCase):
    def test_evidence_requires_every_canonical_current_host_flag(self) -> None:
        evidence = {
            "schema": "fa3.os-runtime-current-host-evidence.v1",
            "conformance_id": "FA3-OS-RUNTIME-CONFORMANCE-001",
            "result": "PASS",
            "captured_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "repository_head": _repo_head(ROOT),
            "journal_is_actual_default_path": True,
            "production_admitted": True,
            "status": "CURRENT_HOST_PASS",
        }
        for flag in REQUIRED_EVIDENCE_FLAGS:
            evidence[flag] = True
        ok, reasons = _evidence_valid(evidence, root=ROOT)
        self.assertTrue(ok, reasons)

        evidence["selective_erasure_retention_verified"] = False
        ok, reasons = _evidence_valid(evidence, root=ROOT)
        self.assertFalse(ok)
        self.assertTrue(any("selective_erasure_retention_verified" in reason for reason in reasons))

    def test_evidence_is_bound_to_repository_head_and_freshness(self) -> None:
        evidence = {
            "schema": "fa3.os-runtime-current-host-evidence.v1",
            "conformance_id": "FA3-OS-RUNTIME-CONFORMANCE-001",
            "result": "PASS",
            "captured_at": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)).isoformat().replace("+00:00", "Z"),
            "repository_head": "WRONG",
            "journal_is_actual_default_path": True,
            "production_admitted": True,
            "status": "CURRENT_HOST_PASS",
            **{flag: True for flag in REQUIRED_EVIDENCE_FLAGS},
        }
        ok, reasons = _evidence_valid(evidence, root=ROOT)
        self.assertFalse(ok)
        self.assertTrue(any("repository HEAD" in reason for reason in reasons))
        self.assertTrue(any("stale" in reason for reason in reasons))


if __name__ == "__main__":
    unittest.main()
