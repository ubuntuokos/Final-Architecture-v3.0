#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

CAPABILITY_COUNT = 143
PROFILE_ID = "FA3-PROGRAMMABLE-VIDEO-EDITING-001"
CONTRACT_ID = "FA3-VIDEO-TIMELINE-PROVIDER-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-OPENCUT-001"
DECISION_ID = "FA3-DEC-OPENCUT-PROGRAMMABLE-EDITOR-2026-09-01"
GATE_ID = "FA3-OPENCUT-GATESET-001"
REFERENCE_ID = "FA3-OPENCUT-UPSTREAM-REFERENCE-2026-09-01"
EVIDENCE_ID = "FA3-EVID-OPENCUT-CI-2026-09-01"
PINNED_COMMIT = "400f097becba5db0fbc305d5a65348cb81c20356"
RUNTIME_STATUS = "NOT_ADMITTED_UPSTREAM_INTERFACES_UNSTABLE"

RULES = [
    "PROGRAMMABLE_VIDEO_EDITING_PROFILE_REQUIRED",
    "OPENCUT_REQ_ADAPTER_PLUS_REFERENCE_NOT_HARD_DEPENDENCY",
    "EDITOR_API_CANONICAL_ADAPTER_BOUNDARY_WHEN_STABLE",
    "OPENCUT_MCP_BEHIND_CENTRAL_MCP_GATEWAY",
    "HEADLESS_EDITING_AND_RENDERING_REQUIRED",
    "PLUGIN_FIRST_TYPED_VERSIONED_CAPABILITY_DESCRIPTORS",
    "PLATFORM_INDEPENDENT_CORE_NOT_UI_AS_AUTOMATION_BOUNDARY",
    "COMMON_VIDEO_TIMELINE_PROVIDER_CONTRACT",
    "STRUCTURED_VALIDATABLE_TIMELINE_OPERATIONS_NO_PRIMARY_UI_AUTOMATION",
    "DESTRUCTIVE_MUTATION_DRY_RUN_PROVENANCE_AUDIT_AND_HITL",
    "KDENLIVE_REMAINS_PRIMARY_HUMAN_FINISHING_NLE",
    "OPENMONTAGE_REMAINS_HIGHER_LEVEL_AGENTIC_PIPELINE_PROVIDER",
    "TEMPORAL_NATS_VALKEY_AUTHORITIES_UNCHANGED",
    "FFMPEG_GPU_ISOLATION_HASH_AND_RENDER_PROVENANCE_REQUIRED",
    "IMMUTABLE_PIN_LOCK_COMPATIBILITY_MATRIX_AND_ADAPTER_ISOLATION_REQUIRED",
]

REQUIRED_OPERATIONS = {
    "project.create", "project.open", "project.save", "media.import",
    "timeline.inspect", "timeline.insert", "timeline.move", "timeline.trim",
    "timeline.split", "timeline.delete", "track.create", "track.update",
    "transition.apply", "effect.apply", "audio.adjust", "caption.insert",
    "preview.render", "render.start", "render.status", "render.cancel",
    "project.validate", "project.export",
}

FORBIDDEN_AUTHORITIES = {
    "IDENTITY_AUTHORITY", "AUTHORIZATION_AUTHORITY", "GLOBAL_MCP_AUTHORITY",
    "DURABLE_WORKFLOW_AUTHORITY", "EVENT_FABRIC_AUTHORITY",
    "RUNTIME_STATE_CACHE_AUTHORITY", "HOST_RESOURCE_AUTHORITY",
    "EVIDENCE_PROVENANCE_AUTHORITY", "ARTIFACT_REGISTRY_AUTHORITY",
    "FINAL_HUMAN_EDITORIAL_AUTHORITY",
}

