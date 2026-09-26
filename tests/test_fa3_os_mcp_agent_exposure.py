from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fa3_mcp_gateway import McpGateway
from fa3_os_mcp_adapter import create_adapters
from fa3_os_mcp_agent_exposure_gate import gate
from fa3_os_runtime import ingest_event, read_journal_events
from fa3_security_policy_plane import resolve_policy

ROOT = Path(__file__).resolve().parents[1]


def registry() -> dict:
    return {
        "schema": "fa3.mcp.capability-registry.v1",
        "profile": "FA3-MCP-CURRENT-HOST-001",
        "authority": "FA3-AUTH-MCP-GATEWAY-001",
        "policy_authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
        "fail_closed": True,
        "automatic_provider_activation": False,
        "direct_agent_provider_bypass": "DENY",
        "capability_delta": 0,
        "authority_delta": 0,
        "capabilities": [{
            "capability_id": "fa3.memory.retrieve",
            "risk_class": "R0",
            "side_effects": ["application-read"],
            "approval": "policy",
            "hrb_required": False,
            "providers": [{
                "provider_id": "FA3-OS-REFERENCE-RUNTIME-001",
                "adapter_id": "fa3.adapter.fa3-os.memory.retrieve",
                "state": "CONNECTED",
                "priority": 10,
                "evidence_ref": "fixture",
                "policy_mode": "external_resolver",
                "identity_scope": {"actor_prefixes": ["FA3-AGENT-"], "client_ids": ["fa3-agent-runtime"]},
                "require_scoped_arguments": True,
                "policy_scope_arguments": ["project_id", "workstream_id"],
                "require_policy_purpose": True,
                "receipt_audit_required": True,
            }],
        }],
    }


def request(*, actor: str = "FA3-AGENT-TEST", scoped: bool = True) -> dict:
    args = {"limit": 10}
    if scoped:
        args.update({"project_id": "P", "workstream_id": "W"})
    return {
        "actor_id": actor,
        "client_id": "fa3-agent-runtime",
        "session_id": "S",
        "capability_id": "fa3.memory.retrieve",
        "arguments": args,
        "policy_request": {"purpose": "unit test"},
    }


def peer(*, agent: bool = True) -> dict:
    return {
        "transport": "unix",
        "pid": os.getpid(),
        "uid": os.getuid(),
        "gid": os.getgid(),
        "cgroup": "0::/user.slice/fa3-agent.slice/test.scope" if agent else "0::/user.slice/app.slice/test.scope",
    }


