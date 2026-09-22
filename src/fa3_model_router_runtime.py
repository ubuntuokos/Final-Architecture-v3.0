#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

AUTHORITY_ID = "FA3-AUTH-MODEL-ROUTER-001"
CATALOG_SCHEMA = "fa3.model-router.provider-catalog.v1"
ROUTES_SCHEMA = "fa3.model-router.routes.v1"
RESOLUTION_SCHEMA = "fa3.model-router.resolution.v1"


class RouterDenied(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RouterDenied(f"JSON object required: {path}")
    return obj


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def _is_loopback_origin(value: str) -> bool:
    try:
        p = urlparse(value)
    except Exception:
        return False
    return (
        p.scheme in {"http", "https"}
        and (p.hostname or "").lower() in {"127.0.0.1", "::1", "localhost"}
        and not p.username
        and not p.password
        and not p.query
        and not p.fragment
    )


def _safe_env_name(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]*", value))


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    provider_id: str
    runtime: str
    model_id: str
    litellm_model: str
    api_base: str | None
    credential_env: str | None
    locality: str
    admitted: bool
    available: bool
    capabilities: frozenset[str]
    priority: int
    metadata: dict[str, Any]

    @classmethod
    def from_obj(cls, obj: dict[str, Any]) -> "Candidate":
        required = ("candidate_id", "provider_id", "runtime", "model_id", "litellm_model")
        missing = [k for k in required if not str(obj.get(k, "")).strip()]
        if missing:
            raise RouterDenied("provider candidate missing required fields: " + ",".join(missing))
        locality = str(obj.get("locality", "LOCAL")).upper()
        if locality not in {"LOCAL", "REMOTE"}:
            raise RouterDenied(f"invalid locality for {obj.get('candidate_id')}: {locality}")
        api_base_raw = obj.get("api_base")
        api_base = str(api_base_raw).rstrip("/") if isinstance(api_base_raw, str) and api_base_raw.strip() else None
        if locality == "LOCAL" and api_base and not _is_loopback_origin(api_base):
            raise RouterDenied(f"local candidate endpoint must be loopback: {obj.get('candidate_id')}")
        cred_raw = obj.get("credential_env")
        credential_env = str(cred_raw).strip() if isinstance(cred_raw, str) and cred_raw.strip() else None
        if credential_env and not _safe_env_name(credential_env):
            raise RouterDenied(f"invalid credential_env for {obj.get('candidate_id')}")
        caps_raw = obj.get("capabilities", [])
        if not isinstance(caps_raw, list) or not all(isinstance(x, str) and x for x in caps_raw):
            raise RouterDenied(f"invalid capabilities for {obj.get('candidate_id')}")
        return cls(
            candidate_id=str(obj["candidate_id"]),
            provider_id=str(obj["provider_id"]),
            runtime=str(obj["runtime"]),
            model_id=str(obj["model_id"]),
            litellm_model=str(obj["litellm_model"]),
            api_base=api_base,
            credential_env=credential_env,
            locality=locality,
            admitted=obj.get("admitted") is True,
            available=obj.get("available") is True,
            capabilities=frozenset(caps_raw),
            priority=int(obj.get("priority", 1000)),
            metadata=dict(obj.get("metadata", {})) if isinstance(obj.get("metadata", {}), dict) else {},
        )


def load_catalog(path: Path) -> tuple[dict[str, Any], list[Candidate]]:
    obj = _load_json(path)
    if obj.get("schema") != CATALOG_SCHEMA:
        raise RouterDenied(f"provider catalog schema must be {CATALOG_SCHEMA}")
    if obj.get("provider_neutral") is not True:
        raise RouterDenied("provider catalog must declare provider_neutral=true")
    rows = obj.get("candidates")
    if not isinstance(rows, list) or not rows:
        raise RouterDenied("provider catalog must contain at least one candidate")
    candidates = [Candidate.from_obj(x) for x in rows if isinstance(x, dict)]
    if len(candidates) != len(rows):
        raise RouterDenied("provider catalog contains non-object candidate")
    ids = [c.candidate_id for c in candidates]
    if len(ids) != len(set(ids)):
        raise RouterDenied("provider catalog candidate_id values must be unique")
    return obj, candidates


def load_routes(path: Path) -> dict[str, Any]:
    obj = _load_json(path)
    if obj.get("schema") != ROUTES_SCHEMA:
        raise RouterDenied(f"route manifest schema must be {ROUTES_SCHEMA}")
    if obj.get("authority") != AUTHORITY_ID:
        raise RouterDenied("route manifest authority mismatch")
    routes = obj.get("routes")
    if not isinstance(routes, list) or not routes:
        raise RouterDenied("route manifest must contain routes")
    aliases: list[str] = []
    for route in routes:
        if not isinstance(route, dict):
            raise RouterDenied("route entry must be object")
        alias = str(route.get("route", "")).strip()
        if not alias or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", alias):
            raise RouterDenied(f"invalid logical route alias: {alias!r}")
        aliases.append(alias)
        for key in ("required_capabilities", "preferred_capabilities"):
            value = route.get(key, [])
            if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
                raise RouterDenied(f"{alias} has invalid {key}")
        if "model" in route or "provider_id" in route or "api_base" in route:
            raise RouterDenied(f"logical route {alias} contains forbidden physical binding")
    if len(aliases) != len(set(aliases)):
        raise RouterDenied("logical route aliases must be unique")
    return obj


def _eligible(route: dict[str, Any], c: Candidate) -> bool:
    if not c.admitted or not c.available:
        return False
    allow_external = route.get("allow_external") is True
    if c.locality == "REMOTE" and not allow_external:
        return False
    required = set(route.get("required_capabilities", []))
    return required.issubset(c.capabilities)


def select_candidate(route: dict[str, Any], candidates: list[Candidate]) -> Candidate:
    eligible = [c for c in candidates if _eligible(route, c)]
    if not eligible:
        raise RouterDenied(f"no admitted/available candidate for logical route {route.get('route')}")
    preferred = set(route.get("preferred_capabilities", []))
    locality_rank = {"LOCAL": 0, "REMOTE": 1}
    eligible.sort(
        key=lambda c: (
            locality_rank[c.locality],
            -len(preferred.intersection(c.capabilities)),
            c.priority,
            c.provider_id,
            c.model_id,
            c.candidate_id,
        )
    )
    return eligible[0]


def resolve(catalog_path: Path, routes_path: Path) -> dict[str, Any]:
    catalog, candidates = load_catalog(catalog_path)
    routes_doc = load_routes(routes_path)
    out: dict[str, Any] = {
        "schema": RESOLUTION_SCHEMA,
        "authority": AUTHORITY_ID,
        "provider_neutral": True,
        "physical_backend_pinned": False,
        "physical_model_pinned": False,
        "selection_source": "CURRENT_HOST_PROVIDER_CATALOG",
        "catalog_sha256": _sha256(catalog_path),
        "routes_sha256": _sha256(routes_path),
        "catalog_producer": catalog.get("producer"),
        "routes": [],
    }
    for route in routes_doc["routes"]:
        chosen = select_candidate(route, candidates)
        out["routes"].append(
            {
                "route": route["route"],
                "selected_candidate_id": chosen.candidate_id,
                "provider_id": chosen.provider_id,
                "runtime": chosen.runtime,
                "model_id": chosen.model_id,
                "litellm_model": chosen.litellm_model,
                "api_base": chosen.api_base,
                "credential_env": chosen.credential_env,
                "locality": chosen.locality,
                "capabilities": sorted(chosen.capabilities),
                "selection_priority": chosen.priority,
            }
        )
    return out


def _yq(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def compile_litellm_config(resolution: dict[str, Any]) -> str:
    if resolution.get("authority") != AUTHORITY_ID:
        raise RouterDenied("resolution authority mismatch")
    rows = resolution.get("routes", [])
    if not isinstance(rows, list) or not rows:
        raise RouterDenied("resolution contains no routes")
    lines = [
        "# GENERATED by FA3-AUTH-MODEL-ROUTER-001. DO NOT EDIT.",
        "# Physical provider/model bindings are current-host runtime decisions only.",
        "model_list:",
    ]
    for row in rows:
        if not isinstance(row, dict):
            raise RouterDenied("invalid route resolution row")
        lines += [
            f"  - model_name: {_yq(str(row['route']))}",
            "    litellm_params:",
            f"      model: {_yq(str(row['litellm_model']))}",
        ]
        if row.get("api_base"):
            lines.append(f"      api_base: {_yq(str(row['api_base']))}")
        if row.get("credential_env"):
            env_name = str(row["credential_env"])
            if not _safe_env_name(env_name):
                raise RouterDenied("unsafe credential env in resolution")
            lines.append(f"      api_key: os.environ/{env_name}")
    lines += [
        "general_settings:",
        "  master_key: os.environ/FA3_LITELLM_MASTER_KEY",
        "router_settings:",
        "  routing_strategy: simple-shuffle",
        "  fallbacks: []",
        "",
    ]
    return "\n".join(lines)


def materialize(catalog_path: Path, routes_path: Path, config_out: Path, resolution_out: Path) -> dict[str, Any]:
    resolution = resolve(catalog_path, routes_path)
    _atomic_write(config_out, compile_litellm_config(resolution), 0o600)
    _atomic_write(resolution_out, json.dumps(resolution, ensure_ascii=False, indent=2) + "\n", 0o600)
    return resolution


def regression_check() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        routes = root / "routes.json"
        catalog = root / "catalog.json"
        routes.write_text(json.dumps({
            "schema": ROUTES_SCHEMA,
            "authority": AUTHORITY_ID,
            "routes": [
                {"route": "fa3-test", "required_capabilities": ["text"], "preferred_capabilities": ["reasoning"], "allow_external": False}
            ],
        }), encoding="utf-8")
        catalog.write_text(json.dumps({
            "schema": CATALOG_SCHEMA,
            "provider_neutral": True,
            "producer": "TEST",
            "candidates": [
                {"candidate_id": "remote", "provider_id": "P-REMOTE", "runtime": "OPENAI_COMPATIBLE", "model_id": "r", "litellm_model": "openai/r", "api_base": "https://example.invalid/v1", "locality": "REMOTE", "admitted": True, "available": True, "capabilities": ["text", "reasoning"], "priority": 1},
                {"candidate_id": "local-a", "provider_id": "P-A", "runtime": "OPENAI_COMPATIBLE", "model_id": "a", "litellm_model": "openai/a", "api_base": "http://127.0.0.1:9001/v1", "locality": "LOCAL", "admitted": True, "available": True, "capabilities": ["text"], "priority": 10},
                {"candidate_id": "local-b", "provider_id": "P-B", "runtime": "OPENAI_COMPATIBLE", "model_id": "b", "litellm_model": "openai/b", "api_base": "http://127.0.0.1:9002/v1", "locality": "LOCAL", "admitted": True, "available": True, "capabilities": ["text", "reasoning"], "priority": 50},
            ],
        }), encoding="utf-8")
        resolution = resolve(catalog, routes)
        chosen = resolution["routes"][0]
        cfg = compile_litellm_config(resolution)
        cases = {
            "local_policy_blocks_remote": chosen["selected_candidate_id"] != "remote",
            "preferred_capability_beats_priority": chosen["selected_candidate_id"] == "local-b",
            "logical_alias_exposed": 'model_name: "fa3-test"' in cfg,
            "master_key_runtime_injected": "os.environ/FA3_LITELLM_MASTER_KEY" in cfg,
            "no_committed_physical_pin_claim": resolution["physical_model_pinned"] is False and resolution["physical_backend_pinned"] is False,
        }
        return {"schema": "fa3.model-router-regression.v1", "result": "PASS" if all(cases.values()) else "FAIL", "cases": cases}


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("materialize")
    p.add_argument("--catalog", required=True)
    p.add_argument("--routes", required=True)
    p.add_argument("--config-out", required=True)
    p.add_argument("--resolution-out", required=True)
    sub.add_parser("regression")
    args = ap.parse_args()
    try:
        if args.command == "regression":
            out = regression_check()
        else:
            out = materialize(Path(args.catalog), Path(args.routes), Path(args.config_out), Path(args.resolution_out))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("result", "PASS") == "PASS" else 2
    except RouterDenied as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
