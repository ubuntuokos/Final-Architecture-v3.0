#!/usr/bin/env python3
from __future__ import annotations

import json
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from fa3_agent_deliberation import (
    DeliberationContractError,
    close_session,
    new_session,
    validate_message,
)

MAX_BODY_BYTES = 262144
LOOPBACK_HOST = "127.0.0.1"


class RoomStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, dict[str, Any]] = {}
        self._messages: dict[str, list[dict[str, Any]]] = {}

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        session = new_session(
            str(body.get("session_id", "")),
            str(body.get("objective", "")),
            list(body.get("participants") or []),
            mode=str(body.get("mode", "OPEN")),
            moderator_id=body.get("moderator_id"),
            human_approval_required=bool(body.get("human_approval_required", False)),
        )
        sid = session["session_id"]
        with self._lock:
            if sid in self._sessions:
                raise DeliberationContractError("session already exists")
            self._sessions[sid] = session
            self._messages[sid] = []
            return self.snapshot(sid)

    def snapshot(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(session_id)
            return {
                "session": deepcopy(self._sessions[session_id]),
                "messages": deepcopy(self._messages[session_id]),
            }

    def add_message(self, session_id: str, body: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(session_id)
            session = self._sessions[session_id]
            msg = body.get("message")
            if not isinstance(msg, dict):
                raise DeliberationContractError("message object required")
            validate_message(session, msg, addressed_to=list(body.get("addressed_to") or []))
            self._messages[session_id].append(deepcopy(msg))
            return {"accepted": True, "message_count": len(self._messages[session_id])}

    def close(self, session_id: str, closure_receipt_ref: str) -> dict[str, Any]:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(session_id)
            self._sessions[session_id] = close_session(self._sessions[session_id], closure_receipt_ref)
            return self.snapshot(session_id)


def _handler(store: RoomStore) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "FA3DeliberationReference/1.0"
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _json(self, status: int, value: dict[str, Any]) -> None:
            raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _body(self) -> dict[str, Any]:
            raw_len = self.headers.get("Content-Length")
            if raw_len is None:
                return {}
            try:
                length = int(raw_len)
            except ValueError as exc:
                raise DeliberationContractError("invalid Content-Length") from exc
            if length < 0 or length > MAX_BODY_BYTES:
                raise DeliberationContractError("request body too large")
            raw = self.rfile.read(length)
            if not raw:
                return {}
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DeliberationContractError("invalid JSON body") from exc
            if not isinstance(value, dict):
                raise DeliberationContractError("JSON body must be object")
            return value

        def do_GET(self) -> None:
            parts = [x for x in urlparse(self.path).path.split("/") if x]
            try:
                if parts == ["health"]:
                    self._json(200, {
                        "ok": True,
                        "runtime": "FA3_AGENT_DELIBERATION_REFERENCE",
                        "authoritative": False,
                        "current_host_runtime_promotion_claim": False,
                    })
                    return
                if len(parts) == 3 and parts[:2] == ["v1", "sessions"]:
                    self._json(200, store.snapshot(parts[2]))
                    return
                self._json(404, {"error": "not found"})
            except KeyError:
                self._json(404, {"error": "session not found"})
            except DeliberationContractError as exc:
                self._json(400, {"error": str(exc)})

        def do_POST(self) -> None:
            parts = [x for x in urlparse(self.path).path.split("/") if x]
            try:
                body = self._body()
                if parts == ["v1", "sessions"]:
                    self._json(201, store.create(body))
                    return
                if len(parts) == 4 and parts[:2] == ["v1", "sessions"] and parts[3] == "messages":
                    self._json(201, store.add_message(parts[2], body))
                    return
                if len(parts) == 4 and parts[:2] == ["v1", "sessions"] and parts[3] == "close":
                    ref = body.get("closure_receipt_ref")
                    self._json(200, store.close(parts[2], str(ref or "")))
                    return
                self._json(404, {"error": "not found"})
            except KeyError:
                self._json(404, {"error": "session not found"})
            except DeliberationContractError as exc:
                self._json(400, {"error": str(exc)})

    return Handler


def make_server(
    host: str = LOOPBACK_HOST,
    port: int = 0,
    *,
    store: RoomStore | None = None,
) -> ThreadingHTTPServer:
    if host != LOOPBACK_HOST:
        raise DeliberationContractError("reference runtime is loopback-only")
    if not isinstance(port, int) or isinstance(port, bool) or not (0 <= port <= 65535):
        raise DeliberationContractError("invalid port")
    room_store = store or RoomStore()
    server = ThreadingHTTPServer((host, port), _handler(room_store))
    server.daemon_threads = True
    return server
