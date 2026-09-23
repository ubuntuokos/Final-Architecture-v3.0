#!/usr/bin/env python3
"""Bounded Jev advisory adapter for FA3 Neural Rendering.

The adapter is deliberately not a router, policy authority, workflow engine,
resource broker, executor, or model provider client. If Jev uses a model, the
caller must supply an invocation that has already traversed FA3 Model Router.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

class JevAdvisoryError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

@dataclass(frozen=True)
class JevRequest:
    operation_id: str
    eligible_candidate_ids: tuple[str, ...]
    context_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

def validate_request(request: JevRequest) -> None:
    if not request.operation_id.strip():
        raise JevAdvisoryError("JEV-NR-REQUEST-INVALID", "operation_id is required")
    ids=request.eligible_candidate_ids
    if not ids or len(ids)>32 or len(set(ids))!=len(ids) or any(not x.strip() for x in ids):
        raise JevAdvisoryError("JEV-NR-CANDIDATE-BOUNDARY", "finite unique non-empty candidate set required")
    if len(request.context_refs)>32:
        raise JevAdvisoryError("JEV-NR-CONTEXT-BOUNDARY", "context reference budget exceeded")

def advise(
    request: JevRequest,
    *,
    invoke_via_fa3_model_router: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    validate_request(request)
    allowed=request.eligible_candidate_ids
    if invoke_via_fa3_model_router is None:
        return {
            "implementation":"DETERMINISTIC_NO_JEV_MODEL_CALL",
            "ranked_candidate_ids":list(allowed),
            "authority":False,
            "execution_authorized":False,
            "candidate_expansion":False,
        }
    payload={
        "schema":"fa3.jev.neural-rendering-advisory-request.v1",
        "operation_id":request.operation_id,
        "eligible_candidate_ids":list(allowed),
        "context_refs":list(request.context_refs),
        "provenance_refs":list(request.provenance_refs),
        "evidence_refs":list(request.evidence_refs),
        "instruction":"Return only a complete ordering of the supplied candidate IDs. Do not add candidates, authorize execution, choose hardware, route providers, or request secrets."
    }
    result=invoke_via_fa3_model_router(payload)
    if not isinstance(result,dict):
        raise JevAdvisoryError("JEV-NR-RESULT-INVALID","advisory result must be an object")
    ranked=result.get("ranked_candidate_ids")
    if not isinstance(ranked,list) or len(ranked)!=len(allowed) or len(set(ranked))!=len(ranked) or set(ranked)!=set(allowed):
        raise JevAdvisoryError("JEV-NR-CANDIDATE-EXPANSION","result must be an exact permutation of eligible candidates")
    return {
        "implementation":"JEV_VIA_FA3_MODEL_ROUTER",
        "ranked_candidate_ids":ranked,
        "human_readable_reason":str(result.get("human_readable_reason","bounded Jev advisory ordering")).strip(),
        "authority":False,
        "execution_authorized":False,
        "candidate_expansion":False,
    }
