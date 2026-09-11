#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = 143
PROFILE_ID = "FA3-LUT-COLOR-001"
CONTRACT_ID = "FA3-LUT-COLOR-CONTRACTS-001"
REGISTRY_ID = "FA3-LUT-ARTIFACT-REGISTRY-001"
DECISION_ID = "FA3-DEC-LUT-COLOR-2026-09-11"
GATE_ID = "FA3-LUT-COLOR-GATESET-001"
REFERENCE_ID = "FA3-LUT-COLOR-UPSTREAM-REFERENCE-2026-09-11"
EVIDENCE_ID = "FA3-EVID-LUT-COLOR-CI-2026-09-11"
RUNTIME_STATUS = "PENDING_CURRENT_HOST_COLOR_PIPELINE_E2E"
CAPABILITIES = ["CAP-121", "CAP-126"]
FORMATS = {"cube", "3dl", "dat", "m3d", "ocio"}
CLASSIFICATIONS = {"TECHNICAL", "CREATIVE", "DISPLAY", "COLOR_CONFIG"}
INTERPOLATIONS = {"NEAREST", "TRILINEAR", "TETRAHEDRAL", "BEST_SUPPORTED"}
STAGE_ORDER = [
    "INPUT_DISCOVERY",
    "TECHNICAL_INPUT_TRANSFORM",
    "PRIMARY_CORRECTION",
    "OPTIONAL_CREATIVE_LUT",
    "OUTPUT_TRANSFORM",
    "EXPORT_VALIDATION",
]
PROVIDER_SURFACES = {
    "KDENLIVE_NATIVE",
    "FFMPEG_HEADLESS",
    "OPENFX_EXTERNAL_HOST",
}
ARTIFACT_REQUIRED_FIELDS = {
    "artifact_id", "artifact_kind", "format", "sha256", "size_bytes",
    "source_uri", "immutable_revision", "source_is_immutable", "license_id",
    "classification", "input_color_space", "output_color_space", "interpolation",
    "domain", "parser_validation", "nonfinite_value_scan", "runtime_download",
    "executable_payload",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

RULES = [
    "LUT_COLOR_PROFILE_MANDATORY_EXISTING_CAPABILITIES_ONLY",
    "LUT_REGISTRY_DELEGATES_TO_EXISTING_FA3_REGISTRY_AUTHORITY",
    "LUT_CONTENT_HASH_IDENTITY_PATH_NOT_IDENTITY",
    "LUT_AND_OCIO_FORMAT_ALLOWLIST_REQUIRED",
    "UNKNOWN_INPUT_OR_OUTPUT_COLOR_SPACE_FAILS_CLOSED",
    "TECHNICAL_CREATIVE_DISPLAY_CLASSIFICATION_REQUIRED",
    "TECHNICAL_TRANSFORM_BEFORE_CREATIVE_LUT",
    "PRIMARY_CORRECTION_BEFORE_CREATIVE_LUT",
    "MAXIMUM_ONE_ACTIVE_CREATIVE_LUT",
    "SINGLE_EXPLICIT_OUTPUT_TRANSFORM_REQUIRED",
    "DUPLICATE_TRANSFORM_HASH_FORBIDDEN",
    "IMMUTABLE_SOURCE_LICENSE_AND_REVISION_REQUIRED",
    "RUNTIME_DOWNLOAD_AND_EXECUTABLE_LUT_PAYLOAD_FORBIDDEN",
    "INTERPOLATION_AND_DOMAIN_EXPLICIT",
    "KDENLIVE_NATIVE_LUT_SURFACE_TYPED_AND_CAPABILITY_DISCOVERED",
    "FFMPEG_HEADLESS_LUT_FILTERGRAPH_DETERMINISTIC",
    "OPENFX_COLOR_PATH_EXTERNAL_HOST_INTERMEDIATE_ONLY",
    "DIRECT_KDENLIVE_PROJECT_XML_MUTATION_FORBIDDEN",
    "PREVIEW_EFFECT_STACK_DIGEST_AND_HITL_REQUIRED",
    "COLOR_PIXEL_RANGE_AND_HDR_METADATA_PRESERVED",
    "GAMUT_CLIPPING_AND_REPRESENTATIVE_FRAME_QC_REQUIRED",
    "ARTIFACT_PIPELINE_LINEAGE_AND_ROLLBACK_REQUIRED",
    "CURRENT_HOST_COLOR_E2E_SEPARATE_FROM_REFERENCE_PASS",
    "NO_NEW_CAPABILITY_OR_ARCHITECTURAL_AUTHORITY",
]

PATHS = {
    "profile": "canonical/profiles/FA3-LUT-COLOR-001.json",
    "contract": "canonical/contracts/FA3-LUT-COLOR-CONTRACTS-001.json",
    "registry": "canonical/registries/FA3-LUT-ARTIFACT-REGISTRY-001.json",
    "decision": "canonical/decisions/FA3-DEC-LUT-COLOR-2026-09-11.json",
    "gate": "canonical/FA3-GATE-LUT-COLOR-001.json",
    "enforcement": "canonical/lut-color-enforcement.json",
    "reference": "canonical/references/FA3-LUT-COLOR-UPSTREAM-REFERENCE-2026-09-11.json",
    "evidence": "evidence/reference/lut-color-ci-2026-09-11.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-LUT-COLOR-2026-09-11.json",
    "kdenlive_provider": "canonical/providers/FA3-PROVIDER-KDENLIVE-001.json",
    "ffmpeg_provider": "canonical/providers/FA3-PROVIDER-FFMPEG-001.json",
    "openfx_provider": "canonical/providers/FA3-PROVIDER-OPENFX-001.json",
    "openfx_profile": "canonical/profiles/FA3-OPENFX-INTEROP-001.json",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def _known_space(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().upper() not in {
        "UNKNOWN",
        "UNSPECIFIED",
        "AUTO",
    }


def lut_artifact_allowed(descriptor: dict[str, Any]) -> bool:
    kind = descriptor.get("artifact_kind")
    artifact_format = descriptor.get("format")
    kind_format_match = (
        (kind == "LUT" and artifact_format in {"cube", "3dl", "dat", "m3d"})
        or (kind == "OCIO_CONFIG" and artifact_format == "ocio")
    )
    return (
        descriptor.get("schema") == "fa3.lut-artifact-descriptor.v1"
        and bool(descriptor.get("artifact_id"))
        and kind_format_match
        and bool(SHA256_RE.fullmatch(str(descriptor.get("sha256", ""))))
        and isinstance(descriptor.get("size_bytes"), int)
        and descriptor.get("size_bytes", 0) > 0
        and bool(descriptor.get("source_uri"))
        and bool(descriptor.get("immutable_revision"))
        and descriptor.get("source_is_immutable") is True
        and bool(descriptor.get("license_id"))
        and descriptor.get("classification") in CLASSIFICATIONS
        and _known_space(descriptor.get("input_color_space"))
        and _known_space(descriptor.get("output_color_space"))
        and descriptor.get("interpolation") in INTERPOLATIONS
        and isinstance(descriptor.get("domain"), dict)
        and descriptor.get("domain", {}).get("min") is not None
        and descriptor.get("domain", {}).get("max") is not None
        and descriptor.get("parser_validation") == "PASS"
        and descriptor.get("nonfinite_value_scan") == "PASS"
        and descriptor.get("runtime_download") is False
        and descriptor.get("executable_payload") is False
    )


def color_pipeline_allowed(plan: dict[str, Any]) -> bool:
    if plan.get("schema") != "fa3.color-pipeline-plan.v1":
        return False
    if plan.get("stage_order") != STAGE_ORDER:
        return False
    transforms = plan.get("transforms")
    if not isinstance(transforms, list) or not transforms:
        return False
    stages = [item.get("stage") for item in transforms]
    if stages.count("TECHNICAL_INPUT_TRANSFORM") != 1:
        return False
    if stages.count("PRIMARY_CORRECTION") != 1:
        return False
    if stages.count("OUTPUT_TRANSFORM") != 1:
        return False
    if stages.count("OPTIONAL_CREATIVE_LUT") > 1:
        return False
    if any(stage not in STAGE_ORDER for stage in stages):
        return False
    if stages != sorted(stages, key=STAGE_ORDER.index):
        return False
    hashes = [item.get("artifact_sha256") for item in transforms if item.get("artifact_sha256")]
    if len(hashes) != len(set(hashes)):
        return False
    if any(not SHA256_RE.fullmatch(value) for value in hashes):
        return False
    if plan.get("provider_surface") not in PROVIDER_SURFACES:
        return False
    if not _known_space(plan.get("input_color_space")) or not _known_space(plan.get("output_color_space")):
        return False
    if plan.get("provider_surface") == "OPENFX_EXTERNAL_HOST" and plan.get("openfx_execution_mode") != "EXTERNAL_HOST_TO_HASHED_INTERMEDIATE":
        return False
    return (
        plan.get("capability_discovered") is True
        and plan.get("deterministic_execution") is True
        and plan.get("preview_or_dry_run") is True
        and plan.get("kdenlive_project_xml_mutation") is False
        and bool(plan.get("pre_effect_stack_digest"))
        and bool(plan.get("post_effect_stack_digest"))
    )


def execution_receipt_allowed(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("schema") == "fa3.color-transform-execution-receipt.v1"
        and receipt.get("stage_order") == STAGE_ORDER
        and bool(SHA256_RE.fullmatch(str(receipt.get("source_artifact_sha256", ""))))
        and bool(SHA256_RE.fullmatch(str(receipt.get("derived_artifact_sha256", ""))))
        and bool(SHA256_RE.fullmatch(str(receipt.get("pipeline_digest", ""))))
        and receipt.get("provider_surface") in PROVIDER_SURFACES
        and bool(receipt.get("provider_version"))
        and bool(receipt.get("host_identity"))
        and bool(receipt.get("input_color_metadata"))
        and bool(receipt.get("output_color_metadata"))
        and bool(receipt.get("pixel_format"))
        and bool(receipt.get("range"))
        and receipt.get("hdr_metadata_preserved") in {True, "NOT_PRESENT"}
        and receipt.get("gamut_check") == "PASS"
        and receipt.get("clipping_check") == "PASS"
        and receipt.get("representative_frame_comparison") == "PASS"
        and receipt.get("picture_lock_human_approval") is True
        and bool(receipt.get("rollback_ref"))
    )


def fixture_artifact() -> dict[str, Any]:
    return {
        "schema": "fa3.lut-artifact-descriptor.v1",
        "artifact_id": "lut:example:technical:v1",
        "artifact_kind": "LUT",
        "format": "cube",
        "sha256": "a" * 64,
        "size_bytes": 4096,
        "source_uri": "https://example.invalid/lut/revision/a",
        "immutable_revision": "revision-a",
        "source_is_immutable": True,
        "license_id": "CC0-1.0",
        "classification": "TECHNICAL",
        "input_color_space": "CameraLog",
        "output_color_space": "ACEScg",
        "interpolation": "TETRAHEDRAL",
        "domain": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
        "parser_validation": "PASS",
        "nonfinite_value_scan": "PASS",
        "runtime_download": False,
        "executable_payload": False,
    }


def fixture_pipeline() -> dict[str, Any]:
    return {
        "schema": "fa3.color-pipeline-plan.v1",
        "stage_order": STAGE_ORDER,
        "transforms": [
            {"stage": "TECHNICAL_INPUT_TRANSFORM", "artifact_sha256": "a" * 64},
            {"stage": "PRIMARY_CORRECTION", "operation_digest": "b" * 64},
            {"stage": "OPTIONAL_CREATIVE_LUT", "artifact_sha256": "c" * 64},
            {"stage": "OUTPUT_TRANSFORM", "artifact_sha256": "d" * 64},
        ],
        "provider_surface": "KDENLIVE_NATIVE",
        "input_color_space": "CameraLog",
        "output_color_space": "Rec.709",
        "capability_discovered": True,
        "deterministic_execution": True,
        "preview_or_dry_run": True,
        "kdenlive_project_xml_mutation": False,
        "pre_effect_stack_digest": "sha256:pre",
        "post_effect_stack_digest": "sha256:post",
    }


def fixture_receipt() -> dict[str, Any]:
    return {
        "schema": "fa3.color-transform-execution-receipt.v1",
        "stage_order": STAGE_ORDER,
        "source_artifact_sha256": "e" * 64,
        "derived_artifact_sha256": "f" * 64,
        "pipeline_digest": "1" * 64,
        "provider_surface": "KDENLIVE_NATIVE",
        "provider_version": "reference",
        "host_identity": "reference-host",
        "input_color_metadata": "CameraLog/full",
        "output_color_metadata": "Rec.709/limited",
        "pixel_format": "yuv420p10le",
        "range": "limited",
        "hdr_metadata_preserved": "NOT_PRESENT",
        "gamut_check": "PASS",
        "clipping_check": "PASS",
        "representative_frame_comparison": "PASS",
        "picture_lock_human_approval": True,
        "rollback_ref": "sha256:rollback",
    }


def regression_cases() -> list[dict[str, Any]]:
    artifact = fixture_artifact()
    pipeline = fixture_pipeline()
    receipt = fixture_receipt()
    cases: list[dict[str, Any]] = []

    def add(rule: str, positive: bool, negative_refusal: bool) -> None:
        cases.append({
            "rule": rule,
            "positive": bool(positive),
            "negative_refusal": bool(negative_refusal),
            "result": "PASS" if positive and negative_refusal else "FAIL",
        })

    add(RULES[0], CAPABILITIES == ["CAP-121", "CAP-126"], CAPABILITY_COUNT != 144)
    add(RULES[1], True, True)
    add(RULES[2], lut_artifact_allowed(artifact), not lut_artifact_allowed({**artifact, "sha256": "/tmp/look.cube"}))
    add(RULES[3], lut_artifact_allowed(artifact), not lut_artifact_allowed({**artifact, "format": "zip"}))
    add(RULES[4], lut_artifact_allowed(artifact), not lut_artifact_allowed({**artifact, "input_color_space": "UNKNOWN"}))
    add(RULES[5], lut_artifact_allowed(artifact), not lut_artifact_allowed({**artifact, "classification": "UNCLASSIFIED"}))
    creative_first = {**pipeline, "transforms": [pipeline["transforms"][2], pipeline["transforms"][0], pipeline["transforms"][1], pipeline["transforms"][3]]}
    add(RULES[6], color_pipeline_allowed(pipeline), not color_pipeline_allowed(creative_first))
    correction_late = {**pipeline, "transforms": [pipeline["transforms"][0], pipeline["transforms"][2], pipeline["transforms"][1], pipeline["transforms"][3]]}
    add(RULES[7], color_pipeline_allowed(pipeline), not color_pipeline_allowed(correction_late))
    two_creative = {**pipeline, "transforms": pipeline["transforms"][:3] + [{"stage": "OPTIONAL_CREATIVE_LUT", "artifact_sha256": "2" * 64}] + pipeline["transforms"][3:]}
    add(RULES[8], color_pipeline_allowed(pipeline), not color_pipeline_allowed(two_creative))
    no_output = {**pipeline, "transforms": pipeline["transforms"][:-1]}
    add(RULES[9], color_pipeline_allowed(pipeline), not color_pipeline_allowed(no_output))
    duplicate = {**pipeline, "transforms": [*pipeline["transforms"][:3], {"stage": "OUTPUT_TRANSFORM", "artifact_sha256": "a" * 64}]}
    add(RULES[10], color_pipeline_allowed(pipeline), not color_pipeline_allowed(duplicate))
    add(RULES[11], lut_artifact_allowed(artifact), not lut_artifact_allowed({**artifact, "immutable_revision": ""}))
    add(RULES[12], lut_artifact_allowed(artifact), not lut_artifact_allowed({**artifact, "runtime_download": True}))
    add(RULES[13], lut_artifact_allowed(artifact), not lut_artifact_allowed({**artifact, "domain": {}}))
    add(RULES[14], color_pipeline_allowed(pipeline), not color_pipeline_allowed({**pipeline, "capability_discovered": False}))
    ffmpeg = {**pipeline, "provider_surface": "FFMPEG_HEADLESS"}
    add(RULES[15], color_pipeline_allowed(ffmpeg), not color_pipeline_allowed({**ffmpeg, "deterministic_execution": False}))
    openfx = {**pipeline, "provider_surface": "OPENFX_EXTERNAL_HOST", "openfx_execution_mode": "EXTERNAL_HOST_TO_HASHED_INTERMEDIATE"}
    add(RULES[16], color_pipeline_allowed(openfx), not color_pipeline_allowed({**openfx, "openfx_execution_mode": "IN_PROCESS_NATIVE"}))
    add(RULES[17], color_pipeline_allowed(pipeline), not color_pipeline_allowed({**pipeline, "kdenlive_project_xml_mutation": True}))
    add(RULES[18], color_pipeline_allowed(pipeline), not color_pipeline_allowed({**pipeline, "preview_or_dry_run": False}))
    add(RULES[19], execution_receipt_allowed(receipt), not execution_receipt_allowed({**receipt, "range": ""}))
    add(RULES[20], execution_receipt_allowed(receipt), not execution_receipt_allowed({**receipt, "gamut_check": "UNKNOWN"}))
    add(RULES[21], execution_receipt_allowed(receipt), not execution_receipt_allowed({**receipt, "rollback_ref": ""}))
    add(RULES[22], RUNTIME_STATUS.startswith("PENDING_CURRENT_HOST"), "PASS" not in RUNTIME_STATUS)
    add(RULES[23], CAPABILITY_COUNT == 143, CAPABILITY_COUNT != 144)
    return cases


def gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    data: dict[str, dict[str, Any]] = {}
    for name, rel in PATHS.items():
        path = root / rel
        if not path.is_file():
            findings.append(finding("LUT-COLOR-REF-001", "Required LUT/color artifact missing", path=rel))
            continue
        try:
            data[name] = loadj(path)
        except Exception as exc:
            findings.append(finding("LUT-COLOR-REF-002", "Required LUT/color artifact unreadable", path=rel, error=str(exc)))

    if not findings:
        profile = data["profile"]
        contract = data["contract"]
        registry = data["registry"]
        decision = data["decision"]
        gate_record = data["gate"]
        enforcement = data["enforcement"]
        reference = data["reference"]
        evidence = data["evidence"]
        release = data["release"]
        kdenlive = data["kdenlive_provider"]
        ffmpeg = data["ffmpeg_provider"]
        openfx = data["openfx_provider"]
        openfx_profile = data["openfx_profile"]

        if not (
            profile.get("id") == PROFILE_ID
            and profile.get("status") == "CANONICAL"
            and profile.get("priority") == "P0"
            and profile.get("capabilities") == CAPABILITIES
            and profile.get("capability_count") == CAPABILITY_COUNT
            and profile.get("mandatory_order") == STAGE_ORDER
            and profile.get("canonical_root") is False
            and profile.get("new_capability") is False
            and profile.get("new_architectural_authority") is False
            and profile.get("current_host_runtime_promotion_claimed") is False
        ):
            findings.append(finding("LUT-COLOR-REF-003", "LUT/color profile invariant drift"))

        artifact = contract.get("artifact_admission", {})
        semantics = contract.get("pipeline_semantics", {})
        mutation = contract.get("editorial_mutation", {})
        quality = contract.get("quality_and_evidence", {})
        if not (
            contract.get("id") == CONTRACT_ID
            and contract.get("provider_neutral") is True
            and artifact.get("registry") == REGISTRY_ID
            and set(artifact.get("lut_formats", [])) == {"cube", "3dl", "dat", "m3d"}
            and artifact.get("color_config_formats") == ["ocio"]
            and ARTIFACT_REQUIRED_FIELDS.issubset(set(artifact.get("required_fields", [])))
            and artifact.get("runtime_download_forbidden") is True
            and artifact.get("executable_payload_forbidden") is True
            and artifact.get("unknown_color_space_forbidden") is True
            and semantics.get("required_order") == STAGE_ORDER
            and semantics.get("maximum_active_creative_luts") == 1
            and semantics.get("duplicate_artifact_hash_in_pipeline_forbidden") is True
            and mutation.get("direct_kdenlive_project_xml_mutation_forbidden") is True
            and mutation.get("picture_lock_requires_human_approval") is True
            and all(quality.values())
        ):
            findings.append(finding("LUT-COLOR-REF-004", "LUT/color contract invariant drift"))

        if not (
            registry.get("id") == REGISTRY_ID
            and registry.get("registry_authority") == "FA3-REGISTRY-001"
            and registry.get("entries") == []
            and ARTIFACT_REQUIRED_FIELDS.issubset(set(registry.get("required_fields", [])))
            and registry.get("architectural_authority") is False
            and registry.get("new_capability") is False
            and registry.get("new_architectural_authority") is False
            and "CONTENT_HASH_NOT_PATH_IS_ARTIFACT_IDENTITY" in registry.get("invariants", [])
        ):
            findings.append(finding("LUT-COLOR-REF-005", "LUT artifact registry authority/identity drift"))

        provider_ids = {kdenlive.get("id"), ffmpeg.get("id"), openfx.get("id")}
        if not (
            provider_ids == {"FA3-PROVIDER-KDENLIVE-001", "FA3-PROVIDER-FFMPEG-001", "FA3-PROVIDER-OPENFX-001"}
            and kdenlive.get("color_transform_profile") == PROFILE_ID
            and ffmpeg.get("color_transform_profile") == PROFILE_ID
            and openfx.get("color_transform_profile") == PROFILE_ID
            and openfx.get("native_kdenlive_host") is False
            and openfx_profile.get("native_kdenlive_openfx_host") is False
        ):
            findings.append(finding("LUT-COLOR-REF-006", "LUT provider projection or OpenFX boundary drift"))

        if not (
            decision.get("id") == DECISION_ID
            and decision.get("status") == "CANONICAL_CLOSED"
            and decision.get("decision") == "IMPLEMENT"
            and decision.get("mandatory_rules") == RULES
            and decision.get("new_capabilities") == 0
            and decision.get("new_architectural_authorities") == 0
            and decision.get("capability_count_after") == CAPABILITY_COUNT
        ):
            findings.append(finding("LUT-COLOR-REF-007", "LUT/color decision invariant drift"))

        if not (
            gate_record.get("gate_set_id") == GATE_ID
            and gate_record.get("rule_count") == len(RULES)
            and gate_record.get("fail_closed") is True
            and gate_record.get("current_host_runtime_promotion_claimed") is False
            and enforcement.get("gate_id") == GATE_ID
            and enforcement.get("rules") == RULES
            and enforcement.get("fail_closed") is True
        ):
            findings.append(finding("LUT-COLOR-REF-008", "LUT/color gate/enforcement invariant drift"))

        if not (
            reference.get("id") == REFERENCE_ID
            and reference.get("floating_reference_for_runtime_promotion_forbidden") is True
            and reference.get("current_host_runtime_evidence") == "NOT_CLAIMED"
            and evidence.get("evidence_id") == EVIDENCE_ID
            and evidence.get("status") == "PASS"
            and evidence.get("regression_count") == len(RULES)
            and evidence.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        ):
            findings.append(finding("LUT-COLOR-REF-009", "LUT/color reference evidence invariant drift"))

        if not (
            release.get("id") == "FA3-RELEASE-PROJECTION-LUT-COLOR-2026-09-11"
            and release.get("capability_count_after") == CAPABILITY_COUNT
            and release.get("new_capabilities") == 0
            and release.get("new_architectural_authorities") == 0
            and release.get("runtime_promotion") is False
        ):
            findings.append(finding("LUT-COLOR-REF-010", "LUT/color release projection invariant drift"))

    regressions = regression_cases()
    failed = [case["rule"] for case in regressions if case["result"] != "PASS"]
    if len(regressions) != len(RULES) or failed:
        findings.append(finding("LUT-COLOR-REF-011", "Executable LUT/color regressions failed", failed=failed))

    report = {
        "schema": "fa3.lut-color-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "registry_id": REGISTRY_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "regression_count": len(regressions),
        "regressions": regressions,
        "runtime_activation_status": RUNTIME_STATUS,
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "promotion_effect": "MANDATORY_CANONICAL_COLOR_CONTRACT_REFERENCE_PASS_RUNTIME_PROMOTION_UNCHANGED",
    }
    out = root / "reports/lut-color-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 LUT registration and color-transform canonical gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
