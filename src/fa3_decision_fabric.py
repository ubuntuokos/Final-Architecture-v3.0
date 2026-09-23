#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

CONTRACTS = {
    "SELECT_ONE", "BOOLEAN", "SCORE", "RANK",
    "MULTI_LABEL", "RELEVANCE", "STOP_CONTINUE",
}
FAILURE_POLICIES = {
    "FAIL_CLOSED", "RULE_FALLBACK", "EXISTING_BEHAVIOR",
    "HUMAN_CONFIRM", "NO_DECISION",
}
ROLLOUT_STATES = {"SHADOW", "ADVISORY", "ACTIVE"}


class DecisionError(RuntimeError):
    pass


class ProviderUnavailable(DecisionError):
    pass


@dataclass(frozen=True)
class Candidate:
    id: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_value(value: str | dict[str, Any]) -> "Candidate":
        if isinstance(value, str):
            if not value:
                raise DecisionError("candidate id must not be empty")
            return Candidate(id=value)
        if not isinstance(value, dict):
            raise DecisionError("candidate must be string or object")
        cid = value.get("id")
        if not isinstance(cid, str) or not cid:
            raise DecisionError("candidate object requires non-empty id")
        desc = value.get("description", "")
        if not isinstance(desc, str):
            raise DecisionError("candidate description must be string")
        metadata = value.get("metadata", {})
        if not isinstance(metadata, dict):
            raise DecisionError("candidate metadata must be object")
        return Candidate(id=cid, description=desc, metadata=dict(metadata))


@dataclass
class DecisionRequest:
    contract: str
    purpose: str
    candidates: list[Candidate]
    constraints: dict[str, Any] = field(default_factory=dict)
    policy_context: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    state: Any = None
    failure_policy: str = "NO_DECISION"
    rollout: str = "SHADOW"
    final_policy_owner: str = ""

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DecisionRequest":
        if not isinstance(data, dict):
            raise DecisionError("decision request must be object")
        contract = data.get("contract")
        if contract not in CONTRACTS:
            raise DecisionError(f"unsupported contract: {contract!r}")
        purpose = data.get("purpose")
        if not isinstance(purpose, str) or not purpose.strip():
            raise DecisionError("purpose is required")
        raw_candidates = data.get("candidates", [])
        if not isinstance(raw_candidates, list):
            raise DecisionError("candidates must be list")
        candidates = [Candidate.from_value(v) for v in raw_candidates]
        ids = [c.id for c in candidates]
        if len(ids) != len(set(ids)):
            raise DecisionError("candidate ids must be unique")
        if contract in {"SELECT_ONE", "RANK", "MULTI_LABEL", "RELEVANCE"} and not candidates:
            raise DecisionError(f"{contract} requires candidates")
        failure_policy = data.get("failure_policy", "NO_DECISION")
        if failure_policy not in FAILURE_POLICIES:
            raise DecisionError("invalid failure policy")
        rollout = data.get("rollout", "SHADOW")
        if rollout not in ROLLOUT_STATES:
            raise DecisionError("invalid rollout state")
        constraints = data.get("constraints", {})
        policy_context = data.get("policy_context", {})
        evidence_refs = data.get("evidence_refs", [])
        if not isinstance(constraints, dict) or not isinstance(policy_context, dict):
            raise DecisionError("constraints/policy_context must be objects")
        if not isinstance(evidence_refs, list) or any(not isinstance(x, str) for x in evidence_refs):
            raise DecisionError("evidence_refs must be string list")
        owner = data.get("final_policy_owner", "")
        if not isinstance(owner, str):
            raise DecisionError("final_policy_owner must be string")
        return DecisionRequest(
            contract=contract,
            purpose=purpose,
            candidates=candidates,
            constraints=dict(constraints),
            policy_context=dict(policy_context),
            evidence_refs=list(evidence_refs),
            state=data.get("state"),
            failure_policy=failure_policy,
            rollout=rollout,
            final_policy_owner=owner,
        )


@dataclass
class ProviderResult:
    status: str
    result: Any
    confidence: float | None = None
    scores: dict[str, float] = field(default_factory=dict)
    provider_meta: dict[str, Any] = field(default_factory=dict)


class DecisionProvider(Protocol):
    provider_id: str
    semantic: bool

    def decide(self, request: DecisionRequest) -> ProviderResult:
        ...


