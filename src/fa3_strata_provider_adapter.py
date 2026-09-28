#!/usr/bin/env python3
"""FA3 clean-room current-host probe for an already-running Strata runtime.

NO_UPSTREAM_STRATA_SOURCE_COPIED.

This module does not install, start, configure, or route applications directly to
Strata. It performs a bounded loopback-only API conformance probe for later
Model Router + HRB admission. Static or probe PASS is never runtime promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-STRATA-001"
SCHEMA = "fa3.strata-current-host-probe.v1"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
MAX_RESPONSE_BYTES = 1024 * 1024


class ProbeError(RuntimeError):
    pass


def _base_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ProbeError("base URL scheme must be http or https")
    if parsed.hostname not in LOOPBACK_HOSTS:
        raise ProbeError("Strata provider admission probe is loopback-only")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProbeError("credentials/query/fragment forbidden in base URL")
    if parsed.path not in {"", "/", "/v1"}:
        raise ProbeError("base URL path must be empty, /, or /v1")
    root = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    return root.rstrip("/")


def _endpoint_fingerprint(root: str) -> str:
    return hashlib.sha256(root.encode("utf-8")).hexdigest()


def _get_json(root: str, path: str, api_key: str | None, timeout: float) -> dict[str, Any]:
    headers = {"Accept": "application/json", "User-Agent": "FA3-Strata-Admission/1"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(root + path, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ProbeError(f"{path} response exceeds safe size ceiling")
            if response.status != 200:
                raise ProbeError(f"{path} returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise ProbeError(f"{path} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ProbeError(f"{path} unavailable: {exc.reason}") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ProbeError(f"{path} did not return JSON") from exc
    if not isinstance(value, dict):
        raise ProbeError(f"{path} JSON root must be an object")
    return value


def validate_health(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("status") != "ok":
        raise ProbeError("/health status is not ok")
    model = value.get("model")
    max_context = value.get("max_context")
    if not isinstance(model, str) or not model:
        raise ProbeError("/health model identity missing")
    if isinstance(max_context, bool) or not isinstance(max_context, int) or max_context <= 0:
        raise ProbeError("/health max_context invalid")
    return {
        "status": "ok",
        "model": model,
        "max_context": max_context,
        "images": bool(value.get("images", False)),
        "api_key_required": bool(value.get("api_key", False)),
    }


def validate_models(value: dict[str, Any], health_model: str) -> list[str]:
    if value.get("object") != "list" or not isinstance(value.get("data"), list):
        raise ProbeError("/v1/models is not an OpenAI-style model list")
    ids: list[str] = []
    for row in value["data"]:
        if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"]:
            ids.append(row["id"])
    ids = sorted(set(ids))
    if not ids:
        raise ProbeError("/v1/models returned no model identity")
    if health_model not in ids:
        raise ProbeError("/health and /v1/models model identity mismatch")
    return ids


def probe(base_url: str, api_key: str | None = None, timeout: float = 5.0,
          runtime_sha256: str | None = None) -> dict[str, Any]:
    root = _base_url(base_url)
    health = validate_health(_get_json(root, "/health", api_key, timeout))
    models = validate_models(_get_json(root, "/v1/models", api_key, timeout), health["model"])
    identity_valid = bool(runtime_sha256 and len(runtime_sha256) == 64 and
                          all(c in "0123456789abcdef" for c in runtime_sha256.lower()))
    return {
        "schema": SCHEMA,
        "provider_id": PROVIDER_ID,
        "result": "PASS",
        "evidence_level": "CURRENT_HOST_LOOPBACK_API_CONFORMANCE_PROBE",
        "endpoint_scope": "LOOPBACK_ONLY",
        "endpoint_fingerprint_sha256": _endpoint_fingerprint(root),
        "health": health,
        "model_ids": models,
        "runtime_identity": {
            "sha256": runtime_sha256.lower() if identity_valid else None,
            "immutable_identity_verified": identity_valid,
        },
        "network_egress_performed": False,
        "runtime_started_by_probe": False,
        "runtime_configuration_mutated": False,
        "model_download_performed": False,
        "inference_performed": False,
        "application_path_proven": False,
        "hrb_admission_receipt_present": False,
        "model_router_selection_receipt_present": False,
        "current_host_runtime_promotion_claim": False,
    }


def regression_check() -> dict[str, Any]:
    cases: dict[str, bool] = {}
    cases["loopback_ipv4"] = _base_url("http://127.0.0.1:18080/v1") == "http://127.0.0.1:18080"
    cases["loopback_localhost"] = _base_url("http://localhost:18080") == "http://localhost:18080"
    try:
        _base_url("https://example.com:8080")
        cases["external_host_rejected"] = False
    except ProbeError:
        cases["external_host_rejected"] = True
    try:
        _base_url("http://user:pass@127.0.0.1:8080")
        cases["embedded_credentials_rejected"] = False
    except ProbeError:
        cases["embedded_credentials_rejected"] = True
    health = validate_health({"status": "ok", "max_context": 262144, "model": "runtime-model", "images": True})
    cases["health_validation"] = health["model"] == "runtime-model" and health["max_context"] == 262144
    cases["models_validation"] = validate_models(
        {"object": "list", "data": [{"id": "runtime-model", "object": "model"}]}, "runtime-model"
    ) == ["runtime-model"]
    return {
        "schema": "fa3.strata-provider-adapter-regression.v1",
        "result": "PASS" if all(cases.values()) else "FAIL",
        "passed": sum(cases.values()),
        "total": len(cases),
        "cases": cases,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("FA3_STRATA_BASE_URL"))
    ap.add_argument("--api-key-env", default="FA3_STRATA_API_KEY")
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--runtime-sha256")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        out = regression_check()
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0 if out["result"] == "PASS" else 2
    if not args.base_url:
        print(json.dumps({
            "schema": SCHEMA,
            "provider_id": PROVIDER_ID,
            "result": "UNAVAILABLE",
            "reason": "EXPLICIT_BASE_URL_REQUIRED",
            "current_host_runtime_promotion_claim": False,
        }, indent=2))
        return 3
    try:
        out = probe(args.base_url, os.environ.get(args.api_key_env), args.timeout, args.runtime_sha256)
    except ProbeError as exc:
        out = {
            "schema": SCHEMA,
            "provider_id": PROVIDER_ID,
            "result": "FAIL",
            "reason": str(exc),
            "current_host_runtime_promotion_claim": False,
        }
        print(json.dumps(out, indent=2, sort_keys=True))
        return 2
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
