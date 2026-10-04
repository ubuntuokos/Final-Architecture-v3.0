#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cfa3_development_ai_behavior_guard import RULE_IDS, authorize_action
from fa3_release_baseline import active_capability_count

POLICY = Path("canonical/CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001.json")
DECISION = Path("canonical/decisions/CFA3-DEC-DEVELOPMENT-AI-BEHAVIOR-LAYERING-2026-10-05.json")
GATE_RECORD = Path("canonical/FA3-GATE-CFA3-DEVELOPMENT-AI-BEHAVIOR-001.json")
GATE_REGISTRY = Path("canonical/FA3-GATE-REGISTRY-001.json")
ENFORCEMENT_POLICY = Path("canonical/enforcement-policy.json")
CURRENT_HOST_IMPACT = Path("canonical/current-host-impact/FA3-CH-IMPACT-CFA3-DEVELOPMENT-AI-BEHAVIOR-20261005.json")
GATE_ID = "CFA3-DEVELOPMENT-AI-BEHAVIOR-GATESET-001"

EXPECTED_DEV = {f"DEV-{i:02d}" for i in range(1, 11)}
EXPECTED_AI = {f"AI-{i:02d}" for i in range(1, 11)}
EXPECTED_LAYERS = {"L0", "L1", "L2", "L3", "L4", "L5"}


def _load(root: Path, rel: Path) -> dict[str, Any]:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    required = [POLICY, DECISION, GATE_RECORD, GATE_REGISTRY, ENFORCEMENT_POLICY, CURRENT_HOST_IMPACT]
    missing = [str(p) for p in required if not (root / p).exists()]
    if missing:
        return {
            "schema": "cfa3.development-ai-behavior-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "checks": [{"name": "required-artifacts", "status": "FAIL", "detail": missing}],
        }

    policy = _load(root, POLICY)
    decision = _load(root, DECISION)
    gate_record = _load(root, GATE_RECORD)
    registry = _load(root, GATE_REGISTRY)
    enforcement = _load(root, ENFORCEMENT_POLICY)
    ch = _load(root, CURRENT_HOST_IMPACT)
    active_count = active_capability_count(root)

    dev_ids = {row.get("id") for row in policy.get("development_rules", [])}
    ai_ids = {row.get("id") for row in policy.get("ai_behavior_rules", [])}
    layer_ids = {row.get("level") for row in policy.get("layers", [])}

    overlap_ctx = {
        "action": "WRITE",
        "current_owner_restriction_allows": True,
        "scope_bound": True,
        "scope_allows_action": True,
        "uncertain_state": False,
        "blocker_kind": "OVERLAP",
        "autonomous_workaround": False,
        "fresh_state_verified": True,
        "mutation_report_pending": False,
        "side_effect_permission": "WRITE",
        "silent_redesign_or_repair": False,
    }
    overlap_stop = authorize_action(overlap_ctx)
    overlap_ctx["owner_override"] = {
        "rule_ids": ["DEV-05", "AI-01"],
        "explicit": True,
        "conversation_bound": True,
        "scope_matches": True,
    }
    overlap_override = authorize_action(overlap_ctx)

    checks = {
        "canonical-policy": policy.get("id") == "CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001"
            and policy.get("status") == "CANONICAL"
            and policy.get("priority") == "P0",
        "development-and-product-scope": policy.get("scope", {}).get("development_process") is True
            and policy.get("scope", {}).get("cfa3_ai_models") is True
            and policy.get("scope", {}).get("cfa3_agents") is True,
        "exact-development-rules": dev_ids == EXPECTED_DEV,
        "exact-ai-rules": ai_ids == EXPECTED_AI,
        "guard-rule-set": RULE_IDS == EXPECTED_DEV | EXPECTED_AI,
        "layer-model": layer_ids == EXPECTED_LAYERS
            and policy.get("composition", {}).get("layers_are_distinct") is True
            and policy.get("composition", {}).get("contradiction_result") == "BLOCKER",
        "pending-pr-not-authority": policy.get("composition", {}).get("pending_pr_is_not_canonical_authority") is True
            and decision.get("pending_pr_semantics", {}).get("listed_prs_are_canonical_authority") is False,
        "owner-override-bounded": policy.get("owner_override", {}).get("explicit_only") is True
            and policy.get("owner_override", {}).get("conversation_bounded") is True
            and policy.get("owner_override", {}).get("not_inferred_from_generic_approval") is True,
        "overlap-default-stop": overlap_stop.get("decision") == "STOP"
            and "DEV-05" in overlap_stop.get("rule_ids", []),
        "overlap-explicit-override": overlap_override.get("decision") == "ALLOW",
        "decision-binding": decision.get("policy_id") == policy.get("id")
            and decision.get("status") == "CANONICAL_CLOSED",
        "baseline-preserved": policy.get("capability_baseline") == active_count
            and decision.get("capability_count_after") == active_count
            and policy.get("capability_delta") == 0
            and policy.get("architectural_authority_delta") == 0,
        "gate-record": gate_record.get("id") == "FA3-GATE-CFA3-DEVELOPMENT-AI-BEHAVIOR-001"
            and gate_record.get("enforcement_id") == GATE_ID
            and gate_record.get("fail_closed") is True,
        "global-gate-membership": GATE_ID in registry.get("mandatory_reference_gates", [])
            and registry.get("mandatory_reference_gates", []) == enforcement.get("mandatory_reference_gates", []),
        "current-host-boundary": ch.get("physical_requalification_required") is False
            and ch.get("current_host_runtime_promotion_claim") is False
            and ch.get("historical_evidence_reused") is False,
    }

    passed = all(checks.values())
    return {
        "schema": "cfa3.development-ai-behavior-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if passed else "FAIL",
        "capability_count": active_count,
        "checks": [
            {"name": name, "status": "PASS" if value else "FAIL"}
            for name, value in checks.items()
        ],
        "current_host_runtime_promotion_claim": False,
    }


def gate(root: Path) -> dict[str, Any]:
    return evaluate(root)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = evaluate(root)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
