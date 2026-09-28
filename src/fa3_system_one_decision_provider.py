#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any, Callable

from fa3_decision_fabric import DecisionRequest, ProviderResult, ProviderUnavailable
from fa3_system_one_reflex import compile_system_one_step, evaluate_system_one_answers

MODEL_ROUTER_AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
DEFAULT_LOGICAL_ROUTE = "fa3-decision-system-one"


class SystemOneDecisionProvider:
    """Provider-neutral System One transport bound exclusively to the FA3 Model Router."""

    provider_id = "FA3-PROVIDER-SYSTEM-ONE-DECISION-001"
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
            explicitly_enabled = os.environ.get("FA3_SYSTEM_ONE_ENABLE") == "1"
        self.explicitly_enabled = bool(explicitly_enabled)
        self.router_transport = router_transport

    def _check_admission(self) -> None:
        if not self.explicitly_enabled:
            raise ProviderUnavailable("System One provider is not explicitly enabled")
        if self.router_transport is None:
            raise ProviderUnavailable("System One provider requires central Model Router transport")

    def decide(self, request: DecisionRequest) -> ProviderResult:
        self._check_admission()
        if request.contract != "BOUNDED_ACTION":
            raise ValueError("System One provider only accepts BOUNDED_ACTION")

        compiled = compile_system_one_step(request)
        envelope = {
            "schema": "fa3.model-router.native-decision-request.v1",
            "authority": MODEL_ROUTER_AUTHORITY,
            "logical_route": self.logical_route,
            "protocol": "system-one-decision-v1",
            "request": {
                "state": request.state if request.state is not None else {
                    "purpose": request.purpose,
                    "policy_context": request.policy_context,
                },
                "questions": compiled.questions,
            },
            "constraints": {
                "physical_provider_selection": "MODEL_ROUTER_ONLY",
                "physical_model_selection": "MODEL_ROUTER_ONLY",
                "resource_placement": "HRB_ONLY",
                "secret_resolution": "SECRET_BROKER_ONLY",
                "silent_fallback": "DENY",
            },
        }
        raw = self.router_transport(envelope)  # type: ignore[misc]
        if not isinstance(raw, dict):
            raise ValueError("Model Router transport must return an object")
        answers = raw.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("System One response missing answers")
        routing = raw.get("_fa3_routing") or {}
        if not isinstance(routing, dict):
            raise ValueError("invalid Model Router routing receipt")
        if routing.get("authority", MODEL_ROUTER_AUTHORITY) != MODEL_ROUTER_AUTHORITY:
            raise ValueError("System One transport routing authority mismatch")

        result = evaluate_system_one_answers(request, compiled, answers)
        result.provider_meta.update({
            "logical_route": self.logical_route,
            "model_router_authority": MODEL_ROUTER_AUTHORITY,
            "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "physical_backend_pinned": False,
            "physical_model_pinned": False,
            "routing_receipt_ref": routing.get("receipt_ref"),
            "runtime_provider_id": routing.get("provider_id"),
            "runtime_model_id": routing.get("model_id"),
            "external_provider": bool(routing.get("external_provider", False)),
            "served_protocol": routing.get("protocol", "system-one-decision-v1"),
            "global_promotion_claim": False,
        })
        return result
