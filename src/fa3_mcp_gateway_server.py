#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from fa3_mcp_gateway import Adapter, McpGateway

MODERN_PROTOCOL_VERSION = "2026-07-28"
SERVER_INFO = {"name": "fa3-central-mcp-gateway", "version": "3.0"}


def load_adapter_factories(gateway: McpGateway, specs: str | None = None) -> int:
    """Load admitted adapter factories declared by the host profile."""
    raw = specs if specs is not None else os.environ.get("FA3_MCP_ADAPTER_FACTORIES", "")
    registered = 0
    for spec in (part.strip() for part in raw.split(",")):
        if not spec:
            continue
        if ":" not in spec:
            raise RuntimeError(f"Invalid MCP adapter factory reference: {spec}")
        module_name, function_name = spec.split(":", 1)
        factory = getattr(importlib.import_module(module_name), function_name)
        produced = factory()
        adapters = (produced,) if isinstance(produced, Adapter) else tuple(produced)
        if not adapters:
            raise RuntimeError(f"MCP adapter factory returned no adapters: {spec}")
        for adapter in adapters:
            if not isinstance(adapter, Adapter):
                raise RuntimeError(f"MCP adapter factory returned invalid object: {spec}")
            gateway.register_adapter(adapter)
            registered += 1
    return registered


def _header(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return str(value)
    return None


def _rpc_error(request_id: Any, code: int, message: str, reason_code: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
            "data": {"reason_code": reason_code},
        },
    }


