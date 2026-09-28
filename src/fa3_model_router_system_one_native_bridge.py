#!/usr/bin/env python3
"""Loopback-only native System One runtime backend for the central LiteLLM pass-through.

This is a provider protocol adapter, not a router. It cannot select a provider,
admit a model, execute an action, or acquire credentials. Runtime admission,
primary-model designation, egress policy and Secret Broker projection precede launch.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import stat
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from fa3_authenticated_approval import verify_authenticated_receipt

AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
NATIVE_PROVIDER_ID = "FA3-PROVIDER-SYSTEM-ONE-NATIVE-001"
ENDPOINTS = {
    "openrouter": (
        "https://openrouter.ai/api/v1/models",
        "https://openrouter.ai/api/alpha/decisions",
    ),
    "typesafe": (
        "https://api.typesafe.ai/v1/models",
        "https://api.typesafe.ai/v1/systemone",
    ),
}
MAX_BYTES = 1024 * 1024
MAX_CATALOG_BYTES = 2 * 1024 * 1024


class NativeBridgeDenied(RuntimeError):
    pass


DESIGNATION_RECEIPT_TYPE = "MODEL_ROUTER_PRIMARY_MODEL_DESIGNATION"
DESIGNATION_SIGNER_ROLE = "PRIMARY_MODEL_DESIGNATOR"
DESIGNATION_APPROVAL_SCOPE = "FA3_MODEL_ROUTER_MODEL_DESIGNATION"


def verify_designation_approval(
    *, root: Path, designation: Path, approval_receipt: Path,
    expected_source_commit: str | None = None,
    verifier: Callable[..., dict[str, Any]] = verify_authenticated_receipt,
) -> str:
    """Require an exact, PKI-verified primary-model designation before any live backend."""
    for path in (designation, approval_receipt):
        if (not path.is_absolute() or path.is_symlink() or not path.is_file()
                or stat.S_IMODE(path.stat().st_mode) not in {0o400, 0o600}):
            raise NativeBridgeDenied("model designation and signed approval must be protected regular files")
    try:
        signed = json.loads(approval_receipt.read_text(encoding="utf-8"))
        designated = json.loads(designation.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise NativeBridgeDenied("protected model designation or signed approval unreadable") from None
    if not isinstance(signed, dict) or not isinstance(designated, dict):
        raise NativeBridgeDenied("protected model designation and signed approval require objects")
    if expected_source_commit is None:
        try:
            expected_source_commit = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            raise NativeBridgeDenied("repository HEAD cannot bind model approval") from None
    qualified = verifier(
        signed, expected_receipt_type=DESIGNATION_RECEIPT_TYPE,
        required_role=DESIGNATION_SIGNER_ROLE, expected_source_commit=expected_source_commit,
        required_grant_scope=DESIGNATION_APPROVAL_SCOPE,
    )
    if not qualified.get("qualified"):
        raise NativeBridgeDenied("primary-model designation lacks authenticated PKI approval")
    payload = signed.get("payload")
    if not isinstance(payload, dict) or not (
        payload.get("model_designation_sha256") == hashlib.sha256(designation.read_bytes()).hexdigest()
        and payload.get("provider_id") == NATIVE_PROVIDER_ID
        and payload.get("logical_route") == "fa3-decision-system-one"
        and payload.get("upstream") == designated.get("upstream")
        and payload.get("approved_models") == designated.get("approved_models")
        and designated.get("approved_by_primary_model") is True
    ):
        raise NativeBridgeDenied("authenticated approval payload does not bind the exact model designation")
    return hashlib.sha256(approval_receipt.read_bytes()).hexdigest()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise NativeBridgeDenied("native provider redirect forbidden")


def upstream_json(method: str, url: str, payload: dict[str, Any] | None,
                  key: str, timeout: float) -> dict[str, Any]:
    # Fixed, reviewed endpoints only; ignore arbitrary process proxy configuration.
    if url not in {endpoint for pair in ENDPOINTS.values() for endpoint in pair}:
        raise NativeBridgeDenied("unreviewed native provider endpoint")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if data is not None and len(data) > MAX_BYTES:
        raise NativeBridgeDenied("native request exceeds bounded size")
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": "FA3-System-One-Native/1"},
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    )
    try:
        with opener.open(req, timeout=timeout) as response:
            raw = response.read(MAX_CATALOG_BYTES + 1)
            if len(raw) > MAX_CATALOG_BYTES:
                raise NativeBridgeDenied("native provider response exceeds bounded size")
    except urllib.error.HTTPError as exc:
        # Never expose provider body, headers, query, bearer, or upstream error text.
        raise NativeBridgeDenied(f"native provider returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError):
        raise NativeBridgeDenied("native provider connection unavailable") from None
    try:
        result = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise NativeBridgeDenied("native provider response is not valid JSON") from None
    if not isinstance(result, dict):
        raise NativeBridgeDenied("native provider response must be an object")
    return result


class NativeBridge:
    """Exactly one approved runtime backend; all model selection comes from the Router."""

    def __init__(
        self, *, upstream: str, designation: dict[str, Any], upstream_key: str,
        bridge_token: str, fetch: Callable[[str, str, dict[str, Any] | None, str, float], dict[str, Any]] = upstream_json,
        timeout: float = 12.0,
    ) -> None:
        if upstream not in ENDPOINTS:
            raise NativeBridgeDenied("upstream provider is not in fixed FA3 egress allowlist")
        if not upstream_key or not bridge_token or upstream_key == bridge_token:
            raise NativeBridgeDenied("distinct broker-projected upstream and bridge credentials required")
        approved_models = designation.get("approved_models")
        if not (
            designation.get("schema") == "fa3.system-one-model-designation.v1"
            and designation.get("result") == "PASS"
            and designation.get("router_authority") == AUTHORITY
            and designation.get("provider_id") == NATIVE_PROVIDER_ID
            and designation.get("logical_route") == "fa3-decision-system-one"
            and designation.get("approved_by_primary_model") is True
            and designation.get("upstream") == upstream
            and isinstance(approved_models, list)
            and bool(approved_models)
            and all(isinstance(model, str) and model for model in approved_models)
            and len(set(approved_models)) == len(approved_models)
        ):
            raise NativeBridgeDenied("missing explicit approved model designation")
        aliases = designation.get("served_model_aliases", {})
        if not isinstance(aliases, dict) or any(
            model not in approved_models or not isinstance(values, list)
            or any(not isinstance(value, str) or not value for value in values)
            for model, values in aliases.items()
        ):
            raise NativeBridgeDenied("served model alias designation invalid")
        self.upstream = upstream
        self.approved = tuple(approved_models)
        self.aliases = aliases
        self._upstream_key = upstream_key
        self._bridge_token = bridge_token
        self._fetch = fetch
        self.timeout = timeout
        self._lock = threading.Lock()
        self._catalog: tuple[float, tuple[str, ...]] | None = None

    def authorized(self, supplied: str | None) -> bool:
        if not supplied or not supplied.startswith("Bearer "):
            return False
        return hmac.compare_digest(supplied[7:], self._bridge_token)

    def models(self) -> list[str]:
        with self._lock:
            if self._catalog and time.monotonic() < self._catalog[0]:
                return list(self._catalog[1])
            catalog_url, _ = ENDPOINTS[self.upstream]
            obj = self._fetch("GET", catalog_url, None, self._upstream_key, self.timeout)
            # TypeSafe's official SDK exposes models[].name; OpenRouter exposes data[].id.
            # Never guess a model from an incompatible catalogue or invent a fallback.
            if self.upstream == "typesafe":
                rows, name_field = obj.get("models"), "name"
            else:
                rows, name_field = obj.get("data"), "id"
            if not isinstance(rows, list) or not rows or any(
                not isinstance(row, dict) or not isinstance(row.get(name_field), str)
                or not row[name_field] for row in rows
            ):
                raise NativeBridgeDenied("live provider model catalogue has an invalid provider-specific shape")
            live = {row[name_field] for row in rows}
            approved = tuple(model for model in self.approved if model in live)
            if not approved:
                raise NativeBridgeDenied("no designated model appears in the live native catalogue")
            self._catalog = (time.monotonic() + 30.0, approved)
            return list(approved)

    def decide(self, body: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(body, dict) or set(body) != {"model", "state", "questions"}:
            raise NativeBridgeDenied("native request shape mismatch")
        model = body.get("model")
        questions = body.get("questions")
        if not isinstance(model, str) or model not in self.models():
            raise NativeBridgeDenied("model is not selected from approved live native catalogue")
        if not isinstance(questions, dict) or not questions or len(questions) > 512:
            raise NativeBridgeDenied("bounded native questions missing or oversized")
        for name, question in questions.items():
            if not isinstance(name, str) or not isinstance(question, dict):
                raise NativeBridgeDenied("invalid bounded native question")
            if question.get("type") not in {"choice", "noul", "score"}:
                raise NativeBridgeDenied("native question has unsupported type")
        _, decision_url = ENDPOINTS[self.upstream]
        response = self._fetch("POST", decision_url, body, self._upstream_key, self.timeout)
        served = response.get("model")
        if not isinstance(served, str) or served not in {model, *self.aliases.get(model, [])}:
            raise NativeBridgeDenied("native upstream returned an unapproved served model")
        answers = response.get("answers")
        if not isinstance(answers, dict) or set(answers) != set(questions):
            raise NativeBridgeDenied("native upstream did not answer the exact bounded questions")
        return {key: value for key, value in response.items()
                if key in {"answers", "model", "usage", "id"}}


class _Handler(BaseHTTPRequestHandler):
    bridge: NativeBridge

    def log_message(self, *_args: Any) -> None:
        # Native decisions and request bodies must never enter HTTP access logs.
        return

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        wire = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(wire)))
        self.end_headers()
        self.wfile.write(wire)

    def _authenticate(self) -> bool:
        if not self.bridge.authorized(self.headers.get("Authorization")):
            self._send(401, {"error": "unauthorized"})
            return False
        return True

    def do_GET(self) -> None:
        if self.path != "/v1/models":
            self._send(404, {"error": "unknown path"})
            return
        if not self._authenticate():
            return
        try:
            data = self.bridge.models()
            self._send(200, {"object": "list", "data": [{"id": x, "object": "model"} for x in data]})
        except NativeBridgeDenied:
            self._send(503, {"error": "native model catalogue unavailable"})

    def do_POST(self) -> None:
        if self.path != "/v1/decisions":
            self._send(404, {"error": "unknown path"})
            return
        if not self._authenticate():
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BYTES:
                self._send(413, {"error": "bounded request size exceeded"})
                return
            body = json.loads(self.rfile.read(size))
            self._send(200, self.bridge.decide(body))
        except (ValueError, TypeError, NativeBridgeDenied):
            self._send(422, {"error": "native decision rejected"})


def server(bridge: NativeBridge, port: int = 0) -> ThreadingHTTPServer:
    if not 0 <= port < 65536:
        raise NativeBridgeDenied("invalid listen port")
    class BoundHandler(_Handler):
        pass
    BoundHandler.bridge = bridge
    httpd = ThreadingHTTPServer(("127.0.0.1", port), BoundHandler)
    httpd.daemon_threads = True
    return httpd


def read_projected_credential(directory: Path, name: str) -> str:
    if not directory.is_absolute() or directory.is_symlink():
        raise NativeBridgeDenied("systemd credential directory must be an absolute non-symlink path")
    path = directory / name
    if path.is_symlink() or not path.is_file():
        raise NativeBridgeDenied("required projected native credential missing")
    if stat.S_IMODE(path.stat().st_mode) not in {0o400, 0o600}:
        raise NativeBridgeDenied("projected native credentials require protected file permissions")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise NativeBridgeDenied("projected native credential is empty")
    return value


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 loopback-only admitted native System One runtime")
    ap.add_argument("--upstream", choices=sorted(ENDPOINTS), required=True)
    ap.add_argument("--designation", type=Path, required=True)
    ap.add_argument("--designation-approval", type=Path, required=True)
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()
    if os.environ.get("FA3_SYSTEM_ONE_NATIVE_ENABLE") != "1":
        raise SystemExit("native runtime requires explicit enable")
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if not directory:
        raise SystemExit("systemd Secret Broker credential projection is required")
    credential_dir = Path(directory)
    upstream_key = read_projected_credential(credential_dir, "fa3-system-one-upstream")
    bridge_token = read_projected_credential(credential_dir, "fa3-system-one-bridge-token")
    if args.designation.is_symlink() or stat.S_IMODE(args.designation.stat().st_mode) not in {0o400, 0o600}:
        raise SystemExit("primary-model designation must be a protected file")
    verify_designation_approval(
        root=Path(__file__).resolve().parents[1], designation=args.designation,
        approval_receipt=args.designation_approval,
    )
    designation = json.loads(args.designation.read_text(encoding="utf-8"))
    bridge = NativeBridge(
        upstream=args.upstream, designation=designation,
        upstream_key=upstream_key, bridge_token=bridge_token,
    )
    bridge.models()  # Fail closed at startup if live catalogue does not prove a designated model.
    httpd = server(bridge, args.port)
    print(json.dumps({"schema": "fa3.system-one-native-listen.v1",
                      "address": f"http://127.0.0.1:{httpd.server_port}/v1",
                      "provider_id": NATIVE_PROVIDER_ID, "routing_authority": AUTHORITY}),
          flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
