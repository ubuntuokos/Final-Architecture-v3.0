from __future__ import annotations

import datetime as dt
import json
import tempfile
import time
import unittest
from pathlib import Path

from fa3_os_context_policy import (
    AuthorizationError,
    authorized_retrieve,
    effective_events,
    record_mcp_gateway_retrieval_audit,
    selective_erase,
    validate_gateway_authorization,
    validate_mcp_gateway_receipt,
)
from fa3_os_current_host_gate import REQUIRED_EVIDENCE_FLAGS, _evidence_valid, _repo_head
from fa3_os_mcp_adapter import create_adapters
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


def valid_mcp_gateway_receipt(source_event_refs: list[str]) -> dict:
    return {
        "schema": "fa3.mcp.gateway.receipt.v1",
        "profile_id": "FA3-MCP-CURRENT-HOST-001",
        "authority": "FA3-AUTH-MCP-GATEWAY-001",
        "timestamp_epoch": int(time.time()),
        "actor_id": "TEST-ACTOR",
        "client_id": "TEST-CLIENT",
        "session_id": "TEST-SESSION",
        "capability_id": "fa3.memory.retrieve",
        "provider_id": "FA3-OS-REFERENCE-RUNTIME-001",
        "adapter_id": "fa3.adapter.fa3-os.memory.retrieve",
        "policy_decision_id": "POLICY-TEST",
        "approval_id": None,
        "resource_lease_id": None,
        "request_sha256": "a" * 64,
        "result_status": "success",
        "reason_code": "DISPATCH_PASS",
        "duration_ms": 1,
        "global_promotion_claim": False,
        "result": {
            "event_count": len(source_event_refs),
            "source_event_refs": source_event_refs,
            "events": [],
        },
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

    def test_mcp_gateway_receipt_is_validated_and_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "active.jsonl"
            event_id = ingest_event(valid_request(), journal)["event_id"]
            receipt = valid_mcp_gateway_receipt([event_id])
            self.assertIs(validate_mcp_gateway_receipt(receipt), receipt)
            audited = record_mcp_gateway_retrieval_audit(
                journal,
                gateway_receipt=receipt,
                purpose="current-host regression",
                project_id="TEST-PROJECT",
            )
            self.assertIn(event_id, audited["source_event_refs"])
            raw = read_journal_events(journal)
            self.assertTrue(
                any(
                    row.get("id") == audited["audit_event_id"]
                    and row.get("event_type") == "AUDIT"
                    for row in raw
                )
            )

    def test_mcp_gateway_receipt_wrong_authority_fails_closed(self) -> None:
        receipt = valid_mcp_gateway_receipt([])
        receipt["authority"] = "WRONG-AUTHORITY"
        with self.assertRaises(AuthorizationError):
            validate_mcp_gateway_receipt(receipt)

    def test_fa3_os_mcp_adapter_factory_is_bound_to_reference_runtime(self) -> None:
        adapters = create_adapters()
        self.assertEqual(len(adapters), 1)
        self.assertEqual(adapters[0].provider_id, "FA3-OS-REFERENCE-RUNTIME-001")
        self.assertEqual(adapters[0].adapter_id, "fa3.adapter.fa3-os.memory.retrieve")

    def test_expired_or_non_admitted_gateway_receipt_fails_closed(self) -> None:
        expired = valid_authorization()
        expired["expires_at"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        with self.assertRaises(AuthorizationError):
            validate_gateway_authorization(expired)
        not_admitted = valid_authorization()
        not_admitted["gateway_runtime_admitted"] = False
        with self.assertRaises(AuthorizationError):
            validate_gateway_authorization(not_admitted)


class Fa3OsCanonicalAdmissionStateTests(unittest.TestCase):
    def test_canonical_conformance_is_bound_to_durable_current_host_evidence(self) -> None:
        conformance = json.loads((ROOT / "canonical/FA3-OS-RUNTIME-CONFORMANCE-001.json").read_text())
        self.assertEqual(conformance["status"], "CURRENT_HOST_ADMITTED")
        self.assertTrue(conformance["production_admitted"])
        self.assertTrue(conformance["evidence_present"])
        self.assertFalse(conformance["promotion_claimed"])
        self.assertFalse(conformance["agent_exposure_admitted"])
        self.assertEqual(conformance["agent_exposure_status"], "ADAPTER_GATED")
        evidence_path = ROOT / conformance["current_host_evidence_ref"]
        self.assertTrue(evidence_path.is_file())
        evidence = json.loads(evidence_path.read_text())
        self.assertEqual(evidence["result"], "PASS")
        self.assertTrue(evidence["production_admitted"])
        self.assertFalse(evidence["global_promotion_claim"])
        self.assertFalse(evidence["agent_exposure_admitted"])
        self.assertEqual(evidence["source"]["workflow_run_id"], 35297182734)
        self.assertEqual(
            evidence["artifact"]["sha256"],
            "430b667173f40471232c21cef26ebc7347238b7331fba7e365ed2680d0e08def",
        )
        self.assertTrue(all(evidence["required_evidence_flags"].values()))

    def test_gui_exposes_admitted_host_but_keeps_agent_exposure_gated(self) -> None:
        page = (ROOT / "apps/fa3-control-center/qml/Fa3OsPage.qml").read_text()
        self.assertIn("CURRENT HOST E2E ADMITTED", page)
        self.assertIn("AGENT EXPOSURE ADAPTER-GATED", page)
        self.assertNotIn("CURRENT HOST E2E PENDING", page)


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
