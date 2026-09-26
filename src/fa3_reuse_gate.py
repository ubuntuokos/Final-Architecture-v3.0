#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from fa3_reuse_assessment import assess_intent
from fa3_reuse_catalog import build_catalog
from fa3_reuse_resolver import bounded_rank
from fa3_release_baseline import load_active_release_baseline

PROFILE = "canonical/profiles/FA3-REUSE-DISCOVERY-001.json"
CONTRACT = "canonical/contracts/FA3-REUSE-DISCOVERY-CONTRACTS-001.json"
CATALOG = "canonical/FA3-REUSE-CATALOG-001.json"
DECISION = "canonical/decisions/FA3-DEC-REUSE-DISCOVERY-2026-09-24.json"
GATE_RECORD = "canonical/FA3-GATE-REUSE-DISCOVERY-001.json"
ENFORCEMENT = "canonical/reuse-discovery-enforcement.json"
DECISION_ASSESSMENT = "canonical/assessments/FA3-REUSE-DISCOVERY-DECISION-ASSESSMENT-2026-09-24.json"
GOLDEN_INTENT = "canonical/intents/FA3-EMBEDDING-FABRIC-APPLICATION-INTENT-001.json"
GOLDEN_ASSESSMENT = "canonical/assessments/FA3-EMBEDDING-FABRIC-REUSE-ASSESSMENT-001.json"
POLICY = "canonical/enforcement-policy.json"
RELEASE = "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
GUI_REGISTRY = "canonical/FA3-GUI-SURFACE-REGISTRY-001.json"
GUI_QML = "apps/fa3-control-center/qml/ProjectRadarPage.qml"
JEV_REUSE = "canonical/third-party/FA3-JEV-CODE-REUSE-001.json"
DIST_REGISTRY = "canonical/distribution-registry.json"
DIST_MANIFEST = "canonical/distribution-manifest.json"
EVIDENCE = "evidence/reference/reuse-discovery-ci-2026-09-24.json"
SKILL_REGISTRY = "canonical/skill-registry.json"
EXTERNAL_SKILL_RADAR = "canonical/FA3-EXTERNAL-SKILL-RADAR-001.json"
GUI_INTENT = "canonical/intents/FA3-GUI-CURRENT-HOST-APPLICATION-INTENT-001.json"
GUI_REUSE_ASSESSMENT = "canonical/assessments/FA3-GUI-CURRENT-HOST-REUSE-ASSESSMENT-001.json"
WORKFLOW = ".github/workflows/fa3-permanent-enforcement.yml"
DEDICATED_WORKFLOW = ".github/workflows/fa3-reuse-discovery.yml"
DECISION_DOC = "docs/decision-fabric.md"


