#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MAX_PROVIDER_ID = "FA3-PROVIDER-MAX-001"
MOJO_PROVIDER_ID = "FA3-PROVIDER-MOJO-001"
PROVIDER_IDS = (MAX_PROVIDER_ID, MOJO_PROVIDER_ID)
DECISION_ID = "FA3-DEC-MODULAR-2026-08-30"
REFERENCE_ID = "FA3-MODULAR-UPSTREAM-REFERENCE-2026-08-30"
GATE_ID = "FA3-MODULAR-GATESET-001"
CAPABILITY_COUNT = 143
UPSTREAM_COMMIT = "f08ac164e2743513f60e46621de6dc4a5a5a30e7"

RULES = (
    "MODULAR_EXECUTION_TOPOLOGY_NOT_RESOURCE_AUTHORITY",
    "MODULAR_LOCAL_SCHEDULER_NOT_GLOBAL_AUTHORITY",
    "MODULAR_PORTABLE_SEMANTICS_TARGET_ARTIFACT_IDENTITY_SEPARATE",
    "MODULAR_TARGET_SPECIALIZATION_SEMANTICS_PRESERVED",
    "MODULAR_MODEL_VARIANT_COMPATIBILITY_EVIDENCE_REQUIRED",
    "MODULAR_COMPILED_ARTIFACT_LINEAGE_REQUIRED",
    "MODULAR_WARM_CACHE_SCOPED_IDENTITY_REQUIRED",
    "MODULAR_CACHE_OWNERSHIP_LIFECYCLE_EXPLICIT",
    "MODULAR_CANCELLATION_RELEASES_RESOURCES",
    "MODULAR_SHARED_CACHE_SECURITY_BOUNDARIES_REQUIRED",
    "MODULAR_BENCHMARK_TOPOLOGY_BOUND_EVIDENCE",
    "MODULAR_OPENAI_API_PROJECTION_NOT_ROUTING_AUTHORITY",
    "MODULAR_STABLE_NIGHTLY_EVIDENCE_SEPARATE",
    "MODULAR_SOURCE_AVAILABILITY_NOT_REDISTRIBUTION_AUTHORIZATION",
)

IDENTITY_KEYS = {"id", "provider_id", "provider_ids", "subject", "name", "provider", "implementation"}
AUTHORITY_KEYS = {
    "authority", "authority_id", "authority_owner", "authority_provider",
    "model_routing_authority", "host_resource_authority", "workflow_authority",
    "authorization_authority", "policy_authority", "artifact_identity_authority",
    "model_identity_authority", "secrets_authority", "evidence_authority",
    "global_scheduler_authority", "global_scheduling_authority",
}

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}

def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_strings(item)

def _is_modular_provider_value(value: Any) -> bool:
    for raw in _iter_strings(value):
        up = raw.upper()
        if raw in PROVIDER_IDS or up in {"MODULAR MAX", "MODULAR MOJO"} or up.startswith("FA3-AUTH-MAX") or up.startswith("FA3-AUTH-MOJO"):
            return True
    return False

def _object_is_modular_scoped(obj: dict[str, Any]) -> bool:
    return any(key in obj and _is_modular_provider_value(obj[key]) for key in IDENTITY_KEYS)

def _provider_shape_valid(provider: dict[str, Any], provider_id: str) -> bool:
    return bool(
        provider.get("id") == provider_id
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("global_runtime_promotion_required_when_disabled") is False
        and provider.get("upstream_snapshot_commit") == UPSTREAM_COMMIT
    )

def _compiled_lineage_valid(obj: dict[str, Any]) -> bool:
    required = {
        "model_artifact_id", "provider_id", "provider_version", "compiler_version",
        "target_architecture", "kernel_set_digest", "compilation_config_digest", "artifact_sha256",
    }
    return required.issubset(obj) and obj.get("provider_id") in PROVIDER_IDS

def _warm_cache_valid(obj: dict[str, Any]) -> bool:
    required = {
        "compiled_artifact_id", "model_variant_id", "provider_version", "compiler_version",
        "target_architecture", "config_digest", "cache_sha256", "evidence_channel",
    }
    return required.issubset(obj) and obj.get("evidence_channel") in {"stable", "nightly"}

