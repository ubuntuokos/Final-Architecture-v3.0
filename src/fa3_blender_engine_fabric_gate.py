#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

INTEGRATION = "canonical/FA3-BLENDER-ENGINE-FABRIC-001.json"
PROFILE = "canonical/profiles/FA3-BLENDER-COMPATIBILITY-PROFILE-001.json"
CONTRACT = "canonical/contracts/FA3-BLENDER-COMPATIBILITY-CONTRACTS-001.json"
ASSESSMENT = "canonical/assessments/FA3-BLENDER-ENGINE-FABRIC-REUSE-ASSESSMENT-001.json"
DECISION = "canonical/decisions/FA3-DEC-BLENDER-ENGINE-FABRIC-2026-10-01.json"
INTENT = "canonical/intents/FA3-BLENDER-ENGINE-FABRIC-APPLICATION-INTENT-001.json"
IMPACT = "canonical/FA3-BLENDER-ENGINE-FABRIC-CURRENT-HOST-IMPACT-001.json"
MODEL = "canonical/FA3-CAPABILITY-MODEL-175-001.json"

EXPECTED_BINDINGS = ["CAP-006","CAP-015","CAP-016","CAP-022","CAP-025","CAP-027","CAP-032","CAP-146","CAP-147","CAP-148","CAP-161","CAP-163","CAP-165","CAP-166","CAP-171","CAP-175"]
REQUIRED_TESTS = {
    "BLEND-ROUNDTRIP",
    "BFORARTISTS-ROUNDTRIP",
    "BLENDER-BFORARTISTS-CROSSOPEN",
    "BPY-CONFORMANCE",
    "RNA-CONFORMANCE",
    "OPERATOR-CONFORMANCE",
    "SCENE-CONFORMANCE",
    "MATERIAL-CONFORMANCE",
    "GEOMETRY-NODES-CONFORMANCE",
    "ANIMATION-CONFORMANCE",
    "RIG-CONFORMANCE",
    "CAMERA-CONFORMANCE",
    "ASSET-CONFORMANCE",
    "CYCLES-CONFORMANCE",
    "EEVEE-CONFORMANCE",
    "USD-ROUNDTRIP",
    "GLTF-ROUNDTRIP",
    "HEADLESS-CONFORMANCE",
    "EXTENSION-CONFORMANCE",
    "ROLLBACK-CONFORMANCE",
}

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value

