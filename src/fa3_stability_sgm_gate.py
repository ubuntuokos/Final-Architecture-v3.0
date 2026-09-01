#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-STABILITY-SGM-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-STABILITY-SGM-001"
PROVIDER_ID = "FA3-PROVIDER-STABILITY-SGM-001"
CONTRACT_ID = "FA3-GENERATIVE-PIPELINE-MULTIVIEW-CONTRACTS-001"
DECISION_ID = "FA3-DEC-STABILITY-SGM-2026-09-01"
REFERENCE_ID = "FA3-STABILITY-SGM-UPSTREAM-REFERENCE-2026-09-01"
EVIDENCE_ID = "FA3-EVIDENCE-STABILITY-SGM-CI-2026-09-01"
UPSTREAM_COMMIT = "e8cd657656fa5d61688191730d0e03242bf4ed44"
CAPABILITY_COUNT = 143

P0_RULES = [
    "GEN_PIPELINE_COMPONENT_ADDRESSABILITY_REQUIRED",
    "GEN_CONDITIONING_TYPED_SEMANTICS_REQUIRED",
    "GEN_SAMPLER_NOT_MODEL_OR_ROUTING_AUTHORITY",
    "GEN_GUIDANCE_SEPARABLE_FROM_SAMPLING",
    "GEN_TRAINING_AND_INFERENCE_DENOISING_SEMANTICS_EXPLICIT",
    "GEN_EXECUTION_RECIPE_IDENTITY_REPRODUCIBLE",
    "GEN_CONTAINER_AND_TENSOR_INTEGRITY_INDEPENDENT",
    "GEN_CODE_LICENSE_NOT_WEIGHT_OR_OUTPUT_LICENSE",
    "GEN_CAMERA_VIEW_CONDITIONING_EXPLICIT",
    "GEN_TEMPORAL_AND_MULTIVIEW_QUALITY_SEPARATE",
    "GEN_AUTOREGRESSIVE_EXTENSION_ANCESTRY_REQUIRED",
    "GEN_LOW_VRAM_POLICY_NOT_MODEL_SEMANTIC_MUTATION",
    "GEN_SV3D_SV4D_OUTPUT_NOT_CANONICAL_GEOMETRY",
    "GEN_PROVIDER_ISOLATED_RUNTIME_REQUIRED",
    "GEN_HRB_ONLY_ACCELERATOR_PLACEMENT",
    "GEN_DISABLED_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST",
]

