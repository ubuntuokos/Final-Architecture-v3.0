#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
import socket
import socketserver
import struct
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from fa3_mcp_gateway import Adapter, McpGateway


def load_adapter_factories(gateway: McpGateway, specs: str | None = None) -> int:
    """Load admitted adapter factories declared by the host profile.

    Specs are comma-separated module:function references. Factories return one
    Adapter or an iterable of Adapters. Any malformed factory fails startup.
    """
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


def load_policy_resolver(spec: str | None = None):
    raw = spec if spec is not None else os.environ.get("FA3_MCP_POLICY_RESOLVER", "")
    raw = raw.strip()
    if not raw:
        return None
    if ":" not in raw:
        raise RuntimeError(f"Invalid MCP policy resolver reference: {raw}")
    module_name, function_name = raw.split(":", 1)
    return getattr(importlib.import_module(module_name), function_name)


class ThreadingUnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    gateway: McpGateway

    def _peer_context(self) -> dict[str, Any]:
        if getattr(self.server, "address_family", None) != socket.AF_UNIX:
            return {"transport": "tcp", "address": str(self.client_address)}
        size = struct.calcsize("3i")
        pid, uid, gid = struct.unpack("3i", self.connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, size))
        try:
            cgroup = Path(f"/proc/{pid}/cgroup").read_text(encoding="utf-8")
        except Exception:
            cgroup = ""
        return {"transport": "unix", "pid": pid, "uid": uid, "gid": gid, "cgroup": cgroup}

    def _send(self, status: int, payload: Any) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._send(200, self.gateway.health())
        elif self.path == "/readyz":
            payload = self.gateway.readiness()
            self._send(200 if payload["ready"] else 503, payload)
        elif self.path == "/capabilities":
            self._send(200, {"capabilities": self.gateway.list_capabilities()})
        else:
            self._send(404, {"error": "NOT_FOUND"})

    def do_POST(self) -> None:
        if self.path != "/invoke":
            self._send(404, {"error": "NOT_FOUND"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1024 * 1024:
                self._send(400, {"error": "INVALID_REQUEST_SIZE"})
                return
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request must be object")
        except Exception:
            self._send(400, {"error": "INVALID_JSON"})
            return
        if "_peer_context" in payload:
            self._send(400, {"error": "RESERVED_FIELD"})
            return
        receipt = self.gateway.invoke(payload, peer_context=self._peer_context())
        self._send(200 if receipt["result_status"] == "success" else 403, receipt)


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Central MCP/Capability Gateway current-host service")
    parser.add_argument("--registry", default="canonical/mcp-capability-registry.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18790)
    parser.add_argument("--unix-socket")
    args = parser.parse_args()
    resolver = load_policy_resolver()
    gateway = McpGateway.from_path(Path(args.registry), policy_resolver=resolver)
    load_adapter_factories(gateway)
    Handler.gateway = gateway
    if args.unix_socket:
        sock = Path(args.unix_socket).expanduser()
        sock.parent.mkdir(parents=True, exist_ok=True)
        try:
            sock.unlink()
        except FileNotFoundError:
            pass
        server = ThreadingUnixHTTPServer(str(sock), Handler)
        os.chmod(sock, 0o600)
        try:
            server.serve_forever()
        finally:
            server.server_close()
            try:
                sock.unlink()
            except FileNotFoundError:
                pass
        return 0
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("Refusing non-loopback bind without a separate canonical exposure profile")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
