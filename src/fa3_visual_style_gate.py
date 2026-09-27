#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Callable

from fa3_release_baseline import module_active_capability_count
from fa3_visual_style import (
    HRB_AUTHORITY,
    MODEL_ROUTER_AUTHORITY,
    VisualStyleDenied,
    build_style_dna,
    build_visual_intent,
    normalize_recipe,
    validate_consumer_binding,
)

PROFILE = "canonical/profiles/FA3-VISUAL-STYLE-FABRIC-001.json"
CONTRACT = "canonical/contracts/FA3-VISUAL-STYLE-FABRIC-CONTRACTS-001.json"
ENFORCEMENT = "canonical/visual-style-fabric-enforcement.json"
BINDINGS = "canonical/visual-style-consumer-bindings.json"
DECISION = "canonical/decisions/FA3-DEC-VISUAL-STYLE-FABRIC-2026-09-27.json"
REFERENCE = "canonical/references/FA3-REF-AI-VISUAL-PROMPT-COOKBOOK-001.json"
INTENT = "canonical/intents/FA3-VISUAL-STYLE-FABRIC-APPLICATION-INTENT-001.json"
ASSESSMENT = "canonical/assessments/FA3-VISUAL-STYLE-FABRIC-REUSE-ASSESSMENT-001.json"
GATE_ID = "FA3-GATE-VISUAL-STYLE-FABRIC-001"


def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def denied(call: Callable[[], object]) -> bool:
    try:
        call()
    except VisualStyleDenied:
        return True
    return False


