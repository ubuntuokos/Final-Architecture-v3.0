#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.client
import json
import socket
from pathlib import Path
from typing import Any


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float = 5.0):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        self.sock = sock


def request(
    socket_path: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float = 5.0,
) -> tuple[int, dict[str, Any]]:
    conn = UnixHTTPConnection(socket_path, timeout=timeout)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {} if body is None else {"Content-Type": "application/json"}
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    value = json.loads(raw.decode("utf-8")) if raw else {}
    if not isinstance(value, dict):
        raise RuntimeError("Gateway returned non-object JSON")
    return response.status, value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--method", choices=("GET", "POST"), default="GET")
    parser.add_argument("--path", required=True)
    parser.add_argument("--request-file")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    payload = None
    if args.request_file:
        payload = json.loads(Path(args.request_file).read_text(encoding="utf-8"))
    status, value = request(args.socket, args.method, args.path, payload, timeout=args.timeout)
    print(json.dumps({"http_status": status, "body": value}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
