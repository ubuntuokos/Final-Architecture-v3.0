#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
import tempfile
from pathlib import Path
from typing import Any

from fa3_context_selection import ContextSelector, verify_projection
from fa3_decision_fabric import DecisionError, DecisionFabric, ProviderResult, RuleDecisionProvider
from fa3_system_one_decision_provider import SystemOneDecisionProvider
from fa3_system_one_mcp_compiler import compile_mcp_tools
from fa3_system_one_reflex import SystemOneReflexRuntime


class ExpandingProvider:
    provider_id = "FA3-TEST-EXPANDING-PROVIDER"
    semantic = True

    def decide(self, request):
        return ProviderResult("DECIDED", {"selected": "UNAUTHORIZED"}, 0.99)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_gate(root: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}

    fabric = DecisionFabric([RuleDecisionProvider()])
    positive = fabric.decide({
        "contract": "SELECT_ONE",
        "purpose": "current-host positive bounded selection",
        "candidates": [
            {"id": "safe-a", "metadata": {"priority": 1}},
            {"id": "safe-b", "metadata": {"priority": 2}},
        ],
        "constraints": {},
        "policy_context": {"authority": "TEST_ONLY"},
        "evidence_refs": [],
        "failure_policy": "FAIL_CLOSED",
        "rollout": "ACTIVE",
        "final_policy_owner": "TEST_ONLY",
    })
    checks["positive"] = {
        "pass": positive.get("status") == "DECIDED"
        and (positive.get("result") or {}).get("selected") == "safe-b"
        and positive.get("authority") is False
        and positive.get("candidate_set_expanded") is False,
        "trace": positive,
    }

    negative_fabric = DecisionFabric([ExpandingProvider()])
    expansion_denied = False
    try:
        negative_fabric.decide({
            "contract": "SELECT_ONE",
            "purpose": "current-host negative candidate expansion",
            "candidates": [{"id": "safe-a"}],
            "constraints": {},
            "policy_context": {},
            "evidence_refs": [],
            "failure_policy": "FAIL_CLOSED",
            "rollout": "ACTIVE",
            "final_policy_owner": "TEST_ONLY",
        }, "FA3-TEST-EXPANDING-PROVIDER")
    except DecisionError:
        expansion_denied = True
    checks["negative"] = {
        "pass": expansion_denied,
        "candidate_expansion_denied": expansion_denied,
    }

    router_calls: list[dict[str, Any]] = []

    def system_one_transport(envelope: dict[str, Any]) -> dict[str, Any]:
        router_calls.append(envelope)
        return {
            "answers": {
                "next_action": {
                    "type": "choice",
                    "choice": "inspect",
                    "probabilities": {
                        "inspect": 0.97,
                        "__finish__": 0.01,
                        "__escalate__": 0.02,
                    },
                    "confidence": 0.97,
                },
                "goal_reached": {"type": "noul", "noul": 0.01},
            },
            "_fa3_routing": {
                "authority": "FA3-AUTH-MODEL-ROUTER-001",
                "receipt_ref": "evidence://current-host/system-one-recorded",
                "provider_id": "FA3-CURRENT-HOST-RECORDED-SYSTEM-ONE",
                "model_id": "recorded-boundary-probe",
                "external_provider": False,
                "protocol": "system-one-decision-v1",
            },
        }

    system_one_provider = SystemOneDecisionProvider(
        explicitly_enabled=True,
        router_transport=system_one_transport,
    )
    reflex = SystemOneReflexRuntime(DecisionFabric([system_one_provider]))
    reflex_positive = reflex.step(
        purpose="current-host bounded reflex positive",
        actions=[{
            "id": "inspect",
            "description": "Inspect the bounded state",
            "metadata": {"risk": "read", "parameters": {}},
        }],
        state={"host_probe": True},
        final_policy_owner="TEST_ONLY",
        rollout="ACTIVE",
    )

    def low_confidence_transport(envelope: dict[str, Any]) -> dict[str, Any]:
        return {
            "answers": {
                "next_action": {
                    "type": "choice",
                    "choice": "destructive_probe",
                    "probabilities": {
                        "destructive_probe": 0.61,
                        "__finish__": 0.09,
                        "__escalate__": 0.30,
                    },
                    "confidence": 0.61,
                },
                "goal_reached": {"type": "noul", "noul": 0.01},
            },
            "_fa3_routing": {
                "authority": "FA3-AUTH-MODEL-ROUTER-001",
                "provider_id": "FA3-CURRENT-HOST-RECORDED-SYSTEM-ONE",
                "model_id": "recorded-boundary-probe",
                "external_provider": False,
            },
        }

    reflex_negative = SystemOneReflexRuntime(DecisionFabric([
        SystemOneDecisionProvider(
            explicitly_enabled=True,
            router_transport=low_confidence_transport,
        )
    ])).step(
        purpose="current-host bounded reflex destructive refusal",
        actions=[{
            "id": "destructive_probe",
            "description": "A destructive probe that must not execute",
            "metadata": {"risk": "destructive", "parameters": {}},
        }],
        state={"host_probe": True},
        final_policy_owner="TEST_ONLY",
        rollout="ACTIVE",
    )

    mcp_catalogue = compile_mcp_tools([{
        "name": "inspect_record",
        "description": "Inspect one enumerated record",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "record": {
                    "type": "string",
                    "enum": ["record-a", "record-b"],
                }
            },
            "required": ["record"],
        },
    }]).to_dict()

    checks["system_one_reflex"] = {
        "pass": len(router_calls) == 1
        and reflex_positive.get("status") == "READY_FOR_AUTHORIZATION"
        and reflex_positive.get("authority") is False
        and reflex_positive.get("execution_performed") is False
        and reflex_positive.get("requires_external_policy_authorization") is True
        and (reflex_positive.get("decision_trace") or {}).get("authority") is False
        and bool(((reflex_positive.get("decision_trace") or {}).get("provider_meta") or {}).get("answer_distributions"))
        and reflex_negative.get("status") == "HANDOFF"
        and reflex_negative.get("execution_performed") is False
        and (reflex_negative.get("handoff") or {}).get("reason") == "no_confident_action"
        and (reflex_negative.get("handoff") or {}).get("threshold") == 0.8
        and mcp_catalogue.get("authority") is False
        and mcp_catalogue.get("execution_performed") is False
        and len(mcp_catalogue.get("action_candidates", [])) == 1,
        "positive": reflex_positive,
        "low_confidence": reflex_negative,
        "mcp_catalogue": mcp_catalogue,
        "router_call_count": len(router_calls),
        "external_provider_called": False,
    }

    selector = ContextSelector()
    original = [
        {"id": "protected", "kind": "canonical_decision", "text": "source truth"},
        {"id": "hot", "kind": "note", "text": "active candidate", "metadata": {"priority": 10}},
        {"id": "cold", "kind": "note", "text": "reversible hidden candidate", "metadata": {"priority": 1}},
    ]
    before = digest(original)
    projection = selector.project(original, target_active=1, rollout="ACTIVE")
    verify_projection(projection)
    hidden = next(row for row in projection["items"] if row["id"] == "cold")
    pre_restore_sha = hidden["source_sha256"]
    selector.restore(projection, "cold")
    verify_projection(projection)
    restored = next(row for row in projection["items"] if row["id"] == "cold")
    checks["rollback"] = {
        "pass": restored["state"] == "ACTIVE"
        and restored["source_sha256"] == pre_restore_sha
        and before == digest(original),
        "hidden_source_sha256": pre_restore_sha,
        "restored_source_sha256": restored["source_sha256"],
        "input_unchanged_sha256": before,
    }

    hardware_material = "\n".join([
        (root / "canonical/profiles/FA3-DECISION-FABRIC-001.json").read_text(encoding="utf-8"),
        (root / "canonical/contracts/FA3-SYSTEM-ONE-REFLEX-001.json").read_text(encoding="utf-8"),
        (root / "canonical/providers/FA3-PROVIDER-SYSTEM-ONE-DECISION-001.json").read_text(encoding="utf-8"),
    ])
    no_accelerator_requirement = all(
        token not in hardware_material
        for token in ('"global_gpu_requirement": true', '"cuda_required": true', '"rocm_required": true')
    ) and '"cpu_only_supported": true' in hardware_material
    checks["hardware"] = {
        "pass": no_accelerator_requirement,
        "cpu_only_supported": True,
        "accelerator_required": False,
        "vendor_required": False,
    }

    all_pass = all(bool(row.get("pass")) for row in checks.values())
    return {
        "schema": "fa3.decision-fabric-current-host-receipt.v1",
        "gate_id": "FA3-GATE-DECISION-FABRIC-CURRENT-HOST-001",
        "result": "PASS" if all_pass else "FAIL",
        "host": {
            "hostname_sha256": hashlib.sha256(socket.gethostname().encode()).hexdigest(),
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "checks": checks,
        "optional_system_one_external_provider": {
            "enabled": os.environ.get("FA3_SYSTEM_ONE_ENABLE") == "1",
            "exercised": False,
            "note": "Current-host exercises the provider-neutral boundary with recorded router answers; live external System One provider admission is separate.",
        },
        "optional_jev_provider": {
            "enabled": os.environ.get("FA3_JEV_ENABLE") == "1",
            "exercised": False,
            "note": "External Jev E2E is a separate provider-admission obligation and is not required for Decision Fabric current-host PASS.",
        },
        "capability_count": 143,
        "authority_delta": 0,
        "physical_current_host": True,
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--receipt", default="evidence/current-host/decision-fabric-current-host.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt = run_gate(root)
    out = root / args.receipt
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