COMPONENT_ROLES = {"model", "conditioner", "guider", "sampler", "scheduler", "denoiser", "decoder"}
CONDITIONING_TYPES = {"TEXT", "IMAGE", "VECTOR", "SEQUENCE", "SPATIAL", "CAMERA", "TEMPORAL"}
LICENSE_FIELDS = {
    "source_code_license",
    "weight_license",
    "model_version",
    "artifact_hash",
    "access_constraints",
    "commercial_use_constraints",
    "acceptable_use_policy",
    "derivative_model_constraints",
    "output_constraints",
    "license_evidence_timestamp",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def provider_shape_valid(provider: dict[str, Any]) -> bool:
    return (
        provider.get("id") == PROVIDER_ID
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT"
        and provider.get("global_runtime_promotion_required_when_disabled") is False
        and provider.get("runtime_activation_requires_current_host_conformance") is True
        and provider.get("runtime_activation_status") == "NOT_PROMOTED_REFERENCE_ONLY"
        and provider.get("current_host_runtime_evidence") is False
        and provider.get("contract") == CONTRACT_ID
        and provider.get("output_semantics", {}).get("canonical_geometry") is False
    )


def component_addressability_valid(components: list[dict[str, Any]]) -> bool:
    roles = {x.get("role") for x in components if isinstance(x, dict)}
    identities = [x.get("identity") for x in components if isinstance(x, dict)]
    return roles == COMPONENT_ROLES and all(identities) and len(identities) == len(set(identities))


def typed_conditioning_valid(conditioning: list[dict[str, Any]]) -> bool:
    if not conditioning:
        return False
    return all(
        isinstance(item, dict)
        and item.get("type") in CONDITIONING_TYPES
        and bool(item.get("artifact_or_value_digest"))
        for item in conditioning
    )


def sampler_authority_valid(*, sampler_component: bool, owns_model_or_routing_authority: bool) -> bool:
    return sampler_component and not owns_model_or_routing_authority


def guidance_separation_valid(*, guider_identity: str, sampler_identity: str, independently_addressable: bool) -> bool:
    return bool(guider_identity and sampler_identity) and guider_identity != sampler_identity and independently_addressable


def denoising_semantics_valid(*, training_semantics: str, inference_semantics: str, explicit_mapping: bool) -> bool:
    return bool(training_semantics and inference_semantics) and explicit_mapping


def recipe_identity(recipe: dict[str, Any]) -> str:
    payload = json.dumps(recipe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def recipe_identity_valid(recipe: dict[str, Any], declared_identity: str) -> bool:
    required = {
        "model_artifact_id",
        "model_revision",
        "config_digest",
        "component_identities",
        "sampler",
        "scheduler",
        "precision",
        "conditioning_digest",
        "runtime_revision",
    }
    return required <= set(recipe) and all(recipe.get(k) for k in required) and declared_identity == recipe_identity(recipe)


def artifact_integrity_valid(*, container_sha256: str, tensor_payload_sha256: str | None, format_permits_tensor_hash: bool) -> bool:
    def digest(value: str | None) -> bool:
        return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())

    return digest(container_sha256) and (not format_permits_tensor_hash or digest(tensor_payload_sha256))


def license_separation_valid(record: dict[str, Any]) -> bool:
    if not LICENSE_FIELDS <= set(record) or any(record.get(k) in (None, "") for k in LICENSE_FIELDS):
        return False
    return record.get("code_license_admits_weights") is False and record.get("code_license_admits_outputs") is False


def camera_conditioning_valid(camera: dict[str, Any]) -> bool:
    required = {"camera_id", "intrinsics_digest", "extrinsics_digest", "view_index", "temporal_index"}
    return required <= set(camera) and all(camera.get(k) is not None for k in required)


def quality_dimensions_valid(metrics: dict[str, Any]) -> bool:
    required = {"temporal_consistency", "multi_view_consistency", "camera_trajectory_conformance"}
    return required <= set(metrics) and all(isinstance(metrics[k], (int, float)) for k in required)


def autoregressive_ancestry_valid(lineage: dict[str, Any]) -> bool:
    required = {
        "source_artifact_id", "source_frame_ids", "camera_ids", "view_parameters",
        "temporal_indices", "conditioning_ancestry", "recipe_identity", "output_artifact_ids",
    }
    return (
        required <= set(lineage)
        and all(lineage.get(k) for k in required)
        and all("parent_frame_ids" in edge and edge.get("output_frame_id") for edge in lineage["conditioning_ancestry"])
    )


def low_vram_policy_valid(*, adaptation_class: str, changes_model_semantics: bool, recipe_bound: bool) -> bool:
    return adaptation_class == "EXECUTION_POLICY" and not changes_model_semantics and recipe_bound


def geometry_boundary_valid(*, output_type: str, canonical_geometry: bool, geometry_authority: str | None) -> bool:
    if canonical_geometry:
        return geometry_authority == "FA3-3D-GEOM-001"
    return output_type == "GENERATED_VISUAL_OBSERVATION_SET" and geometry_authority in (None, "")


def runtime_isolation_valid(*, isolated_environment: bool, immutable_revision: str, selects_host_stack: bool) -> bool:
    return isolated_environment and bool(immutable_revision) and immutable_revision not in {"main", "latest", "floating"} and not selects_host_stack


def hrb_placement_valid(*, accelerator_requested: bool, placement_authority: str, lease_id: str | None, lease_verified: bool) -> bool:
    if not accelerator_requested:
        return True
    return placement_authority == "FA3-AUTH-HOST-RESOURCE-BROKER-001" and bool(lease_id) and lease_verified


def disabled_provider_valid(*, enabled: bool, resident_processes: int, active_gpu_leases: int, polling_workers: int) -> bool:
    return enabled or (resident_processes == 0 and active_gpu_leases == 0 and polling_workers == 0)


def scan_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0

    def is_provider(value: Any) -> bool:
        return isinstance(value, str) and value.strip().lower() in {
            PROVIDER_ID.lower(), "stability sgm", "stability ai generative models / sgm"
        }

    def walk(value: Any, *, file: str, path: str, provider_scope: bool = False) -> None:
        if isinstance(value, dict):
            local_scope = provider_scope or any(is_provider(value.get(k)) for k in ("id", "provider_id", "name", "provider"))
            if local_scope and value.get("architectural_authority") is True:
                findings.append(_finding("SGM-AUTH-001", "SGM architectural authority was enabled", file=file, path=path))
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if "authority" in key.lower().replace("-", "_") and is_provider(child):
                    findings.append(_finding("SGM-AUTH-002", "SGM was assigned to an authority-bearing field", file=file, path=child_path))
                walk(child, file=file, path=child_path, provider_scope=local_scope)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, file=file, path=f"{path}[{index}]", provider_scope=provider_scope)

    for path in sorted((root / "canonical").rglob("*.json")):
        scanned += 1
        try:
            walk(_load(path), file=str(path.relative_to(root)), path="$")
        except Exception as exc:
            findings.append(_finding("SGM-AUTH-003", "Canonical JSON parse failure", file=str(path.relative_to(root)), error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL", "scanned_json_files": scanned, "findings": findings}


def reference_check(root: Path) -> dict[str, Any]:
    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-STABILITY-SGM-001.json",
        "contract": root / "canonical/contracts/FA3-GENERATIVE-PIPELINE-MULTIVIEW-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-STABILITY-SGM-2026-09-01.json",
        "reference": root / "canonical/references/FA3-STABILITY-SGM-UPSTREAM-REFERENCE-2026-09-01.json",
        "gate": root / "canonical/FA3-GATE-STABILITY-SGM-001.json",
        "enforcement": root / "canonical/stability-sgm-enforcement.json",
        "evidence": root / "evidence/reference/stability-sgm-ci-2026-09-01.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    findings: list[dict[str, Any]] = []
    records: dict[str, dict[str, Any]] = {}
    for name, path in paths.items():
        if not path.is_file():
            findings.append(_finding("SGM-REF-001", "Required materialization record is missing", record=name, path=str(path.relative_to(root))))
            continue
        try:
            records[name] = _load(path)
        except Exception as exc:
            findings.append(_finding("SGM-REF-002", "Required record is not valid JSON", record=name, error=str(exc)))
    if findings:
        return {"result": "FAIL", "findings": findings}

    if not provider_shape_valid(records["provider"]):
        findings.append(_finding("SGM-REF-003", "Provider shape or non-authority boundary mismatch"))
    contract = records["contract"]
    if contract.get("id") != CONTRACT_ID or contract.get("invariants") != P0_RULES:
        findings.append(_finding("SGM-REF-004", "Contract identity or invariant set mismatch"))
    decision = records["decision"]
    if decision.get("id") != DECISION_ID or decision.get("authority_decision", {}).get("capability_count_after") != CAPABILITY_COUNT:
        findings.append(_finding("SGM-REF-005", "Decision identity/capability invariant mismatch"))
    reference = records["reference"]
    if reference.get("id") != REFERENCE_ID or reference.get("resolved_commit") != UPSTREAM_COMMIT or reference.get("floating_reference_forbidden_for_promotion") is not True:
        findings.append(_finding("SGM-REF-006", "Immutable upstream reference mismatch"))
    enforcement = records["enforcement"]
    if enforcement.get("gate_id") != GATE_ID or enforcement.get("p0_invariants") != P0_RULES or enforcement.get("fail_closed") is not True:
        findings.append(_finding("SGM-REF-007", "Enforcement record mismatch"))
    evidence = records["evidence"]
    if (
        evidence.get("id") != EVIDENCE_ID or evidence.get("status") != "PASS"
        or evidence.get("mandatory_rules_passed") != len(P0_RULES)
        or evidence.get("current_host_runtime_evidence") is not False
        or evidence.get("capability_count_after") != CAPABILITY_COUNT
    ):
        findings.append(_finding("SGM-REF-008", "Reference evidence mismatch or overclaims runtime promotion"))
    policy = records["policy"]
    if GATE_ID not in policy.get("mandatory_reference_gates", []) or policy.get("stability_sgm_mandatory_p0_rules") != P0_RULES:
        findings.append(_finding("SGM-REF-009", "Global enforcement policy is not bound to the SGM gate/rules"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def regression_cases() -> list[dict[str, Any]]:
    components = [{"role": role, "identity": f"sha256:{i:064x}"} for i, role in enumerate(sorted(COMPONENT_ROLES), 1)]
    conditioning = [{"type": kind, "artifact_or_value_digest": f"sha256:{i:064x}"} for i, kind in enumerate(sorted(CONDITIONING_TYPES), 1)]
    recipe = {
        "model_artifact_id": "model:sv4d2",
        "model_revision": UPSTREAM_COMMIT,
        "config_digest": "sha256:" + "1" * 64,
        "component_identities": [x["identity"] for x in components],
        "sampler": "sampler:edm",
        "scheduler": "scheduler:explicit",
        "precision": "fp16",
        "conditioning_digest": "sha256:" + "2" * 64,
        "runtime_revision": "runtime:sgm-e8cd657",
    }
    license_record = {key: "KNOWN" for key in LICENSE_FIELDS}
    license_record.update({"code_license_admits_weights": False, "code_license_admits_outputs": False})
    lineage = {
        "source_artifact_id": "video:source",
        "source_frame_ids": ["frame:1"],
        "camera_ids": ["camera:1"],
        "view_parameters": [{"azimuth": 0}],
        "temporal_indices": [0],
        "conditioning_ancestry": [{"output_frame_id": "frame:out:1", "parent_frame_ids": ["frame:1"]}],
        "recipe_identity": recipe_identity(recipe),
        "output_artifact_ids": ["observation-set:1"],
    }
    checks = [
        component_addressability_valid(components),
        typed_conditioning_valid(conditioning),
        sampler_authority_valid(sampler_component=True, owns_model_or_routing_authority=False),
        guidance_separation_valid(guider_identity="guider:cfg", sampler_identity="sampler:edm", independently_addressable=True),
        denoising_semantics_valid(training_semantics="EDM_TRAIN", inference_semantics="EDM_SAMPLE", explicit_mapping=True),
        recipe_identity_valid(recipe, recipe_identity(recipe)),
        artifact_integrity_valid(container_sha256="a" * 64, tensor_payload_sha256="b" * 64, format_permits_tensor_hash=True),
        license_separation_valid(license_record),
        camera_conditioning_valid({"camera_id": "cam:1", "intrinsics_digest": "sha256:i", "extrinsics_digest": "sha256:e", "view_index": 0, "temporal_index": 0}),
        quality_dimensions_valid({"temporal_consistency": 0.9, "multi_view_consistency": 0.8, "camera_trajectory_conformance": 1.0}),
        autoregressive_ancestry_valid(lineage),
        low_vram_policy_valid(adaptation_class="EXECUTION_POLICY", changes_model_semantics=False, recipe_bound=True),
        geometry_boundary_valid(output_type="GENERATED_VISUAL_OBSERVATION_SET", canonical_geometry=False, geometry_authority=None),
        runtime_isolation_valid(isolated_environment=True, immutable_revision=UPSTREAM_COMMIT, selects_host_stack=False),
        hrb_placement_valid(accelerator_requested=True, placement_authority="FA3-AUTH-HOST-RESOURCE-BROKER-001", lease_id="lease:1", lease_verified=True),
        disabled_provider_valid(enabled=False, resident_processes=0, active_gpu_leases=0, polling_workers=0),
    ]
    return [{"rule": rule, "result": "PASS" if passed else "FAIL"} for rule, passed in zip(P0_RULES, checks)]


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    reference = reference_check(root)
    authority = scan_authority_assignments(root)
    cases = regression_cases()
    failed = [case for case in cases if case["result"] != "PASS"]
    findings = list(reference.get("findings", [])) + list(authority.get("findings", []))
    if failed:
        findings.append(_finding("SGM-REG-001", "One or more mandatory executable regression cases failed", failed_rules=[x["rule"] for x in failed]))
    result = "PASS" if not findings and reference["result"] == "PASS" and authority["result"] == "PASS" else "FAIL"
    report = {
        "schema": "fa3.stability-sgm-gate-report.v1",
        "gate_id": GATE_ID,
        "executable_gate_id": EXECUTABLE_GATE_ID,
        "provider_id": PROVIDER_ID,
        "contract_id": CONTRACT_ID,
        "upstream_commit": UPSTREAM_COMMIT,
        "result": result,
        "blocking_findings": len(findings),
        "findings": findings,
        "reference_check": reference,
        "authority_scan": authority,
        "regressions": {"passed": len(cases) - len(failed), "failed": len(failed), "total": len(cases), "cases": cases},
        "runtime_provider_required": False,
        "current_host_runtime_evidence": False,
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
    }
    _write(root / "reports/stability-sgm-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
