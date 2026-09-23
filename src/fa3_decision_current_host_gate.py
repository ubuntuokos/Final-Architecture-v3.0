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

    no_accelerator_requirement = all(
        token not in (root / "canonical/profiles/FA3-DECISION-FABRIC-001.json").read_text(encoding="utf-8")
        for token in ('"global_gpu_requirement": true', '"cuda_required": true', '"rocm_required": true')
    )
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