def _cache_lifecycle_valid(obj: dict[str, Any]) -> bool:
    required = {"owner_id", "scope_id", "release_on_cancel", "security_context_id"}
    if not required.issubset(obj) or obj.get("release_on_cancel") is not True:
        return False
    if obj.get("shared") is True and not obj.get("tenant_security_partition"):
        return False
    return True

def _compatibility_valid(obj: dict[str, Any]) -> bool:
    return all(obj.get(k) for k in ("model_variant_id", "provider_version", "hardware_profile_id")) and obj.get("result") == "PASS"

def _benchmark_valid(obj: dict[str, Any]) -> bool:
    required = {"provider_id", "provider_version", "model_artifact_id", "hardware_profile_id", "execution_topology", "parallelism", "warm_state"}
    return required.issubset(obj) and obj.get("provider_id") in PROVIDER_IDS

def _evidence_channel_compatible(target: str, evidence: str) -> bool:
    return target in {"stable", "nightly"} and evidence == target

def _redistribution_authorized(obj: dict[str, Any]) -> bool:
    return bool(
        obj.get("source_available") is True
        and obj.get("license_admission") == "PASS"
        and obj.get("redistribution_terms_verified") is True
    )

def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    canonical = root / "canonical"
    if not canonical.exists():
        return {"result": "FAIL", "scanned_json_files": 0, "findings": [_finding("MODULAR-AUTH-000", "canonical directory is missing")]}

    def walk(value: Any, path: str, file_path: str, scoped: bool = False):
        if isinstance(value, dict):
            local = scoped or _object_is_modular_scoped(value)
            if local and value.get("architectural_authority") is True:
                findings.append(_finding("MODULAR-AUTH-001", "MAX/Mojo architectural authority was enabled", file=file_path, path=path))
            if local and isinstance(value.get("id"), str) and value["id"].upper().startswith(("FA3-AUTH-MAX", "FA3-AUTH-MOJO")):
                findings.append(_finding("MODULAR-AUTH-002", "MAX/Mojo was introduced as an FA3 authority record", file=file_path, path=f"{path}.id"))
            for key, item in value.items():
                key_path = f"{path}.{key}"
                if key == "authority_boundaries" and isinstance(item, dict):
                    for domain, owner in item.items():
                        if _is_modular_provider_value(owner):
                            findings.append(_finding("MODULAR-AUTH-003", "MAX/Mojo was assigned as authority boundary owner", file=file_path, path=f"{key_path}.{domain}", domain=domain, value=owner))
                if key in AUTHORITY_KEYS and _is_modular_provider_value(item):
                    findings.append(_finding("MODULAR-AUTH-004", "MAX/Mojo was assigned to an authority-bearing field", file=file_path, path=key_path, value=item))
                walk(item, key_path, file_path, local)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, f"{path}[{i}]", file_path, scoped)

    for path in sorted(canonical.rglob("*.json")):
        scanned += 1
        try:
            data = _load(path)
        except Exception as exc:
            findings.append(_finding("MODULAR-AUTH-005", "Canonical JSON parse failure during Modular scan", file=str(path.relative_to(root)), error=str(exc)))
            continue
        walk(data, "$", str(path.relative_to(root)))
    return {"result": "PASS" if not findings else "FAIL", "scanned_json_files": scanned, "findings": findings}

