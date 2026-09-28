#!/usr/bin/env python3
"""Optional loopback-only transport for FA3 PR Watch signed GitHub webhooks.

No service auto-start, external port, model request, GitHub token or workflow
execution. Expose externally only through an independently approved reverse
proxy/tunnel retaining exact raw payload and X-Hub-Signature-256 headers.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fa3_pr_watch import (MAX_PAYLOAD, PRWatchDenied, ProjectionStore,
                          normalize_webhook)
from fa3_pr_watch_operator_export import export_operator_view


def make_handler(secret: bytes, store: ProjectionStore, operator_export_path: Path | None = None):
    class PRWatchHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        timeout = 10

        def log_message(self, fmt, *args):
            # No attacker-controlled HTTP path, event body or signature in logs.
            return

        def _respond(self, status, result):
            raw = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)
            self.close_connection = True

        def do_GET(self):
            if self.path != "/health":
                return self._respond(404, {"status": "NOT_FOUND"})
            self._respond(200, {"status": "READY_LOOPBACK_ONLY",
                                "execution_enabled": False, "authority": False})

        def do_POST(self):
            if self.path != "/github":
                return self._respond(404, {"status": "NOT_FOUND"})
            lengths = self.headers.get_all("Content-Length", [])
            length = lengths[0] if len(lengths) == 1 else ""
            if (self.headers.get("Transfer-Encoding") or len(length) > 7
                    or not re.fullmatch(r"[0-9]{1,7}", length)
                    or not 0 < int(length) <= MAX_PAYLOAD):
                return self._respond(413, {"status": "DENIED", "code": "PAYLOAD_SIZE"})
            required = ("X-Hub-Signature-256", "X-GitHub-Event", "X-GitHub-Delivery")
            if any(len(self.headers.get_all(h, [])) != 1 for h in required):
                return self._respond(403, {"status": "DENIED", "code": "HEADER_CARDINALITY"})
            try:
                data = self.rfile.read(int(length))
                event = normalize_webhook(
                    data, signature=self.headers.get("X-Hub-Signature-256", ""),
                    secret=secret, event_type=self.headers.get("X-GitHub-Event", ""),
                    delivery_id=self.headers.get("X-GitHub-Delivery", ""),
                )
                result = store.ingest(event)
                if operator_export_path is not None:
                    export_operator_view(store, operator_export_path)
                status = 409 if result["status"] in ("STALE", "CONFLICT") else 200 if result["status"] == "DUPLICATE" else 202
                self._respond(status, result)
            except PRWatchDenied as exc:
                self._respond(403, {"status": "DENIED", "code": exc.code})
            except (OSError, ValueError, KeyError, TypeError):
                self._respond(503, {"status": "DENIED", "code": "STORE_UNAVAILABLE"})

    return PRWatchHandler


def main(argv=None):
    parser = argparse.ArgumentParser(description="Opt-in loopback-only PR Watch webhook receiver")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", default=0, type=int, help="0 selects a free loopback port")
    parser.add_argument("--secret-fd", required=True, type=int)
    parser.add_argument("--state-dir", type=Path, default=None)
    parser.add_argument("--operator-export-path", type=Path)
    args = parser.parse_args(argv)
    try:
        if not ipaddress.ip_address(args.bind).is_loopback or args.secret_fd < 3 or not 0 <= args.port <= 65535:
            raise PRWatchDenied("LOOPBACK_OR_SECRET_FD_REQUIRED")
        secret = os.read(args.secret_fd, 4097)
        os.close(args.secret_fd)
        if len(secret) < 16 or len(secret) > 4096:
            raise PRWatchDenied("SECRET_INVALID")
        store = ProjectionStore(args.state_dir)
        store._ensure_dir()
        family = ThreadingHTTPServer
        with family((args.bind, args.port), make_handler(secret, store, args.operator_export_path)) as srv:
            srv.daemon_threads = True
            address, port = srv.server_address[:2]
            print(json.dumps({"listen": f"http://{address}:{port}/github",
                              "transport": "LOCAL_OPT_IN",
                              "execution_enabled": False}), flush=True)
            srv.serve_forever(poll_interval=0.5)
        return 0
    except (PRWatchDenied, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, PRWatchDenied) else "RECEIVER_DENIED"
        print(json.dumps({"status": "DENIED", "code": code}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
