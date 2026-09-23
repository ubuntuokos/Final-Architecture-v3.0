#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from fa3_decision_fabric import DecisionRequest, ProviderResult, ProviderUnavailable


class JevDecisionProvider:
    provider_id = "FA3-PROVIDER-JEV-DECISION-001"
    semantic = True

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        explicitly_enabled: bool | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.endpoint = endpoint or os.environ.get(
            "FA3_JEV_API_URL", "https://api.typesafe.ai/v1/systemone"
        )
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        self.model = model or os.environ.get("FA3_JEV_MODEL")
        if explicitly_enabled is None:
            explicitly_enabled = os.environ.get("FA3_JEV_ENABLE") == "1"
        self.explicitly_enabled = bool(explicitly_enabled)
        self.timeout = timeout

    def _check_admission(self) -> None:
        if not self.explicitly_enabled:
            raise ProviderUnavailable("Jev provider is not explicitly enabled")
        if not self.api_key:
            raise ProviderUnavailable("Jev credential unavailable")
        if not self.model:
            raise ProviderUnavailable("Jev physical model is intentionally not canonically pinned; FA3_JEV_MODEL required")

    @staticmethod
    def _criteria(request: DecisionRequest) -> dict[str, str]:
        return {
            candidate.id: candidate.description or candidate.id
            for candidate in request.candidates
        }

    def _payload(self, request: DecisionRequest) -> tuple[dict[str, Any], str]:
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
            questions["decision"] = {
                "type": "noul",
                "instructions": purpose,
            }
            mode = "noul"
        elif request.contract == "SCORE":
            levels = request.constraints.get("levels")
            if not isinstance(levels, list) or not 2 <= len(levels) <= 10 or any(not isinstance(x, str) for x in levels):
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
                    "instructions": f"{purpose}. Candidate: {candidate.description or candidate.id}",
                }
            mode = "parallel_noul"
        else:
            raise ValueError(f"unsupported Jev mapping: {request.contract}")

        return {
            "model": self.model,
            "state": state,
            "questions": questions,
        }, mode

    def decide(self, request: DecisionRequest) -> ProviderResult:
        self._check_admission()
        payload, mode = self._payload(request)
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable(f"Jev request failed: {type(exc).__name__}") from exc

        answers = raw.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("Jev response missing answers")

        meta = {
            "remote_model": raw.get("model"),
            "usage": raw.get("usage", {}),
            "external_provider": True,
            "global_promotion_claim": False,
        }

        if mode == "choice":
            ans = answers.get("decision", {})
            chosen = ans.get("choice")
            probabilities = ans.get("probabilities", {})
            return ProviderResult(
                "DECIDED",
                {"selected": chosen},
                float(ans["confidence"]) if isinstance(ans.get("confidence"), (int, float)) else None,
                {k: float(v) for k, v in probabilities.items() if isinstance(v, (int, float))},
                meta,
            )
        if mode == "noul":
            ans = answers.get("decision", {})
            p = ans.get("noul")
            if not isinstance(p, (int, float)):
                raise ValueError("Jev noul answer invalid")
            value = float(p) >= float(request.constraints.get("threshold", 0.5))
            key = "continue" if request.contract == "STOP_CONTINUE" else "value"
            return ProviderResult("DECIDED", {key: value, "probability": float(p)}, None, {}, meta)
        if mode == "score":
            ans = answers.get("decision", {})
            score = ans.get("score")
            if not isinstance(score, (int, float)):
                raise ValueError("Jev score answer invalid")
            probs = ans.get("probabilities", {})
            return ProviderResult(
                "DECIDED",
                {"score": float(score), "legend": ans.get("legend", {})},
                float(ans["confidence"]) if isinstance(ans.get("confidence"), (int, float)) else None,
                {str(k): float(v) for k, v in probs.items() if isinstance(v, (int, float))},
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
            result = {"selected": [cid for cid in ranked if scores[cid] >= threshold]}
        else:
            result = {"ranked": ranked}
        return ProviderResult("DECIDED", result, None, scores, meta)
