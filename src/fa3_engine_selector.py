#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("canonical/FA3-ENGINE-REGISTRY-001.json")
ALLOWED_SCOPES = {"GLOBAL","PRODUCT_FAMILY","APPLICATION","WORKSPACE","PROJECT","SEQUENCE","SCENE","TRACK","CLIP","NODE","TASK"}
PRODUCT_FAMILY_REGISTRY = "canonical/FA3-PRODUCT-FAMILY-REGISTRY-001.json"
FALLBACK_MODES = {"OFF","ASK","APPROVED_ONLY"}
SELECTABLE_HEALTH = {"READY","AVAILABLE_CONDITIONAL"}

class EngineSelectionError(RuntimeError):
    pass

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def product_family_ids(root: Path) -> set[str]:
    registry=_load(root/PRODUCT_FAMILY_REGISTRY)
    if registry.get("id")!="FA3-PRODUCT-FAMILY-REGISTRY-001" or registry.get("authority") is not False:
        raise EngineSelectionError("invalid product-family registry")
    return {
        str(row["family_id"])
        for row in registry.get("product_families",[])
        if isinstance(row,dict) and row.get("family_id")
    }

def _pointer(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise EngineSelectionError(f"projection pointer not found: {dotted}")
        cur = cur[part]
    return cur

def _string_values(value: Any) -> list[str]:
    out: list[str] = []
    if value is None:
        return out
    if isinstance(value, dict):
        for child in value.values():
            out.extend(_string_values(child))
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            out.extend(_string_values(child))
    elif isinstance(value, bool):
        out.append("TRUE" if value else "FALSE")
    else:
        text=str(value).strip()
        if text:
            out.append(text)
    return out

def _provider_capabilities(provider: dict[str, Any]) -> list[str]:
    values: set[str] = set()
    for key in ("capability_projection","capability_bindings","capabilities"):
        for item in _string_values(provider.get(key)):
            if item.startswith("CAP-"):
                values.add(item)
    return sorted(values)

def _provider_admission_text(provider: dict[str, Any]) -> str:
    fields = [
        provider.get("status"),
        provider.get("runtime_activation_status"),
        provider.get("runtime_admission"),
        provider.get("activation_mode"),
        provider.get("activation"),
        provider.get("runtime_activation"),
        provider.get("license_admission"),
    ]
    return " ".join(_string_values(fields)).upper()

def _health_from_provider(provider: dict[str, Any]) -> str:
    text=_provider_admission_text(provider)
    activation=provider.get("activation") if isinstance(provider.get("activation"),dict) else {}
    runtime=provider.get("runtime_activation") if isinstance(provider.get("runtime_activation"),dict) else {}
    runtime_admission=provider.get("runtime_admission") if isinstance(provider.get("runtime_admission"),dict) else {}

    if "SECURITY_BLOCKED" in text or "SECURITY_DENIED" in text:
        return "SECURITY_BLOCKED"
    if "LICENSE_BLOCKED" in text or "LICENSE_DENIED" in text:
        return "LICENSE_BLOCKED"
    if "NOT_ADMITTED" in text or "REFERENCE_ONLY" in text or "ACCEPTED_REFERENCE" in text or "REFERENCE_NOT_PRODUCTION" in text:
        return "REFERENCE_ONLY"
    if "DISABLED" in text or "RETIRED" in text:
        return "DISABLED"
    if activation.get("production_admitted") is True:
        return "READY"
    if runtime.get("current_host_runtime_promotion_claimed") is True or runtime_admission.get("current_host_runtime_promotion_claim") is True:
        return "READY"
    if "CURRENT_HOST_PASS" in text or ("PRODUCTION_ADMITTED" in text and "NOT_PRODUCTION_ADMITTED" not in text):
        return "READY"
    if (
        activation.get("production_admitted") is False
        or runtime.get("current_host_runtime_promotion_claimed") is False
        or runtime_admission.get("current_host_runtime_promotion_claim") is False
        or "PENDING" in text
        or "NOT_PROMOTED" in text
        or "CONDITIONAL" in text
    ):
        return "CURRENT_HOST_NOT_ADMITTED"
    return "CURRENT_HOST_NOT_ADMITTED"

def _execution_modes(provider: dict[str, Any], defaults: list[str]) -> list[str]:
    tokens: list[str] = []
    for key in ("execution_modes","execution_topologies","classification"):
        tokens.extend(_string_values(provider.get(key)))
    modes: set[str] = set()
    for token in tokens:
        upper=token.upper()
        if "LOCAL" in upper:
            modes.add("LOCAL")
        if "LAN" in upper:
            modes.add("LAN")
        if "REMOTE" in upper:
            modes.add("REMOTE")
        if "CLOUD" in upper:
            modes.add("CLOUD")
        if "HYBRID" in upper:
            modes.add("HYBRID")
    return sorted(modes) if modes else list(defaults)

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
    explicit_provider_engines: dict[str,str] = {}
    for item in registry.get("engine_records", []):
        row=dict(item)
        eid=row["engine_id"]
        catalog[eid]=row
        provider_id=row.get("provider_record")
        if provider_id:
            if provider_id in explicit_provider_engines:
                raise EngineSelectionError(f"duplicate explicit provider binding: {provider_id}")
            explicit_provider_engines[provider_id]=eid

    for rule in registry.get("provider_projection_rules", []):
        source = _load(root / rule["source"])
        value = _pointer(source, rule["pointer"])
        provider_ids = value if isinstance(value, list) else [value]
        for provider_id in provider_ids:
            if provider_id in explicit_provider_engines:
                continue
            path = root / "canonical/providers" / f"{provider_id}.json"
            if not path.is_file():
                if rule.get("require_provider_record"):
                    raise EngineSelectionError(f"required provider record missing: {provider_id}")
                provider = {"id": provider_id, "name": provider_id, "status": "MISSING_PROVIDER_RECORD"}
            else:
                provider = _load(path)
            eid = f"FA3-ENGINE-PROJECTION::{provider_id}"
            if eid in catalog:
                raise EngineSelectionError(f"duplicate engine projection: {eid}")
            catalog[eid] = {
                "engine_id": eid,
                "name": provider.get("name", provider_id),
                "implementation_kind": "CANONICAL_PROVIDER_PROJECTION",
                "engine_classes": list(rule.get("engine_classes", [])),
                "capability_projection": _provider_capabilities(provider),
                "execution_modes": _execution_modes(provider, list(rule.get("execution_mode_default", ["UNSPECIFIED"]))),
                "status": provider.get("status", "UNKNOWN"),
                "health_state": "MISSING_PROVIDER_RECORD" if not path.is_file() else _health_from_provider(provider),
                "architectural_authority": False,
                "provider_record": provider_id,
                "model_router_bound": bool(rule.get("provider_model_selection_authority")),
                "current_host_runtime_promotion_claim": bool(
                    (provider.get("runtime_activation") or {}).get("current_host_runtime_promotion_claimed", False)
                    if isinstance(provider.get("runtime_activation"),dict) else False
                ),
            }
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
        if not include_unavailable and e.get("health_state") not in SELECTABLE_HEALTH:
            continue
        hay=" ".join([
            str(e.get("name","")),str(e.get("engine_id","")),
            *map(str,e.get("engine_classes",[])),
            *map(str,e.get("capability_projection",[])),
            *map(str,e.get("execution_modes",[])),
        ]).lower()
        if query and query not in hay:
            continue
        out.append(e)
    return out

def compatibility_report(
    catalog: list[dict[str, Any]], *,
    engine_id: str,
    required_capabilities: list[str] | None = None,
) -> dict[str, Any]:
    by_id={e["engine_id"]:e for e in catalog}
    if engine_id not in by_id:
        raise EngineSelectionError(f"unknown engine: {engine_id}")
    engine=by_id[engine_id]
    required=set(required_capabilities or [])
    declared=set(engine.get("capability_projection", []))
    supported=sorted(required & declared)
    missing=sorted(required - declared)
    if not required or not missing:
        grade="NATIVE"
    elif supported:
        grade="PARTIAL"
    else:
        grade="UNSUPPORTED"
    return {
        "schema":"fa3.engine-compatibility-report.v1",
        "engine_id":engine_id,
        "required_capabilities":sorted(required),
        "supported_capabilities":supported,
        "missing_capabilities":missing,
        "grade":grade,
        "execution_eligible":engine.get("health_state") in SELECTABLE_HEALTH,
        "health_state":engine.get("health_state"),
        "evidence_semantics":"DECLARED_CAPABILITY_PROJECTION_ONLY",
        "unproven_grade_escalation":False,
    }

def selection_intent(
    catalog: list[dict[str, Any]], *,
    engine_id: str,
    scope: str,
    scope_target_id: str | None = None,
    required_capabilities: list[str] | None = None,
    fallback_mode: str = "OFF",
    approved_fallback_engine_ids: list[str] | None = None,
    valid_product_family_ids: set[str] | None = None,
) -> dict[str, Any]:
    if scope not in ALLOWED_SCOPES:
        raise EngineSelectionError("invalid selection scope")
    target=(scope_target_id or "").strip()
    if scope == "GLOBAL":
        target="GLOBAL"
    elif not target:
        raise EngineSelectionError("non-GLOBAL selection scope requires scope_target_id")
    if scope == "PRODUCT_FAMILY":
        if valid_product_family_ids is None or target not in valid_product_family_ids:
            raise EngineSelectionError("unknown product-family scope target")
    if fallback_mode not in FALLBACK_MODES:
        raise EngineSelectionError("invalid fallback mode")
    by_id={e["engine_id"]:e for e in catalog}
    if engine_id not in by_id:
        raise EngineSelectionError("unknown engine")
    engine=by_id[engine_id]
    required=set(required_capabilities or [])
    if not required.issubset(set(engine.get("capability_projection", []))):
        raise EngineSelectionError("selected engine does not declare all required capabilities")
    if engine.get("health_state") not in SELECTABLE_HEALTH:
        raise EngineSelectionError("selected engine is not execution-eligible")

    approved=[]
    for candidate_id in approved_fallback_engine_ids or []:
        if candidate_id == engine_id:
            continue
        candidate=by_id.get(candidate_id)
        if candidate is None:
            raise EngineSelectionError(f"unknown approved fallback engine: {candidate_id}")
        if candidate.get("health_state") not in SELECTABLE_HEALTH:
            raise EngineSelectionError(f"approved fallback engine is not execution-eligible: {candidate_id}")
        if not required.issubset(set(candidate.get("capability_projection", []))):
            raise EngineSelectionError(f"approved fallback engine lacks required capabilities: {candidate_id}")
        if candidate_id not in approved:
            approved.append(candidate_id)
    if fallback_mode == "APPROVED_ONLY" and not approved:
        raise EngineSelectionError("APPROVED_ONLY requires a user-approved engine allowlist")

    return {
        "schema":"fa3.engine-selection-intent.v1",
        "scope":scope,
        "scope_target_id":target,
        "engine_id":engine_id,
        "required_capabilities":sorted(required),
        "compatibility":compatibility_report(catalog,engine_id=engine_id,required_capabilities=sorted(required)),
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
        if e.get("health_state") not in SELECTABLE_HEALTH:
            continue
        if required.issubset(set(e.get("capability_projection", []))):
            result.append(e)
    return result

def compare_static(
    catalog: list[dict[str, Any]],
    engine_ids: list[str],
    required_capabilities: list[str] | None = None,
) -> list[dict[str, Any]]:
    by_id={e["engine_id"]:e for e in catalog}
    rows=[]
    for eid in engine_ids:
        if eid not in by_id:
            raise EngineSelectionError(f"unknown engine: {eid}")
        e=by_id[eid]
        compatibility=compatibility_report(
            catalog,engine_id=eid,required_capabilities=required_capabilities or [])
        rows.append({
            "engine_id":eid,
            "name":e.get("name"),
            "engine_classes":e.get("engine_classes",[]),
            "capabilities":e.get("capability_projection",[]),
            "execution_modes":e.get("execution_modes",[]),
            "health_state":e.get("health_state"),
            "implementation_kind":e.get("implementation_kind"),
            "compatibility_grade":compatibility["grade"],
            "compatibility":compatibility,
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
    sel.add_argument("--scope-target")
    sel.add_argument("--capability", action="append", default=[])
    sel.add_argument("--fallback", choices=sorted(FALLBACK_MODES), default="OFF")
    sel.add_argument("--approved-fallback-engine", action="append", default=[])

    comp=sub.add_parser("compare")
    comp.add_argument("--engine", action="append", required=True)
    comp.add_argument("--capability", action="append", default=[])

    args=ap.parse_args()
    root=Path(args.root).resolve()
    catalog=materialize_catalog(root)
    if args.cmd=="list":
        out=filter_catalog(
            catalog,required_capabilities=args.capability,
            engine_classes=args.classes,execution_modes=args.mode,text=args.text)
    elif args.cmd=="compare":
        out=compare_static(catalog,args.engine,args.capability)
    else:
        out=selection_intent(
            catalog,engine_id=args.engine,scope=args.scope,scope_target_id=args.scope_target,
            required_capabilities=args.capability,fallback_mode=args.fallback,
            approved_fallback_engine_ids=args.approved_fallback_engine,
            valid_product_family_ids=product_family_ids(root))
    print(json.dumps(out,indent=2,ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
