#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from fa3_decision_fabric import DecisionRequest, ProviderResult, ProviderUnavailable


class LocalSemanticDecisionProvider:
    provider_id = "FA3-PROVIDER-DECISION-LOCAL-001"
    semantic = True

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        logical_route: str = "fa3-text-primary",
        token: str | None = None,
        credential_file: str | None = None,
        explicitly_enabled: bool | None = None,
        timeout: float = 30.0,
        transport: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.endpoint = endpoint or os.environ.get(
            "FA3_MODEL_ROUTER_CHAT_URL", "http://127.0.0.1:4000/v1/chat/completions"
        )
        self.logical_route = logical_route
        self.token = token
        self.credential_file = credential_file or os.environ.get("FA3_MODEL_ROUTER_MASTER_KEY_FILE")
        if explicitly_enabled is None:
            explicitly_enabled = os.environ.get("FA3_DECISION_LOCAL_ENABLE") == "1"
        self.explicitly_enabled = bool(explicitly_enabled)
        self.timeout = timeout
        self.transport = transport

    def _credential(self) -> str:
        if self.token:
            return self.token
        if not self.credential_file:
            raise ProviderUnavailable("Model Router credential projection unavailable")
        path = Path(self.credential_file).expanduser()
        if not path.is_file():
            raise ProviderUnavailable("Model Router credential file unavailable")
        return path.read_text(encoding="utf-8").strip()

    def _request_payload(self, request: DecisionRequest) -> dict[str, Any]:
        candidates = [
            {"id": c.id, "description": c.description, "metadata": c.metadata}
            for c in request.candidates
        ]
        instruction = {
            "contract": request.contract,
            "purpose": request.purpose,
            "candidates": candidates,
            "constraints": request.constraints,
            "state": request.state,
            "rules": {
                "candidate_ids_must_come_only_from_candidates": True,
                "do_not_execute": True,
                "do_not_add_candidates": True,
                "return_json_only": True,
            },
            "output_shapes": {
                "SELECT_ONE": {"selected": "candidate-id"},
                "RANK": {"ranked": ["candidate-id"]},
                "RELEVANCE": {"ranked": ["candidate-id"], "scores": {"candidate-id": 0.0}},
                "MULTI_LABEL": {"selected": ["candidate-id"]},
                "BOOLEAN": {"value": True, "confidence": 0.0},
                "STOP_CONTINUE": {"continue": True, "confidence": 0.0},
                "SCORE": {"score": 0.0, "confidence": 0.0},
            },
        }
        return {
            "model": self.logical_route,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an FA3 bounded decision provider. Return only one JSON object matching the requested output shape. Never invent candidate IDs and never execute actions.",
                },
                {
                    "role": "user",
                    "content": json.dumps(instruction, ensure_ascii=False, sort_keys=True),
                },
            ],
            "temperature": 0,
        }

    def _http(self, payload: dict[str, Any]) -> dict[str, Any]:
        credential = self._credential()
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {credential}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable(f"central Model Router call failed: {type(exc).__name__}") from exc

    @staticmethod
    def _extract_json(raw: dict[str, Any]) -> dict[str, Any]:
        choices = raw.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Model Router response missing choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise ValueError("Model Router response missing text content")
        content = content.strip()
        try:
            value = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError("semantic decision response is not JSON")
            value = json.loads(match.group(0))
        if not isinstance(value, dict):
            raise ValueError("semantic decision result must be object")
        return value

    def decide(self, request: DecisionRequest) -> ProviderResult:
        if not self.explicitly_enabled:
            raise ProviderUnavailable("local semantic decision provider not explicitly enabled")
        payload = self._request_payload(request)
        raw = self.transport(payload) if self.transport is not None else self._http(payload)
        result = self._extract_json(raw)
        confidence = result.pop("confidence", None)
        scores = result.pop("scores", {})
        if scores is None:
            scores = {}
        if not isinstance(scores, dict):
            raise ValueError("scores must be object")
        return ProviderResult(
            "DECIDED",
            result,
            float(confidence) if isinstance(confidence, (int, float)) else None,
            {str(k): float(v) for k, v in scores.items() if isinstance(v, (int, float))},
            {
                "logical_route": self.logical_route,
                "model_router_authority": "FA3-AUTH-MODEL-ROUTER-001",
                "physical_backend_pinned": False,
                "physical_model_pinned": False,
                "external_provider": False,
            },
        )
