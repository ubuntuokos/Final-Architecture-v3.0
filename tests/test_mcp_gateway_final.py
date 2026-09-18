from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_mcp_gateway import Adapter, McpGateway
from fa3_mcp_gateway_gate import gate
from fa3_mcp_gateway_server import MODERN_PROTOCOL_VERSION, handle_mcp_rpc


def connected_gateway() -> McpGateway:
    registry = {
        "schema": "fa3.mcp.capability-registry.v1",
        "profile": "FA3-MCP-CURRENT-HOST-001",
        "authority": "FA3-AUTH-MCP-GATEWAY-001",
        "policy_authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
        "fail_closed": True,
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
                "evidence_ref": "fixture"
            }]
        }]
    }
    gw = McpGateway(registry)
    gw.register_adapter(Adapter("fa3.adapter.test.echo", "FA3-PROVIDER-TEST-001", lambda args: {"echo": args}))
    return gw


class FinalMcpGatewayTests(unittest.TestCase):
    def test_static_canonical_gate(self) -> None:
        self.assertEqual("PASS", gate(ROOT)["result"])

    def test_server_discover_is_stateless_modern(self) -> None:
        body = {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": {
            "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientCapabilities": {}
        }}}
        response = handle_mcp_rpc(connected_gateway(), body, {
            "MCP-Protocol-Version": MODERN_PROTOCOL_VERSION,
            "Mcp-Method": "server/discover",
            "Mcp-Name": "server/discover",
        })
        self.assertEqual([MODERN_PROTOCOL_VERSION], response["result"]["supportedVersions"])

    def test_mcp_session_id_is_rejected(self) -> None:
        body = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {"_meta": {
            "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientCapabilities": {}
        }}}
        response = handle_mcp_rpc(connected_gateway(), body, {
            "MCP-Protocol-Version": MODERN_PROTOCOL_VERSION,
            "Mcp-Method": "tools/list",
            "Mcp-Name": "tools/list",
            "Mcp-Session-Id": "legacy",
        })
        self.assertEqual(-32001, response["error"]["code"])
        self.assertEqual("MCP_SESSION_ID_FORBIDDEN", response["error"]["data"]["reason_code"])

    def test_header_body_mismatch_is_rejected(self) -> None:
        body = {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {"_meta": {
            "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientCapabilities": {}
        }}}
        response = handle_mcp_rpc(connected_gateway(), body, {
            "MCP-Protocol-Version": MODERN_PROTOCOL_VERSION,
            "Mcp-Method": "tools/call",
            "Mcp-Name": "x",
        })
        self.assertEqual("HEADER_BODY_MISMATCH", response["error"]["data"]["reason_code"])

    def test_tools_call_preserves_fa3_governance(self) -> None:
        meta = {
            "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientCapabilities": {},
            "io.fa3/governance": {
                "actor_id": "operator",
                "client_id": "test-client",
                "context_id": "ctx-1",
                "policy_decision": {
                    "authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
                    "decision_id": "p1",
                    "capability_id": "fa3.test.echo",
                    "status": "ALLOW"
                }
            }
        }
        body = {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
            "name": "fa3.test.echo",
            "arguments": {"value": 7},
            "_meta": meta
        }}
        response = handle_mcp_rpc(connected_gateway(), body, {
            "MCP-Protocol-Version": MODERN_PROTOCOL_VERSION,
            "Mcp-Method": "tools/call",
            "Mcp-Name": "fa3.test.echo",
        })
        receipt = response["result"]["structuredContent"]["receipt"]
        self.assertEqual("success", receipt["result_status"])
        self.assertEqual({"value": 7}, receipt["result"]["echo"])


if __name__ == "__main__":
    unittest.main()
