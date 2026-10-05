#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import posixpath
import re
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

PROFILE = "canonical/profiles/FA3-SKILL-FABRIC-001.json"
ADMISSION = "canonical/contracts/FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001.json"
HARDENING = "canonical/contracts/FA3-SKILL-ENGINEERING-HARDENING-CONTRACTS-001.json"
DECISION = "canonical/decisions/FA3-DEC-SKILL-FABRIC-V14-ENGINEERING-HARDENING-2026-09-27.json"
RADAR = "canonical/FA3-EXTERNAL-SKILL-RADAR-001.json"
LEDGER = "canonical/skill-rejected-change-ledger.json"
BINDINGS = "canonical/skill-artifact-bindings.json"
ENFORCEMENT = "canonical/skill-fabric-enforcement.json"

POSITIVE_TRIGGER = re.compile(r"\buse(?:\s+this)?\s+(?:when|before|after|during)\b", re.I)
NEGATED_TRIGGER = re.compile(r"\b(?:do not|don't|never)\s+use(?:\s+this)?\s+(?:when|before|after|during)\b", re.I)


def loadj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level object required")
    return value


def _safe_relpath(value: str) -> bool:
    if not isinstance(value, str) or not value or value.startswith("/"):
        return False
    norm = posixpath.normpath(value)
    return norm not in (".", "..") and not norm.startswith("../") and "/../" not in f"/{norm}/"


def positive_trigger_allowed(description: str) -> bool:
    if not isinstance(description, str) or not description.strip():
        return False
    cleaned = NEGATED_TRIGGER.sub("", description)
    return bool(POSITIVE_TRIGGER.search(cleaned))


def quality_floor_change_allowed(before: dict[str, Any], after: dict[str, Any]) -> bool:
    if before.get("capability_count") is not None:
        if not isinstance(after.get("capability_count"), int) or after["capability_count"] < before["capability_count"]:
            return False
    if before.get("fail_closed") is True and after.get("fail_closed") is not True:
        return False
    if before.get("priority") == "P0" and after.get("priority") != "P0":
        return False
    if before.get("requirement") == "MUST" and after.get("requirement") != "MUST":
        return False
    for key in ("mandatory_rules", "required_fields", "descriptor_required_fields"):
        if key in before and not set(before.get(key, [])).issubset(set(after.get(key, []))):
            return False
    return True


def ledger_update_allowed(before: dict[str, Any], after: dict[str, Any]) -> bool:
    if before.get("append_only") is not True or after.get("append_only") is not True:
        return False
    old = before.get("entries")
    new = after.get("entries")
    if not isinstance(old, list) or not isinstance(new, list) or len(new) < len(old):
        return False
    return new[:len(old)] == old


def source_grounding_allowed(record: dict[str, Any]) -> bool:
    if not record.get("claim") or not record.get("source_uri") or not record.get("immutable_source_ref"):
        return False
    if record.get("claim_source_match") is not True or record.get("verified") is not True:
        return False
    if record.get("source_is_authority") is not False:
        return False
    if record.get("implementation_affecting") is True:
        rv = record.get("runtime_verification", {})
        if rv.get("required") is not True or rv.get("result") != "PASS":
            return False
    return True


def adversarial_review_allowed(record: dict[str, Any]) -> bool:
    if record.get("fresh_context") is not True or record.get("original_conclusion_withheld") is not True:
        return False
    if not record.get("artifact_ref") or not record.get("contract_ref"):
        return False
    routes = record.get("routes", {})
    if routes.get("model") != "FA3-AUTH-MODEL-ROUTER-001":
        return False
    if routes.get("resource") != "FA3-AUTH-HOST-RESOURCE-BROKER-001":
        return False
    if routes.get("federation") != "FA3-AGENT-FEDERATION-001":
        return False
    if record.get("provider_self_selected") is not False or record.get("reviewer_is_promotion_authority") is not False:
        return False
    return record.get("unresolved_critical_findings") == 0


def artifact_binding_allowed(record: dict[str, Any]) -> bool:
    if not record.get("artifact_id") or not record.get("schema_id") or not record.get("authority_owner"):
        return False
    producer = record.get("producer", {})
    path = producer.get("path")
    if not producer.get("component") or not _safe_relpath(path):
        return False
    consumers = record.get("consumers")
    if not isinstance(consumers, list) or not consumers:
        return False
    for row in consumers:
        if not row.get("component") or row.get("expected_path") != path or not _safe_relpath(row.get("expected_path", "")):
            return False
    return True


def destructive_path_guard_allowed(record: dict[str, Any]) -> bool:
    required = ("symlink_resolved", "allowed_root_verified", "minimum_depth_verified", "ownership_verified", "authorized")
    return all(record.get(k) is True for k in required) and record.get("skill_grants_execution_authority") is False


def distributed_rate_limit_allowed(record: dict[str, Any]) -> bool:
    count = record.get("instance_count")
    if not isinstance(count, int) or count < 1:
        return False
    if count > 1:
        return record.get("shared_counter_store") is True and record.get("atomic_updates") is True and record.get("in_process_only") is False
    return True


