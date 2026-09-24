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


def post_adoption_new_project_check(root: Path) -> dict[str, Any]:
    history = _git(root, "log", "--format=%H", "--reverse", "--", DECISION)
    if not history:
        return {"result": "PASS", "state": "ADOPTION_MARKER_NOT_COMMITTED_YET", "checked": []}
    marker = history.splitlines()[0]
    changed = _git(root, "diff", "--name-only", "--diff-filter=A", f"{marker}..HEAD", "--", "canonical/profiles", "canonical/providers")
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
        valid = False
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
            findings.append(finding("REUSE-ADOPT-002", "post-adoption new profile/provider lacks PASS reuse assessment + ApplicationIntent", record_id=rid, path=rel))
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
        and decision.get("capability_count_after") == capability_count
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
        and gate_record.get("mandatory_checks") == enforcement.get("mandatory_rule_count") == 20
        and len(enforcement.get("p0_invariants", [])) == 20
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
