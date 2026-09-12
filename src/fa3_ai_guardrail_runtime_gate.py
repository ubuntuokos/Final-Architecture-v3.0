#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-AI-SEC-VALIDATION-001"
CONTRACT_ID = "FA3-AI-GUARDRAIL-RUNTIME-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-ANY-GUARDRAIL-001"
DECISION_ID = "FA3-DEC-ANY-GUARDRAIL-2026-09-07"
REFERENCE_ID = "FA3-ANY-GUARDRAIL-UPSTREAM-REFERENCE-2026-09-07"
GATE_ID = "FA3-AI-GUARDRAIL-RUNTIME-GATESET-001"
CAPABILITY_COUNT = 143
REFERENCE_RELEASE = "0.7.7"
REFERENCE_COMMIT = "8cb63bd664a0b7f44deb81a14b575611277fafe8"

P0_INVARIANTS = [
    "GUARDRAIL_PROVIDER_NOT_SECURITY_AUTHORITY",
    "GUARDRAIL_CAPABILITY_TASK_MAPPING_REQUIRED",
    "GUARDRAIL_INPUT_OUTPUT_TOOL_PHASES_DISTINCT",
    "GUARDRAIL_TOOL_VERDICT_NOT_TOOL_AUTHORIZATION",
    "GUARDRAIL_FAIL_MODE_EXPLICIT_AND_RISK_TIERED",
    "GUARDRAIL_HEALTH_READINESS_DISTINCT",
    "GUARDRAIL_READINESS_DEPENDENCY_MODEL_AUTH_CACHE_SMOKE_REQUIRED",
    "GUARDRAIL_BENCHMARK_CALIBRATION_REQUIRED_BEFORE_PROMOTION",
    "GUARDRAIL_MODEL_PROVIDER_VERSION_PROVENANCE_REQUIRED",
    "GUARDRAIL_ERROR_FALLBACK_AND_AUDIT_METADATA_REQUIRED",
    "GUARDRAIL_MODEL_BACKED_CONCURRENCY_EVIDENCE_REQUIRED",
    "GUARDRAIL_PLAINTEXT_SECRET_FORBIDDEN",
    "GUARDRAIL_RUNTIME_DOWNLOAD_POLICY_EXPLICIT",
    "GUARDRAIL_SYSTEMD_UNIT_DIRECTIVE_VALIDATION_REQUIRED",
    "GUARDRAIL_PRESSURE_BEFORE_OOM_AND_TELEMETRY_REQUIRED",
    "GUARDRAIL_GRACEFUL_MULTIPROCESS_TERMINATION_REQUIRED",
    "GUARDRAIL_HOST_PLACEMENT_REMAINS_HRB_OWNED",
]


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, value: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if value else "FAIL", "detail": detail}


def capability_task_valid(*, capability: str, task: str, validated_mapping: dict[str, list[str]], verdict: str) -> bool:
    if task not in validated_mapping.get(capability, []):
        return verdict not in {"ALLOW", "PASS"}
    return True


def readiness_valid(*, dependency_ok: bool, model_identity_ok: bool, auth_ok: bool,
                    cache_ok: bool, capability_smoke_ok: bool) -> bool:
    return all([dependency_ok, model_identity_ok, auth_ok, cache_ok, capability_smoke_ok])


def fail_mode_valid(*, risk_tier: str, fail_mode: str, privileged_or_destructive_tool: bool) -> bool:
    allowed = {"FAIL_OPEN", "FAIL_CLOSED", "DEGRADE_TO_SECONDARY_PROVIDER", "HUMAN_APPROVAL"}
    if fail_mode not in allowed:
        return False
    if privileged_or_destructive_tool:
        return fail_mode in {"FAIL_CLOSED", "HUMAN_APPROVAL"}
    return bool(risk_tier)


def concurrency_valid(*, worker_count: int, model_backed: bool, shared_model_proven: bool,
                      benchmark_pass: bool, memory_budget_pass: bool) -> bool:
    if worker_count < 1:
        return False
    if not model_backed or worker_count == 1:
        return True
    return shared_model_proven and benchmark_pass and memory_budget_pass


