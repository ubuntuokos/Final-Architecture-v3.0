#!/usr/bin/env python3
"""Deterministic static validator for the CFA3 Shared Semantic/Ontology foundation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROFILE = "canonical/profiles/FA3-SHARED-SEMANTIC-ONTOLOGY-001.json"
CORE = "canonical/contracts/FA3-SHARED-SEMANTIC-ONTOLOGY-CONTRACTS-001.json"
SDK = "canonical/contracts/FA3-SDK-SEMANTIC-ONTOLOGY-CONTRACTS-001.json"
GUI = "canonical/contracts/FA3-SEMANTIC-STUDIO-GUI-CONTRACTS-001.json"
DECISION = "canonical/decisions/CFA3-DEC-SEMANTIC-ONTOLOGY-FABRIC-2026-10-07.json"
CH_IMPACT = "canonical/current-host-impact/CFA3-CH-IMPACT-SEMANTIC-ONTOLOGY-FABRIC-20261007.json"

FILES = (PROFILE, CORE, SDK, GUI, DECISION, CH_IMPACT)


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load(root: Path, rel: str) -> dict[str, Any]:
    with (root / rel).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{rel}: expected JSON object")
    return data


def validate(root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    errors: list[str] = []
    try:
        profile = _load(root, PROFILE)
        core = _load(root, CORE)
        sdk = _load(root, SDK)
        gui = _load(root, GUI)
        decision = _load(root, DECISION)
        impact = _load(root, CH_IMPACT)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"result": "FAIL", "errors": [str(exc)]}

    expected_ids = {
        PROFILE: "FA3-SHARED-SEMANTIC-ONTOLOGY-001",
        CORE: "FA3-SHARED-SEMANTIC-ONTOLOGY-CONTRACTS-001",
        SDK: "FA3-SDK-SEMANTIC-ONTOLOGY-CONTRACTS-001",
        GUI: "FA3-SEMANTIC-STUDIO-GUI-CONTRACTS-001",
        DECISION: "CFA3-DEC-SEMANTIC-ONTOLOGY-FABRIC-2026-10-07",
        CH_IMPACT: "CFA3-CH-IMPACT-SEMANTIC-ONTOLOGY-FABRIC-20261007",
    }
    loaded = {PROFILE: profile, CORE: core, SDK: sdk, GUI: gui, DECISION: decision, CH_IMPACT: impact}
    for rel, expected in expected_ids.items():
        if loaded[rel].get("id") != expected:
            errors.append(f"{rel}: id mismatch")

    for rel, obj in loaded.items():
        count = obj.get("capability_count", obj.get("capability_baseline"))
        if count != 175:
            errors.append(f"{rel}: capability baseline/count must remain 175")
        if obj.get("new_architectural_authority") is True or obj.get("authority_delta", 0) != 0:
            errors.append(f"{rel}: architectural authority delta must remain zero")
        if obj.get("new_capability") is True or obj.get("capability_delta", 0) != 0:
            errors.append(f"{rel}: capability delta must remain zero")

    if profile.get("contract_family") != core.get("id"):
        errors.append("profile/core contract binding mismatch")
    if profile.get("sdk_contract_family") != sdk.get("id"):
        errors.append("profile/SDK contract binding mismatch")
    if profile.get("gui_contract_family") != gui.get("id"):
        errors.append("profile/GUI contract binding mismatch")

    invariants = set(profile.get("invariants", []))
    for required in (
        "AI_OUTPUT_IS_PROPOSAL_NOT_CANONICAL_TRUTH",
        "NO_DIRECT_AI_TO_CANONICAL_WRITE",
        "NO_SILENT_IDENTITY_MERGE",
        "CLOSE_MATCH_NEVER_ENTERS_IDENTITY_CLOSURE",
        "MODEL_SELECTION_ONLY_VIA_MODEL_ROUTER",
        "NO_SILENT_LOCAL_TO_CLOUD_FALLBACK",
        "CPU_ONLY_PATH_REQUIRED",
    ):
        if required not in invariants:
            errors.append(f"profile: missing invariant {required}")

    semantics = core.get("required_semantics", {})
    if semantics.get("ai_generation") != "PROPOSAL_ONLY":
        errors.append("core: AI generation must remain proposal-only")
    if "IDENTICAL_OR_EXACT_MATCH_ONLY" not in semantics.get("identity_closure", ""):
        errors.append("core: identity closure must be exact/identical-only")
    if semantics.get("close_match") != "NON_MERGING":
        errors.append("core: close_match must remain non-merging")
    if semantics.get("model_routing") != "FA3_AUTH_MODEL_ROUTER_001_ONLY":
        errors.append("core: Model Router must remain exclusive model-routing authority")

    routing = sdk.get("routing_policy", {})
    if routing.get("model_router") != "FA3-AUTH-MODEL-ROUTER-001":
        errors.append("sdk: wrong Model Router binding")
    if routing.get("provider_selection_outside_model_router") != "FORBIDDEN":
        errors.append("sdk: provider selection outside Model Router must be forbidden")
    if routing.get("silent_fallback") != "FORBIDDEN":
        errors.append("sdk: silent fallback must be forbidden")
    if routing.get("cpu_only_reference_path") != "REQUIRED":
        errors.append("sdk: CPU-only reference path must be required")

    namespaces = sdk.get("namespaces", [])
    if len(namespaces) != len(set(namespaces)):
        errors.append("sdk: namespaces must be unique")
    if not all(isinstance(item, str) and item.startswith("cfa3.semantic") for item in namespaces):
        errors.append("sdk: all namespaces must stay under cfa3.semantic")

    gui_requirements = set(gui.get("global_requirements", []))
    if "MANDATORY_GLOBAL_WORKLOAD_MODE_INDICATOR" not in gui_requirements:
        errors.append("gui: global Workload Mode indicator is mandatory")
    if gui.get("identity_review", {}).get("silent_merge") is not False:
        errors.append("gui: silent identity merge must be disabled")
    if gui.get("ai_proposal_review", {}).get("direct_apply_to_canonical") is not False:
        errors.append("gui: AI proposal may not directly apply to canonical ontology")

    blocked = decision.get("blocked_subscope", {})
    if blocked.get("canonical_donor_registry_mutation") != "BLOCKED_BY_ACTIVE_PARALLEL_DONOR_INTAKE":
        errors.append("decision: donor-registry overlap block must remain explicit")
    if blocked.get("l0_l5_materialization") != "BLOCKED_BY_PR_743":
        errors.append("decision: L0-L5 overlap block must remain explicit")

    if impact.get("status") != "NO_RUNTIME_IMPACT":
        errors.append("current-host impact: static foundation must remain NO_RUNTIME_IMPACT")
    if impact.get("physical_current_host_pass_claimed") is not False:
        errors.append("current-host impact: physical PASS must not be claimed")

    return {
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "files_checked": len(FILES),
        "capability_baseline": 175,
        "capability_delta": 0,
        "authority_delta": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = validate(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