def validate(root: Path | None = None) -> list[str]:
    if root is None:
        root = Path(__file__).resolve().parents[1]

    profile = loadj(root, PROFILE)
    contract = loadj(root, CONTRACT)
    enforcement = loadj(root, ENFORCEMENT)
    bindings = loadj(root, BINDINGS)
    decision = loadj(root, DECISION)
    reference = loadj(root, REFERENCE)
    intent = loadj(root, INTENT)
    assessment = loadj(root, ASSESSMENT)

    count = module_active_capability_count(__file__)
    failures: list[str] = []

    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)

    rules = set(enforcement.get("rules", []))
    invariants = set(contract.get("invariants", []))
    check("baseline-stable", profile.get("capability_count") == contract.get("capability_count") == enforcement.get("capability_count") == decision.get("capability_count_after") == count)
    check("no-new-capability", profile.get("new_capability") is False and contract.get("new_capability") is False and enforcement.get("new_capabilities") == 0 and decision.get("capability_delta") == 0 and intent.get("declared_new_capabilities") == [] and assessment.get("new_capabilities") == 0)
    check("no-new-authority", profile.get("new_architectural_authority") is False and contract.get("new_architectural_authority") is False and enforcement.get("new_architectural_authorities") == 0 and decision.get("authority_delta") == 0 and intent.get("proposed_authority_roles") == [] and assessment.get("new_architectural_authorities") == 0)
    check("fail-closed-rules", enforcement.get("fail_closed") is True and len(rules) == enforcement.get("mandatory_rule_count") == len(invariants) and rules == invariants)
    check("router-authority", profile.get("authority", {}).get("model_routing") == MODEL_ROUTER_AUTHORITY)
    check("resource-authority", profile.get("authority", {}).get("resource_admission") == HRB_AUTHORITY)
    check("no-fixed-route", profile.get("routing", {}).get("fixed_provider_allowed") is False and profile.get("routing", {}).get("fixed_model_allowed") is False and profile.get("routing", {}).get("fixed_runtime_allowed") is False and profile.get("routing", {}).get("silent_fallback_allowed") is False)
    check("upstream-pin", reference.get("upstream", {}).get("commit") == "d320e7a99819a54da6ff56abbc19a83fb6741772" and reference.get("upstream", {}).get("catalog_cardinality_policy") == "DISCOVER_AT_IMPORT_TIME_DO_NOT_HARDCODE")
    check("license-split", reference.get("licensing", {}).get("code_scripts_documentation") == "MIT" and reference.get("licensing", {}).get("style_json_prompt_content") == "CC-BY-4.0" and reference.get("licensing", {}).get("attribution_required_for_style_content") is True and reference.get("licensing", {}).get("preview_images") == "VISUAL_REFERENCE_ONLY_NOT_BUNDLED_BY_DEFAULT")
    storage = profile.get("storage", {})
    check("namespaced-storage", all(str(storage.get(k, "")).startswith("$XDG_") for k in ("config_root","data_root","cache_root","runtime_root")) and storage.get("project_local_root") == ".fa3/visual-style" and storage.get("shared_global_unscoped_paths") is False)
    check("hardware-audit", profile.get("hardware_audit", {}).get("vendor_neutral") is True and profile.get("hardware_audit", {}).get("cpu_only_viable") is True and profile.get("hardware_audit", {}).get("accelerator_cardinality") == "0..N" and profile.get("hardware_audit", {}).get("global_accelerator_requirement") is False)
    check("coexistence", profile.get("coexistence", {}).get("host_non_interference_required") is True and profile.get("coexistence", {}).get("requires_upstream_uninstall") is False and profile.get("coexistence", {}).get("replaces_upstream_application") is False and profile.get("coexistence", {}).get("global_environment_mutation") is False)
    check("preserve-native-authority", profile.get("preservation", {}).get("native_project_files_remain_authoritative") is True and profile.get("preservation", {}).get("canonical_3d_scene_graph_remains_authoritative") is True)
    check("reuse-intent", intent.get("schema") == "fa3.application-intent.v1" and intent.get("project_id") == profile.get("id"))
    check("reuse-assessment", assessment.get("schema") == "fa3.reuse-assessment.v1" and assessment.get("result") == "PASS" and profile.get("id") in assessment.get("covered_ids", []) and reference.get("id") in assessment.get("covered_ids", []))
    check("no-runtime-promotion", all(obj.get("current_host_runtime_promotion_claim") is False for obj in (profile, enforcement, decision, reference, assessment)) and decision.get("global_promotion_claim") is False and assessment.get("global_promotion_claim") is False)

    consumers = bindings.get("consumers", [])
    required_consumers = {
        "fa3.photo", "fa3.video-editor", "fa3.quickclip", "fa3.story-screenplay",
        "fa3.storyboard", "fa3.vector-graphics", "fa3.world-location-generator",
        "fa3.character-animation", "fa3.3d-fabric", "fa3.vfx-compositing",
        "fa3.credits-titles", "fa3.marketing-poster", "fa3.live-broadcast",
    }
    check("planned-consumers-covered", required_consumers.issubset({row.get("consumer_id") for row in consumers}))
    check("planned-consumers-not-promoted", bool(consumers) and all(validate_consumer_binding(row) for row in consumers))
    check("3d-authority-preserved", any(row.get("consumer_id") == "fa3.3d-fabric" and row.get("canonical_authority_preserved") == "FA3-3D-GEOM-001" for row in consumers))

    synthetic = {
        "style_name": "Synthetic Editorial",
        "style_slug": "synthetic-editorial",
        "style_version": "1",
        "prompt_template": "Create {SUBJECT}",
        "environment_variables": {"SUBJECT": "main subject"},
        "style_fidelity_anchors": ["high contrast"],
        "source_content_to_avoid": ["copied identity"],
        "negative_prompt": "watermark, logo",
        "camera_language": "editorial close framing",
        "continuity_constraints": ["preserve identity across shots"],
    }
    recipe = normalize_recipe(
        synthetic,
        source_project="VigoZhao/AI-Visual-Prompt-Cookbook",
        source_revision="d320e7a99819a54da6ff56abbc19a83fb6741772",
        source_license="CC-BY-4.0",
        attribution="@VigoCreativeAI",
        source_url="https://github.com/VigoZhao/AI-Visual-Prompt-Cookbook",
    )
    check("canonical-import", recipe.get("schema") == "fa3.visual-style-recipe.v1" and recipe.get("provider_neutral") is True and recipe.get("provenance", {}).get("license") == "CC-BY-4.0" and recipe.get("provenance", {}).get("attribution") == "@VigoCreativeAI")
    check("constraints-preserved", recipe.get("style_fidelity_anchors") == synthetic["style_fidelity_anchors"] and recipe.get("source_content_to_avoid") == synthetic["source_content_to_avoid"] and recipe.get("negative_prompt") == synthetic["negative_prompt"])
    check("fa3-extension-preserved", recipe.get("fa3_extensions", {}).get("camera_language") == synthetic["camera_language"] and recipe.get("fa3_extensions", {}).get("continuity_constraints") == synthetic["continuity_constraints"])

    ir = build_visual_intent(recipe, values={"SUBJECT": "new subject"}, scope="SHOT", target_id="shot-001")
    route = ir.get("route_request", {})
    check("visual-intent-ir", ir.get("schema") == "fa3.visual-intent-ir.v1" and ir.get("scope") == "SHOT" and ir.get("canonical_prompt") is False and ir.get("derived_prompt_required") is True)
    check("route-is-unpinned", route.get("authority") == MODEL_ROUTER_AUTHORITY and route.get("resource_authority") == HRB_AUTHORITY and route.get("provider") is None and route.get("model") is None and route.get("runtime") is None and route.get("silent_fallback_allowed") is False)
    check("intent-not-promoted", ir.get("current_host_runtime_promotion_claim") is False)

    dna = build_style_dna([
        {"recipe_id": recipe["id"], "weight": 3},
        {"recipe_id": "fa3.visual-style.secondary", "weight": 1},
    ])
    check("style-dna", dna.get("normalized") is True and abs(sum(x["weight"] for x in dna["components"]) - 1.0) < 1e-9)

    bad_recipe = copy.deepcopy(recipe)
    bad_recipe["runtime"]["fixed_provider"] = "forbidden-provider"
    check("fixed-provider-denied", denied(lambda: build_visual_intent(bad_recipe)))
    check("invalid-scope-denied", denied(lambda: build_visual_intent(recipe, scope="GLOBAL")))
    check("invalid-dna-denied", denied(lambda: build_style_dna([{"recipe_id": recipe["id"], "weight": 0}])))

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    failures = validate(args.root)
    payload = {
        "schema": "fa3.visual-style-fabric-gate-result.v1",
        "gate_id": GATE_ID,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "current_host_runtime_promotion_claim": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
