#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("canonical/FA3-ENGINE-REGISTRY-001.json")
ALLOWED_SCOPES = {"GLOBAL","APPLICATION","WORKSPACE","PROJECT","SEQUENCE","SCENE","TRACK","CLIP","NODE","TASK"}
FALLBACK_MODES = {"OFF","ASK","APPROVED_ONLY"}
BLOCKED_HEALTH = {"LICENSE_BLOCKED","SECURITY_BLOCKED","REFERENCE_ONLY","MISSING_PROVIDER_RECORD"}

class EngineSelectionError(RuntimeError):
    pass

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _pointer(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise EngineSelectionError(f"projection pointer not found: {dotted}")
        cur = cur[part]
    return cur

def _health_from_provider(provider: dict[str, Any]) -> str:
    status = str(provider.get("status", "")).upper()
    runtime = provider.get("runtime_activation") or {}
    if "REFERENCE_ONLY" in status:
        return "REFERENCE_ONLY"
    if runtime and runtime.get("current_host_runtime_promotion_claimed") is False:
        return "CURRENT_HOST_NOT_ADMITTED"
    if "PENDING" in status or "NOT_PROMOTED" in status:
        return "CURRENT_HOST_NOT_ADMITTED"
    if "DISABLED" in status or "RETIRED" in status:
        return "DISABLED"
    return "AVAILABLE_CONDITIONAL"

def _execution_modes(provider: dict[str, Any], defaults: list[str]) -> list[str]:
    cls = {str(x).upper() for x in provider.get("classification", [])}
    if any("REMOTE" in x or "CLOUD" in x for x in cls):
        return ["CLOUD"]
    return list(defaults)

def load_registry(root: Path) -> dict[str, Any]:
    registry = _load(root / REGISTRY_REL)
    if registry.get("schema") != "fa3.engine-registry.v1" or registry.get("id") != "FA3-ENGINE-REGISTRY-001":
        raise EngineSelectionError("engine registry identity/schema mismatch")
    if registry.get("authority") is not False or registry.get("selection_is_execution_authority") is not False:
        raise EngineSelectionError("engine registry may not become execution authority")
    if registry.get("default_engine") is not None:
        raise EngineSelectionError("default engine mandate is forbidden")
    return registry

def materialize_catalog(root: Path) -> list[dict[str, Any]]:
    registry = load_registry(root)
    catalog: dict[str, dict[str, Any]] = {}
    for item in registry.get("engine_records", []):
        catalog[item["engine_id"]] = dict(item)

    for rule in registry.get("provider_projection_rules", []):
        source = _load(root / rule["source"])
        value = _pointer(source, rule["pointer"])
        provider_ids = value if isinstance(value, list) else [value]
        for provider_id in provider_ids:
            path = root / "canonical/providers" / f"{provider_id}.json"
            if not path.is_file():
                if rule.get("require_provider_record"):
                    continue
                provider = {"id": provider_id, "name": provider_id, "status": "MISSING_PROVIDER_RECORD"}
            else:
                provider = _load(path)
            eid = f"FA3-ENGINE-PROJECTION::{provider_id}"
            catalog.setdefault(eid, {
                "engine_id": eid,
                "name": provider.get("name", provider_id),
                "implementation_kind": "CANONICAL_PROVIDER_PROJECTION",
                "engine_classes": list(rule.get("engine_classes", [])),
                "capability_projection": list(provider.get("capability_projection", [])),
                "execution_modes": _execution_modes(provider, list(rule.get("execution_mode_default", ["UNSPECIFIED"]))),
                "status": provider.get("status", "UNKNOWN"),
                "health_state": _health_from_provider(provider),
                "architectural_authority": False,
                "provider_record": provider_id,
                "model_router_bound": bool(rule.get("provider_model_selection_authority")),
                "current_host_runtime_promotion_claim": bool((provider.get("runtime_activation") or {}).get("current_host_runtime_promotion_claimed", False)),
            })
    return sorted(catalog.values(), key=lambda x: (x.get("name","").lower(), x["engine_id"]))

def filter_catalog(
    catalog: list[dict[str, Any]], *,
    required_capabilities: list[str] | None = None,
    engine_classes: list[str] | None = None,
    execution_modes: list[str] | None = None,
    include_unavailable: bool = True,
    text: str = "",
) -> list[dict[str, Any]]:
    caps=set(required_capabilities or [])
    classes=set(engine_classes or [])
    modes=set(execution_modes or [])
    query=text.strip().lower()
    out=[]
    for e in catalog:
        if caps and not caps.issubset(set(e.get("capability_projection", []))):
            continue
        if classes and not classes.intersection(set(e.get("engine_classes", []))):
            continue
        if modes and not modes.intersection(set(e.get("execution_modes", []))):
            continue
        if not include_unavailable and e.get("health_state") not in {"READY","AVAILABLE_CONDITIONAL"}:
            continue
        hay=" ".join([str(e.get("name","")),str(e.get("engine_id","")),*map(str,e.get("engine_classes",[])),*map(str,e.get("capability_projection",[]))]).lower()
        if query and query not in hay:
            continue
        out.append(e)
    return out

def selection_intent(
    catalog: list[dict[str, Any]], *,
    engine_id: str,
    scope: str,
    required_capabilities: list[str] | None = None,
    fallback_mode: str = "OFF",
    approved_fallback_engine_ids: list[str] | None = None,
) -> dict[str, Any]:
    if scope not in ALLOWED_SCOPES:
        raise EngineSelectionError("invalid selection scope")
    if fallback_mode not in FALLBACK_MODES:
        raise EngineSelectionError("invalid fallback mode")
    by_id={e["engine_id"]:e for e in catalog}
    if engine_id not in by_id:
        raise EngineSelectionError("unknown engine")
    engine=by_id[engine_id]
    required=set(required_capabilities or [])
    if not required.issubset(set(engine.get("capability_projection", []))):
        raise EngineSelectionError("selected engine does not declare all required capabilities")
    if engine.get("health_state") in BLOCKED_HEALTH:
        raise EngineSelectionError("selected engine is blocked/reference-only")
    approved=list(approved_fallback_engine_ids or [])
    if fallback_mode == "APPROVED_ONLY" and not approved:
        raise EngineSelectionError("APPROVED_ONLY requires a user-approved engine allowlist")
    return {
        "schema":"fa3.engine-selection-intent.v1",
        "scope":scope,
        "engine_id":engine_id,
        "required_capabilities":sorted(required),
        "fallback_policy":{"mode":fallback_mode,"approved_engine_ids":approved},
        "execution_requested":False,
        "execution_ready":engine.get("health_state") == "READY",
        "health_state":engine.get("health_state"),
        "provider_model_routing_authority":"FA3-AUTH-MODEL-ROUTER-001",
        "resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "secret_authority":"FA3-AUTH-SECRETS-001",
        "silent_fallback":False,
    }

def fallback_candidates(catalog: list[dict[str, Any]], intent: dict[str, Any]) -> list[dict[str, Any]]:
    policy=intent.get("fallback_policy", {})
    mode=policy.get("mode", "OFF")
    if mode == "OFF":
        return []
    approved=set(policy.get("approved_engine_ids", []))
    if mode == "APPROVED_ONLY" and not approved:
        raise EngineSelectionError("approved fallback list missing")
    required=set(intent.get("required_capabilities", []))
    result=[]
    for e in catalog:
        if e["engine_id"] == intent.get("engine_id"):
            continue
        if mode == "APPROVED_ONLY" and e["engine_id"] not in approved:
            continue
        if e.get("health_state") in BLOCKED_HEALTH:
            continue
        if required.issubset(set(e.get("capability_projection", []))):
            result.append(e)
    return result

def compare_static(catalog: list[dict[str, Any]], engine_ids: list[str]) -> list[dict[str, Any]]:
    by_id={e["engine_id"]:e for e in catalog}
    rows=[]
    for eid in engine_ids:
        if eid not in by_id:
            raise EngineSelectionError(f"unknown engine: {eid}")
        e=by_id[eid]
        rows.append({
            "engine_id":eid,
            "name":e.get("name"),
            "engine_classes":e.get("engine_classes",[]),
            "capabilities":e.get("capability_projection",[]),
            "execution_modes":e.get("execution_modes",[]),
            "health_state":e.get("health_state"),
            "implementation_kind":e.get("implementation_kind"),
            "static_only":True,
        })
    return rows

def main() -> int:
    ap=argparse.ArgumentParser(description="FA3 shared Engine Registry/Selector static projection")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub=ap.add_subparsers(dest="cmd", required=True)
    ls=sub.add_parser("list")
    ls.add_argument("--capability", action="append", default=[])
    ls.add_argument("--class", dest="classes", action="append", default=[])
    ls.add_argument("--mode", action="append", default=[])
    ls.add_argument("--text", default="")
    sel=sub.add_parser("select")
    sel.add_argument("--engine", required=True)
    sel.add_argument("--scope", default="PROJECT")
    sel.add_argument("--capability", action="append", default=[])
    sel.add_argument("--fallback", choices=sorted(FALLBACK_MODES), default="OFF")
    args=ap.parse_args()
    root=Path(args.root).resolve()
    catalog=materialize_catalog(root)
    if args.cmd=="list":
        out=filter_catalog(catalog,required_capabilities=args.capability,engine_classes=args.classes,execution_modes=args.mode,text=args.text)
    else:
        out=selection_intent(catalog,engine_id=args.engine,scope=args.scope,required_capabilities=args.capability,fallback_mode=args.fallback)
    print(json.dumps(out,indent=2,ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