def validate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, str]] = []

    def fail(code: str, detail: str) -> None:
        findings.append({"code": code, "detail": detail})

    integration = load(root / INTEGRATION)
    profile = load(root / PROFILE)
    contract = load(root / CONTRACT)
    assessment = load(root / ASSESSMENT)
    decision = load(root / DECISION)
    intent = load(root / INTENT)
    impact = load(root / IMPACT)
    model = load(root / MODEL)

    if model.get("canonical_capability_count") != 175:
        fail("GLOBAL_CAPABILITY_BASELINE_DRIFT", str(model.get("canonical_capability_count")))

    if integration.get("id") != "FA3-BLENDER-ENGINE-FABRIC-001":
        fail("INTEGRATION_ID", str(integration.get("id")))
    if integration.get("capability_baseline") != 175 or integration.get("capability_delta") != 0:
        fail("CAPABILITY_DELTA", f'{integration.get("capability_baseline")}:{integration.get("capability_delta")}')
    if integration.get("authority") is not False or integration.get("new_architectural_authority") is not False:
        fail("AUTHORITY_DELTA", "Blender fabric must not become an authority")
    if integration.get("new_capability") is not False:
        fail("NEW_CAPABILITY_FORBIDDEN", "CAP-176 is not allowed")

    architecture = integration.get("architecture", {})
    if architecture.get("primary_dcc") != "BFORARTISTS":
        fail("PRIMARY_DCC_DRIFT", str(architecture.get("primary_dcc")))
    if architecture.get("blender_core_fork") is not False:
        fail("BLENDER_FORK_FORBIDDEN", "blender_core_fork")
    if architecture.get("blender_core_patch_required") is not False:
        fail("BLENDER_CORE_PATCH_NOT_AUTHORIZED", "blender_core_patch_required")
    if architecture.get("adapter_first") is not True:
        fail("ADAPTER_FIRST_REQUIRED", "adapter_first")
    if architecture.get("new_project_format") is not False or architecture.get("native_project_authority") != ".blend":
        fail("NATIVE_PROJECT_AUTHORITY", str(architecture.get("native_project_authority")))

    bindings = integration.get("capability_bindings", [])
    if bindings != EXPECTED_BINDINGS:
        fail("CAPABILITY_BINDING_DRIFT", repr(bindings))
    for cap in bindings:
        try:
            n = int(cap.split("-", 1)[1])
        except Exception:
            n = 0
        if n < 1 or n > 175:
            fail("CAPABILITY_OUT_OF_BASELINE", str(cap))

    for obj, label in ((profile, "profile"), (contract, "contract")):
        if obj.get("capability_count") != 175:
            fail("COMPONENT_CAPABILITY_COUNT", f"{label}:{obj.get('capability_count')}")
        if obj.get("capability_bindings") != EXPECTED_BINDINGS:
            fail("COMPONENT_BINDING_DRIFT", label)
        if obj.get("new_capability") is not False or obj.get("new_architectural_authority") is not False:
            fail("COMPONENT_DELTA", label)
        if obj.get("provider_neutral") is not True:
            fail("PROVIDER_NEUTRAL_REQUIRED", label)

    tests = set(profile.get("conformance_tests", []))
    if not REQUIRED_TESTS.issubset(tests):
        fail("CONFORMANCE_TEST_SET", ",".join(sorted(REQUIRED_TESTS - tests)))

    loss = profile.get("loss_policy", {})
    if loss.get("allowed_outcomes") != ["LOSSLESS", "LOSSY_WITH_EXPLICIT_REPORT", "BLOCKED"]:
        fail("LOSS_OUTCOME_DRIFT", repr(loss.get("allowed_outcomes")))
    if loss.get("silent_loss_forbidden") is not True:
        fail("SILENT_LOSS_FORBIDDEN", "profile")
    if contract.get("roundtrip_contract", {}).get("silent_loss_forbidden") is not True:
        fail("SILENT_LOSS_FORBIDDEN", "contract")

    resource = integration.get("resource_policy", {})
    if resource.get("resource_authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001":
        fail("HRB_AUTHORITY", str(resource.get("resource_authority")))
    for key in ("hardware_safety_envelope_mandatory", "vendor_neutral", "cpu_only_viable"):
        if resource.get(key) is not True:
            fail("HARDWARE_POLICY", key)
    if resource.get("silent_device_fallback") is not False:
        fail("SILENT_DEVICE_FALLBACK", "forbidden")
    if resource.get("automatic_display_gpu_compute_recruitment") is not False:
        fail("DISPLAY_GPU_AUTO_RECRUITMENT", "forbidden")
    if resource.get("hardware_mutation") is not False:
        fail("HARDWARE_MUTATION", "forbidden")

    ai = integration.get("ai_policy", {})
    if ai.get("optional") is not True or ai.get("per_application_module_function_disable_required") is not True:
        fail("AI_OPTIONALITY", "AI must remain explicitly disableable")
    if ai.get("model_provider_authority") != "FA3-AUTH-MODEL-ROUTER-001":
        fail("MODEL_ROUTER_AUTHORITY", str(ai.get("model_provider_authority")))
    if ai.get("silent_ai_fallback") is not False:
        fail("SILENT_AI_FALLBACK", "forbidden")

    render = integration.get("render_policy", {})
    for key in ("cycles_preserved", "eevee_preserved", "cpu_render_path_preserved"):
        if render.get(key) is not True:
            fail("RENDER_COMPATIBILITY", key)
    if render.get("direct_opendlss_nr_blender_core_coupling") is not False:
        fail("NEURAL_CORE_COUPLING", "OpenDLSS-NR must stay behind CAP-163/Render Fabric")
    if render.get("paid_renderer_baseline_dependency") is not False:
        fail("PAID_RENDERER_BASELINE_DEPENDENCY", "forbidden")

    runtime = integration.get("runtime_materialization", {})
    for key, value in runtime.items():
        if value is not False:
            fail("STATIC_RUNTIME_ACTIVATION", f"{key}:{value}")

    rights = integration.get("license_rights", {})
    for key in ("no_third_party_source_copied", "no_blender_source_imported", "no_cycles_source_imported", "no_addon_source_imported"):
        if rights.get(key) is not True:
            fail("LICENSE_RIGHTS_BOUNDARY", key)

    reuse = integration.get("source_reuse", {})
    if reuse.get("reuse_discovery_performed") is not True:
        fail("REUSE_DISCOVERY_REQUIRED", "not performed")
    if reuse.get("donor_registry_mutation") is not False or reuse.get("new_donor_identity_created") is not False:
        fail("DONOR_MUTATION_FORBIDDEN", "this scope does not mutate donor registry")

    if decision.get("status") != "OWNER_APPROVED_MATERIALIZATION":
        fail("OWNER_DECISION", str(decision.get("status")))
    if intent.get("declared_new_capabilities") != [] or intent.get("proposed_authority_roles") != []:
        fail("INTENT_DELTA", "intent proposes capability/authority")
    if assessment.get("static_materialization_authorized") is not True:
        fail("REUSE_ASSESSMENT", "static materialization not authorized")
    if assessment.get("code_import_authorized") is not False or assessment.get("runtime_admission_authorized") is not False:
        fail("UNAUTHORIZED_SOURCE_OR_RUNTIME_ADOPTION", "assessment")

    if impact.get("structural_alignment_performed") is not True:
        fail("CURRENT_HOST_ALIGNMENT", "missing")
    if impact.get("runtime_change") is not False:
        fail("CURRENT_HOST_RUNTIME_DELTA", "must be static")
    if impact.get("physical_current_host_pass_claimed") is not False or impact.get("current_host_runtime_promotion_claim") is not False:
        fail("CURRENT_HOST_FALSE_PROMOTION", "physical/runtime promotion is forbidden")
    obligations = impact.get("obligation_model", {})
    if obligations.get("capability_count") != 175 or obligations.get("global_obligation_count") != 525 or obligations.get("new_obligation_count") != 0:
        fail("CURRENT_HOST_OBLIGATION_DRIFT", repr(obligations))
    if set(obligations.get("proof_classes", [])) != {"POSITIVE", "NEGATIVE", "ROLLBACK"}:
        fail("CURRENT_HOST_PROOF_CLASSES", repr(obligations.get("proof_classes")))

    return {
        "schema": "fa3.blender-engine-fabric-validation.v1",
        "id": integration.get("id"),
        "capability_baseline": 175,
        "capability_bindings": len(bindings),
        "components": len(integration.get("components", [])),
        "runtime_activation": False,
        "physical_current_host_pass_claimed": False,
        "validation": {
            "result": "PASS" if not findings else "FAIL",
            "findings": findings,
        },
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = validate(Path(args.root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if args.check and report["validation"]["result"] != "PASS" else 0

if __name__ == "__main__":
    raise SystemExit(main())