def observability_attribution_allowed(record: dict[str, Any]) -> bool:
    if not record.get("correlation_id"):
        return False
    if record.get("shared_sink") is True and record.get("entry_path_count", 0) > 1:
        return bool(record.get("entry_point"))
    return True


def _mut(value: dict[str, Any], fn) -> dict[str, Any]:
    result = copy.deepcopy(value)
    fn(result)
    return result


def run_regressions() -> dict[str, Any]:
    before = {"capability_count": 175, "fail_closed": True, "priority": "P0", "requirement": "MUST", "mandatory_rules": ["A", "B"]}
    source = {
        "claim": "API behavior", "source_uri": "https://example.invalid/spec", "immutable_source_ref": "v1",
        "claim_source_match": True, "verified": True, "source_is_authority": False,
        "implementation_affecting": True, "runtime_verification": {"required": True, "result": "PASS"},
    }
    review = {
        "fresh_context": True, "original_conclusion_withheld": True, "artifact_ref": "artifact:1", "contract_ref": "contract:1",
        "routes": {"model": "FA3-AUTH-MODEL-ROUTER-001", "resource": "FA3-AUTH-HOST-RESOURCE-BROKER-001", "federation": "FA3-AGENT-FEDERATION-001"},
        "provider_self_selected": False, "reviewer_is_promotion_authority": False, "unresolved_critical_findings": 0,
    }
    binding = {
        "artifact_id": "A", "schema_id": "S",
        "producer": {"component": "producer", "path": "reports/a.json"},
        "consumers": [{"component": "consumer", "expected_path": "reports/a.json"}],
        "authority_owner": "FA3-AUTH-OBS-EVIDENCE-001",
    }
    path_guard = {
        "symlink_resolved": True, "allowed_root_verified": True, "minimum_depth_verified": True,
        "ownership_verified": True, "authorized": True, "skill_grants_execution_authority": False,
    }
    ledger = {"append_only": True, "entries": [{"id": "R1"}]}
    checks = [
        ("positive-trigger", positive_trigger_allowed("Use when implementing an API.")),
        ("negated-only-trigger-denied", not positive_trigger_allowed("Do not use when editing prose.")),
        ("multiple-negated-only-denied", not positive_trigger_allowed("Do not use when A. Never use before B.")),
        ("floor-unchanged", quality_floor_change_allowed(before, copy.deepcopy(before))),
        ("floor-capability-decrease-denied", not quality_floor_change_allowed(before, _mut(before, lambda x: x.update(capability_count=174)))),
        ("floor-fail-open-denied", not quality_floor_change_allowed(before, _mut(before, lambda x: x.update(fail_closed=False)))),
        ("floor-rule-removal-denied", not quality_floor_change_allowed(before, _mut(before, lambda x: x.update(mandatory_rules=["A"])))),
        ("ledger-append", ledger_update_allowed(ledger, {"append_only": True, "entries": [{"id": "R1"}, {"id": "R2"}]})),
        ("ledger-rewrite-denied", not ledger_update_allowed(ledger, {"append_only": True, "entries": [{"id": "X"}]})),
        ("source-grounded", source_grounding_allowed(source)),
        ("source-runtime-proof-required", not source_grounding_allowed(_mut(source, lambda x: x["runtime_verification"].update(result="PENDING")))),
        ("source-not-authority", not source_grounding_allowed(_mut(source, lambda x: x.update(source_is_authority=True)))),
        ("adversarial-review", adversarial_review_allowed(review)),
        ("review-original-conclusion-denied", not adversarial_review_allowed(_mut(review, lambda x: x.update(original_conclusion_withheld=False)))),
        ("review-direct-provider-denied", not adversarial_review_allowed(_mut(review, lambda x: x.update(provider_self_selected=True)))),
        ("review-critical-finding-blocks", not adversarial_review_allowed(_mut(review, lambda x: x.update(unresolved_critical_findings=1)))),
        ("artifact-binding", artifact_binding_allowed(binding)),
        ("artifact-path-drift-denied", not artifact_binding_allowed(_mut(binding, lambda x: x["consumers"][0].update(expected_path="reports/b.json")))),
        ("destructive-path-guard", destructive_path_guard_allowed(path_guard)),
        ("destructive-path-ownership-denied", not destructive_path_guard_allowed(_mut(path_guard, lambda x: x.update(ownership_verified=False)))),
        ("distributed-rate-limit", distributed_rate_limit_allowed({"instance_count": 2, "shared_counter_store": True, "atomic_updates": True, "in_process_only": False})),
        ("per-instance-rate-limit-denied", not distributed_rate_limit_allowed({"instance_count": 2, "shared_counter_store": False, "atomic_updates": True, "in_process_only": True})),
        ("observability-entry-point", observability_attribution_allowed({"correlation_id": "c1", "shared_sink": True, "entry_path_count": 2, "entry_point": "scheduler"})),
        ("observability-missing-entry-point-denied", not observability_attribution_allowed({"correlation_id": "c1", "shared_sink": True, "entry_path_count": 2})),
    ]
    cases = [{"case_id": f"SKF14-{i:03d}", "name": name, "status": "PASS" if ok else "FAIL"} for i, (name, ok) in enumerate(checks, 1)]
    return {"result": "PASS" if all(ok for _, ok in checks) else "FAIL", "total": len(cases), "passed": sum(c["status"] == "PASS" for c in cases), "cases": cases}


