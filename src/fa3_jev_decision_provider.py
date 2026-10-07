#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any, Callable

from fa3_decision_fabric import DecisionRequest, ProviderResult, ProviderUnavailable

MODEL_ROUTER_AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
DEFAULT_LOGICAL_ROUTE = "fa3-decision-jev"


class JevDecisionProvider:
    """Jev semantic adapter bound to the central FA3 Model Router."""

    provider_id = "FA3-PROVIDER-JEV-DECISION-001"
    semantic = True

    def __init__(
        self,
        *,
        logical_route: str = DEFAULT_LOGICAL_ROUTE,
        explicitly_enabled: bool | None = None,
        router_transport: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.logical_route = str(logical_route).strip() or DEFAULT_LOGICAL_ROUTE
        if explicitly_enabled is None:
            explicitly_enabled = os.environ.get("FA3_JEV_ENABLE") == "1"
        self.explicitly_enabled = bool(explicitly_enabled)
        self.router_transport = router_transport

    def _check_admission(self) -> None:
        if not self.explicitly_enabled:
            raise ProviderUnavailable("Jev provider is not explicitly enabled")
        if self.router_transport is None:
            raise ProviderUnavailable(
                "Jev provider requires a central Model Router transport binding"
            )

    @staticmethod
    def _criteria(request: DecisionRequest) -> dict[str, str]:
        return {
            candidate.id: candidate.description or candidate.id
            for candidate in request.candidates
        }

    def _native_request(self, request: DecisionRequest) -> tuple[dict[str, Any], str]:
        state = request.state if request.state is not None else {
            "purpose": request.purpose,
            "policy_context": request.policy_context,
            "constraints": request.constraints,
        }
        purpose = request.purpose
        questions: dict[str, Any] = {}
        if request.contract == "SELECT_ONE":
            questions["decision"] = {
                "type": "choice",
                "instructions": purpose,
                "criteria": self._criteria(request),
            }
            mode = "choice"
        elif request.contract in {"BOOLEAN", "STOP_CONTINUE"}:
            questions["decision"] = {"type": "noul", "instructions": purpose}
            mode = "noul"
        elif request.contract == "SCORE":
            levels = request.constraints.get("levels")
            if (
                not isinstance(levels, list)
                or not 2 <= len(levels) <= 10
                or any(not isinstance(x, str) for x in levels)
            ):
                raise ValueError("Jev SCORE requires 2..10 string levels")
            questions["decision"] = {
                "type": "score",
                "instructions": purpose,
                "criteria": levels,
            }
            mode = "score"
        elif request.contract in {"RANK", "RELEVANCE", "MULTI_LABEL"}:
            for candidate in request.candidates:
                questions[candidate.id] = {
                    "type": "noul",
                    "instructions": (
                        f"{purpose}. Candidate: "
                        f"{candidate.description or candidate.id}"
                    ),
                }
            mode = "parallel_noul"
        else:
            raise ValueError(f"unsupported Jev mapping: {request.contract}")
        return {"state": state, "questions": questions}, mode

    def decide(self, request: DecisionRequest) -> ProviderResult:
        self._check_admission()
        native_request, mode = self._native_request(request)
        envelope = {
            "schema": "fa3.model-router.native-decision-request.v1",
            "authority": MODEL_ROUTER_AUTHORITY,
            "logical_route": self.logical_route,
            "protocol": "jev-systemone-v1",
            "request": native_request,
            "constraints": {
                "physical_provider_selection": "MODEL_ROUTER_ONLY",
                "physical_model_selection": "MODEL_ROUTER_ONLY",
                "silent_fallback": "DENY",
            },
        }
        raw = self.router_transport(envelope)  # type: ignore[misc]
        if not isinstance(raw, dict):
            raise ValueError("Model Router transport must return an object")
        answers = raw.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("Jev response missing answers")
        routing = raw.get("_fa3_routing") or {}
        if not isinstance(routing, dict):
            raise ValueError("invalid Model Router routing receipt")
        if routing.get("authority", MODEL_ROUTER_AUTHORITY) != MODEL_ROUTER_AUTHORITY:
            raise ValueError("Jev transport routing authority mismatch")
        meta = {
            "logical_route": self.logical_route,
            "model_router_authority": MODEL_ROUTER_AUTHORITY,
            "physical_backend_pinned": False,
            "physical_model_pinned": False,
            "routing_receipt_ref": routing.get("receipt_ref"),
            "runtime_provider_id": routing.get("provider_id"),
            "runtime_model_id": routing.get("model_id"),
            "external_provider": bool(routing.get("external_provider", True)),
            "global_promotion_claim": False,
        }
        if mode == "choice":
            ans = answers.get("decision", {})
            probabilities = ans.get("probabilities", {})
            return ProviderResult(
                "DECIDED",
                {"selected": ans.get("choice")},
                float(ans["confidence"])
                if isinstance(ans.get("confidence"), (int, float))
                else None,
                {
                    k: float(v)
                    for k, v in probabilities.items()
                    if isinstance(v, (int, float))
                }
                if isinstance(probabilities, dict)
                else {},
                meta,
            )
        if mode == "noul":
            ans = answers.get("decision", {})
            p = ans.get("noul")
            if not isinstance(p, (int, float)):
                raise ValueError("Jev noul answer invalid")
            value = float(p) >= float(request.constraints.get("threshold", 0.5))
            key = "continue" if request.contract == "STOP_CONTINUE" else "value"
            return ProviderResult(
                "DECIDED", {key: value, "probability": float(p)}, None, {}, meta
            )
        if mode == "score":
            ans = answers.get("decision", {})
            score = ans.get("score")
            if not isinstance(score, (int, float)):
                raise ValueError("Jev score answer invalid")
            probs = ans.get("probabilities", {})
            return ProviderResult(
                "DECIDED",
                {"score": float(score), "legend": ans.get("legend", {})},
                float(ans["confidence"])
                if isinstance(ans.get("confidence"), (int, float))
                else None,
                {
                    str(k): float(v)
                    for k, v in probs.items()
                    if isinstance(v, (int, float))
                }
                if isinstance(probs, dict)
                else {},
                meta,
            )
        scores: dict[str, float] = {}
        for candidate in request.candidates:
            ans = answers.get(candidate.id, {})
            p = ans.get("noul")
            if not isinstance(p, (int, float)):
                raise ValueError(f"Jev parallel noul invalid for {candidate.id}")
            scores[candidate.id] = float(p)
        ranked = sorted(scores, key=lambda cid: (-scores[cid], cid))
        if request.contract == "MULTI_LABEL":
            threshold = float(request.constraints.get("threshold", 0.5))
            result = {
                "selected": [cid for cid in ranked if scores[cid] >= threshold]
            }
        else:
            result = {"ranked": ranked}
        return ProviderResult("DECIDED", result, None, scores, meta)