def unit_projection_valid(unit_text: str) -> tuple[bool, list[str]]:
    findings: list[str] = []
    section = ""
    singleton_values: dict[tuple[str, str], str] = {}
    service_only = {
        "MemoryHigh", "MemoryMax", "MemorySwapMax", "OOMPolicy", "OOMScoreAdjust",
        "CPUQuota", "CPUWeight", "IOWeight", "Nice", "CPUAffinity", "TimeoutStopSec",
        "KillMode", "SendSIGKILL", "LimitNOFILE", "Environment", "EnvironmentFile",
    }
    unit_only = {"StartLimitIntervalSec", "StartLimitBurst"}
    conflict_sensitive = {
        "MemoryHigh", "MemoryMax", "MemorySwapMax", "OOMPolicy", "CPUQuota",
        "CPUAffinity", "Slice", "Nice", "TimeoutStopSec", "KillMode",
        "StartLimitIntervalSec", "StartLimitBurst",
    }
    secret_pattern = re.compile(r"(?i)(HF_TOKEN|HUGGINGFACE_HUB_TOKEN|API_KEY|ACCESS_TOKEN)\s*=\s*hf_[A-Za-z0-9]+")
    for raw in unit_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if "=" not in line:
            continue
        key, value = [x.strip() for x in line.split("=", 1)]
        if key in service_only and section != "Service":
            findings.append(f"{key} must be in [Service]")
        if key in unit_only and section != "Unit":
            findings.append(f"{key} must be in [Unit]")
        if secret_pattern.search(line):
            findings.append("plaintext provider credential in unit")
        if key in conflict_sensitive:
            slot = (section, key)
            if slot in singleton_values and singleton_values[slot] != value:
                findings.append(f"conflicting duplicate {key}")
            singleton_values.setdefault(slot, value)
    return not findings, findings


def _forbidden_hardcoded_runtime_value(obj: Any) -> bool:
    forbidden_numeric_keys = {
        "cpu_id", "cpu_ids", "cpu_list", "numa_node", "numa_nodes", "cuda_ordinal",
        "cuda_visible_devices", "worker_count", "workers", "port", "cpu_quota_percent",
        "memory_high_gb", "memory_max_gb",
    }
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() in forbidden_numeric_keys and isinstance(value, (int, float)):
                return True
            if _forbidden_hardcoded_runtime_value(value):
                return True
    elif isinstance(obj, list):
        return any(_forbidden_hardcoded_runtime_value(v) for v in obj)
    return False