class RuleDecisionProvider:
    provider_id = "FA3-PROVIDER-DECISION-RULES-001"
    semantic = False

    def decide(self, request: DecisionRequest) -> ProviderResult:
        if request.contract == "SELECT_ONE":
            chosen = max(
                request.candidates,
                key=lambda c: (int(c.metadata.get("priority", 0)), c.id),
            )
            return ProviderResult("DECIDED", {"selected": chosen.id}, 1.0)
        if request.contract == "RANK":
            ordered = sorted(
                request.candidates,
                key=lambda c: (-int(c.metadata.get("priority", 0)), c.id),
            )
            return ProviderResult("DECIDED", {"ranked": [c.id for c in ordered]}, 1.0)
        if request.contract == "RELEVANCE":
            scores = {
                c.id: float(c.metadata.get("relevance", c.metadata.get("score", 0.0)))
                for c in request.candidates
            }
            ordered = sorted(scores, key=lambda x: (-scores[x], x))
            return ProviderResult("DECIDED", {"ranked": ordered}, 1.0, scores=scores)
        if request.contract == "MULTI_LABEL":
            selected = [
                c.id for c in request.candidates
                if bool(c.metadata.get("selected", False))
            ]
            return ProviderResult("DECIDED", {"selected": selected}, 1.0)
        if request.contract in {"BOOLEAN", "STOP_CONTINUE"}:
            value = request.constraints.get("value")
            if not isinstance(value, bool):
                return ProviderResult("NO_DECISION", None)
            key = "continue" if request.contract == "STOP_CONTINUE" else "value"
            return ProviderResult("DECIDED", {key: value}, 1.0)
        if request.contract == "SCORE":
            value = request.constraints.get("score")
            if not isinstance(value, (int, float)):
                return ProviderResult("NO_DECISION", None)
            lo = float(request.constraints.get("min", 0.0))
            hi = float(request.constraints.get("max", 1.0))
            score = min(max(float(value), lo), hi)
            return ProviderResult("DECIDED", {"score": score}, 1.0)
        raise DecisionError("unreachable contract")


def _candidate_digest(request: DecisionRequest) -> str:
    payload = [
        {"id": c.id, "description": c.description, "metadata": c.metadata}
        for c in request.candidates
    ]
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _selected_ids(result: Any) -> set[str]:
    if not isinstance(result, dict):
        return set()
    out: set[str] = set()
    selected = result.get("selected")
    if isinstance(selected, str):
        out.add(selected)
    elif isinstance(selected, list):
        out.update(x for x in selected if isinstance(x, str))
    ranked = result.get("ranked")
    if isinstance(ranked, list):
        out.update(x for x in ranked if isinstance(x, str))
    return out


class DecisionFabric:
    def __init__(self, providers: list[DecisionProvider] | None = None) -> None:
        self.providers: dict[str, DecisionProvider] = {}
        for provider in providers or [RuleDecisionProvider()]:
            self.register(provider)

    def register(self, provider: DecisionProvider) -> None:
        if not getattr(provider, "provider_id", ""):
            raise DecisionError("provider_id required")
        self.providers[provider.provider_id] = provider

    def decide(self, request_data: dict[str, Any], provider_id: str = "FA3-PROVIDER-DECISION-RULES-001") -> dict[str, Any]:
        request = DecisionRequest.from_dict(request_data)
        provider = self.providers.get(provider_id)
        if provider is None:
            return self._failure(request, provider_id, ProviderUnavailable("provider unavailable"))

        started = time.monotonic()
        try:
            provider_result = provider.decide(request)
        except Exception as exc:
            return self._failure(request, provider_id, exc, started)

        allowed = {c.id for c in request.candidates}
        selected = _selected_ids(provider_result.result)
        expansion = bool(selected - allowed)
        if expansion:
            raise DecisionError("provider attempted candidate-set expansion")

        if provider_result.status not in {
            "DECIDED", "NO_DECISION", "HUMAN_CONFIRM", "DENIED", "PROVIDER_UNAVAILABLE"
        }:
            raise DecisionError("provider returned invalid status")

        trace = {
            "schema": "fa3.decision-trace.v1",
            "decision_id": str(uuid.uuid4()),
            "contract": request.contract,
            "purpose": request.purpose,
            "provider": provider_id,
            "semantic_provider": bool(getattr(provider, "semantic", False)),
            "rollout": request.rollout,
            "status": provider_result.status,
            "result": provider_result.result,
            "confidence": provider_result.confidence,
            "scores": provider_result.scores,
            "candidate_count": len(request.candidates),
            "candidate_digest_sha256": _candidate_digest(request),
            "candidate_set_expanded": False,
            "authority": False,
            "final_policy_owner": request.final_policy_owner,
            "evidence_refs": request.evidence_refs,
            "latency_ms": round((time.monotonic() - started) * 1000.0, 3),
            "provider_meta": provider_result.provider_meta,
            "global_promotion_claim": False,
        }
        return trace

    def _failure(
        self,
        request: DecisionRequest,
        provider_id: str,
        exc: Exception,
        started: float | None = None,
    ) -> dict[str, Any]:
        latency = 0.0 if started is None else round((time.monotonic() - started) * 1000.0, 3)
        if request.failure_policy == "FAIL_CLOSED":
            status = "DENIED"
        elif request.failure_policy == "HUMAN_CONFIRM":
            status = "HUMAN_CONFIRM"
        elif request.failure_policy in {"RULE_FALLBACK", "EXISTING_BEHAVIOR", "NO_DECISION"}:
            status = "NO_DECISION"
        else:
            status = "PROVIDER_UNAVAILABLE"
        return {
            "schema": "fa3.decision-trace.v1",
            "decision_id": str(uuid.uuid4()),
            "contract": request.contract,
            "purpose": request.purpose,
            "provider": provider_id,
            "semantic_provider": False,
            "rollout": request.rollout,
            "status": status,
            "result": None,
            "confidence": None,
            "scores": {},
            "candidate_count": len(request.candidates),
            "candidate_digest_sha256": _candidate_digest(request),
            "candidate_set_expanded": False,
            "authority": False,
            "final_policy_owner": request.final_policy_owner,
            "evidence_refs": request.evidence_refs,
            "latency_ms": latency,
            "failure_policy": request.failure_policy,
            "error_class": type(exc).__name__,
            "global_promotion_claim": False,
        }