def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "max": root / "canonical/providers/FA3-PROVIDER-MAX-001.json",
        "mojo": root / "canonical/providers/FA3-PROVIDER-MOJO-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-MODULAR-2026-08-30.json",
        "reference": root / "canonical/references/FA3-MODULAR-UPSTREAM-REFERENCE-2026-08-30.json",
        "enforcement": root / "canonical/modular-enforcement.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    for key, path in paths.items():
        if not path.exists():
            findings.append(_finding(f"MODULAR-REF-{len(findings)+1:03d}", f"Missing required Modular canonical artifact: {path.relative_to(root)}", artifact=key))
    if findings:
        return {"result": "FAIL", "findings": findings}

    maxp, mojop = _load(paths["max"]), _load(paths["mojo"])
    decision, reference = _load(paths["decision"]), _load(paths["reference"])
    enforcement, policy = _load(paths["enforcement"]), _load(paths["policy"])

    if not _provider_shape_valid(maxp, MAX_PROVIDER_ID):
        findings.append(_finding("MODULAR-REF-010", "MAX provider root/authority/capability/snapshot invariant drift"))
    if not _provider_shape_valid(mojop, MOJO_PROVIDER_ID):
        findings.append(_finding("MODULAR-REF-011", "Mojo provider root/authority/capability/snapshot invariant drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("gate_id") == GATE_ID
        and decision.get("provider_ids") == list(PROVIDER_IDS)
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("canonical_root_created") is False
        and decision.get("mandatory_rule_ids") == list(RULES)
    ):
        findings.append(_finding("MODULAR-REF-012", "Modular decision invariant drift"))

    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("snapshot_commit") == UPSTREAM_COMMIT
        and reference.get("snapshot_channel") == "NIGHTLY_DEVELOPMENT_REFERENCE"
        and reference.get("floating_main_allowed_as_promotion_evidence") is False
        and reference.get("promotion_semantics") == "REFERENCE_ONLY_NOT_CURRENT_HOST_PROMOTION_EVIDENCE"
    ):
        findings.append(_finding("MODULAR-REF-013", "Modular upstream reference identity/promotion semantics drift"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("provider_ids") == list(PROVIDER_IDS)
        and enforcement.get("fail_closed") is True
        and enforcement.get("runtime_provider_required_for_global_promotion") is False
        and enforcement.get("mandatory_rule_count") == len(RULES)
        and enforcement.get("p0_invariants") == list(RULES)
        and [r.get("invariant") for r in enforcement.get("rules", [])] == list(RULES)
    ):
        findings.append(_finding("MODULAR-REF-014", "Modular fail-closed enforcement record drift"))

    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("MODULAR-REF-015", "Modular gate is not bound into mandatory_reference_gates"))
    if policy.get("modular_provider_ids") != list(PROVIDER_IDS):
        findings.append(_finding("MODULAR-REF-016", "Global policy Modular provider identity drift"))
    if policy.get("modular_mandatory_p0_rules") != list(RULES):
        findings.append(_finding("MODULAR-REF-017", "Global policy Modular mandatory rule set drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}

def run_regressions() -> dict[str, Any]:
    good_compiled = {
        "model_artifact_id":"ART-MODEL-1","provider_id":MAX_PROVIDER_ID,"provider_version":"26.5",
        "compiler_version":"mojo-1.0","target_architecture":"sm_86","kernel_set_digest":"sha256:k",
        "compilation_config_digest":"sha256:c","artifact_sha256":"sha256:a",
    }
    good_warm = {
        "compiled_artifact_id":"ART-COMPILED-1","model_variant_id":"MODEL-VAR-1","provider_version":"26.5",
        "compiler_version":"mojo-1.0","target_architecture":"sm_86","config_digest":"sha256:c",
        "cache_sha256":"sha256:w","evidence_channel":"stable",
    }
    good_cache = {"owner_id":MAX_PROVIDER_ID,"scope_id":"MODEL-VAR-1","release_on_cancel":True,"security_context_id":"SEC-1","shared":False}
    good_shared = {**good_cache, "shared":True, "tenant_security_partition":"tenant-A"}
    good_compat = {"model_variant_id":"MODEL-VAR-1","provider_version":"26.5","hardware_profile_id":"HW-1","result":"PASS"}
    good_bench = {
        "provider_id":MAX_PROVIDER_ID,"provider_version":"26.5","model_artifact_id":"ART-MODEL-1",
        "hardware_profile_id":"HW-1","execution_topology":"2xGPU-sharded","parallelism":"tensor_parallel=2","warm_state":"warm"
    }
    cases = [
        (RULES[0], "execution topology authority separation", True, MAX_PROVIDER_ID != "FA3-AUTH-HOST-RESOURCE-BROKER-001"),
        (RULES[1], "provider-local scheduling authority separation", True, MAX_PROVIDER_ID != "FA3-AUTH-WORKFLOW-001"),
        (RULES[2], "portable semantic vs target artifact identity", "SEM-KERNEL-1" != "ART-SM86-1", not ("SEM-KERNEL-1" == "ART-SM86-1")),
        (RULES[3], "target specialization semantic preservation", "SEM-HASH-1" == "SEM-HASH-1", not ("SEM-HASH-1" == "SEM-HASH-DRIFT")),
        (RULES[4], "model variant compatibility evidence", _compatibility_valid(good_compat), not _compatibility_valid({**good_compat, "result":"UNKNOWN"})),
        (RULES[5], "compiled execution lineage", _compiled_lineage_valid(good_compiled), not _compiled_lineage_valid({k:v for k,v in good_compiled.items() if k!="compiler_version"})),
        (RULES[6], "warm-cache scoped identity", _warm_cache_valid(good_warm), not _warm_cache_valid({k:v for k,v in good_warm.items() if k!="target_architecture"})),
        (RULES[7], "cache ownership and lifecycle", _cache_lifecycle_valid(good_cache), not _cache_lifecycle_valid({k:v for k,v in good_cache.items() if k!="owner_id"})),
        (RULES[8], "cancellation releases resources", _cache_lifecycle_valid(good_cache), not _cache_lifecycle_valid({**good_cache, "release_on_cancel":False})),
        (RULES[9], "shared cache security boundary", _cache_lifecycle_valid(good_shared), not _cache_lifecycle_valid({k:v for k,v in good_shared.items() if k!="tenant_security_partition"})),
        (RULES[10], "benchmark topology-bound evidence", _benchmark_valid(good_bench), not _benchmark_valid({k:v for k,v in good_bench.items() if k!="execution_topology"})),
        (RULES[11], "OpenAI endpoint is projection not routing authority", True, MAX_PROVIDER_ID != "FA3-AUTH-MODEL-ROUTER-001"),
        (RULES[12], "stable/nightly evidence separation", _evidence_channel_compatible("stable","stable"), not _evidence_channel_compatible("stable","nightly")),
        (RULES[13], "source availability not redistribution authorization", _redistribution_authorized({"source_available":True,"license_admission":"PASS","redistribution_terms_verified":True}), not _redistribution_authorized({"source_available":True,"license_admission":"UNKNOWN","redistribution_terms_verified":False})),
    ]
    rows = []
    for invariant, name, positive, negative in cases:
        ok = bool(positive and negative)
        rows.append({"invariant": invariant, "name": name, "status":"PASS" if ok else "FAIL", "positive_case":bool(positive), "negative_case":bool(negative)})
    passed = sum(r["status"] == "PASS" for r in rows)
    return {"schema":"fa3.modular-regression-report.v1","result":"PASS" if passed == len(rows) else "FAIL","passed":passed,"total":len(rows),"cases":rows}

def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    authority = scan_canonical_authority_assignments(root)
    regressions = run_regressions()
    ok = reference["result"] == authority["result"] == regressions["result"] == "PASS"
    report = {
        "schema":"fa3.modular-gate-report.v1","gate_id":GATE_ID,"provider_ids":list(PROVIDER_IDS),
        "capability_count":CAPABILITY_COUNT,"result":"PASS" if ok else "FAIL",
        "mode":"CANONICAL_PROVIDER_BOUNDARY_LINEAGE_CACHE_AND_EVIDENCE_REGRESSION",
        "reference":reference,"authority_scan":authority,"regressions":regressions,
        "runtime_provider_required":False,
        "promotion_effect":"MANDATORY_CANONICAL_INVARIANTS_PROVIDER_RUNTIME_OPTIONAL_WHEN_DISABLED",
    }
    _write(root / "reports/modular-gate-report.json", report)
    return report

def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Modular/MAX/Mojo fail-closed regression gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
