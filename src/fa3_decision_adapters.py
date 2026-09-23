#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from fa3_decision_fabric import DecisionFabric


class Fa3DecisionAdapters:
    """Bounded adapters for existing FA3 authorities.

    These helpers only ask for judgment. They never execute the selected action,
    admit a provider/model/agent, acquire a secret, or obtain an HRB lease.
    """

    def __init__(self, fabric: DecisionFabric) -> None:
        self.fabric = fabric

    def knowledge_rerank(self, candidates: list[dict[str, Any]], *, state: Any, provider_id: str) -> dict[str, Any]:
        return self.fabric.decide({
            "contract": "RELEVANCE",
            "purpose": "Rank already-retrieved knowledge evidence by relevance to the current request",
            "candidates": candidates,
            "constraints": {},
            "policy_context": {"authority": "FA3-KNOWLEDGE-001"},
            "evidence_refs": [],
            "state": state,
            "failure_policy": "EXISTING_BEHAVIOR",
            "rollout": "SHADOW",
            "final_policy_owner": "FA3-KNOWLEDGE-001",
        }, provider_id)

    def tool_or_skill_selection(self, candidates: list[dict[str, Any]], *, state: Any, provider_id: str) -> dict[str, Any]:
        return self.fabric.decide({
            "contract": "SELECT_ONE",
            "purpose": "Choose the best fitting pre-authorized tool, skill or specialist for this bounded task",
            "candidates": candidates,
            "constraints": {},
            "policy_context": {"execution_authority": "FA3-UNIFIED-ACTION-FABRIC-001"},
            "evidence_refs": [],
            "state": state,
            "failure_policy": "HUMAN_CONFIRM",
            "rollout": "SHADOW",
            "final_policy_owner": "FA3-UNIFIED-ACTION-FABRIC-001",
        }, provider_id)

    def model_router_advisory(self, candidates: list[dict[str, Any]], *, state: Any, provider_id: str) -> dict[str, Any]:
        return self.fabric.decide({
            "contract": "RANK",
            "purpose": "Rank only the model/provider candidates already admitted by the central Model Router",
            "candidates": candidates,
            "constraints": {},
            "policy_context": {"routing_authority": "FA3-AUTH-MODEL-ROUTER-001"},
            "evidence_refs": [],
            "state": state,
            "failure_policy": "EXISTING_BEHAVIOR",
            "rollout": "SHADOW",
            "final_policy_owner": "FA3-AUTH-MODEL-ROUTER-001",
        }, provider_id)

    def security_risk_signal(self, *, state: Any, levels: list[str], provider_id: str) -> dict[str, Any]:
        return self.fabric.decide({
            "contract": "SCORE",
            "purpose": "Assess semantic risk as evidence for FA3 security policy; do not grant permission",
            "candidates": [],
            "constraints": {"levels": levels},
            "policy_context": {"authority": "FA3-SCS-001", "may_grant_permission": False},
            "evidence_refs": [],
            "state": state,
            "failure_policy": "FAIL_CLOSED",
            "rollout": "SHADOW",
            "final_policy_owner": "FA3-SCS-001",
        }, provider_id)

    def browser_action(self, candidates: list[dict[str, Any]], *, state: Any, provider_id: str) -> dict[str, Any]:
        return self.fabric.decide({
            "contract": "SELECT_ONE",
            "purpose": "Choose one pre-authorized browser/computer-use action from the current observation",
            "candidates": candidates,
            "constraints": {},
            "policy_context": {"execution_after_policy_check": True},
            "evidence_refs": [],
            "state": state,
            "failure_policy": "HUMAN_CONFIRM",
            "rollout": "SHADOW",
            "final_policy_owner": "FA3-WEB-AI-001",
        }, provider_id)

    def voice_completion(self, *, state: Any, provider_id: str, threshold: float = 0.5) -> dict[str, Any]:
        return self.fabric.decide({
            "contract": "BOOLEAN",
            "purpose": "Is the current utterance or command semantically complete?",
            "candidates": [],
            "constraints": {"threshold": threshold},
            "policy_context": {"signal_only": True},
            "evidence_refs": [],
            "state": state,
            "failure_policy": "EXISTING_BEHAVIOR",
            "rollout": "SHADOW",
            "final_policy_owner": "FA3-STT-001",
        }, provider_id)

    def creative_preset(self, candidates: list[dict[str, Any]], *, state: Any, provider_id: str) -> dict[str, Any]:
        return self.fabric.decide({
            "contract": "SELECT_ONE",
            "purpose": "Recommend one pre-defined creative tool/workspace/preset candidate",
            "candidates": candidates,
            "constraints": {},
            "policy_context": {"recommendation_only": True},
            "evidence_refs": [],
            "state": state,
            "failure_policy": "NO_DECISION",
            "rollout": "SHADOW",
            "final_policy_owner": "FA3-CREATIVE-STUDIO",
        }, provider_id)
