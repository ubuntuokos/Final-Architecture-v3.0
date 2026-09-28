#!/usr/bin/env python3
"""Model Router-owned System One transport through its authenticated LiteLLM data plane.

Only the central Router selection receipt determines runtime and model. This
transport cannot discover/admit a model, change provider, or contact a vendor API.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import stat
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from fa3_model_router_materialize import AUTHORITY, sha256_file

ROUTE = "fa3-decision-system-one"
NATIVE_PROVIDER = "FA3-PROVIDER-SYSTEM-ONE-NATIVE-001"
PROTOCOL = "SYSTEM_ONE_DECISIONS_V1"
PASSTHROUGH = "/fa3/system-one/decisions"
MAX_BYTES = 1024 * 1024


class RouterNativeDenied(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise RouterNativeDenied("LiteLLM redirected the native decision request")


def _loopback(origin: str) -> bool:
    parsed = urlparse(origin)
    return parsed.scheme == "http" and (parsed.hostname or "").lower() in {"127.0.0.1", "::1", "localhost"} and parsed.path in {"", "/"}


def _read_protected(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise RouterNativeDenied("router selection path must not be symlinked")
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode not in {0o400, 0o600} or not path.is_file():
            raise RouterNativeDenied("router selection receipt must be a protected regular file")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        raise RouterNativeDenied("router selection receipt is missing or invalid") from None
    if not isinstance(data, dict):
        raise RouterNativeDenied("router selection receipt must be an object")
    return data


def _request(url: str, payload: dict[str, Any], master_key: str, timeout: float) -> dict[str, Any]:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise RouterNativeDenied("native System One request exceeds bounded size")
    req = urllib.request.Request(
        url, data=raw, method="POST",
        headers={"Authorization": f"Bearer {master_key}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": "FA3-System-One-Router/1"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as response:
            data = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        # No upstream response body, header, or credential ever appears in traces.
        raise RouterNativeDenied(f"LiteLLM native pass-through returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError):
        raise RouterNativeDenied("LiteLLM native pass-through is unavailable") from None
    if len(data) > MAX_BYTES:
        raise RouterNativeDenied("native decision response exceeds bounded size")
    try:
        response = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise RouterNativeDenied("native decision response is invalid JSON") from None
    if not isinstance(response, dict):
        raise RouterNativeDenied("native decision response must be an object")
    return response


class NativeRouterTransport:
    def __init__(
        self, *, selection_receipt: Path, route_registry: Path,
        router_origin: str, master_key: str,
        request: Callable[[str, dict[str, Any], str, float], dict[str, Any]] = _request,
        timeout: float = 15.0,
    ) -> None:
        if not _loopback(router_origin):
            raise RouterNativeDenied("only the local, central LiteLLM origin is permitted")
        if not master_key:
            raise RouterNativeDenied("Secret Broker-projected Model Router credential required")
        self.selection_receipt = Path(selection_receipt)
        self.route_registry = Path(route_registry)
        self.router_origin = router_origin.rstrip("/")
        self._master_key = master_key
        self._request = request
        self.timeout = float(timeout)

    @classmethod
    def from_env(cls, *, root: Path) -> "NativeRouterTransport":
        if os.environ.get("FA3_SYSTEM_ONE_LIVE_ROUTER_ENABLE") != "1":
            raise RouterNativeDenied("live native routing was not explicitly enabled")
        selection = os.environ.get("FA3_MODEL_ROUTER_SELECTION_RECEIPT")
        origin = os.environ.get("FA3_MODEL_ROUTER_ORIGIN")
        credential = os.environ.get("FA3_MODEL_ROUTER_MASTER_KEY")
        if not selection or not origin or not credential:
            raise RouterNativeDenied("live Router selection, origin and broker-projected credential required")
        transport = cls(
            selection_receipt=Path(selection),
            route_registry=root / "deployment/model-router/routes.json",
            router_origin=origin, master_key=credential,
        )
        e2e_path = os.environ.get("FA3_SYSTEM_ONE_NATIVE_E2E_RECEIPT")
        if not e2e_path:
            raise RouterNativeDenied("live native Router E2E admission proof is required")
        transport.validate_live_e2e(Path(e2e_path), root=root)
        return transport

    def binding(self) -> tuple[dict[str, Any], dict[str, Any]]:
        receipt = _read_protected(self.selection_receipt)
        if not (
            receipt.get("schema") == "fa3.model-router-runtime-selection.v1"
            and receipt.get("result") == "PASS"
            and receipt.get("authority") == AUTHORITY
            and receipt.get("runtime_selected") is True
            and receipt.get("physical_backend_pinned") is False
            and receipt.get("physical_model_pinned") is False
            and receipt.get("route_registry_sha256") == sha256_file(self.route_registry)
        ):
            raise RouterNativeDenied("current Model Router selection receipt does not bind the canonical route set")
        generated = Path(str(receipt.get("generated_config") or ""))
        if not generated.is_absolute() or generated.is_symlink() or not generated.is_file():
            raise RouterNativeDenied("generated LiteLLM config is not an exact runtime artifact")
        if stat.S_IMODE(generated.stat().st_mode) not in {0o400, 0o600}:
            raise RouterNativeDenied("generated LiteLLM config requires protected file permissions")
        if receipt.get("generated_config_sha256") != sha256_file(generated):
            raise RouterNativeDenied("runtime LiteLLM config differs from selected Router config")
        binding = (receipt.get("route_bindings") or {}).get(ROUTE)
        if not isinstance(binding, dict) or not (
            binding.get("route") == ROUTE
            and binding.get("runtime_api") == PROTOCOL
            and binding.get("selection") == "RUNTIME_DISCOVERED"
            and binding.get("provider_id") == NATIVE_PROVIDER
            and binding.get("native_bridge_auth_env") == "FA3_SYSTEM_ONE_BRIDGE_TOKEN"
            and isinstance(binding.get("model"), str) and binding["model"]
        ):
            raise RouterNativeDenied("native System One route lacks an exact admitted Router binding")
        evidence = receipt.get("admission_receipt_sha256") or {}
        digest = evidence.get(NATIVE_PROVIDER) if isinstance(evidence, dict) else None
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise RouterNativeDenied("selected native provider has no current-host admission proof")
        return receipt, binding

    def validate_live_e2e(self, receipt_path: Path, *, root: Path) -> None:
        evidence = _read_protected(receipt_path)
        selection, binding = self.binding()
        try:
            captured = dt.datetime.fromisoformat(str(evidence.get("captured_at") or ""))
            if captured.tzinfo is None:
                raise ValueError("timezone required")
            age = dt.datetime.now(dt.timezone.utc) - captured.astimezone(dt.timezone.utc)
            if not dt.timedelta(0) <= age <= dt.timedelta(hours=24):
                raise ValueError("stale proof")
        except (ValueError, TypeError):
            raise RouterNativeDenied("native Router E2E evidence is stale or undated") from None
        from fa3_model_router_materialize import git_head
        if not (
            evidence.get("schema") == "fa3.system-one-router-e2e-current-host.v1"
            and evidence.get("result") == "PASS"
            and evidence.get("authority") == AUTHORITY
            and evidence.get("logical_route") == ROUTE
            and evidence.get("data_plane") == "LITELLM_AUTHENTICATED_PASS_THROUGH"
            and evidence.get("native_provider_id") == binding["provider_id"]
            and evidence.get("selection_receipt_sha256") == sha256_file(self.selection_receipt)
            and evidence.get("native_admission_sha256") == selection["admission_receipt_sha256"][NATIVE_PROVIDER]
            and evidence.get("router_origin") == self.router_origin
            and evidence.get("repository_head") == git_head(root)
            and evidence.get("invalid_and_missing_master_key_rejected") is True
            and evidence.get("native_probability_distribution_preserved") is True
            and evidence.get("real_native_provider_request") is True
            and evidence.get("execution_performed") is False
            and evidence.get("confidence_is_authorization") is False
            and evidence.get("global_promotion_claim") is False
        ):
            raise RouterNativeDenied("native LiteLLM E2E proof does not bind this exact live runtime")

    def __call__(self, envelope: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(envelope, dict) or not (
            envelope.get("schema") == "fa3.model-router.native-decision-request.v1"
            and envelope.get("authority") == AUTHORITY
            and envelope.get("logical_route") == ROUTE
            and envelope.get("protocol") == "system-one-decision-v1"
        ):
            raise RouterNativeDenied("native decision envelope does not target the central Model Router")
        request = envelope.get("request")
        if not isinstance(request, dict) or set(request) != {"state", "questions"}:
            raise RouterNativeDenied("bounded native request shape mismatch")
        questions = request["questions"]
        if not isinstance(questions, dict) or not questions:
            raise RouterNativeDenied("native decision questions are required")
        receipt, binding = self.binding()
        payload = {"model": binding["model"], "state": request["state"], "questions": questions}
        raw = self._request(self.router_origin + PASSTHROUGH, payload, self._master_key, self.timeout)
        if not isinstance(raw.get("answers"), dict) or set(raw["answers"]) != set(questions):
            raise RouterNativeDenied("LiteLLM did not return the exact native question set")
        if not isinstance(raw.get("model"), str) or not raw["model"]:
            raise RouterNativeDenied("native upstream model receipt missing")
        return {
            "answers": raw["answers"],
            "_fa3_routing": {
                "authority": AUTHORITY,
                "provider_id": binding["provider_id"],
                "runtime_id": binding["runtime_id"],
                "model_id": binding["model"],
                "served_model_id": raw["model"],
                "receipt_ref": f"sha256:{sha256_file(self.selection_receipt)}",
                "native_provider_admission_sha256": receipt["admission_receipt_sha256"][NATIVE_PROVIDER],
                "protocol": "system-one-decision-v1",
                "data_plane": "LITELLM_AUTHENTICATED_PASS_THROUGH",
                "external_provider": True,
                "upstream_request_id": raw.get("id"),
                "usage": raw.get("usage") if isinstance(raw.get("usage"), dict) else {},
                "silent_fallback": False,
            },
        }
