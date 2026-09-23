#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fa3_quality_filter import RULE_REGISTRY, analyze_text, scan, select_quality_skills

PROFILE = "canonical/profiles/FA3-QUALITY-ANTI-SLOP-001.json"
CONTRACT = "canonical/contracts/FA3-QUALITY-ANTI-SLOP-CONTRACTS-001.json"
DECISION = "canonical/decisions/FA3-DEC-QUALITY-ANTI-SLOP-NATIVE-2026-09-23.json"
GATE_RECORD = "canonical/FA3-GATE-QUALITY-ANTI-SLOP-001.json"
SKILL_REGISTRY = "canonical/skill-registry.json"
AGENT_PROFILE = "canonical/profiles/FA3-AGENT-INSTRUCTIONS-001.json"
SKILL_PROFILE = "canonical/profiles/FA3-SKILL-FABRIC-001.json"
DECISION_PROFILE = "canonical/profiles/FA3-DECISION-FABRIC-001.json"
SKILL_DISCOVERY_CONTRACT = "canonical/contracts/FA3-SKILL-DISCOVERY-CONTRACTS-001.json"
UPSTREAM_REFERENCE = "canonical/references/FA3-ANTI-SLOP-UPSTREAM-REFERENCE-2026-09-23.json"
DISTRIBUTION_REGISTRY = "canonical/distribution-registry.json"
DISTRIBUTION_MANIFEST = "canonical/distribution-manifest.json"
RECONCILER = "scripts/fa3_reconcile_release_projection.py"
ENFORCEMENT = "canonical/enforcement-policy.json"
WORKFLOW = ".github/workflows/fa3-quality-anti-slop.yml"
PERMANENT_WORKFLOW = ".github/workflows/fa3-permanent-enforcement.yml"
GUI_WORKFLOW = ".github/workflows/fa3-gui-gate.yml"
BIN_ENFORCE = "bin/fa3-enforce"
CANONICAL_ENFORCER = "src/fa3_enforce.py"
GATESET_ID = "FA3-QUALITY-ANTI-SLOP-GATESET-001"
PROFILE_ID = "FA3-QUALITY-ANTI-SLOP-001"
CONTRACT_ID = "FA3-QUALITY-ANTI-SLOP-CONTRACTS-001"
RULE_REGISTRY_ID = "FA3-QUALITY-RULE-REGISTRY-001"
SKILLS = [
    "fa3-quality-ui",
    "fa3-quality-copy",
    "fa3-quality-human",
    "fa3-quality-responsive",
    "fa3-quality-code",
]
ALLOWED_TIERS = {"HARD_GATE", "PURPOSE_GATE", "QUALITY_LOCK"}
ALLOWED_CONCERNS = {"CORE", "UI", "COPY", "HUMAN", "RESPONSIVE", "CODE", "FA3"}

def loadj(root: Path, rel: str) -> dict[str, Any]:
    obj = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"{rel}: top-level object required")
    return obj

def check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}

def _validate_skill_file(root: Path, skill: str) -> tuple[bool, str]:
    p = root / "skills" / skill / "SKILL.md"
    if not p.is_file():
        return False, f"missing {p.relative_to(root)}"
    text = p.read_text(encoding="utf-8")
    required = [
        "name:", "description:", "version:", "trigger:",
        "## use_when", "## inputs", "## procedure", "## guardrails",
        "## pitfalls", "## acceptance_checks",
    ]
    missing = [x for x in required if x not in text]
    forbidden = ["curl ", "wget ", "npx ", "sudo ", "FA3-QUALITY-JUSTIFY Q-"]
    if missing:
        return False, f"missing sections/metadata={missing}"
    bad = [x for x in forbidden if x in text]
    if bad:
        return False, f"forbidden executable or blanket-justification token={bad}"
    return True, "declarative task-scoped skill entrypoint present"

