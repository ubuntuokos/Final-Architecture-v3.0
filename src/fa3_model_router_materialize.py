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


def receipt_proves_provider(path: Path, provider_id: str, api_base: str) -> bool:
    if not path.is_file():
        return False
    rec = loadj(path)
    if rec.get("status") != "PASS" and rec.get("result") != "PASS":
        return False
    expected = api_base.rstrip("/")

    providers = rec.get("providers")
    if isinstance(providers, dict):
        item = providers.get(provider_id)
        if not (
            isinstance(item, dict)
            and item.get("provider_id", provider_id) == provider_id
            and item.get("status") == "PASS"
            and _current_host_level(item.get("evidence_level"))
        ):
            return False
        handoff = item.get("runtime_handoff")
        return (
            isinstance(handoff, dict)
            and handoff.get("preserved") is True
            and handoff.get("server_cpu_only") is True
            and handoff.get("accelerator_visibility") == "BLOCKED_FOR_SERVER_LIFETIME"
            and str(handoff.get("api_base") or "").strip().rstrip("/") == expected
        )

    endpoint = str(rec.get("api_base") or rec.get("endpoint") or "").strip().rstrip("/")
    return (
        rec.get("provider_id") == provider_id
        and _current_host_level(rec.get("evidence_level"))
        and endpoint == expected
    )


def _native_process_matches(handoff: dict[str, Any]) -> bool:
    from fa3_model_router_provider_discovery import process_start_ticks
    pid = handoff.get("process_id")
    ticks = handoff.get("process_start_ticks")
    return isinstance(pid, int) and pid > 0 and isinstance(ticks, int) and ticks > 0 and process_start_ticks(pid) == ticks


def auth_header(candidate: dict[str, Any]) -> dict[str, str]:
    env_name = str(candidate.get("api_key_env", "")).strip()
    if not env_name:
        return {}
    token = os.environ.get(env_name, "").strip()
    if not token and env_name == "FA3_SYSTEM_ONE_BRIDGE_TOKEN":
        # The current-host native bridge credentials are systemd LoadCredential
        # files from Secret Broker, not a globally stored environment value.
        import stat
        directory = os.environ.get("CREDENTIALS_DIRECTORY", "")
        if directory:
            path = Path(directory) / "fa3-system-one-bridge-token"
            if (not path.is_symlink() and path.is_file()
                    and stat.S_IMODE(path.stat().st_mode) in {0o400, 0o600}):
                token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise MaterializationDenied(f"backend API key environment variable is empty: {env_name}")
    return {"Authorization": f"Bearer {token}"}


def fetch_models(candidate: dict[str, Any], timeout: float) -> list[str]:
    api_base = str(candidate.get("catalog_api_base") or candidate["api_base"]).rstrip("/")
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


