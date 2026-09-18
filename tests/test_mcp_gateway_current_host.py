from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_mcp_current_host_gate import gate, validate_receipt, validate_registry  # noqa: E402
from fa3_mcp_gateway import Adapter, McpGateway  # noqa: E402


def registry(*, connected: bool = True, hrb: bool = False, approval: str = "policy") -> dict:
    return {
        "schema": "fa3.mcp.capability-registry.v1",
        "profile": "FA3-MCP-CURRENT-HOST-001",
        "authority": "FA3-AUTH-MCP-GATEWAY-001",
        "policy_authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
        "status": "PENDING_CURRENT_HOST",
        "fail_closed": True,
        "automatic_provider_activation": False,
        "direct_agent_provider_bypass": "DENY",
        "capability_delta": 0,
        "authority_delta": 0,
        "capabilities": [{
            "capability_id": "fa3.test.echo",
            "risk_class": "R0",
            "side_effects": [],
            "approval": approval,
            "hrb_required": hrb,
            "providers": [{
                "provider_id": "PROVIDER-TEST-001",
                "adapter_id": "fa3.adapter.test",
                "state": "CONNECTED" if connected else "ADAPTER_GATED",
                "priority": 100,
                "evidence_ref": "fixture-evidence" if connected else None,
            }],
        }],
    }


def request() -> dict:
    return {
        "actor_id": "actor",
        "client_id": "client",
        "session_id": "session",
        "capability_id": "fa3.test.echo",
        "arguments": {"value": "ok"},
        "policy_decision": {
            "authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
            "decision_id": "decision",
            "capability_id": "fa3.test.echo",
            "status": "ALLOW",
        },
    }


def pass_receipt() -> dict:
    denials = {
        code: "DENY"
        for code in {
            "UNKNOWN_IDENTITY",
            "UNKNOWN_CAPABILITY",
            "UNADMITTED_ADAPTER",
            "INVALID_SCHEMA",
            "MISSING_POLICY_DECISION",
            "MISSING_REQUIRED_APPROVAL",
            "MISSING_OR_INVALID_HRB_LEASE",
            "INLINE_SECRET_FORBIDDEN",
        }
    }
    denials.update({
        "ADMITTED_PROVIDER_INVOCATION": "PASS",
        "EVIDENCE_RECEIPT": "PASS",
        "TIMEOUT_CANCELLATION": "PASS",
        "AUTHORITY_NONREGRESSION": "PASS",
        "MODERN_STATELESS_PROTOCOL": "PASS",
        "HEADER_ROUTING": "PASS",
    })
    return {
        "schema": "fa3.mcp.current-host.evidence.v1",
        "profile_id": "FA3-MCP-CURRENT-HOST-001",
        "gate_id": "FA3-GATE-MCP-CURRENT-HOST-001",
        "status": "PASS",
        "global_promotion_claim": False,
        "gateway_health": {"status": "ok", "authority": "FA3-AUTH-MCP-GATEWAY-001"},
        "gateway_readiness": {"ready": True},
        "checks": denials,
    }


class GatewayTests(unittest.TestCase):
    def configured(self, **kwargs) -> McpGateway:
        gateway = McpGateway(registry(**kwargs))
        gateway.register_adapter(Adapter("fa3.adapter.test", "PROVIDER-TEST-001", lambda args: {"echo": args}))
        return gateway

    def test_success_requires_connected_admitted_binding(self) -> None:
        receipt = self.configured().invoke(request())
        self.assertEqual(receipt["result_status"], "success")
        self.assertEqual(receipt["reason_code"], "DISPATCH_PASS")
        self.assertFalse(receipt["global_promotion_claim"])

    def test_unknown_identity_denied(self) -> None:
        payload = request()
        payload.pop("actor_id")
        self.assertEqual(self.configured().invoke(payload)["reason_code"], "UNKNOWN_IDENTITY")

    def test_unknown_capability_denied(self) -> None:
        payload = request()
        payload["capability_id"] = "fa3.unknown"
        self.assertEqual(self.configured().invoke(payload)["reason_code"], "UNKNOWN_CAPABILITY")

    def test_missing_policy_denied(self) -> None:
        payload = request()
        payload.pop("policy_decision")
        self.assertEqual(self.configured().invoke(payload)["reason_code"], "MISSING_POLICY_DECISION")

    def test_policy_deny(self) -> None:
        payload = request()
        payload["policy_decision"]["status"] = "DENY"
        self.assertEqual(self.configured().invoke(payload)["reason_code"], "POLICY_DENY")

    def test_adapter_gated_is_not_executable(self) -> None:
        self.assertEqual(self.configured(connected=False).invoke(request())["reason_code"], "UNADMITTED_ADAPTER")

    def test_approval_required(self) -> None:
        self.assertEqual(self.configured(approval="explicit").invoke(request())["reason_code"], "MISSING_REQUIRED_APPROVAL")

    def test_hrb_required(self) -> None:
        self.assertEqual(self.configured(hrb=True).invoke(request())["reason_code"], "MISSING_OR_INVALID_HRB_LEASE")

    def test_valid_hrb(self) -> None:
        payload = request()
        payload["hrb_lease"] = {
            "issuer": "FA3-HOST-RESOURCE-BROKER-001",
            "status": "ACTIVE",
            "lease_id": "lease",
            "expires_epoch": int(time.time()) + 60,
        }
        self.assertEqual(self.configured(hrb=True).invoke(payload)["result_status"], "success")

    def test_inline_secret_denied_and_value_not_in_receipt(self) -> None:
        payload = request()
        payload["token"] = "super-secret-value"
        receipt = self.configured().invoke(payload)
        self.assertEqual(receipt["reason_code"], "INLINE_SECRET_FORBIDDEN")
        self.assertNotIn("super-secret-value", str(receipt))

    def test_readiness_requires_bound_runtime_adapter(self) -> None:
        self.assertTrue(self.configured().readiness()["ready"])
        self.assertFalse(McpGateway(registry(connected=True)).readiness()["ready"])

    def test_static_registry_rejects_connected_without_evidence(self) -> None:
        data = registry()
        data["capabilities"][0]["providers"][0].pop("evidence_ref")
        self.assertTrue(any(item["code"] == "MCP-STATIC-015" for item in validate_registry(data)))

    def test_current_host_receipt_contract(self) -> None:
        self.assertEqual(validate_receipt(pass_receipt()), [])

    def test_missing_positive_check_blocks_receipt(self) -> None:
        receipt = pass_receipt()
        receipt["checks"]["ADMITTED_PROVIDER_INVOCATION"] = "PENDING"
        self.assertTrue(any(item["code"] == "MCP-HOST-008" for item in validate_receipt(receipt)))

    def test_static_gate_passes_repository_registry(self) -> None:
        report = gate(ROOT, static_only=True)
        self.assertEqual(report["result"], "PASS")
        self.assertFalse(report["global_promotion_claim"])

    def test_missing_real_receipt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = gate(ROOT, receipt_path=Path(temp) / "missing.json")
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["decision"]["exit_code"], 2)


if __name__ == "__main__":
    unittest.main()
