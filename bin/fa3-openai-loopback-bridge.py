#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.server
import json
import ssl
import urllib.error
import urllib.request
from typing import Final

UPSTREAM_BASE: Final[str] = "https://api.openai.com/v1"
MAX_REQUEST_BYTES: Final[int] = 2 * 1024 * 1024
MAX_RESPONSE_BYTES: Final[int] = 16 * 1024 * 1024
ALLOWED = {
    ("GET", "/v1/models"),
    ("POST", "/v1/chat/completions"),
}


class BridgeError(RuntimeError):
    pass


def bearer(header: str | None) -> str:
    if not header or not header.startswith("Bearer "):
        raise BridgeError("bearer credential required")
    token = header[7:].strip()
    if not token or len(token) > 8192:
        raise BridgeError("invalid bearer credential envelope")
    return token


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "FA3OpenAILoopback/1"

    def log_message(self, fmt: str, *args: object) -> None:
        # Never emit request headers, bodies, or credentials.
        return

    def _json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _forward(self) -> None:
        path = self.path.split("?", 1)[0]
        if (self.command, path) not in ALLOWED:
            self._json(404, {"error": {"message": "FA3 OpenAI bridge path denied"}})
            return
        try:
            token = bearer(self.headers.get("Authorization"))
        except BridgeError:
            self._json(401, {"error": {"message": "Bearer authentication required"}})
            return

        body = None
        if self.command == "POST":
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._json(400, {"error": {"message": "invalid content length"}})
                return
            if length <= 0 or length > MAX_REQUEST_BYTES:
                self._json(413, {"error": {"message": "request size denied"}})
                return
            body = self.rfile.read(length)

        req = urllib.request.Request(
            UPSTREAM_BASE + path.removeprefix("/v1"),
            data=body,
            method=self.command,
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/json",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=180.0, context=ssl.create_default_context()) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    self._json(502, {"error": {"message": "upstream response exceeds FA3 bridge limit"}})
                    return
                self.send_response(int(response.status))
                self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                request_id = response.headers.get("x-request-id")
                if request_id:
                    self.send_header("x-request-id", request_id)
                self.end_headers()
                self.wfile.write(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raw = b'{"error":{"message":"upstream error response exceeds FA3 bridge limit"}}'
            self.send_response(int(exc.code))
            self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            request_id = exc.headers.get("x-request-id")
            if request_id:
                self.send_header("x-request-id", request_id)
            self.end_headers()
            self.wfile.write(raw)
        except urllib.error.URLError:
            self._json(502, {"error": {"message": "OpenAI upstream transport unavailable"}})

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._json(200, {
                "schema": "fa3.openai-loopback-bridge-health.v1",
                "status": "READY",
                "credential_storage": False,
                "upstream": "api.openai.com",
            })
            return
        self._forward()

    def do_POST(self) -> None:
        self._forward()


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 loopback-only OpenAI API projection")
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    args = ap.parse_args()
    if args.bind not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("FA3 OpenAI bridge must bind to loopback")
    server = http.server.ThreadingHTTPServer((args.bind, args.port), Handler)
    server.daemon_threads = True
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