def _result(request_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload.setdefault("resultType", "complete")
    meta = payload.setdefault("_meta", {})
    if isinstance(meta, dict):
        meta.setdefault("io.modelcontextprotocol/serverInfo", SERVER_INFO)
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def _validate_modern_request(body: dict[str, Any], headers: Mapping[str, str]) -> dict[str, Any] | None:
    request_id = body.get("id")
    if _header(headers, "Mcp-Session-Id") is not None:
        return _rpc_error(request_id, -32001, "Mcp-Session-Id is forbidden on the FA3 modern endpoint", "MCP_SESSION_ID_FORBIDDEN")

    version = _header(headers, "MCP-Protocol-Version")
    if version != MODERN_PROTOCOL_VERSION:
        return _rpc_error(request_id, -32022, "Unsupported MCP protocol version", "UNSUPPORTED_PROTOCOL_VERSION")

    method = body.get("method")
    if not isinstance(method, str) or not method:
        return _rpc_error(request_id, -32600, "JSON-RPC method is required", "INVALID_SCHEMA")
    method_header = _header(headers, "Mcp-Method")
    name_header = _header(headers, "Mcp-Name")
    if method_header != method:
        return _rpc_error(request_id, -32020, "Mcp-Method does not match JSON-RPC method", "HEADER_BODY_MISMATCH")

    params = body.get("params", {})
    if not isinstance(params, dict):
        return _rpc_error(request_id, -32602, "params must be an object", "INVALID_SCHEMA")
    expected_name = params.get("name") if method == "tools/call" else method
    if name_header != expected_name:
        return _rpc_error(request_id, -32020, "Mcp-Name does not match request target", "HEADER_BODY_MISMATCH")

    meta = params.get("_meta")
    if not isinstance(meta, dict):
        return _rpc_error(request_id, -32602, "Per-request MCP metadata is required", "MISSING_PROTOCOL_METADATA")
    if meta.get("io.modelcontextprotocol/protocolVersion") != MODERN_PROTOCOL_VERSION:
        return _rpc_error(request_id, -32022, "Per-request protocol metadata mismatch", "UNSUPPORTED_PROTOCOL_VERSION")
    if not isinstance(meta.get("io.modelcontextprotocol/clientCapabilities"), dict):
        return _rpc_error(request_id, -32021, "Client capabilities metadata is required", "MISSING_PROTOCOL_METADATA")
    return None


def _tool_catalog(gateway: McpGateway) -> list[dict[str, Any]]:
    rows = []
    for item in sorted(gateway.list_capabilities(), key=lambda x: str(x.get("capability_id", ""))):
        if item.get("available") is not True:
            continue
        capability_id = str(item["capability_id"])
        rows.append({
            "name": capability_id,
            "title": capability_id,
            "description": f"FA3 governed capability ({item.get('risk_class', 'unknown')})",
            "inputSchema": {"type": "object", "additionalProperties": True},
        })
    return rows


def handle_mcp_rpc(gateway: McpGateway, body: dict[str, Any], headers: Mapping[str, str]) -> dict[str, Any]:
    """Handle the canonical MCP 2026-07-28 stateless request path."""
    if body.get("jsonrpc") != "2.0":
        return _rpc_error(body.get("id"), -32600, "jsonrpc must be 2.0", "INVALID_SCHEMA")

    validation = _validate_modern_request(body, headers)
    if validation is not None:
        return validation

    request_id = body.get("id")
    method = body["method"]
    params = body.get("params", {})
    meta = params.get("_meta", {})

    if method in {"initialize", "notifications/initialized"}:
        return _rpc_error(request_id, -32601, "Legacy initialization is forbidden on the modern endpoint", "LEGACY_INITIALIZE_FORBIDDEN")

    if method == "server/discover":
        return _result(request_id, {
            "supportedVersions": [MODERN_PROTOCOL_VERSION],
            "capabilities": {"tools": {"listChanged": False}},
            "instructions": "FA3 Central MCP Gateway; governed capabilities only.",
            "ttlMs": 0,
            "cacheScope": "private",
        })

    if method == "tools/list":
        return _result(request_id, {
            "tools": _tool_catalog(gateway),
            "ttlMs": 0,
            "cacheScope": "private",
        })

    if method == "tools/call":
        capability_id = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(capability_id, str) or not isinstance(arguments, dict):
            return _rpc_error(request_id, -32602, "tools/call requires name and object arguments", "INVALID_SCHEMA")
        governance = meta.get("io.fa3/governance")
        if not isinstance(governance, dict):
            governance = {}
        request = {
            "actor_id": governance.get("actor_id"),
            "client_id": governance.get("client_id"),
            "session_id": governance.get("context_id"),
            "capability_id": capability_id,
            "arguments": arguments,
            "provider_id": governance.get("provider_id"),
            "policy_decision": governance.get("policy_decision"),
            "approval": governance.get("approval"),
            "hrb_lease": governance.get("hrb_lease"),
            "secret_refs": governance.get("secret_refs", []),
        }
        receipt = gateway.invoke(request)
        return _result(request_id, {
            "content": [{"type": "text", "text": json.dumps(receipt, ensure_ascii=False, sort_keys=True)}],
            "structuredContent": {"receipt": receipt},
            "isError": receipt.get("result_status") != "success",
        })

    return _rpc_error(request_id, -32601, "Method not supported by FA3 Central MCP Gateway", "METHOD_NOT_SUPPORTED")


class Handler(BaseHTTPRequestHandler):
    gateway: McpGateway

    def _send(self, status: int, payload: Any, extra_headers: Mapping[str, str] | None = None) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _json_body(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1024 * 1024:
                return None
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    def do_GET(self) -> None:
        if self.path == "/healthz":
            payload = self.gateway.health()
            payload["canonical_profile"] = "FA3-MCP-GATEWAY-001"
            payload["protocol_version"] = MODERN_PROTOCOL_VERSION
            payload["transport_mode"] = "STATELESS"
            self._send(200, payload)
        elif self.path == "/readyz":
            self_payload = self.gateway.readiness()
            self._send(200 if self_payload["ready"] else 503, self_payload)
        elif self.path == "/capabilities":
            self._send(200, {"capabilities": self.gateway.list_capabilities()})
        elif self.path == "/mcp":
            self._send(405, {"error": "METHOD_NOT_ALLOWED"}, {"Allow": "POST"})
        else:
            self._send(404, {"error": "NOT_FOUND"})

    def do_DELETE(self) -> None:
        if self.path == "/mcp":
            self._send(405, {"error": "METHOD_NOT_ALLOWED"}, {"Allow": "POST"})
        else:
            self._send(404, {"error": "NOT_FOUND"})

    def do_POST(self) -> None:
        payload = self._json_body()
        if payload is None:
            self._send(400, {"error": "INVALID_JSON_OR_REQUEST_SIZE"})
            return

        if self.path == "/mcp":
            headers = {key: value for key, value in self.headers.items()}
            self._send(200, handle_mcp_rpc(self.gateway, payload, headers))
            return

        if self.path not in {"/invoke", "/v1/dispatch"}:
            self._send(404, {"error": "NOT_FOUND"})
            return

        receipt = self.gateway.invoke(payload)
        self._send(200 if receipt["result_status"] == "success" else 403, receipt)


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Central MCP/Capability Gateway current-host service")
    parser.add_argument("--registry", default="canonical/mcp-capability-registry.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18790)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("Refusing non-loopback bind without a separate canonical exposure profile")
    gateway = McpGateway.from_path(Path(args.registry))
    load_adapter_factories(gateway)
    Handler.gateway = gateway
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
