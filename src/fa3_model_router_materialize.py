#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
ROUTES_REL = Path("deployment/model-router/routes.json")


class MaterializationDenied(RuntimeError):
    pass


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_head(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def loopback_origin(api_base: str) -> bool:
    parsed = urlparse(api_base)
    return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in {"127.0.0.1", "::1", "localhost"}


def canonical_provider_ok(root: Path, provider_id: str) -> bool:
    path = root / "canonical/providers" / f"{provider_id}.json"
    if not path.is_file():
        return False
    record = loadj(path)
    if record.get("architectural_authority") is not False:
        return False
    bindings = record.get("authority_boundaries", {})
    policy = record.get("fa3_usage_policy", {})
    return (
        bindings.get("model_routing") == AUTHORITY
        or policy.get("model_routing") == "DELEGATE_TO_EXISTING_FA3_MODEL_ROUTER"
    )


def _current_host_level(value: Any) -> bool:
    level = str(value or "").strip()
    return (
        level.startswith("CURRENT_HOST_")
        and "NOT_ADMITTED" not in level
        and "FAIL" not in level
        and "UNAVAILABLE" not in level
    )


def receipt_proves_provider(path: Path, provider_id: str) -> bool:
    if not path.is_file():
        return False
    rec = loadj(path)
    if rec.get("status") != "PASS" and rec.get("result") != "PASS":
        return False

    providers = rec.get("providers")
    if isinstance(providers, dict):
        item = providers.get(provider_id)
        return (
            isinstance(item, dict)
            and item.get("provider_id", provider_id) == provider_id
            and item.get("status") == "PASS"
            and _current_host_level(item.get("evidence_level"))
        )

    return (
        rec.get("provider_id") == provider_id
        and _current_host_level(rec.get("evidence_level"))
    )


def auth_header(candidate: dict[str, Any]) -> dict[str, str]:
    env_name = str(candidate.get("api_key_env", "")).strip()
    if not env_name:
        return {}
    token = os.environ.get(env_name, "").strip()
    if not token:
        raise MaterializationDenied(f"backend API key environment variable is empty: {env_name}")
    return {"Authorization": f"Bearer {token}"}


def fetch_models(candidate: dict[str, Any], timeout: float) -> list[str]:
    api_base = str(candidate["api_base"]).rstrip("/")
    url = api_base + "/models"
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json", **auth_header(candidate)})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(8 * 1024 * 1024)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise MaterializationDenied(f"provider model catalog probe failed for {candidate['runtime_id']}: {exc}") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise MaterializationDenied(f"provider model catalog returned invalid JSON for {candidate['runtime_id']}") from exc
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise MaterializationDenied(f"provider model catalog lacks OpenAI-compatible data list: {candidate['runtime_id']}")
    ids = sorted({
        str(row.get("id")).strip()
        for row in rows
        if isinstance(row, dict) and str(row.get("id", "")).strip()
    })
    return ids


def is_chat_candidate(model_id: str) -> bool:
    low = model_id.lower()
    blocked = ("embed", "rerank", "whisper", "tts", "vision-encoder", "clip", "vae")
    return not any(token in low for token in blocked)


def choose_model(models: list[str], preferred: list[str] | None = None) -> str:
    available = [m for m in models if is_chat_candidate(m)]
    if not available:
        raise MaterializationDenied("active provider exposes no chat-capable model candidate")
    preferred = preferred or []
    for wanted in preferred:
        if wanted in available:
            return wanted
    return sorted(available)[0]


def route_allowed(candidate: dict[str, Any], route: str) -> bool:
    allowed = candidate.get("routes")
    if allowed is None:
        return True
    return isinstance(allowed, list) and (route in allowed or "*" in allowed)


def select_bindings(routes: list[dict[str, Any]], candidates: list[dict[str, Any]], catalogs: dict[str, list[str]]) -> dict[str, dict[str, Any]]:
    ordered = sorted(candidates, key=lambda c: (-int(c.get("priority", 0)), str(c.get("runtime_id", ""))))
    out: dict[str, dict[str, Any]] = {}
    for route in routes:
        name = str(route.get("route", "")).strip()
        if not name:
            raise MaterializationDenied("logical route name is empty")
        eligible = [candidate for candidate in ordered if route_allowed(candidate, name)]
        if not eligible:
            raise MaterializationDenied(f"no admitted runtime candidate is policy-allowed for logical route {name}")
        # Fail closed after selecting the highest-priority policy-allowed runtime.
        # Trying a second provider automatically would be a silent provider->provider fallback.
        candidate = eligible[0]
        runtime_id = str(candidate["runtime_id"])
        preferred_map = candidate.get("route_preferred_models", {})
        preferred = preferred_map.get(name, []) if isinstance(preferred_map, dict) else []
        if not preferred:
            preferred = candidate.get("preferred_models", [])
        model = choose_model(catalogs.get(runtime_id, []), preferred if isinstance(preferred, list) else [])
        out[name] = {
            "route": name,
            "provider_id": candidate["provider_id"],
            "runtime_id": runtime_id,
            "api_base": candidate["api_base"],
            "litellm_provider": candidate.get("litellm_provider", "openai"),
            "model": model,
            "api_key_env": candidate.get("api_key_env"),
            "selection": "RUNTIME_DISCOVERED",
            "provider_failover_performed": False,
        }
    return out

def validate_candidates(root: Path, providers_file: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    obj = loadj(providers_file)
    if obj.get("schema") != "fa3.model-router-runtime-providers.v1":
        raise MaterializationDenied("runtime provider registry schema mismatch")
    rows = obj.get("providers")
    if not isinstance(rows, list) or not rows:
        raise MaterializationDenied("runtime provider registry contains no providers")
    candidates: list[dict[str, Any]] = []
    receipt_hashes: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("enabled") is not True:
            continue
        provider_id = str(row.get("provider_id", "")).strip()
        runtime_id = str(row.get("runtime_id", "")).strip()
        api_base = str(row.get("api_base", "")).strip().rstrip("/")
        if not provider_id or not runtime_id or not api_base:
            raise MaterializationDenied("enabled runtime provider entry lacks provider_id/runtime_id/api_base")
        if not loopback_origin(api_base):
            raise MaterializationDenied(f"baseline current-host router rejects non-loopback provider endpoint: {runtime_id}")
        if not canonical_provider_ok(root, provider_id):
            raise MaterializationDenied(f"provider is not canonically bound to central Model Router authority: {provider_id}")
        receipt_value = str(row.get("admission_receipt", "")).strip()
        if not receipt_value:
            raise MaterializationDenied(f"provider admission receipt missing: {provider_id}")
        receipt = Path(receipt_value).expanduser()
        if not receipt.is_absolute():
            receipt = (root / receipt).resolve()
        if not receipt_proves_provider(receipt, provider_id):
            raise MaterializationDenied(f"current-host admission receipt does not prove provider: {provider_id}")
        copy = dict(row)
        copy["provider_id"] = provider_id
        copy["runtime_id"] = runtime_id
        copy["api_base"] = api_base
        copy["_admission_receipt"] = str(receipt)
        candidates.append(copy)
        receipt_hashes[provider_id] = sha256_file(receipt)
    if not candidates:
        raise MaterializationDenied("no enabled admitted runtime provider remains")
    return candidates, receipt_hashes


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_litellm(bindings: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# GENERATED by FA3-AUTH-MODEL-ROUTER-001. DO NOT COMMIT.",
        "model_list:",
    ]
    for route, item in sorted(bindings.items()):
        prefix = str(item.get("litellm_provider", "openai")).strip() or "openai"
        model = str(item["model"])
        lines += [
            f"  - model_name: {yaml_quote(route)}",
            "    litellm_params:",
            f"      model: {yaml_quote(prefix + '/' + model)}",
            f"      api_base: {yaml_quote(str(item['api_base']))}",
        ]
        env_name = str(item.get("api_key_env") or "").strip()
        if env_name:
            lines.append(f"      api_key: os.environ/{env_name}")
        else:
            lines.append("      api_key: os.environ/FA3_MODEL_ROUTER_BACKEND_DUMMY_KEY")
    lines += [
        "router_settings:",
        "  routing_strategy: simple-shuffle",
        "general_settings:",
        "  master_key: os.environ/FA3_MODEL_ROUTER_MASTER_KEY",
        "",
    ]
    return "\n".join(lines)


def materialize(root: Path, providers_file: Path, output: Path, receipt_path: Path, timeout: float = 5.0) -> dict[str, Any]:
    routes_obj = loadj(root / ROUTES_REL)
    if routes_obj.get("authority") != AUTHORITY:
        raise MaterializationDenied("route registry authority mismatch")
    if routes_obj.get("physical_provider_pins") is not False or routes_obj.get("physical_model_pins") is not False:
        raise MaterializationDenied("canonical route registry must not pin physical provider/model")
    routes = routes_obj.get("routes")
    if not isinstance(routes, list) or not routes:
        raise MaterializationDenied("route registry is empty")
    candidates, receipt_hashes = validate_candidates(root, providers_file)
    catalogs: dict[str, list[str]] = {}
    for candidate in candidates:
        catalogs[str(candidate["runtime_id"])] = fetch_models(candidate, timeout)
    bindings = select_bindings(routes, candidates, catalogs)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_litellm(bindings), encoding="utf-8")
    output.chmod(0o600)
    receipt = {
        "schema": "fa3.model-router-runtime-selection.v1",
        "authority": AUTHORITY,
        "result": "PASS",
        "provider_neutral": True,
        "repository_head": git_head(root),
        "route_registry_sha256": sha256_file(root / ROUTES_REL),
        "runtime_provider_registry_sha256": sha256_file(providers_file),
        "admission_receipt_sha256": receipt_hashes,
        "physical_backend_pinned": False,
        "physical_model_pinned": False,
        "runtime_selected": True,
        "route_bindings": bindings,
        "logical_routes": sorted(bindings),
        "generated_config": str(output),
    }
    writej(receipt_path, receipt)
    receipt_path.chmod(0o600)
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--providers", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--selection-receipt", required=True)
    ap.add_argument("--timeout", type=float, default=5.0)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    rec = materialize(
        root,
        Path(args.providers).expanduser().resolve(),
        Path(args.output).expanduser().resolve(),
        Path(args.selection_receipt).expanduser().resolve(),
        args.timeout,
    )
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