def evaluate(root: Path) -> dict[str, Any]:
    paths = {
        "profile": root / "canonical/profiles/FA3-AI-SEC-VALIDATION-001.json",
        "contracts": root / "canonical/contracts/FA3-AI-GUARDRAIL-RUNTIME-CONTRACTS-001.json",
        "provider": root / "canonical/providers/FA3-PROVIDER-ANY-GUARDRAIL-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-ANY-GUARDRAIL-2026-09-07.json",
        "reference": root / "canonical/references/FA3-ANY-GUARDRAIL-UPSTREAM-REFERENCE-2026-09-07.json",
        "enforcement": root / "canonical/any-guardrail-runtime-enforcement.json",
        "hrb": root / "canonical/contracts/FA3-HOST-RESOURCE-BROKER-CONTRACTS-001.json",
        "systemd": root / "canonical/providers/FA3-PROVIDER-SYSTEMD-CGROUPV2-001.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        return {"schema": "fa3.ai-guardrail-runtime-gate-report.v1", "gate_id": GATE_ID,
                "status": "FAIL", "checks": [check("required-artifacts", False, f"missing: {', '.join(missing)}")]} 

    profile = loadj(paths["profile"])
    contract = loadj(paths["contracts"])
    provider = loadj(paths["provider"])
    decision = loadj(paths["decision"])
    reference = loadj(paths["reference"])
    enforcement = loadj(paths["enforcement"])
    hrb = loadj(paths["hrb"])
    systemd = loadj(paths["systemd"])
    policy = loadj(paths["policy"])

    semantics = contract.get("mandatory_semantics", {})
    upstream = provider.get("upstream", {})
    capability_policy = provider.get("capability_policy", {})
    preflight = provider.get("runtime_preflight", {})
    concurrency = provider.get("concurrency_policy", {})
    placement = provider.get("placement_policy", {})
    systemd_validation = systemd.get("unit_validation_policy", {})
    model_runtime = systemd.get("model_backed_runtime_policy", {})
    hrb_contracts = set(hrb.get("contracts", []))

    checks = [
        check("capability-count-stable", all(x.get("capability_count", 143) == CAPABILITY_COUNT for x in [profile, contract, provider, hrb, systemd]), "capability count remains 143"),
        check("no-new-authority", contract.get("new_architectural_authority") is False and provider.get("new_architectural_authority") is False and provider.get("architectural_authority") is False, "no new architectural authority"),
        check("global-gate-binding", GATE_ID in policy.get("mandatory_reference_gates", []), "guardrail gate is globally mandatory"),
        check("profile-binding", CONTRACT_ID in profile.get("contracts", []) and PROVIDER_ID in profile.get("providers", []), "runtime contract/provider bound to existing AI security profile"),
        check("provider-boundaries", provider.get("parent_profile") == PROFILE_ID and provider.get("authority_boundaries", {}).get("security_policy") == "FA3-AUTH-SECURITY-GOV-001" and provider.get("authority_boundaries", {}).get("host_resource") == "FA3-AUTH-HOST-RESOURCE-BROKER-001", "security and host-resource authorities remain existing FA3 authorities"),
        check("immutable-upstream", upstream.get("repository") == "mozilla-ai/any-guardrail" and upstream.get("reference_release") == REFERENCE_RELEASE and upstream.get("reference_commit") == REFERENCE_COMMIT and upstream.get("floating_main_allowed_as_promotion_evidence") is False, "upstream reference is immutable"),
        check("capability-task-scoped", capability_policy.get("backend_capability_mapping_required") is True and capability_policy.get("backend_may_be_used_only_for_validated_tasks") is True and semantics.get("capability_task_match_required") is True, "guardrail use is task/capability scoped"),
        check("deepset-not-generic-harm", capability_policy.get("deepset_reference_classification") == "PROMPT_INJECTION_DETECTION_NOT_GENERIC_HARM_MODERATION", "Deepset reference semantics are not misclassified"),
        check("tool-authorization-separated", semantics.get("tool_boundary_guardrail_is_authorization_authority") is False and semantics.get("tool_execution_requires_existing_deterministic_schema_permission_policy_or_approval_authority") is True, "guardrail verdict cannot authorize tool execution"),
        check("risk-tier-fail-mode", semantics.get("privileged_or_destructive_tool_execution_default") == "FAIL_CLOSED_OR_HUMAN_APPROVAL" and provider.get("fail_mode_policy", {}).get("must_be_explicit_per_endpoint_and_risk_tier") is True, "fail mode is explicit and privileged actions fail closed/approval"),
        check("health-readiness-separated", semantics.get("health_is_readiness") is False and preflight.get("health_and_readiness_separate") is True, "process health is not readiness"),
        check("readiness-preflight", preflight.get("optional_dependency_extras_verified") is True and preflight.get("credential_mapping_verified_when_required") is True and preflight.get("central_cache_policy_required") is True and len(semantics.get("readiness_requires", [])) >= 5, "dependency/model/auth/cache/smoke readiness required"),
        check("benchmark-promotion", semantics.get("promotion_requires_benchmark_calibration") is True and len(semantics.get("benchmark_dimensions", [])) >= 8, "benchmark/calibration gates promotion"),
        check("secret-shell-boundary", preflight.get("interactive_shell_or_bashrc_dependency_forbidden") is True and preflight.get("plaintext_secret_in_unit_or_repository_forbidden") is True, "no bashrc dependency or plaintext unit/repo credential"),
        check("runtime-download-policy", preflight.get("runtime_download_policy_explicit") is True, "runtime model/artifact download is policy-controlled"),
        check("concurrency-evidenced", concurrency.get("static_high_worker_count_for_model_backed_runtime_forbidden") is True and concurrency.get("safe_default_when_model_sharing_unproven") == "SINGLE_WORKER" and len(concurrency.get("multi_worker_requires", [])) >= 4, "model-backed worker count is evidence-derived"),
        check("hrb-extension", {"ModelBackedWorkerConcurrencyPolicy", "SystemdUnitValidationPolicy", "GracefulTerminationPolicy", "PressureTelemetryPolicy"}.issubset(hrb_contracts), "HRB typed QoS/runtime contracts present"),
        check("systemd-unit-validation", systemd_validation.get("duplicate_or_conflicting_directives_forbidden") is True and systemd_validation.get("directive_section_validation_required") is True and systemd_validation.get("host_systemd_version_and_feature_detection_required") is True and systemd_validation.get("unknown_or_ignored_directive_blocks_promotion") is True, "systemd projection validates directive conflicts/sections/features"),
        check("pressure-before-oom", "ManagedOOMMemoryPressure" in systemd.get("canonical_mapping", {}).get("pressure_policy_when_supported", []) and "memory.pressure_or_PSI_when_supported" in systemd.get("pressure_telemetry", []) and "oom_and_oom_kill_events" in systemd.get("pressure_telemetry", []), "pressure and OOM telemetry are explicit"),
        check("graceful-multiprocess-stop", model_runtime.get("worker_death_and_respawn_telemetry_required") is True and model_runtime.get("stuck_deactivating_or_unbounded_stop_forbidden") is True and "KillMode" in systemd.get("canonical_mapping", {}).get("graceful_termination_policy", []), "bounded child lifecycle is explicit"),
        check("host-values-not-canonical", placement.get("fixed_cpu_ids_forbidden") is True and placement.get("fixed_numa_node_forbidden") is True and placement.get("fixed_cuda_ordinal_as_canonical_identity_forbidden") is True and not _forbidden_hardcoded_runtime_value(provider), "host values remain HRB runtime projections"),
        check("decision-closed", decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_CLOSED" and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0 and decision.get("capability_count_after") == CAPABILITY_COUNT and decision.get("mandatory_canonical_rules") == P0_INVARIANTS, "decision is closed with no capability/authority change"),
        check("reference-pinned", reference.get("id") == REFERENCE_ID and reference.get("stable_reference", {}).get("release") == REFERENCE_RELEASE and reference.get("stable_reference", {}).get("commit_sha") == REFERENCE_COMMIT, "reference record matches immutable upstream pin"),
        check("enforcement-complete", enforcement.get("gate_id") == GATE_ID and enforcement.get("fail_closed") is True and enforcement.get("p0_invariants") == P0_INVARIANTS and enforcement.get("mandatory_rule_count") == len(P0_INVARIANTS) and len(enforcement.get("rules", [])) == len(P0_INVARIANTS), "all guardrail runtime invariants are fail-closed"),
    ]
    passed = all(c["status"] == "PASS" for c in checks)
    return {
        "schema": "fa3.ai-guardrail-runtime-gate-report.v1",
        "gate_id": GATE_ID,
        "status": "PASS" if passed else "FAIL",
        "current_host_runtime_promotion_claim": False,
        "checks": checks,
        "summary": {"passed": sum(c["status"] == "PASS" for c in checks), "total": len(checks)},
    }


def gate(root: Path) -> dict[str, Any]:
    result = evaluate(root)
    report = root / "reports/any-guardrail-runtime-gate-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"result": result["status"], **result}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report")
    args = parser.parse_args()
    result = evaluate(Path(args.root).resolve())
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