class AgentExposureTests(unittest.TestCase):
    def configured(self) -> McpGateway:
        gateway = McpGateway(registry(), policy_resolver=resolve_policy)
        for adapter in create_adapters():
            gateway.register_adapter(adapter)
        return gateway

    def test_static_pending_repository_gate_passes(self) -> None:
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", json.dumps(report, indent=2))

    def test_non_agent_cgroup_denied(self) -> None:
        receipt = self.configured().invoke(request(), peer_context=peer(agent=False))
        self.assertEqual(receipt["result_status"], "denied")
        self.assertEqual(receipt["reason_code"], "POLICY_DENY")

    def test_wrong_actor_denied(self) -> None:
        receipt = self.configured().invoke(request(actor="OTHER"), peer_context=peer())
        self.assertEqual(receipt["reason_code"], "POLICY_DENY")

    def test_unscoped_retrieval_denied(self) -> None:
        receipt = self.configured().invoke(request(scoped=False), peer_context=peer())
        self.assertEqual(receipt["reason_code"], "POLICY_DENY")

    def test_scoped_agent_retrieval_is_minimized_and_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "active.jsonl"
            previous = os.environ.get("FA3_OS_JOURNAL_PATH")
            os.environ["FA3_OS_JOURNAL_PATH"] = str(journal)
            try:
                event_id = ingest_event({
                    "source_kind": "FA3_NATIVE",
                    "capture_kind": "APPLICATION_EVENT",
                    "action": "TEST",
                    "subject": {"kind": "WORKSTREAM", "reference": "W"},
                    "application_id": "Test",
                    "project_id": "P",
                    "session_id": "S",
                    "workstream_id": "W",
                    "artifact_id": "A",
                    "provenance": {"source_class": "FA3_NATIVE", "source_reference": "test"},
                    "confidence": 1.0,
                    "tags": ["test"],
                }, journal)["event_id"]
                gateway = self.configured()
                receipt = gateway.invoke(request(), peer_context=peer())
                self.assertEqual(receipt["result_status"], "success", receipt)
                self.assertIn(event_id, receipt["result"]["source_event_refs"])
                self.assertEqual(receipt["result"]["projection_mode"], "MINIMIZED_AGENT_CONTEXT")
                audit_id = receipt["result"]["audit_event_id"]
                rows = read_journal_events(journal)
                self.assertTrue(any(row.get("id") == audit_id and row.get("event_type") == "AUDIT" for row in rows))
            finally:
                if previous is None:
                    os.environ.pop("FA3_OS_JOURNAL_PATH", None)
                else:
                    os.environ["FA3_OS_JOURNAL_PATH"] = previous

    def test_client_supplied_allow_does_not_bypass_external_resolver(self) -> None:
        payload = request(actor="OTHER")
        payload["policy_decision"] = {
            "authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
            "status": "ALLOW",
            "capability_id": "fa3.memory.retrieve",
            "decision_id": "FORGED",
        }
        receipt = self.configured().invoke(payload, peer_context=peer())
        self.assertEqual(receipt["reason_code"], "POLICY_DENY")


    def test_user_service_working_directory_is_absolute_and_unquoted(self) -> None:
        template = (ROOT / "deployment/mcp-gateway/fa3-mcp-gateway-user.service.in").read_text(encoding="utf-8")
        installer = (ROOT / "bin/fa3-os-mcp-agent-exposure-install").read_text(encoding="utf-8")
        self.assertIn("WorkingDirectory=@WORKING_DIR@", template)
        self.assertNotIn("WorkingDirectory=@RUNTIME_ROOT@", template)
        self.assertIn('text = text.replace("@WORKING_DIR@", runtime_root)', installer)
        self.assertNotIn('text = text.replace("@WORKING_DIR@", q(runtime_root))', installer)
        self.assertIn("FA3 MCP runtime root must be absolute", installer)

    def test_installer_fails_closed_on_foreign_unit_and_has_owned_uninstall(self) -> None:
        installer = (ROOT / "bin/fa3-os-mcp-agent-exposure-install").read_text(encoding="utf-8")
        self.assertIn('MANAGED_MARKER="# FA3-MANAGED: FA3-MCP-GATEWAY-001"', installer)
        self.assertIn("unit collision with non-FA3-owned file", installer)
        self.assertIn("refusing to remove non-FA3-owned unit", installer)
        self.assertIn("--uninstall", installer)
        self.assertIn("capture_previous_state", installer)
        self.assertIn("fa3.mcp-gateway-install-state.v1", installer)
        self.assertIn("fa3.mcp-gateway-uninstall-receipt.v1", installer)
        self.assertIn('"upstream_resources_modified":False', installer)

    def test_current_host_workflow_propagates_pipeline_failures(self) -> None:
        workflow = (ROOT / ".github/workflows/fa3-os-mcp-agent-exposure.yml").read_text(encoding="utf-8")
        self.assertGreaterEqual(workflow.count("set -o pipefail"), 2)

    def test_current_host_agent_probe_uses_transient_service_not_scope(self) -> None:
        collector = (ROOT / "evidence/collect-fa3-os-mcp-agent-exposure-current-host.py").read_text(encoding="utf-8")
        self.assertIn('"--slice=fa3-agent.slice"', collector)
        self.assertNotIn('"--scope"', collector)
        self.assertIn('"--pipe"', collector)


    def test_current_host_collector_uses_run_unique_retrieval_scope(self) -> None:
        collector = (ROOT / "evidence/collect-fa3-os-mcp-agent-exposure-current-host.py").read_text(encoding="utf-8")
        self.assertIn("time.time_ns()", collector)
        self.assertIn('project_id = f"{PROJECT}-{run_scope}"', collector)
        self.assertIn('workstream_id = f"{WORKSTREAM}-{run_scope}"', collector)
        self.assertIn("_payload(project_id=project_id, workstream_id=workstream_id)", collector)


if __name__ == "__main__":
    unittest.main()