def load(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {rel}")
    return value


def finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def _git(root: Path, *args: str) -> str | None:
    proc = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _assessment_index(root: Path) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    base = root / "canonical/assessments"
    if not base.is_dir():
        return index
    for path in sorted(base.glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(row, dict) or row.get("schema") != "fa3.reuse-assessment.v1":
            continue
        for covered in row.get("covered_ids", []):
            index.setdefault(str(covered), []).append({"path": path.relative_to(root).as_posix(), "row": row})
    return index


def _capability_model_175_mirror_only(root: Path, marker: str, rel: str, current: dict[str, Any]) -> bool:
    """Allow only the declared 143->175 baseline-mirror migration without treating it as a new project."""
    previous_text = _git(root, "show", f"{marker}:{rel}")
    if not previous_text:
        return False
    try:
        previous = json.loads(previous_text)
    except Exception:
        return False
    if previous.get("capability_count") != 143 or current.get("capability_count") != 175:
        return False
    active = load_active_release_baseline(root)
    if active.release != "2026-09-26/v3.1.0" or active.capability_count != 175:
        return False
    if current.get("capability_model_reconciliation") != "FA3-DEC-CAPABILITY-MODEL-175-2026-09-26":
        return False
    old = dict(previous)
    new = dict(current)
    old.pop("capability_count", None)
    new.pop("capability_count", None)
    new.pop("capability_baseline_release", None)
    new.pop("capability_model_reconciliation", None)
    return old == new


def post_adoption_new_project_check(root: Path) -> dict[str, Any]:
    history = _git(root, "log", "--format=%H", "--reverse", "--", DECISION)
    if not history:
        return {"result": "PASS", "state": "ADOPTION_MARKER_NOT_COMMITTED_YET", "checked": []}
    marker = history.splitlines()[0]
    changed = _git(root, "diff", "--name-only", "--diff-filter=AM", f"{marker}..HEAD", "--", "canonical/profiles", "canonical/providers")
    if changed is None:
        return {"result": "PASS", "state": "GIT_DIFF_UNAVAILABLE", "checked": []}
    assessments = _assessment_index(root)
    findings = []
    checked = []
    for rel in [x for x in changed.splitlines() if x.endswith(".json")]:
        try:
            row = load(root, rel)
        except Exception as exc:
            findings.append(finding("REUSE-ADOPT-001", "new canonical record unreadable", path=rel, error=repr(exc)))
            continue
        rid = row.get("id")
        if not rid:
            continue
        checked.append(str(rid))
        matches = assessments.get(str(rid), [])
        valid = _capability_model_175_mirror_only(root, marker, rel, row)
        for match in matches:
            assessment = match["row"]
            intent_path = assessment.get("intent_path")
            if (
                assessment.get("result") == "PASS"
                and isinstance(intent_path, str)
                and (root / intent_path).is_file()
            ):
                valid = True
                break
        if not valid:
            findings.append(finding("REUSE-ADOPT-002", "post-adoption new or materially modified profile/provider lacks PASS reuse assessment + ApplicationIntent", record_id=rid, path=rel))
    return {"result": "PASS" if not findings else "FAIL", "state": "ENFORCED", "marker_commit": marker, "checked": checked, "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    capability_count = load_active_release_baseline(root).capability_count
    findings: list[dict[str, Any]] = []
    required = [
        PROFILE, CONTRACT, CATALOG, DECISION, GATE_RECORD, ENFORCEMENT,
        "canonical/contracts/FA3-APPLICATION-INTENT-001.schema.json",
        "canonical/contracts/FA3-REUSABLE-PATTERN-001.schema.json",
        "canonical/contracts/FA3-REUSE-ASSESSMENT-001.schema.json",
        DECISION_ASSESSMENT, GOLDEN_INTENT, GOLDEN_ASSESSMENT,
        "canonical/intents/FA3-REUSE-DISCOVERY-APPLICATION-INTENT-001.json",
        "canonical/assessments/FA3-REUSE-DISCOVERY-REUSE-ASSESSMENT-001.json",
        "src/fa3_reuse_catalog.py", "src/fa3_reuse_resolver.py", "src/fa3_reuse_assessment.py",
        "bin/fa3-reuse-assess", "tests/test_reuse_discovery_gate.py", DECISION_DOC,
        SKILL_REGISTRY, EXTERNAL_SKILL_RADAR, GUI_INTENT, GUI_REUSE_ASSESSMENT,
    ]
    for rel in required:
        if not (root / rel).is_file():
            findings.append(finding("REUSE-001", "required reuse-discovery materialization missing", path=rel))
    if findings:
        return {"schema": "fa3.reuse-discovery-gate-report.v1", "gate_id": "FA3-GATE-REUSE-DISCOVERY-001", "result": "FAIL", "findings": findings}

    profile = load(root, PROFILE)
    contract = load(root, CONTRACT)
    catalog_policy = load(root, CATALOG)
    decision = load(root, DECISION)
    gate_record = load(root, GATE_RECORD)
    enforcement = load(root, ENFORCEMENT)
    dfa = load(root, DECISION_ASSESSMENT)
    golden_intent = load(root, GOLDEN_INTENT)
    golden_committed = load(root, GOLDEN_ASSESSMENT)
    policy = load(root, POLICY)
    gui = load(root, GUI_REGISTRY)
    jev = load(root, JEV_REUSE)
    dist = load(root, DIST_REGISTRY)
    manifest = load(root, DIST_MANIFEST)
    evidence = load(root, EVIDENCE)
    skill_registry = load(root, SKILL_REGISTRY)
    external_skill_radar = load(root, EXTERNAL_SKILL_RADAR)
    gui_intent = load(root, GUI_INTENT)
    gui_reuse_assessment = load(root, GUI_REUSE_ASSESSMENT)

    if not (
        gui_intent.get("schema") == "fa3.application-intent.v1"
        and gui_intent.get("project_id") == "FA3-DESKTOP-001"
        and gui_intent.get("declared_new_capabilities") == []
        and gui_intent.get("proposed_authority_roles") == []
        and gui_intent.get("hardware_audit", {}).get("vendor_neutral") is True
        and gui_intent.get("hardware_audit", {}).get("cpu_only_viable") is True
        and gui_intent.get("hardware_audit", {}).get("accelerator_cardinality") == "0..N"
        and gui_intent.get("namespace_claims", {}).get("requires_upstream_uninstall") is False
        and gui_intent.get("namespace_claims", {}).get("global_environment_mutation") is False
    ):
        findings.append(finding("REUSE-024", "GUI current-host ApplicationIntent boundary drift"))

    if not (
        gui_reuse_assessment.get("schema") == "fa3.reuse-assessment.v1"
        and gui_reuse_assessment.get("project_id") == "FA3-DESKTOP-001"
        and gui_reuse_assessment.get("intent_id") == "FA3-GUI-CURRENT-HOST-APPLICATION-INTENT-001"
        and gui_reuse_assessment.get("result") == "PASS"
        and gui_reuse_assessment.get("coexistence", {}).get("result") == "PASS"
        and gui_reuse_assessment.get("coexistence", {}).get("upstream_uninstall_required") is False
        and gui_reuse_assessment.get("coexistence", {}).get("global_mutation") is False
        and gui_reuse_assessment.get("hardware_audit", {}).get("cpu_only_viable") is True
        and gui_reuse_assessment.get("current_host_runtime_promotion_claim") is False
        and gui_reuse_assessment.get("global_promotion_claim") is False
        and gui_reuse_assessment.get("capability_count_after") == capability_count
        and gui_reuse_assessment.get("new_capabilities") == 0
        and gui_reuse_assessment.get("new_architectural_authorities") == 0
    ):
        findings.append(finding("REUSE-025", "GUI current-host ReuseAssessment boundary drift"))

    if not (
        profile.get("id") == "FA3-REUSE-DISCOVERY-001"
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == capability_count
        and profile.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(finding("REUSE-002", "profile capability/authority/promotion boundary drift"))

    if not (
        decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and isinstance(decision.get("capability_count_after"), int) and decision.get("capability_count_after") <= capability_count
        and decision.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(finding("REUSE-003", "decision baseline delta drift"))

    if not (
        catalog_policy.get("authority") is False
        and catalog_policy.get("derived") is True
        and catalog_policy.get("rebuildable") is True
        and catalog_policy.get("canonical_source_of_truth") is False
        and catalog_policy.get("capability_count") == capability_count
    ):
        findings.append(finding("REUSE-004", "derived reuse catalog authority boundary drift"))

    if not (
        contract.get("provider_neutral") is True
        and contract.get("new_capability") is False
        and contract.get("new_architectural_authority") is False
        and contract.get("capability_count") == capability_count
    ):
        findings.append(finding("REUSE-005", "contract family boundary drift"))

    if not (
        gate_record.get("gateset_id") == "FA3-REUSE-DISCOVERY-GATESET-001"
        and gate_record.get("fail_closed") is True
        and gate_record.get("mandatory_checks") == enforcement.get("mandatory_rule_count") == 23
        and len(enforcement.get("p0_invariants", [])) == 23
    ):
        findings.append(finding("REUSE-006", "gate/enforcement inventory drift"))

    if not (
        dfa.get("assessment") == "RECOMMENDED"
        and dfa.get("project_radar_checked") is True
        and dfa.get("hardware_audit", {}).get("vendor_neutral") is True
        and dfa.get("hardware_audit", {}).get("cpu_only_viable") is True
        and dfa.get("hardware_audit", {}).get("global_accelerator_requirement") is False
        and dfa.get("security_boundary", {}).get("may_expand_candidate_set") is False
    ):
        findings.append(finding("REUSE-007", "Decision Fabric bounded-advisory assessment drift"))

    built = build_catalog(root)
    ids = {row["candidate_id"] for row in built["entries"]}
    for rid in ("FA3-HARDWARE-BASELINE-001", "FA3-DISTRIBUTION-COMPLIANCE-001", "FA3-HIERARCHICAL-HYBRID-RETRIEVAL-001", "FA3-INFERENCE-PORTABILITY-001"):
        if rid not in ids:
            findings.append(finding("REUSE-008", "derived catalog missed required canonical reuse source", record_id=rid))

    skill_rows = {
        row["candidate_id"]: row
        for row in built["entries"]
        if row.get("candidate_class") == "SKILL"
    }
    admitted_skill_ids = {
        str(row.get("skill_id"))
        for row in skill_registry.get("entries", [])
        if isinstance(row, dict) and row.get("admission_status") == "ADMITTED" and row.get("skill_id")
    }
    if not admitted_skill_ids or not admitted_skill_ids.issubset(set(skill_rows)):
        findings.append(finding(
            "REUSE-021",
            "derived reuse catalog does not federate all admitted Skill Registry entries",
            missing=sorted(admitted_skill_ids - set(skill_rows)),
        ))
    for skill_id in sorted(admitted_skill_ids):
        row = skill_rows.get(skill_id, {})
        if not (
            row.get("status") == "ADMITTED"
            and row.get("task_scoped") is True
            and row.get("authority") is False
            and row.get("remote_fetch") is False
        ):
            findings.append(finding("REUSE-021", "admitted skill reuse boundary drift", skill_id=skill_id, row=row))

    external_rows = {
        (row.get("repository"), row.get("source_commit")): row
        for row in built["entries"]
        if row.get("candidate_class") == "EXTERNAL_SKILL_SOURCE"
    }
    radar_sources = [
        row for row in external_skill_radar.get("sources", [])
        if isinstance(row, dict) and row.get("repository") and row.get("commit")
    ]
    missing_external = [
        f"{row.get('repository')}@{row.get('commit')}"
        for row in radar_sources
        if (row.get("repository"), row.get("commit")) not in external_rows
    ]
    if missing_external:
        findings.append(finding("REUSE-022", "external skill radar sources missing from reuse catalog", missing=missing_external))
    for source in radar_sources:
        row = external_rows.get((source.get("repository"), source.get("commit")), {})
        if not (
            source.get("classification") == "REFERENCE_ONLY"
            and row.get("status") == "REFERENCE_ONLY"
            and row.get("distribution_class") == "REFERENCE_ONLY"
            and row.get("authority") is False
            and row.get("automatic_fetch") is False
            and row.get("automatic_install") is False
            and row.get("automatic_activation") is False
        ):
            findings.append(finding("REUSE-022", "external skill source gained trust/install semantics", source=source, row=row))

    skill_binding = profile.get("skill_fabric_binding", {})
    skill_contract = contract.get("contracts", {}).get("SkillReuseProjection", {})
    external_contract = contract.get("contracts", {}).get("ExternalSkillSourceProjection", {})
    registry_binding = skill_registry.get("reuse_discovery_binding", {})
    radar_binding = external_skill_radar.get("reuse_discovery_binding", {})
    if not (
        skill_binding.get("profile_id") == "FA3-SKILL-FABRIC-001"
        and skill_binding.get("registry_id") == "FA3-SKILL-REGISTRY-001"
        and skill_binding.get("external_radar_id") == "FA3-EXTERNAL-SKILL-RADAR-001"
        and skill_binding.get("only_admitted_skill_may_be_selected_for_task_context") is True
        and skill_binding.get("activation_remains_task_scoped") is True
        and skill_binding.get("automatic_install") is False
        and skill_binding.get("automatic_activation") is False
        and skill_contract.get("activation_authority") is False
        and skill_contract.get("task_scoped_required") is True
        and external_contract.get("classification_required") == "REFERENCE_ONLY"
        and external_contract.get("install_authority") is False
        and external_contract.get("admission_authority") is False
        and registry_binding.get("profile_id") == "FA3-REUSE-DISCOVERY-001"
        and registry_binding.get("admitted_entries_discoverable") is True
        and registry_binding.get("registry_entry_is_selection") is False
        and registry_binding.get("registry_entry_is_activation") is False
        and registry_binding.get("task_scoped_materialization_still_required") is True
        and radar_binding.get("profile_id") == "FA3-REUSE-DISCOVERY-001"
        and radar_binding.get("role") == "REFERENCE_IDEA_SOURCE_ONLY"
        and radar_binding.get("discovery_is_installation") is False
        and radar_binding.get("discovery_is_admission") is False
        and radar_binding.get("discovery_is_activation") is False
        and radar_binding.get("catalog_is_trust_authority") is False
    ):
        findings.append(finding("REUSE-023", "Skill Fabric / external skill source reuse contract boundary drift"))

    generated = assess_intent(root, golden_intent)
    selected_ids = {row["id"] for row in generated.get("selected_reuse", [])}
    if not (
        generated.get("result") == "PASS"
        and generated.get("implementation_readiness") == "PENDING_GAPS"
        and "fa3.document.retrieve" in selected_ids
        and not generated.get("authority_collisions")
        and not generated.get("hardware_findings")
        and not generated.get("coexistence_findings")
    ):
        findings.append(finding("REUSE-009", "Embedding Fabric golden reuse assessment no longer resolves deterministically", generated=generated))

    if not (
        golden_committed.get("project_status") == "PLANNED_NOT_MATERIALIZED_BY_THIS_CHANGE"
        and golden_committed.get("implementation_readiness") == "PENDING_GAPS"
        and golden_committed.get("result") == "PASS"
    ):
        findings.append(finding("REUSE-010", "committed Embedding Fabric golden assessment overclaims implementation/admission"))

    try:
        bounded_rank(["a", "b"], ["b", "a"])
        expanded_denied = False
        try:
            bounded_rank(["a", "b"], ["a", "c"])
        except ValueError:
            expanded_denied = True
        if not expanded_denied:
            findings.append(finding("REUSE-011", "Decision Fabric candidate expansion negative guard missing"))
    except Exception as exc:
        findings.append(finding("REUSE-011", "bounded ranking regression failed", error=repr(exc)))

    radar_surface = next((x for x in gui.get("surfaces", []) if x.get("route_id") == "decision.project-radar"), {})
    children = radar_surface.get("children", [])
    if not any(isinstance(x, dict) and x.get("surface_id") == "decision.reusable-assets" and x.get("authority") is False for x in children):
        findings.append(finding("REUSE-012", "Reusable Assets read-only GUI child projection missing"))
    qml = (root / GUI_QML).read_text(encoding="utf-8")
    if "Reusable Assets" not in qml or 'searchRecords("REUSE")' not in qml or 'searchRecords("PATTERN")' not in qml:
        findings.append(finding("REUSE-013", "Project Radar reusable-assets GUI projection drift"))

    jev_entry = next((x for x in jev.get("entries", []) if isinstance(x, dict) and x.get("source_repository") == "browser-use/jev-ultrafast"), {})
    if jev_entry.get("pattern_reimplementation_only") is not True or jev_entry.get("imports_architectural_authority") is not False:
        findings.append(finding("REUSE-014", "Jev reuse provenance federation boundary drift"))

    dist_rows = {x.get("subject_id"): x for x in dist.get("records", []) if isinstance(x, dict)}
    excluded = {x.get("subject_id"): x for x in manifest.get("excluded", []) if isinstance(x, dict)}
    if not (
        dist_rows.get("FA3-JEV-CODE-REUSE-001", {}).get("class") == "REFERENCE_ONLY"
        and excluded.get("FA3-JEV-CODE-REUSE-001", {}).get("release_bundle_status") == "EXCLUDED"
        and manifest.get("included_external_count") == 0
    ):
        findings.append(finding("REUSE-015", "reference-only reuse source distribution boundary drift"))

    if not (
        "FA3-REUSE-DISCOVERY-GATESET-001" in policy.get("mandatory_reference_gates", [])
        and policy.get("reuse_discovery_profile_id") == "FA3-REUSE-DISCOVERY-001"
        and policy.get("reuse_discovery_catalog_id") == "FA3-REUSE-CATALOG-001"
        and policy.get("reuse_discovery_mandatory_p0_rules") == enforcement.get("p0_invariants")
    ):
        findings.append(finding("REUSE-016", "global enforcement policy binding missing"))

    release = load(root, RELEASE)
    rec = release.get("reuse_discovery_reconciliation", {})
    if not (
        "FA3-REUSE-DISCOVERY-GATESET-001" in release.get("mandatory_reference_gates", [])
        and rec.get("profile_id") == "FA3-REUSE-DISCOVERY-001"
        and rec.get("catalog_id") == "FA3-REUSE-CATALOG-001"
        and rec.get("capability_count_after") == capability_count
        and rec.get("new_capabilities") == 0
        and rec.get("new_architectural_authorities") == 0
        and rec.get("global_promotion_claim") is False
    ):
        findings.append(finding("REUSE-017", "unified release projection reuse-discovery reconciliation missing or stale"))

    workflow = (root / WORKFLOW).read_text(encoding="utf-8")
    dedicated = (root / DEDICATED_WORKFLOW).read_text(encoding="utf-8") if (root / DEDICATED_WORKFLOW).is_file() else ""
    if "./bin/fa3-enforce reuse-discovery" not in workflow or "test_reuse_discovery_gate.py" not in dedicated:
        findings.append(finding("REUSE-018", "permanent/dedicated CI binding missing"))

    docs = (root / DECISION_DOC).read_text(encoding="utf-8")
    if "Reuse Discovery" not in docs or "FA3-REUSE-ASSESSMENT-001" not in docs:
        findings.append(finding("REUSE-019", "new-project adoption documentation missing mandatory reuse stage"))

    adoption = post_adoption_new_project_check(root)
    if adoption.get("result") != "PASS":
        findings.append(finding("REUSE-020", "post-adoption new-project requirement failed", adoption=adoption))

    result = "PASS" if not findings else "FAIL"
    return {
        "schema": "fa3.reuse-discovery-gate-report.v1",
        "gate_id": "FA3-GATE-REUSE-DISCOVERY-001",
        "gateset_id": "FA3-REUSE-DISCOVERY-GATESET-001",
        "profile_id": "FA3-REUSE-DISCOVERY-001",
        "result": result,
        "findings": findings,
        "catalog_entry_count": built["entry_count"],
        "golden_project": generated,
        "adoption_enforcement": adoption,
        "reference_evidence_status": evidence.get("status"),
        "capability_count": capability_count,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "current_host_runtime_promotion_claim": False,
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default="reports/reuse-discovery-gate-report.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = gate(root)
    path = root / args.report
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