def evaluate(root: Path, *, scope: str | None = None, changed_from: str | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    checks: list[dict[str, str]] = []
    required = [PROFILE, CONTRACT, DECISION, GATE_RECORD, RULE_REGISTRY, SKILL_REGISTRY, AGENT_PROFILE, SKILL_PROFILE, DECISION_PROFILE, SKILL_DISCOVERY_CONTRACT, UPSTREAM_REFERENCE, DISTRIBUTION_REGISTRY, DISTRIBUTION_MANIFEST, RECONCILER, ENFORCEMENT, WORKFLOW, PERMANENT_WORKFLOW, GUI_WORKFLOW, BIN_ENFORCE, CANONICAL_ENFORCER]
    missing = [x for x in required if not (root / x).is_file()]
    checks.append(check("core-records-present", not missing, f"missing={missing}"))
    if missing:
        return {"schema": "fa3.quality-gate-report.v1", "gate_id": GATESET_ID, "result": "FAIL", "fail_closed": True, "checks": checks}

    profile = loadj(root, PROFILE)
    contract = loadj(root, CONTRACT)
    decision = loadj(root, DECISION)
    gate = loadj(root, GATE_RECORD)
    registry = loadj(root, RULE_REGISTRY)
    skill_registry = loadj(root, SKILL_REGISTRY)
    agent_profile = loadj(root, AGENT_PROFILE)
    skill_profile = loadj(root, SKILL_PROFILE)
    decision_profile = loadj(root, DECISION_PROFILE)
    skill_discovery_contract = loadj(root, SKILL_DISCOVERY_CONTRACT)
    upstream_reference = loadj(root, UPSTREAM_REFERENCE)
    distribution_registry = loadj(root, DISTRIBUTION_REGISTRY)
    distribution_manifest = loadj(root, DISTRIBUTION_MANIFEST)
    enforcement = loadj(root, ENFORCEMENT)

    profile_ok = (
        profile.get("id") == PROFILE_ID and profile.get("status") == "CANONICAL"
        and profile.get("priority") == "P0" and profile.get("requirement") == "MUST"
        and profile.get("architectural_authority") is False
        and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == 143
        and profile.get("design_boundary", {}).get("quality_filter_is_style_guide") is False
        and profile.get("design_boundary", {}).get("application_design_contract_remains_authoritative_for_visual_direction") is True
        and profile.get("activation", {}).get("decision_fabric_candidate_expansion") == "DENY"
        and profile.get("upstream_relationship", {}).get("upstream_runtime_dependency") is False
        and profile.get("upstream_relationship", {}).get("upstream_installer_used") is False
        and profile.get("upstream_relationship", {}).get("upstream_agent_entry_file_mutation_used") is False
        and profile.get("authority_boundaries", {}).get("design_authority") is False
    )
    checks.append(check("profile-boundary", profile_ok, "native filter, no authority, design contract precedence preserved"))

    contract_ok = (
        contract.get("id") == CONTRACT_ID and contract.get("status") == "CANONICAL"
        and contract.get("new_capability") is False and contract.get("new_architectural_authority") is False
        and contract.get("capability_count") == 143
        and contract.get("concern_selection", {}).get("decision_fabric_candidate_expansion") == "DENY"
        and contract.get("rule_contract", {}).get("hard_gate_waiver_allowed") is False
        and contract.get("rule_contract", {}).get("purpose_gate_requires_justification") is True
        and contract.get("execution_boundary", {}).get("network_required") is False
        and contract.get("execution_boundary", {}).get("model_required") is False
        and contract.get("execution_boundary", {}).get("tool_execution_authority") is False
    )
    checks.append(check("contract-boundary", contract_ok, "deterministic quality contracts preserve authority boundaries"))

    decision_ok = (
        decision.get("id") == "FA3-DEC-QUALITY-ANTI-SLOP-NATIVE-2026-09-23"
        and decision.get("status") == "CANONICAL"
        and decision.get("upstream_observation", {}).get("license") == "MIT"
        and decision.get("upstream_observation", {}).get("code_reuse") == "NONE"
        and decision.get("upstream_observation", {}).get("runtime_dependency") == "NONE"
        and decision.get("authority_effect", {}).get("new_capability") is False
        and decision.get("authority_effect", {}).get("new_authority") is False
    )
    checks.append(check("decision-provenance", decision_ok, "upstream is inspiration/provenance only; FA3 implementation is native"))

    distribution_rows = {x.get("subject_id"): x for x in distribution_registry.get("records", []) if isinstance(x, dict)}
    provenance_ok = (
        upstream_reference.get("id") == "FA3-ANTI-SLOP-UPSTREAM-REFERENCE-2026-09-23"
        and upstream_reference.get("observed_commit") == "0e384b7bff3301c8ec56dea300330772fed28e6a"
        and upstream_reference.get("observed_version") == "3.2.15"
        and upstream_reference.get("distribution_class") == "REFERENCE_ONLY"
        and upstream_reference.get("runtime_dependency") is False
        and upstream_reference.get("installation_required") is False
        and not any(upstream_reference.get("imported", {}).values())
        and distribution_rows.get("FA3-ANTI-SLOP-UPSTREAM-REFERENCE-2026-09-23", {}).get("class") == "REFERENCE_ONLY"
        and distribution_rows.get("FA3-ANTI-SLOP-UPSTREAM-REFERENCE-2026-09-23", {}).get("release_bundle_status") == "EXCLUDED"
        and any(x.get("subject_id") == "FA3-ANTI-SLOP-UPSTREAM-REFERENCE-2026-09-23" and x.get("class") == "REFERENCE_ONLY" and x.get("release_bundle_status") == "EXCLUDED" for x in distribution_manifest.get("excluded", []))
        and not any(x.get("subject_id") == "FA3-ANTI-SLOP-UPSTREAM-REFERENCE-2026-09-23" for x in distribution_manifest.get("included", []))
    )
    checks.append(check("upstream-reference-distribution", provenance_ok, "anti-slop upstream is immutable REFERENCE_ONLY provenance with zero imported payload"))

    gate_ok = (
        gate.get("id") == "FA3-GATE-QUALITY-ANTI-SLOP-001"
        and gate.get("gateset_id") == GATESET_ID
        and gate.get("profile_id") == PROFILE_ID and gate.get("contract_id") == CONTRACT_ID
        and gate.get("rule_registry_id") == RULE_REGISTRY_ID
        and gate.get("fail_closed") is True and gate.get("static_enforcement") is True
        and gate.get("current_host_runtime_required") is False
        and gate.get("capability_count_after") == 143
    )
    checks.append(check("gate-record", gate_ok, "P0 static gate is canonical and does not claim current-host runtime"))

    rule_rows = registry.get("rules", [])
    ids = [r.get("id") for r in rule_rows if isinstance(r, dict)]
    rules_ok = (
        registry.get("id") == RULE_REGISTRY_ID and registry.get("status") == "CANONICAL"
        and len(rule_rows) >= 24 and len(ids) == len(set(ids))
        and all(r.get("tier") in ALLOWED_TIERS for r in rule_rows)
        and all(r.get("concern") in ALLOWED_CONCERNS for r in rule_rows)
        and all(isinstance(r.get("blocking"), bool) and r.get("pattern") and r.get("message") for r in rule_rows)
        and all(not (r.get("tier") == "HARD_GATE" and r.get("blocking") is False) for r in rule_rows)
    )
    regex_ok = True
    regex_error = ""
    for r in rule_rows:
        try:
            re.compile(str(r.get("pattern", "")))
        except re.error as exc:
            regex_ok = False
            regex_error = f"{r.get('id')}: {exc}"
            break
    checks.append(check("rule-registry", rules_ok and regex_ok, f"rules={len(rule_rows)} regex_error={regex_error or 'none'}"))

    skills_ok = True
    skill_details = []
    for skill in SKILLS:
        ok, detail = _validate_skill_file(root, skill)
        skills_ok &= ok
        skill_details.append(f"{skill}:{detail}")
    checks.append(check("quality-skill-entrypoints", skills_ok, "; ".join(skill_details)))

    entries = {x.get("skill_id"): x for x in skill_registry.get("entries", []) if isinstance(x, dict)}
    reg_ok = all(
        sid in entries
        and entries[sid].get("admission_status") == "ADMITTED"
        and entries[sid].get("distribution_class") == "FA3_NATIVE"
        and entries[sid].get("task_scoped") is True
        and entries[sid].get("authority") is False
        for sid in SKILLS
    )
    checks.append(check("skill-registry-bindings", reg_ok, "five FA3-native task-scoped quality skills admitted"))

    integration_ok = (
        agent_profile.get("generated_deliverable_quality", {}).get("profile_id") == PROFILE_ID
        and agent_profile.get("generated_deliverable_quality", {}).get("core_filter_required_for_generated_deliverables") is True
        and agent_profile.get("generated_deliverable_quality", {}).get("skill_context_cannot_create_authority") is True
        and skill_profile.get("integration_bindings", {}).get("quality_filter") == PROFILE_ID
        and skill_profile.get("selection_and_composition", {}).get("quality_skill_candidates_deterministically_prefiltered") is True
        and skill_profile.get("selection_and_composition", {}).get("quality_skill_global_auto_injection") is False
        and decision_profile.get("quality_skill_selection_binding", {}).get("consumer_profile") == PROFILE_ID
        and decision_profile.get("quality_skill_selection_binding", {}).get("candidate_expansion") == "DENY"
        and decision_profile.get("quality_skill_selection_binding", {}).get("design_authority") is False
        and skill_discovery_contract.get("eligibility_semantics", {}).get("task_class_filter_supported") is True
        and skill_discovery_contract.get("eligibility_semantics", {}).get("task_scoped_skill_without_matching_task_class_ineligible") is True
    )
    checks.append(check("agent-skill-decision-bindings", integration_ok, "Agent Native, Skill Fabric and Decision Fabric use deterministic task-scoped quality selection"))

    mandatory = enforcement.get("mandatory_reference_gates", [])
    enforcement_ok = (
        GATESET_ID in mandatory
        and enforcement.get("quality_anti_slop_profile_id") == PROFILE_ID
        and enforcement.get("quality_anti_slop_gate_id") == GATESET_ID
        and enforcement.get("quality_anti_slop_upstream_runtime_required") is False
        and enforcement.get("quality_anti_slop_installer_allowed") is False
        and enforcement.get("quality_anti_slop_entry_file_auto_mutation_allowed") is False
    )
    checks.append(check("permanent-enforcement-binding", enforcement_ok, "quality gate is mandatory; external installer/runtime mutation paths are disabled"))

    bin_text = (root / BIN_ENFORCE).read_text(encoding="utf-8")
    canonical_enforcer_text = (root / CANONICAL_ENFORCER).read_text(encoding="utf-8")
    perm_text = (root / PERMANENT_WORKFLOW).read_text(encoding="utf-8")
    gui_text = (root / GUI_WORKFLOW).read_text(encoding="utf-8")
    workflow_text = (root / WORKFLOW).read_text(encoding="utf-8")
    reconciler_text = (root / RECONCILER).read_text(encoding="utf-8")
    workflow_ok = (
        "quality-anti-slop" in bin_text and "fa3_quality_gate.py" in bin_text
        and "from fa3_quality_gate import evaluate as quality_anti_slop_gate" in canonical_enforcer_text
        and "quality_anti_slop_ref=quality_anti_slop_gate(root)" in canonical_enforcer_text
        and "FA3-STATIC-124" in canonical_enforcer_text
        and "./bin/fa3-enforce quality-anti-slop" in perm_text
        and "quality-anti-slop-gate-report.json" in perm_text
        and "fa3_quality_gate.py" in gui_text
        and "src/fa3_quality_filter.py" in workflow_text and "tests.test_quality_filter" in workflow_text
        and "quality_anti_slop_reconciliation" in reconciler_text
    )
    checks.append(check("workflow-bindings", workflow_ok, "standalone, GUI and permanent enforcement paths are wired"))

    smoke_bad = analyze_text("apps/demo.qml", 'Text { text: "Lorem ipsum" }', registry, {"CORE"})
    smoke_good = analyze_text("apps/demo.qml", 'Text { text: "Project status" }', registry, {"CORE"})
    smoke_purpose_fail = analyze_text("apps/demo.qml", 'Text { text: "World-class workflow" }', registry, {"COPY"})
    smoke_purpose_pass = analyze_text("apps/demo.qml", '// FA3-QUALITY-JUSTIFY Q-COPY-003: independently benchmarked copy claim\nText { text: "World-class workflow" }', registry, {"COPY"})
    selection = select_quality_skills(["ui", "accessibility"])
    smoke_ok = (
        smoke_bad["result"] == "FAIL" and smoke_good["result"] == "PASS"
        and smoke_purpose_fail["result"] == "FAIL" and smoke_purpose_pass["result"] == "PASS"
        and {"fa3-quality-ui", "fa3-quality-copy", "fa3-quality-human", "fa3-quality-responsive"}.issubset(selection)
        and "fa3-quality-code" not in selection
    )
    checks.append(check("deterministic-smoke-tests", smoke_ok, "hard gate, purpose justification and minimal quality-skill selection behave deterministically"))

    scoped_scan = None
    if scope:
        scoped_scan = scan(root, scope=scope, changed_from=changed_from)
        checks.append(check("artifact-quality-scan", scoped_scan.get("result") == "PASS", f"scope={scope} blocking={scoped_scan.get('blocking_findings')} warnings={scoped_scan.get('warnings')}"))

    result = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    return {
        "schema": "fa3.quality-gate-report.v1",
        "gate_id": GATESET_ID,
        "profile_id": PROFILE_ID,
        "result": result,
        "fail_closed": True,
        "current_host_runtime_promotion_claim": False,
        "checks": checks,
        "scan": scoped_scan,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--scope", choices=["gui", "repo"], default=None)
    ap.add_argument("--changed-from", default=None)
    ap.add_argument("--report", default="reports/quality-anti-slop-gate-report.json")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    report = evaluate(root, scope=args.scope, changed_from=args.changed_from)
    out = root / args.report
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