def select_bindings(
    routes: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    catalogs: dict[str, list[str]],
    *,
    decision_fabric: Any = None,
    decision_provider_id: str = "FA3-PROVIDER-DECISION-RULES-001",
    decision_rollout: str = "SHADOW",
    decision_state: Any = None,
) -> dict[str, dict[str, Any]]:
    """Select runtime bindings while keeping the central Router authoritative.

    Admission, route scope and live-catalog filtering are deterministic and happen
    before any Decision Fabric call. The optional Decision Fabric sees only the
    resulting bounded eligible set. SHADOW/ADVISORY never changes routing.
    """
    ordered = sorted(candidates, key=lambda c: (-int(c.get("priority", 0)), str(c.get("runtime_id", ""))))
    out: dict[str, dict[str, Any]] = {}
    for route in routes:
        name = str(route.get("route", "")).strip()
        if not name:
            raise MaterializationDenied("logical route name is empty")
        required_api = str(route.get("required_runtime_api") or "OPENAI_COMPATIBLE_CHAT")
        if required_api not in {"OPENAI_COMPATIBLE_CHAT", "SYSTEM_ONE_DECISIONS_V1"}:
            raise MaterializationDenied(f"unsupported route protocol for {name}")
        eligible: list[dict[str, Any]] = []
        failures: list[str] = []
        for candidate in ordered:
            if not route_allowed(candidate, name):
                continue
            candidate_apis = candidate.get("runtime_apis", ["OPENAI_COMPATIBLE_CHAT"])
            if not isinstance(candidate_apis, list) or required_api not in candidate_apis:
                continue
            runtime_id = str(candidate["runtime_id"])
            try:
                preferred_map = candidate.get("route_preferred_models", {})
                preferred = preferred_map.get(name, []) if isinstance(preferred_map, dict) else []
                if not preferred:
                    preferred = candidate.get("preferred_models", [])
                available = catalogs.get(runtime_id, [])
                if required_api == "SYSTEM_ONE_DECISIONS_V1":
                    approved = candidate.get("approved_models")
                    if not isinstance(approved, list) or not approved or any(not isinstance(x, str) or not x for x in approved):
                        raise MaterializationDenied(f"native System One route lacks explicitly designated models: {runtime_id}")
                    available = sorted(set(available) & set(approved))
                    if not available:
                        raise MaterializationDenied(f"no designated System One model in live runtime catalogue: {runtime_id}")
                model = choose_model(available, preferred if isinstance(preferred, list) else [])
                raw_options = candidate.get("litellm_options", {})
                if raw_options is None:
                    raw_options = {}
                if not isinstance(raw_options, dict):
                    raise MaterializationDenied(f"runtime provider litellm_options must be an object: {runtime_id}")
                if required_api == "SYSTEM_ONE_DECISIONS_V1" and raw_options:
                    raise MaterializationDenied(f"native System One does not admit chat-only LiteLLM provider options: {runtime_id}")
                reserved = {"model", "api_base", "api_key", "custom_llm_provider"}
                if reserved.intersection(raw_options):
                    raise MaterializationDenied(f"runtime provider litellm_options contains reserved routing fields: {runtime_id}")
                litellm_options: dict[str, Any] = {}
                for key, value in raw_options.items():
                    if not isinstance(key, str) or not key.strip():
                        raise MaterializationDenied(f"runtime provider litellm_options contains invalid key: {runtime_id}")
                    if not isinstance(value, (str, int, float, bool)) and value is not None:
                        raise MaterializationDenied(f"runtime provider litellm_options contains non-scalar value: {runtime_id}:{key}")
                    litellm_options[key] = value
                eligible.append({
                    "route": name,
                    "provider_id": candidate["provider_id"],
                    "runtime_id": runtime_id,
                    "api_base": candidate["api_base"],
                    "litellm_provider": candidate.get("litellm_provider", "openai"),
                    "litellm_options": litellm_options,
                    "model": model,
                    "api_key_env": candidate.get("api_key_env"),
                    "selection": "RUNTIME_DISCOVERED",
                    "runtime_api": required_api,
                    "native_bridge_auth_env": candidate.get("native_bridge_auth_env") if required_api == "SYSTEM_ONE_DECISIONS_V1" else None,
                    "_priority": int(candidate.get("priority", 0)),
                })
            except MaterializationDenied as exc:
                failures.append(f"{runtime_id}:{exc}")
        if not eligible:
            if route.get("optional") is True and required_api == "SYSTEM_ONE_DECISIONS_V1":
                continue
            raise MaterializationDenied(f"no admitted runtime can satisfy logical route {name}: {' | '.join(failures)}")

        selected = eligible[0]
        decision_trace = None
        if decision_fabric is not None:
            decision_candidates = [
                {
                    "id": f"{item['runtime_id']}::{item['model']}",
                    "description": f"admitted runtime/model candidate for logical route {name}",
                    "metadata": {
                        "priority": item["_priority"],
                        "provider_id": item["provider_id"],
                        "runtime_id": item["runtime_id"],
                        "model_id": item["model"],
                    },
                }
                for item in eligible
            ]
            try:
                decision_trace = decision_fabric.decide(
                    {
                        "contract": "RANK",
                        "purpose": "Rank only pre-admitted, route-compatible, live-catalog Model Router candidates",
                        "candidates": decision_candidates,
                        "constraints": {},
                        "policy_context": {
                            "routing_authority": AUTHORITY,
                            "deterministic_admission_already_applied": True,
                            "logical_route": name,
                        },
                        "evidence_refs": [],
                        "state": decision_state,
                        "failure_policy": "EXISTING_BEHAVIOR",
                        "rollout": decision_rollout,
                        "final_policy_owner": AUTHORITY,
                    },
                    decision_provider_id,
                )
            except Exception as exc:
                # A provider escaping the bounded candidate set is a policy
                # violation, not a reason to silently choose its proposal.
                raise MaterializationDenied(f"Decision Fabric advisory rejected for {name}: {type(exc).__name__}") from exc

            if decision_rollout == "ACTIVE" and decision_trace.get("status") == "DECIDED":
                ranked = (decision_trace.get("result") or {}).get("ranked", [])
                if ranked:
                    by_id = {f"{item['runtime_id']}::{item['model']}": item for item in eligible}
                    proposed = ranked[0]
                    if proposed not in by_id:
                        raise MaterializationDenied("Decision Fabric attempted to escape pre-admitted Model Router candidate set")
                    selected = by_id[proposed]

        selected = {key: value for key, value in selected.items() if key != "_priority"}
        if decision_trace is not None:
            selected["decision_advisory"] = decision_trace
            selected["decision_advisory_changes_authority"] = False
        out[name] = selected
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
        catalog_api_base = str(row.get("catalog_api_base") or api_base).strip().rstrip("/")
        admission_api_base = str(row.get("admission_api_base") or catalog_api_base).strip().rstrip("/")
        if not provider_id or not runtime_id or not api_base or not catalog_api_base or not admission_api_base:
            raise MaterializationDenied("enabled runtime provider entry lacks provider_id/runtime_id/api_base/catalog_api_base/admission_api_base")
        if not all(loopback_origin(value) for value in (api_base, catalog_api_base, admission_api_base)):
            raise MaterializationDenied(f"baseline current-host router rejects non-loopback provider endpoint: {runtime_id}")
        if not canonical_provider_ok(root, provider_id):
            raise MaterializationDenied(f"provider is not canonically bound to central Model Router authority: {provider_id}")
        receipt_value = str(row.get("admission_receipt", "")).strip()
        if not receipt_value:
            raise MaterializationDenied(f"provider admission receipt missing: {provider_id}")
        receipt = Path(receipt_value).expanduser()
        if not receipt.is_absolute():
            receipt = (root / receipt).resolve()
        if not receipt_proves_provider(receipt, provider_id, admission_api_base):
            raise MaterializationDenied(f"current-host admission receipt does not prove provider instance: {provider_id}")
        apis = row.get("runtime_apis", ["OPENAI_COMPATIBLE_CHAT"])
        if not isinstance(apis, list) or not apis or any(
            api not in {"OPENAI_COMPATIBLE_CHAT", "SYSTEM_ONE_DECISIONS_V1"} for api in apis
        ):
            raise MaterializationDenied(f"unknown native runtime API: {runtime_id}")
        if "SYSTEM_ONE_DECISIONS_V1" in apis:
            if (
                apis != ["SYSTEM_ONE_DECISIONS_V1"]
                or provider_id != "FA3-PROVIDER-SYSTEM-ONE-NATIVE-001"
                or row.get("routes") != ["fa3-decision-system-one"]
                or row.get("native_bridge_auth_env") != "FA3_SYSTEM_ONE_BRIDGE_TOKEN"
            ):
                raise MaterializationDenied("native System One provider must be explicitly scoped and projected")
            designation_path = str(row.get("model_designation_receipt", "")).strip()
            if not designation_path:
                raise MaterializationDenied("native System One provider requires primary-model designation receipt")
            designation = Path(designation_path).expanduser()
            if not designation.is_absolute():
                designation = (root / designation).resolve()
            if not designation.is_file():
                raise MaterializationDenied("model designation receipt is missing")
            approved = loadj(designation)
            if not (
                approved.get("schema") == "fa3.system-one-model-designation.v1"
                and approved.get("result") == "PASS"
                and approved.get("router_authority") == AUTHORITY
                and approved.get("provider_id") == provider_id
                and approved.get("logical_route") == "fa3-decision-system-one"
                and approved.get("approved_by_primary_model") is True
                and approved.get("approved_models") == row.get("approved_models")
                and isinstance(row.get("approved_models"), list)
                and bool(row["approved_models"])
            ):
                raise MaterializationDenied("native System One model designation does not bind approved model set")
            native_rec = loadj(receipt)
            if not (
                native_rec.get("schema") == "fa3.system-one-native-current-host-receipt.v1"
                and native_rec.get("protocol") == "SYSTEM_ONE_DECISIONS_V1"
                and native_rec.get("real_upstream_response") is True
                and native_rec.get("invalid_bearer_rejected") is True
                and native_rec.get("secret_broker_admission_verified") is True
                and native_rec.get("model_designation_sha256") == sha256_file(designation)
                and native_rec.get("selected_model") in row["approved_models"]
                and isinstance(native_rec.get("runtime_handoff"), dict)
                and isinstance(native_rec["runtime_handoff"].get("process_id"), int)
                and isinstance(native_rec["runtime_handoff"].get("process_start_ticks"), int)
                and _native_process_matches(native_rec["runtime_handoff"])
            ):
                raise MaterializationDenied("native System One current-host receipt lacks real upstream/security proof")
        copy = dict(row)
        copy["provider_id"] = provider_id
        copy["runtime_id"] = runtime_id
        copy["api_base"] = api_base
        copy["catalog_api_base"] = catalog_api_base
        copy["admission_api_base"] = admission_api_base
        copy["_admission_receipt"] = str(receipt)
        candidates.append(copy)
        receipt_hashes[provider_id] = sha256_file(receipt)
    if not candidates:
        raise MaterializationDenied("no enabled admitted runtime provider remains")
    return candidates, receipt_hashes