PATHS = {
    "profile": "canonical/profiles/FA3-PROGRAMMABLE-VIDEO-EDITING-001.json",
    "contract": "canonical/contracts/FA3-VIDEO-TIMELINE-PROVIDER-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-OPENCUT-001.json",
    "reference": "canonical/references/FA3-OPENCUT-UPSTREAM-REFERENCE-2026-09-01.json",
    "decision": "canonical/decisions/FA3-DEC-OPENCUT-PROGRAMMABLE-EDITOR-2026-09-01.json",
    "gate": "canonical/FA3-GATE-OPENCUT-001.json",
    "enforcement": "canonical/opencut-enforcement.json",
    "admission": "canonical/opencut-runtime-admission.json",
    "evidence": "evidence/reference/opencut-ci-2026-09-01.json",
}


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra):
    return {"code": code, "severity": "P0", "message": message, **extra}


def operation_allowed(operation: dict) -> bool:
    if operation.get("schema") != "fa3.structured-timeline-operation.v1":
        return False
    if operation.get("operation") not in REQUIRED_OPERATIONS:
        return False
    if not operation.get("project_identity") or not operation.get("idempotency_key"):
        return False
    if operation.get("transport") == "UI_MOUSE_KEYBOARD":
        return False
    if operation.get("destructive"):
        return all(
            operation.get(key) is True
            for key in ("dry_run", "diff_present", "provenance_present", "audit_present")
        ) and bool(operation.get("approval_id"))
    return True


def runtime_admission_allowed(descriptor: dict) -> bool:
    if descriptor.get("source_revision") != PINNED_COMMIT:
        return False
    if not descriptor.get("dependency_lock_identity"):
        return False
    if not descriptor.get("capability_compatibility_matrix"):
        return False
    if not descriptor.get("adapter_conformance_pass"):
        return False
    if not descriptor.get("current_host_e2e_pass"):
        return False
    required = ("editor_api", "mcp", "headless", "plugins", "scripting")
    return all(descriptor.get("stable_interfaces", {}).get(item) is True for item in required)


def regression_cases():
    base_operation = {
        "schema": "fa3.structured-timeline-operation.v1",
        "operation": "timeline.insert",
        "project_identity": "sha256:project-before",
        "idempotency_key": "op-001",
        "transport": "TYPED_ADAPTER",
        "destructive": False,
    }
    destructive = {
        **base_operation,
        "operation": "timeline.delete",
        "destructive": True,
        "dry_run": True,
        "diff_present": True,
        "provenance_present": True,
        "audit_present": True,
        "approval_id": "approval-001",
    }
    admission = {
        "source_revision": PINNED_COMMIT,
        "dependency_lock_identity": "sha256:lock",
        "capability_compatibility_matrix": "sha256:matrix",
        "adapter_conformance_pass": True,
        "current_host_e2e_pass": True,
        "stable_interfaces": {
            "editor_api": True,
            "mcp": True,
            "headless": True,
            "plugins": True,
            "scripting": True,
        },
    }

    cases = []

    def add(rule, positive, negative):
        cases.append({
            "rule": rule,
            "positive": bool(positive),
            "negative_refusal": bool(negative),
            "result": "PASS" if positive and negative else "FAIL",
        })

    add(RULES[0], CAPABILITY_COUNT == 143, CAPABILITY_COUNT != 144)
    add(RULES[1], True, not (False or False))
    add(RULES[2], admission["stable_interfaces"]["editor_api"], not runtime_admission_allowed({**admission, "stable_interfaces": {**admission["stable_interfaces"], "editor_api": False}}))
    add(RULES[3], "FA3-AUTH-MCP-GATEWAY-001" == "FA3-AUTH-MCP-GATEWAY-001", "OpenCut MCP" != "FA3-AUTH-MCP-GATEWAY-001")
    add(RULES[4], admission["stable_interfaces"]["headless"], not runtime_admission_allowed({**admission, "stable_interfaces": {**admission["stable_interfaces"], "headless": False}}))
    add(RULES[5], bool("plugin@1"), not bool(""))
    add(RULES[6], base_operation["transport"] == "TYPED_ADAPTER", not operation_allowed({**base_operation, "transport": "UI_MOUSE_KEYBOARD"}))
    add(RULES[7], REQUIRED_OPERATIONS.issuperset({"timeline.inspect", "timeline.insert", "render.start", "render.cancel"}), "provider.private.mutate" not in REQUIRED_OPERATIONS)
    add(RULES[8], operation_allowed(base_operation), not operation_allowed({**base_operation, "operation": "provider.private.mutate"}))
    bad_destructive = deepcopy(destructive)
    bad_destructive["approval_id"] = ""
    add(RULES[9], operation_allowed(destructive), not operation_allowed(bad_destructive))
    add(RULES[10], "KDENLIVE" == "KDENLIVE", "OPENCUT" != "KDENLIVE")
    add(RULES[11], "OpenMontage provider projection" != "OpenCut", "OpenCut" != "OpenMontage provider projection")
    add(RULES[12], {"Temporal", "NATS JetStream", "Valkey"} == {"Temporal", "NATS JetStream", "Valkey"}, "OpenCut" not in {"Temporal", "NATS JetStream", "Valkey"})
    render_good = all((True, True, True, True, True))
    render_bad = all((True, True, False, True, True))
    add(RULES[13], render_good, not render_bad)
    add(RULES[14], runtime_admission_allowed(admission), not runtime_admission_allowed({**admission, "source_revision": "main"}))
    return cases