def canonical_check(root: Path) -> list[str]:
    findings: list[str] = []
    required = [PROFILE, ADMISSION, HARDENING, DECISION, RADAR, LEDGER, BINDINGS, ENFORCEMENT]
    missing = [p for p in required if not (root / p).is_file()]
    if missing:
        return [f"missing v1.4 artifacts: {missing}"]
    profile = loadj(root / PROFILE)
    admission = loadj(root / ADMISSION)
    hardening = loadj(root / HARDENING)
    decision = loadj(root / DECISION)
    radar = loadj(root / RADAR)
    ledger = loadj(root / LEDGER)
    bindings = loadj(root / BINDINGS)
    enforcement = loadj(root / ENFORCEMENT)
    cap = module_active_capability_count(__file__)

    if profile.get("version") != "1.4.0" or admission.get("version") != "1.4.0":
        findings.append("Skill Fabric/admission 1.4 not active")
    if profile.get("capability_count") != cap or admission.get("capability_count") != cap or hardening.get("capability_count") != cap:
        findings.append("Skill Fabric 1.4 capability baseline drift")
    if profile.get("new_capability") is not False or profile.get("new_architectural_authority") is not False:
        findings.append("Skill Fabric 1.4 created forbidden authority/capability")
    if hardening.get("new_capability") is not False or hardening.get("new_architectural_authority") is not False:
        findings.append("engineering hardening created forbidden authority/capability")

    cid = "FA3-SKILL-ENGINEERING-HARDENING-CONTRACTS-001"
    if cid not in admission.get("extension_contracts", []):
        findings.append("admission missing 1.4 hardening contract")
    if cid not in enforcement.get("extension_contract_ids", []):
        findings.append("enforcement missing 1.4 hardening contract")
    if enforcement.get("v14_companion_validator") != "src/fa3_skill_fabric_v14.py":
        findings.append("v1.4 companion validator not enforced")

    trig = hardening.get("trigger_semantics", {})
    if trig.get("explicit_positive_trigger_required") is not True or trig.get("negated_trigger_does_not_establish_eligibility") is not True:
        findings.append("trigger semantics weakened")
    floor = hardening.get("quality_floor", {})
    if floor.get("weakening_fails_closed") is not True or floor.get("tightening_is_not_a_violation") is not True:
        findings.append("quality floor policy weakened")
    if ledger.get("append_only") is not True or ledger.get("authority") is not False or not isinstance(ledger.get("entries"), list):
        findings.append("rejected-change ledger invariant failed")
    if bindings.get("drift_policy") != "FAIL_CLOSED" or not bindings.get("bindings"):
        findings.append("artifact binding registry missing/fail-open")
    for record in bindings.get("bindings", []):
        if not artifact_binding_allowed(record):
            findings.append(f"invalid artifact binding: {record.get('artifact_id')}")

    repos = {row.get("repository"): row for row in radar.get("sources", [])}
    row = repos.get("addyosmani/agent-skills")
    if not row or row.get("commit") != "2686b620fc1fed2e8f60c704839c766b8594c6b6" or row.get("classification") != "REFERENCE_ONLY":
        findings.append("addyosmani/agent-skills audited immutable pin missing")

    effect = decision.get("authority_effect", {})
    if effect != {"new_capability": False, "new_architectural_authority": False, "capability_count_after": cap}:
        findings.append("1.4 decision capability/authority invariant drift")
    hw = decision.get("hardware_audit", {})
    if not (hw.get("vendor_neutral") and hw.get("cpu_only_viable") and hw.get("global_accelerator_requirement") is False):
        findings.append("1.4 Hardware Audit invariant failed")
    coexist = decision.get("coexistence", {})
    if coexist.get("replaces_upstream_tools") is not False or coexist.get("installs_upstream_repository") is not False:
        findings.append("1.4 software coexistence invariant failed")
    if decision.get("evidence_boundary", {}).get("current_host_runtime_claim") is not False:
        findings.append("1.4 static materialization overclaims current-host runtime")

    required_rules = set(hardening.get("mandatory_rules", []))
    if not required_rules.issubset(set(profile.get("mandatory_rules", []))):
        findings.append("profile missing one or more 1.4 mandatory rules")
    return findings


def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings = canonical_check(root)
    regressions = run_regressions()
    result = "PASS" if not findings and regressions["result"] == "PASS" else "FAIL"
    report = {
        "schema": "fa3.skill-fabric-v14-gate-report.v1",
        "result": result,
        "findings": findings,
        "regressions": regressions,
        "provider_specific": False,
        "capability_count": module_active_capability_count(__file__),
        "new_architectural_authority": False,
        "current_host_runtime_claim": False,
        "upstream_runtime_admitted": False,
    }
    out = root / "reports/skill-fabric-v14-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = evaluate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