def yaml_quote(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_litellm(bindings: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# GENERATED by FA3-AUTH-MODEL-ROUTER-001. DO NOT COMMIT.",
        "model_list:",
    ]
    native_routes = {route: item for route, item in bindings.items()
                     if item.get("runtime_api") == "SYSTEM_ONE_DECISIONS_V1"}
    if set(native_routes) - {"fa3-decision-system-one"}:
        raise MaterializationDenied("unknown native System One route would bypass central policy")
    for route, item in sorted(bindings.items()):
        if item.get("runtime_api") == "SYSTEM_ONE_DECISIONS_V1":
            continue
        prefix = str(item.get("litellm_provider", "openai")).strip() or "openai"
        model = str(item["model"])
        lines += [
            f"  - model_name: {yaml_quote(route)}",
            "    litellm_params:",
            f"      model: {yaml_quote(prefix + '/' + model)}",
            f"      api_base: {yaml_quote(str(item['api_base']))}",
        ]
        options = item.get("litellm_options", {})
        if isinstance(options, dict):
            for key, value in sorted(options.items()):
                lines.append(f"      {key}: {yaml_quote(value)}")
        env_name = str(item.get("api_key_env") or "").strip()
        if env_name:
            lines.append(f"      api_key: os.environ/{env_name}")
        elif prefix not in {"ollama", "ollama_chat"}:
            lines.append("      api_key: os.environ/FA3_MODEL_ROUTER_BACKEND_DUMMY_KEY")
    lines += [
        "router_settings:",
        "  routing_strategy: simple-shuffle",
        "general_settings:",
        "  master_key: os.environ/FA3_MODEL_ROUTER_MASTER_KEY",
    ]
    for route, item in sorted(native_routes.items()):
        env_name = item.get("native_bridge_auth_env")
        if env_name != "FA3_SYSTEM_ONE_BRIDGE_TOKEN":
            raise MaterializationDenied("native bridge token must be the projected Secret Broker environment")
        api_base = str(item["api_base"]).rstrip("/")
        if not loopback_origin(api_base):
            raise MaterializationDenied("native System One pass-through must target loopback")
        lines += [
            "  pass_through_endpoints:",
            "    - path: \"/fa3/system-one/decisions\"",
            f"      target: {yaml_quote(api_base + '/decisions')}",
            "      auth: true",
            "      forward_headers: false",
            "      include_subpath: false",
            "      methods: [\"POST\"]",
            "      timeout: 20",
            "      headers:",
            "        Authorization: \"Bearer os.environ/FA3_SYSTEM_ONE_BRIDGE_TOKEN\"",
            "        content-type: \"application/json\"",
        ]
    lines.append("")
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
        "optional_routes_not_admitted": sorted({
            row["route"] for row in routes if row.get("optional") is True
        } - set(bindings)),
        "generated_config": str(output),
        "generated_config_sha256": sha256_file(output),
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