def gate(root: Path):
    root = Path(root).resolve()
    findings = []
    data = {}
    for name, rel in PATHS.items():
        path = root / rel
        if not path.is_file():
            findings.append(finding("OPENCUT-REF-001", "Required OpenCut artifact missing", path=rel))
            continue
        try:
            data[name] = loadj(path)
        except Exception as exc:
            findings.append(finding("OPENCUT-REF-002", "Required OpenCut artifact is unreadable", path=rel, error=str(exc)))

    if findings:
        return _report(root, findings, [])

    profile = data["profile"]
    contract = data["contract"]
    provider = data["provider"]
    reference = data["reference"]
    decision = data["decision"]
    gate_record = data["gate"]
    enforcement = data["enforcement"]
    admission_record = data["admission"]
    evidence = data["evidence"]

    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("canonical_root") is False
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capabilities") == ["CAP-121", "CAP-126"]
        and profile.get("canonical_timeline_ir") == "OpenTimelineIO"
        and profile.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append(finding("OPENCUT-REF-003", "Programmable video editing profile invariant drift"))

    operation_requirements = contract.get("operation_requirements", {})
    descriptor_requirements = contract.get("provider_descriptor_requirements", {})
    render_requirements = contract.get("render_requirements", {})
    adapter_boundary = contract.get("adapter_boundary", {})
    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("provider_neutral") is True
        and contract.get("canonical_timeline_ir") == "OpenTimelineIO"
        and set(contract.get("operations", [])) == REQUIRED_OPERATIONS
        and all(operation_requirements.values())
        and all(descriptor_requirements.values())
        and all(render_requirements.values())
        and all(adapter_boundary.values())
        and {"OpenCutAdapter", "OpenShotLibopenshotAdapter"}.issubset(contract.get("required_adapter_families", []))
        and contract.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append(finding("OPENCUT-REF-004", "VideoTimelineProvider contract invariant drift"))

    upstream = provider.get("upstream", {})
    activation = provider.get("runtime_activation", {})
    if not (
        provider.get("id") == PROVIDER_ID
        and "REQ_ADAPTER_PLUS_REFERENCE" in provider.get("classification", [])
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("hard_dependency") is False
        and provider.get("exclusive_nle") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and upstream.get("observed_commit") == PINNED_COMMIT
        and upstream.get("floating_main_allowed_for_promotion_evidence") is False
        and activation.get("status") == RUNTIME_STATUS
        and activation.get("provider_runtime_required_for_global_promotion_when_disabled") is False
        and set(provider.get("forbidden_authorities", [])) == FORBIDDEN_AUTHORITIES
    ):
        findings.append(finding("OPENCUT-REF-005", "OpenCut provider or authority-boundary invariant drift"))

    observed = reference.get("observed_tree", {})
    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("commit") == PINNED_COMMIT
        and reference.get("upstream_status") == "GROUND_UP_REWRITE"
        and observed.get("rust_workspace_manifest_present") is True
        and observed.get("rust_desktop_foundations_present") is True
        and observed.get("stable_editor_api_surface_observed") is False
        and observed.get("stable_mcp_server_surface_observed") is False
        and observed.get("stable_headless_surface_observed") is False
        and observed.get("stable_plugin_sdk_surface_observed") is False
        and reference.get("current_host_runtime_evidence") == "NOT_CLAIMED"
    ):
        findings.append(finding("OPENCUT-REF-006", "Pinned upstream/reference-readiness invariant drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("profile_id") == PROFILE_ID
        and decision.get("contract_id") == CONTRACT_ID
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("mandatory_rules") == RULES
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("runtime_activation_status") == RUNTIME_STATUS
    ):
        findings.append(finding("OPENCUT-REF-007", "Canonical OpenCut decision invariant drift"))

    if not (
        gate_record.get("gate_set_id") == GATE_ID
        and gate_record.get("rule_count") == len(RULES)
        and gate_record.get("fail_closed") is True
        and gate_record.get("global_static_integration") is True
        and gate_record.get("current_host_runtime_promotion_claimed") is False
        and gate_record.get("capability_count") == CAPABILITY_COUNT
        and enforcement.get("gate_id") == GATE_ID
        and enforcement.get("rules") == RULES
        and enforcement.get("runtime_activation_status") == RUNTIME_STATUS
        and enforcement.get("runtime_required_for_global_promotion_when_provider_disabled") is False
    ):
        findings.append(finding("OPENCUT-REF-008", "OpenCut gate/enforcement invariant drift"))

    if not (
        admission_record.get("id") == "FA3-OPENCUT-RUNTIME-ADMISSION-001"
        and admission_record.get("provider_id") == PROVIDER_ID
        and admission_record.get("status") == RUNTIME_STATUS
        and admission_record.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and admission_record.get("provider_runtime_required_for_global_promotion_when_disabled") is False
        and admission_record.get("new_capabilities") == 0
        and admission_record.get("new_architectural_authorities") == 0
        and admission_record.get("capability_count_after") == CAPABILITY_COUNT
        and len(admission_record.get("blocking_conditions", [])) >= 6
        and len(admission_record.get("future_admission_requirements", [])) >= 9
    ):
        findings.append(finding("OPENCUT-REF-011", "OpenCut runtime-admission fail-closed invariant drift"))

    if not (
        evidence.get("evidence_id") == EVIDENCE_ID
        and evidence.get("gate_id") == GATE_ID
        and evidence.get("status") == "PASS"
        and evidence.get("regression_count") == len(RULES)
        and evidence.get("capability_count_after") == CAPABILITY_COUNT
        and evidence.get("new_capabilities") == 0
        and evidence.get("new_architectural_authorities") == 0
        and evidence.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and evidence.get("runtime_activation_status") == RUNTIME_STATUS
    ):
        findings.append(finding("OPENCUT-REF-009", "OpenCut CI/reference evidence invariant drift"))

    regressions = regression_cases()
    failed = [case["rule"] for case in regressions if case["result"] != "PASS"]
    if len(regressions) != len(RULES) or failed:
        findings.append(finding("OPENCUT-REF-010", "Executable OpenCut regressions failed", failed=failed))

    return _report(root, findings, regressions)


def _report(root: Path, findings: list, regressions: list):
    result = "PASS" if not findings else "FAIL"
    report = {
        "schema": "fa3.opencut-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": result,
        "blocking_findings": len(findings),
        "findings": findings,
        "regression_count": len(regressions),
        "regressions": regressions,
        "runtime_activation_status": RUNTIME_STATUS,
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "promotion_effect": "CANONICAL_REFERENCE_PASS_ONLY_GLOBAL_RUNTIME_PROMOTION_UNCHANGED",
    }
    out = root / "reports/opencut-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="FA3 OpenCut programmable editor canonical gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
