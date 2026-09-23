#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from typing import Any

from fa3_decision_fabric import DecisionFabric
from fa3_decision_adapters import Fa3DecisionAdapters

STRATEGY_ORDER = ("metadata", "hierarchical", "lexical", "vector", "tree_reasoning", "rerank", "evidence_fusion")


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_plan(request: dict[str, Any]) -> dict[str, Any]:
    query = str(request.get("query", "")).strip()
    if not query:
        raise ValueError("query is required")
    requested = request.get("strategies")
    if requested is None:
        strategies = ["metadata", "hierarchical", "lexical", "tree_reasoning", "rerank", "evidence_fusion"]
        if request.get("allow_vector", True) is True:
            strategies.insert(3, "vector")
    else:
        if not isinstance(requested, list) or not requested:
            raise ValueError("strategies must be a non-empty list")
        unknown = sorted(set(requested) - set(STRATEGY_ORDER))
        if unknown:
            raise ValueError("unknown strategies: " + ",".join(unknown))
        strategies = [s for s in STRATEGY_ORDER if s in requested]
    source_scope = request.get("source_scope", {})
    if not isinstance(source_scope, dict):
        raise ValueError("source_scope must be an object")
    authority_snapshot = {
        "knowledge_root": "FA3-KNOWLEDGE-001",
        "model_router": "FA3-AUTH-MODEL-ROUTER-001",
        "mcp_gateway": "FA3-AUTH-MCP-GATEWAY-001",
        "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
    }
    material = {"query": query, "strategies": strategies, "source_scope": source_scope, "authority_snapshot": authority_snapshot}
    plan_id = "FA3-RPLAN-" + canonical_sha256(material)[:24].upper()
    return {
        "schema": "fa3.retrieval-plan.v1",
        "plan_id": plan_id,
        "query": query,
        "strategy_order": strategies,
        "source_scope": source_scope,
        "provider_preferences": request.get("provider_preferences", ["LOCAL_FIRST"]),
        "stages": [{"stage_id": f"S{i+1:02d}", "strategy": strategy, "authority": "FA3-KNOWLEDGE-001"} for i, strategy in enumerate(strategies)],
        "authority_snapshot": authority_snapshot,
        "provider_neutral": True,
    }


def fuse_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for item in candidates:
        source_id = str(item.get("source_id", "")).strip()
        locator = str(item.get("locator", "")).strip()
        if not source_id or not locator:
            raise ValueError("candidate source_id and locator are required")
        score = float(item.get("score", 0.0))
        key = (source_id, locator)
        strategy = str(item.get("strategy", "unknown"))
        evidence = [str(x) for x in item.get("evidence_refs", [])]
        if key not in merged:
            merged[key] = {
                "candidate_id": "FA3-RCAND-" + canonical_sha256({"source_id": source_id, "locator": locator})[:20].upper(),
                "source_id": source_id,
                "locator": locator,
                "score": score,
                "strategies": [strategy],
                "evidence_refs": sorted(set(evidence)),
            }
        else:
            row = merged[key]
            row["score"] = max(float(row["score"]), score)
            if strategy not in row["strategies"]:
                row["strategies"].append(strategy)
            row["evidence_refs"] = sorted(set(row["evidence_refs"]) | set(evidence))
    return sorted(merged.values(), key=lambda x: (-float(x["score"]), x["source_id"], x["locator"]))


def make_trace(plan: dict[str, Any], candidates: list[dict[str, Any]], provider_receipts: list[dict[str, Any]]) -> dict[str, Any]:
    if plan.get("schema") != "fa3.retrieval-plan.v1":
        raise ValueError("invalid plan")
    fused = fuse_candidates(candidates)
    evidence_refs = sorted({ref for item in fused for ref in item.get("evidence_refs", [])})
    provider_projection = [
        {
            "provider_id": r.get("provider_id"),
            "adapter_id": r.get("adapter_id"),
            "receipt_id": r.get("receipt_id"),
            "status": r.get("status"),
        }
        for r in provider_receipts
    ]
    material = {"plan_id": plan["plan_id"], "candidates": fused, "providers": provider_projection, "evidence_refs": evidence_refs}
    return {
        "schema": "fa3.retrieval-trace.v1",
        "trace_id": "FA3-RTRACE-" + canonical_sha256(material)[:24].upper(),
        "plan_id": plan["plan_id"],
        "stages": plan["stages"],
        "candidates": fused,
        "provider_receipts": provider_projection,
        "evidence_refs": evidence_refs,
        "authority_snapshot": plan["authority_snapshot"],
        "derived": True,
    }


def context_passport(trace: dict[str, Any]) -> dict[str, Any]:
    if trace.get("schema") != "fa3.retrieval-trace.v1":
        raise ValueError("invalid trace")
    source_refs = sorted({f"{x['source_id']}#{x['locator']}" for x in trace.get("candidates", [])})
    content_sha = canonical_sha256({"trace_id": trace["trace_id"], "source_refs": source_refs, "evidence_refs": trace.get("evidence_refs", [])})
    return {
        "schema": "fa3.context-passport.v1",
        "passport_id": "FA3-CPASS-" + content_sha[:24].upper(),
        "trace_id": trace["trace_id"],
        "source_refs": source_refs,
        "evidence_refs": trace.get("evidence_refs", []),
        "content_sha256": content_sha,
        "derived": True,
        "rebuildable": True,
        "authority": "FA3-KNOWLEDGE-001",
    }


def decision_rerank(
    trace: dict[str, Any],
    *,
    fabric: DecisionFabric | None = None,
    provider_id: str = "FA3-PROVIDER-DECISION-RULES-001",
    rollout: str = "SHADOW",
) -> dict[str, Any]:
    """Optionally rerank an existing RetrievalTrace through the Decision Fabric.

    The retrieval candidate set is closed before this call. In SHADOW mode the
    original ordering is preserved and only the Decision Trace is attached.
    """
    if trace.get("schema") != "fa3.retrieval-trace.v1":
        raise ValueError("invalid trace")
    fabric = fabric or DecisionFabric()
    adapters = Fa3DecisionAdapters(fabric)
    candidates = []
    by_id: dict[str, dict[str, Any]] = {}
    for row in trace.get("candidates", []):
        cid = str(row.get("candidate_id", "")).strip()
        if not cid:
            raise ValueError("retrieval candidate missing candidate_id")
        by_id[cid] = row
        candidates.append({
            "id": cid,
            "description": f"{row.get('source_id', '')}#{row.get('locator', '')}",
            "metadata": {
                "relevance": float(row.get("score", 0.0)),
                "priority": int(round(float(row.get("score", 0.0)) * 1000000)),
            },
        })
    decision = adapters.knowledge_rerank(
        candidates,
        state={
            "query_plan": trace.get("plan_id"),
            "evidence_refs": trace.get("evidence_refs", []),
        },
        provider_id=provider_id,
    )
    decision["rollout"] = rollout
    out = dict(trace)
    out["decision_rerank_trace"] = decision
    out["decision_rerank_applied"] = False
    if rollout != "ACTIVE" or decision.get("status") != "DECIDED":
        return out
    ranked = (decision.get("result") or {}).get("ranked", [])
    if not isinstance(ranked, list):
        return out
    allowed = set(by_id)
    if any(cid not in allowed for cid in ranked):
        raise ValueError("Decision Fabric attempted retrieval candidate expansion")
    remainder = [cid for cid in by_id if cid not in ranked]
    out["candidates"] = [by_id[cid] for cid in ranked + remainder]
    out["decision_rerank_applied"] = True
    return out
