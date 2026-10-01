#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
KHRONOS_REUSE_DECISION = "canonical/decisions/FA3-DEC-KHRONOS-REUSE-SOURCE-2026-09-28.json"
KHRONOS_PROFILE = "canonical/profiles/FA3-KHRONOS-OPEN-STANDARDS-001.json"
KHRONOS_ADAPTER_REGISTRY = "canonical/FA3-KHRONOS-ADAPTER-REGISTRY-001.json"
KHRONOS_INTEGRATION = "canonical/integrations/FA3-KHRONOS-OPEN-STANDARDS-INTEGRATION-001.json"
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
DONOR_REGISTRY = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DONOR_REJECTION_AUDIT = "canonical/FA3-DONOR-REJECTION-AUDIT-001.json"
DONOR_LIFECYCLE_DECISION = "canonical/decisions/FA3-DEC-DONOR-LIFECYCLE-APPLICATION-SYNC-2026-09-30.json"
APPLICATION_DONOR_LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
DONOR_PLANNING_SNAPSHOT_GATESET = "FA3-DONOR-PLANNING-SNAPSHOT-GATESET-001"
EXPECTED_REUSE_RULE_COUNT = 38
DONOR_DECISION = "canonical/decisions/FA3-DEC-DONOR-REFERENCE-REGISTRY-2026-09-28.json"
DONOR_CAPTURE = "src/fa3_donor_registry.py"
DONOR_CAPTURE_BIN = "bin/fa3-donor-capture"
AGENT_INSTRUCTIONS = "AGENTS.md"
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


def _git_bytes(root: Path, *args: str) -> bytes | None:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout


def _git_show_bytes(root: Path, ref: str, rel: str) -> bytes | None:
    return _git_bytes(root, "show", f"{ref}:{rel}")


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _valid_sha40(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def validate_donor_planning_snapshot(
    assessment: dict[str, Any], expected: dict[str, Any]
) -> list[dict[str, Any]]:
    snapshot = assessment.get("donor_planning_snapshot")
    if not isinstance(snapshot, dict):
        return [finding(
            "REUSE-SNAPSHOT-001",
            "material reuse assessment missing donor_planning_snapshot",
            assessment_id=assessment.get("id"),
        )]
    findings: list[dict[str, Any]] = []
    required = {
        "published_main_commit": expected["published_main_commit"],
        "donor_registry_id": expected["donor_registry_id"],
        "donor_registry_blob_sha": expected["donor_registry_blob_sha"],
        "donor_registry_sha256": expected["donor_registry_sha256"],
        "donor_registry_entry_count": expected["donor_registry_entry_count"],
    }
    for key, value in required.items():
        if snapshot.get(key) != value:
            findings.append(finding(
                "REUSE-SNAPSHOT-002",
                "reuse assessment donor planning snapshot is stale or incomplete",
                assessment_id=assessment.get("id"),
                field=key,
                expected=value,
                declared=snapshot.get(key),
            ))
    return findings


def validate_shared_capability_placement(
    assessment: dict[str, Any]
) -> list[dict[str, Any]]:
    placement = assessment.get("shared_capability_placement")
    if not isinstance(placement, dict):
        return [finding(
            "REUSE-SNAPSHOT-010",
            "material reuse assessment missing shared_capability_placement review",
            assessment_id=assessment.get("id"),
        )]
    findings: list[dict[str, Any]] = []
    if placement.get("reviewed") is not True:
        findings.append(finding(
            "REUSE-SNAPSHOT-011",
            "shared-capability placement review must be explicit",
            assessment_id=assessment.get("id"),
        ))
    if placement.get("retrospective_consumer_impact_reviewed") is not True:
        findings.append(finding(
            "REUSE-SNAPSHOT-012",
            "shared-capability review must cover planned, in-progress and materialized consumers",
            assessment_id=assessment.get("id"),
        ))
    multi = placement.get("multi_application_reuse_detected")
    if not isinstance(multi, bool):
        findings.append(finding(
            "REUSE-SNAPSHOT-013",
            "shared-capability review must explicitly classify multi-application reuse",
            assessment_id=assessment.get("id"),
        ))
        return findings
    disposition = placement.get("disposition")
    allowed = {"SHARED", "LOCAL_SINGLE_CONSUMER", "LOCAL_WITH_REVIEWED_JUSTIFICATION", "NOT_APPLICABLE"}
    if disposition not in allowed:
        findings.append(finding(
            "REUSE-SNAPSHOT-014",
            "invalid shared-capability placement disposition",
            assessment_id=assessment.get("id"),
            disposition=disposition,
        ))
    if multi:
        if disposition == "SHARED":
            ids = placement.get("shared_component_ids")
            if not isinstance(ids, list) or not ids or not all(isinstance(x, str) and x for x in ids):
                findings.append(finding(
                    "REUSE-SNAPSHOT-015",
                    "multi-application shared disposition requires shared_component_ids",
                    assessment_id=assessment.get("id"),
                ))
        elif disposition == "LOCAL_WITH_REVIEWED_JUSTIFICATION":
            reason = placement.get("local_exception_reason")
            if not isinstance(reason, str) or not reason.strip():
                findings.append(finding(
                    "REUSE-SNAPSHOT-016",
                    "local duplicate of multi-application function requires reviewed justification",
                    assessment_id=assessment.get("id"),
                ))
        else:
            findings.append(finding(
                "REUSE-SNAPSHOT-017",
                "multi-application function must be shared or have a reviewed local exception",
                assessment_id=assessment.get("id"),
                disposition=disposition,
            ))
    return findings


def validate_assessment_donor_usage_edges(
    assessment: dict[str, Any], links: dict[str, Any]
) -> list[dict[str, Any]]:
    expected: set[str] = set()
    for row in assessment.get("donor_pattern_reuse", []):
        if isinstance(row, dict) and isinstance(row.get("donor_id"), str):
            expected.add(row["donor_id"])
    for row in assessment.get("adopted_donors", []):
        if isinstance(row, dict) and isinstance(row.get("donor_id"), str):
            expected.add(row["donor_id"])
    if assessment.get("adoption_authorized") is True or assessment.get("donor_adoption_authorized") is True:
        selected = assessment.get("selected_existing_donor_ids", [])
        if isinstance(selected, list):
            expected.update(x for x in selected if isinstance(x, str))
    if not expected:
        return []
    active = {
        row.get("donor_id")
        for row in links.get("donor_usage_records", [])
        if isinstance(row, dict) and row.get("status") != "REMOVED"
    }
    return [
        finding(
            "REUSE-SNAPSHOT-018",
            "actual donor adoption/pattern use lacks canonical donor usage edge",
            assessment_id=assessment.get("id"),
            donor_id=donor_id,
        )
        for donor_id in sorted(expected - active)
    ]


def _material_planning_path(rel: str) -> bool:
    if rel in {PROFILE, CONTRACT}:
        return False
    if rel.startswith(("canonical/intents/", "canonical/profiles/", "canonical/providers/", "apps/")):
        return True
    if rel.startswith("canonical/contracts/"):
        return True
    name = Path(rel).name
    return rel.startswith("canonical/") and "SHARED" in name and rel.endswith(".json")


def donor_planning_snapshot_check(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    base = os.getenv("FA3_CHANGE_BASE_SHA", "").strip()
    head = os.getenv("FA3_CHANGE_HEAD_SHA", "").strip()
    published = os.getenv("FA3_PUBLISHED_MAIN_SHA", "").strip()

    links = load(root, APPLICATION_DONOR_LINKS)
    usage_policy = links.get("policy", {})
    if not (
        usage_policy.get("donor_usage_record_required_before_adoption") is True
        and usage_policy.get("explicit_canonical_donor_use_requires_usage_edge") is True
        and usage_policy.get("shared_capability_donor_adoption_requires_usage_edge") is True
        and usage_policy.get("shared_capability_local_duplication_forbidden_without_justification") is True
        and usage_policy.get("retrospective_shared_impact_required") is True
    ):
        findings.append(finding(
            "REUSE-SNAPSHOT-020",
            "donor usage/shared capability fail-closed policy binding is incomplete",
        ))

    if not (base or head or published):
        return {
            "gate_id": DONOR_PLANNING_SNAPSHOT_GATESET,
            "result": "PASS" if not findings else "FAIL",
            "state": "STATIC_POLICY_ONLY",
            "material_change_paths": [],
            "assessment_paths": [],
            "findings": findings,
        }
    if not all(_valid_sha40(x) for x in (base, head, published)):
        findings.append(finding("REUSE-SNAPSHOT-021", "invalid or incomplete Git change context"))
        return {
            "gate_id": DONOR_PLANNING_SNAPSHOT_GATESET,
            "result": "FAIL",
            "state": "CHANGE_CONTEXT_INVALID",
            "material_change_paths": [],
            "assessment_paths": [],
            "findings": findings,
        }
    if published != base:
        findings.append(finding(
            "REUSE-SNAPSHOT-022",
            "published-main planning anchor differs from PR/change base",
            published_main_commit=published,
            change_base_commit=base,
        ))

    raw_registry = _git_show_bytes(root, published, DONOR_REGISTRY)
    if raw_registry is None:
        findings.append(finding(
            "REUSE-SNAPSHOT-023",
            "published-main donor registry snapshot is unavailable",
            published_main_commit=published,
        ))
        return {
            "gate_id": DONOR_PLANNING_SNAPSHOT_GATESET,
            "result": "FAIL",
            "state": "PUBLISHED_MAIN_SNAPSHOT_UNAVAILABLE",
            "material_change_paths": [],
            "assessment_paths": [],
            "findings": findings,
        }
    try:
        registry = json.loads(raw_registry.decode("utf-8"))
    except Exception as exc:
        findings.append(finding(
            "REUSE-SNAPSHOT-024",
            "published-main donor registry is unreadable",
            error=repr(exc),
        ))
        registry = {"entries": []}

    expected = {
        "published_main_commit": published,
        "donor_registry_id": registry.get("id"),
        "donor_registry_blob_sha": _git_blob_sha(raw_registry),
        "donor_registry_sha256": hashlib.sha256(raw_registry).hexdigest(),
        "donor_registry_entry_count": len(registry.get("entries", [])) if isinstance(registry.get("entries"), list) else -1,
    }

    changed_text = _git(root, "diff", "--name-only", "--diff-filter=AM", base, head, "--")
    if changed_text is None:
        findings.append(finding("REUSE-SNAPSHOT-025", "change-set diff unavailable"))
        changed: list[str] = []
    else:
        changed = [x for x in changed_text.splitlines() if x]
    material = sorted(rel for rel in changed if _material_planning_path(rel))

    assessments: list[tuple[str, dict[str, Any]]] = []
    for rel in changed:
        if not (rel.startswith("canonical/assessments/") and rel.endswith(".json")):
            continue
        raw = _git_show_bytes(root, head, rel)
        if raw is None:
            continue
        try:
            row = json.loads(raw.decode("utf-8"))
        except Exception:
            findings.append(finding("REUSE-SNAPSHOT-026", "changed assessment unreadable", path=rel))
            continue
        if isinstance(row, dict) and row.get("schema") == "fa3.reuse-assessment.v1":
            assessments.append((rel, row))

    if material and not assessments:
        findings.append(finding(
            "REUSE-SNAPSHOT-027",
            "material application/module/profile/provider/shared change lacks changed Reuse Assessment",
            material_change_paths=material,
        ))

    intent_ids: list[str] = []
    record_ids: list[str] = []
    for rel in material:
        raw = _git_show_bytes(root, head, rel)
        if raw is None or not rel.endswith(".json"):
            continue
        try:
            row = json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        if rel.startswith("canonical/intents/") and row.get("schema") == "fa3.application-intent.v1":
            if isinstance(row.get("id"), str):
                intent_ids.append(row["id"])
        elif rel.startswith(("canonical/profiles/", "canonical/providers/")) and isinstance(row.get("id"), str):
            record_ids.append(row["id"])

    for rel, assessment in assessments:
        if assessment.get("result") != "PASS":
            findings.append(finding(
                "REUSE-SNAPSHOT-028",
                "material Reuse Assessment must be PASS before finalization",
                path=rel,
                result=assessment.get("result"),
            ))
        findings.extend(validate_donor_planning_snapshot(assessment, expected))
        findings.extend(validate_shared_capability_placement(assessment))
        findings.extend(validate_assessment_donor_usage_edges(assessment, links))

    for intent_id in sorted(set(intent_ids)):
        if not any(row.get("intent_id") == intent_id for _, row in assessments):
            findings.append(finding(
                "REUSE-SNAPSHOT-029",
                "changed ApplicationIntent lacks matching changed Reuse Assessment",
                intent_id=intent_id,
            ))
    for record_id in sorted(set(record_ids)):
        def covers(row: dict[str, Any]) -> bool:
            covered = row.get("covered_ids", [])
            return (
                row.get("subject_id") == record_id
                or row.get("project_id") == record_id
                or (isinstance(covered, list) and record_id in covered)
            )
        if not any(covers(row) for _, row in assessments):
            findings.append(finding(
                "REUSE-SNAPSHOT-030",
                "changed profile/provider lacks matching changed Reuse Assessment",
                record_id=record_id,
            ))

    return {
        "gate_id": DONOR_PLANNING_SNAPSHOT_GATESET,
        "result": "PASS" if not findings else "FAIL",
        "state": "ENFORCED",
        "published_main_snapshot": expected,
        "material_change_paths": material,
        "assessment_paths": [rel for rel, _ in assessments],
        "findings": findings,
    }


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


def _assessment_by_intent_index(root: Path) -> dict[str, list[dict[str, Any]]]:
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
        intent_id = row.get("intent_id")
        if isinstance(intent_id, str) and intent_id:
            index.setdefault(intent_id, []).append({"path": path.relative_to(root).as_posix(), "row": row})
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
    active = load_active_release_baseline(root)
    if active.release != "2026-09-26/v3.1.0" or active.capability_count != 175:
        return False
    if current.get("capability_model_reconciliation") != "FA3-DEC-CAPABILITY-MODEL-175-2026-09-26":
        return False

    old = json.loads(json.dumps(previous))
    new = json.loads(json.dumps(current))
    new.pop("capability_baseline_release", None)
    new.pop("capability_model_reconciliation", None)

    mirrored = False
    if old.get("capability_count") == 143 and new.get("capability_count") == 175:
        old.pop("capability_count", None)
        new.pop("capability_count", None)
        mirrored = True

    old_accounting = old.get("capability_accounting")
    new_accounting = new.get("capability_accounting")
    if isinstance(old_accounting, dict) and isinstance(new_accounting, dict):
        if old_accounting.get("capability_count_after") == 143 and new_accounting.get("capability_count_after") == 175:
            old_accounting.pop("capability_count_after", None)
            new_accounting.pop("capability_count_after", None)
            mirrored = True

    return mirrored and old == new


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


def post_khronos_source_adoption_check(root: Path) -> dict[str, Any]:
    history = _git(root, "log", "--format=%H", "--reverse", "--", KHRONOS_REUSE_DECISION)
    if not history:
        return {"result": "PASS", "state": "ADOPTION_MARKER_NOT_COMMITTED_YET", "checked": []}
    marker = history.splitlines()[0]
    changed = _git(root, "diff", "--name-only", "--diff-filter=AM", f"{marker}..HEAD", "--", "canonical/intents")
    if changed is None:
        return {"result": "PASS", "state": "GIT_DIFF_UNAVAILABLE", "checked": []}
    assessments = _assessment_by_intent_index(root)
    findings = []
    checked = []
    for rel in [x for x in changed.splitlines() if x.endswith(".json")]:
        try:
            intent = load(root, rel)
        except Exception as exc:
            findings.append(finding("REUSE-KHRONOS-ADOPT-001", "ApplicationIntent unreadable", path=rel, error=repr(exc)))
            continue
        if intent.get("schema") != "fa3.application-intent.v1":
            continue
        intent_id = intent.get("id")
        if not isinstance(intent_id, str) or not intent_id:
            findings.append(finding("REUSE-KHRONOS-ADOPT-002", "ApplicationIntent missing id", path=rel))
            continue
        checked.append(intent_id)
        discovery_declared = (
            intent.get("project_id") == "FA3-REUSE-DISCOVERY-001"
            or "FA3-REUSE-DISCOVERY-001" in intent.get("integration_requirements", [])
        )
        valid_assessment = False
        for match in assessments.get(intent_id, []):
            assessment = match["row"]
            review = next((
                row for row in assessment.get("mandatory_source_reviews", [])
                if isinstance(row, dict) and row.get("source_family_id") == "FA3-KHRONOS-OPEN-STANDARDS-001"
            ), {})
            if (
                assessment.get("result") == "PASS"
                and review.get("review_status") in {"MATCHED", "REVIEWED_NO_MATCH"}
                and review.get("authority") is False
                and review.get("automatic_selection") is False
            ):
                valid_assessment = True
                break
        if not discovery_declared or not valid_assessment:
            findings.append(finding(
                "REUSE-KHRONOS-ADOPT-003",
                "post-adoption ApplicationIntent lacks mandatory Khronos source-family review",
                intent_id=intent_id,
                path=rel,
                reuse_discovery_declared=discovery_declared,
                matching_assessment=valid_assessment,
            ))
    return {"result": "PASS" if not findings else "FAIL", "state": "ENFORCED", "marker_commit": marker, "checked": checked, "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    capability_count = load_active_release_baseline(root).capability_count
    findings: list[dict[str, Any]] = []
    required = [
        PROFILE, CONTRACT, CATALOG, DECISION, KHRONOS_REUSE_DECISION, KHRONOS_PROFILE,
        KHRONOS_ADAPTER_REGISTRY, KHRONOS_INTEGRATION, GATE_RECORD, ENFORCEMENT,
        "canonical/contracts/FA3-APPLICATION-INTENT-001.schema.json",
        "canonical/contracts/FA3-REUSABLE-PATTERN-001.schema.json",
        "canonical/contracts/FA3-REUSE-ASSESSMENT-001.schema.json",
        DECISION_ASSESSMENT, GOLDEN_INTENT, GOLDEN_ASSESSMENT,
        "canonical/intents/FA3-REUSE-DISCOVERY-APPLICATION-INTENT-001.json",
        "canonical/assessments/FA3-REUSE-DISCOVERY-REUSE-ASSESSMENT-001.json",
        "src/fa3_reuse_catalog.py", "src/fa3_reuse_resolver.py", "src/fa3_reuse_assessment.py",
        "bin/fa3-reuse-assess", "tests/test_reuse_discovery_gate.py", DECISION_DOC,
        SKILL_REGISTRY, EXTERNAL_SKILL_RADAR, GUI_INTENT, GUI_REUSE_ASSESSMENT,
        DONOR_REGISTRY, DONOR_DECISION, DONOR_CAPTURE, DONOR_CAPTURE_BIN, AGENT_INSTRUCTIONS,
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
    khronos_reuse_decision = load(root, KHRONOS_REUSE_DECISION)
    khronos_profile = load(root, KHRONOS_PROFILE)
    khronos_adapter_registry = load(root, KHRONOS_ADAPTER_REGISTRY)
    khronos_integration = load(root, KHRONOS_INTEGRATION)
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
    donor_registry = load(root, DONOR_REGISTRY)
    donor_rejection_audit = load(root, DONOR_REJECTION_AUDIT)
    donor_lifecycle_decision = load(root, DONOR_LIFECYCLE_DECISION)
    donor_decision = load(root, DONOR_DECISION)
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
        and gate_record.get("mandatory_checks") == enforcement.get("mandatory_rule_count") == EXPECTED_REUSE_RULE_COUNT
        and len(enforcement.get("p0_invariants", [])) == EXPECTED_REUSE_RULE_COUNT
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

    donor_binding = profile.get("donor_reference_binding", {})
    donor_catalog_binding = catalog_policy.get("donor_registry_binding", {})
    donor_contract = contract.get("contracts", {}).get("DonorReferenceProjection", {})
    donor_capture_policy = donor_registry.get("capture_policy", {})
    donor_planning_policy = donor_registry.get("planning_policy", {})
    donor_safety = donor_registry.get("safety_boundary", {})
    donor_hardware = donor_registry.get("hardware_audit", {})
    donor_entries = [row for row in donor_registry.get("entries", []) if isinstance(row, dict)]
    required_donor_fields = {
        "donor_id", "name", "source", "status", "donor_modes", "capability_hints",
        "domain_hints", "target_hints", "license", "code_reuse_policy",
        "discoverable_for_planning", "authority",
    }
    allowed_donor_states = {"CANDIDATE", "ANALYZED", "ACCEPTED_REFERENCE", "SUPERSEDED"}
    donor_ids = [str(row.get("donor_id")) for row in donor_entries if row.get("donor_id")]
    donor_keys = [
        str(row.get("source", {}).get("normalized_key"))
        for row in donor_entries
        if isinstance(row.get("source"), dict) and row.get("source", {}).get("normalized_key")
    ]
    invalid_donor_entries = [
        str(row.get("donor_id") or row.get("name") or "<unknown>")
        for row in donor_entries
        if not required_donor_fields.issubset(row)
        or row.get("status") not in allowed_donor_states
        or row.get("authority") is not False
    ]
    required_backfill = {
        "FA3-DONOR-AGENT0AI-AGENT-ZERO-001",
        "FA3-DONOR-MICROSOFT-MCP-GATEWAY-001",
        "FA3-DONOR-CYTOSTACK-OPENWOLF-001",
        "FA3-DONOR-VIGOZHAO-AI-VISUAL-PROMPT-COOKBOOK-001",
        "FA3-DONOR-NVIDIA-MODEL-OPTIMIZER-001",
        "FA3-DONOR-GARRYTAN-GSTACK-001",
        "FA3-DONOR-BOADIJ-PI-HERDSMAN-001",
        "FA3-DONOR-P4NDA0S-REVERSE-SKILLS-001",
        "FA3-DONOR-SYSTEM-ONE-HARNESS-001",
    }
    if not (
        donor_registry.get("schema") == "fa3.donor-reference-registry.v1"
        and donor_registry.get("id") == "FA3-DONOR-REFERENCE-REGISTRY-001"
        and donor_registry.get("authority") is False
        and donor_registry.get("new_capability") is False
        and donor_registry.get("new_architectural_authority") is False
        and donor_registry.get("capability_count") == capability_count
        and donor_decision.get("capture_rule") == "ONLY_LINKS_EXPLICITLY_PRECEDED_BY_OWNER_DONORNAK_MARKER_MAY_ENTER_REGISTRY"
        and "AUTOMATIC_POTENTIAL_DONOR_CANDIDATE_CAPTURE" in donor_decision.get("policy_supersedes", [])
        and donor_capture_policy.get("potential_donor_signal_requires_capture") is False
        and donor_capture_policy.get("trigger_semantics") == "ONLY_EXPLICIT_OWNER_DONORNAK_MARKED_LINKS_MAY_ENTER_REGISTRY"
        and donor_capture_policy.get("default_status") == "NO_CAPTURE_ANALYSIS_ONLY"
        and donor_capture_policy.get("owner_marker_required") == "donornak"
        and donor_capture_policy.get("owner_role_required") is True
        and donor_capture_policy.get("owner_marked_capture_status") == "ACCEPTED_REFERENCE"
        and donor_capture_policy.get("unmarked_link_disposition") == "ANALYSIS_ONLY_NO_REGISTRY_MUTATION"
        and donor_capture_policy.get("legacy_automatic_candidate_capture") is False
        and donor_capture_policy.get("conversation_capture_is_admission") is False
        and donor_planning_policy.get("query_required_for_every_new_or_materially_modified_application_capability_or_module") is True
        and donor_planning_policy.get("query_before_new_implementation") is True
        and donor_planning_policy.get("future_applications_supported") is True
        and donor_planning_policy.get("every_donor_change_requires_processing") is True
        and donor_planning_policy.get("donor_change_application_reconciliation_required") is True
        and donor_planning_policy.get("donor_usage_reverse_traceability_required") is True
        and donor_planning_policy.get("monthly_capability_refresh_days") == 31
        and donor_planning_policy.get("capability_non_regression_on_donor_change") is True
        and donor_planning_policy.get("capability_loss_only_for_verified_fa3_risk") is True
        and donor_planning_policy.get("security_reentry_requires_verified_safe_evidence") is True
        and donor_planning_policy.get("rejected_history_registry") == DONOR_REJECTION_AUDIT
        and donor_binding.get("registry_id") == "FA3-DONOR-REFERENCE-REGISTRY-001"
        and donor_binding.get("potential_donor_signal_requires_capture") is False
        and donor_binding.get("owner_marker_required") == "donornak"
        and donor_binding.get("published_main_registry_only") is True
        and donor_binding.get("authority") is False
        and donor_catalog_binding.get("registry_id") == "FA3-DONOR-REFERENCE-REGISTRY-001"
        and donor_catalog_binding.get("query_required_before_new_implementation") is True
        and donor_catalog_binding.get("authority") is False
        and donor_contract.get("potential_signal_capture_required") is False
        and donor_contract.get("owner_marker_required") == "donornak"
        and donor_contract.get("unmarked_links_analysis_only") is True
        and donor_contract.get("rejected_sources_archived_outside_active_registry") is True
        and donor_contract.get("rejection_audit_id") == "FA3-DONOR-REJECTION-AUDIT-001"
        and donor_contract.get("rejected_reentry_requires_verified_safe_evidence") is True
        and donor_contract.get("every_donor_change_requires_processing") is True
        and donor_contract.get("donor_to_application_reverse_traceability_required") is True
        and donor_contract.get("capability_non_regression_on_donor_change") is True
        and donor_contract.get("capability_loss_only_for_verified_fa3_risk") is True
        and donor_contract.get("authority") is False
        and donor_contract.get("admission_authority") is False
        and donor_hardware.get("vendor_neutral") is True
        and donor_hardware.get("cpu_only_viable") is True
        and donor_hardware.get("accelerator_cardinality") == "0..N"
        and donor_hardware.get("global_accelerator_requirement") is False
        and all(donor_safety.get(key) is False for key in (
            "automatic_dependency", "automatic_code_import", "automatic_fetch", "automatic_install",
            "automatic_provider_admission", "automatic_model_selection", "automatic_activation",
            "architectural_authority", "runtime_promotion_from_registry_entry",
        ))
    ):
        findings.append(finding("REUSE-031", "Donor Registry canonical non-authority/capture/planning boundary drift"))

    if not (
        donor_rejection_audit.get("id") == "FA3-DONOR-REJECTION-AUDIT-001"
        and donor_rejection_audit.get("active_donor_registry") is False
        and donor_lifecycle_decision.get("id") == "FA3-DEC-DONOR-LIFECYCLE-APPLICATION-SYNC-2026-09-30"
        and donor_lifecycle_decision.get("capability_count") == capability_count
        and donor_lifecycle_decision.get("rules", {}).get("every_donor_change_must_be_processed") is True
        and donor_lifecycle_decision.get("rules", {}).get("donor_change_capability_non_regression") is True
        and len(donor_entries) >= 160
        and donor_registry.get("backfill", {}).get("entry_count") == len(donor_entries)
        and len(donor_ids) == len(set(donor_ids)) == len(donor_entries)
        and len(donor_keys) == len(set(donor_keys)) == len(donor_entries)
        and not invalid_donor_entries
        and required_backfill.issubset(set(donor_ids))
    ):
        findings.append(finding(
            "REUSE-032",
            "Donor Registry backfill/integrity drift",
            entry_count=len(donor_entries),
            invalid_entries=invalid_donor_entries[:20],
            missing_required_backfill=sorted(required_backfill - set(donor_ids)),
        ))

    if not (
        donor_decision.get("registry_id") == "FA3-DONOR-REFERENCE-REGISTRY-001"
        and donor_decision.get("reuse_discovery_profile_id") == "FA3-REUSE-DISCOVERY-001"
        and donor_decision.get("new_capabilities") == 0
        and donor_decision.get("new_architectural_authorities") == 0
        and donor_decision.get("capability_count_after") == capability_count
        and donor_decision.get("authority") is False
        and donor_decision.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(finding("REUSE-033", "Donor Registry adoption decision boundary drift"))

    agent_instructions = (root / AGENT_INSTRUCTIONS).read_text(encoding="utf-8")
    capture_source = (root / DONOR_CAPTURE).read_text(encoding="utf-8")
    capture_bin = (root / DONOR_CAPTURE_BIN).read_text(encoding="utf-8")
    if not (
        "## FA3 donor capture rule" in agent_instructions
        and "./bin/fa3-donor-capture" in agent_instructions
        and "capture_candidate(" in capture_source
        and "default=\"conversation\"" in capture_source
        and "fa3_donor_registry.py" in capture_bin
    ):
        findings.append(finding("REUSE-034", "explicit owner donor-capture instruction/tooling drift"))

    source_review = next((
        row for row in catalog_policy.get("mandatory_source_reviews", [])
        if isinstance(row, dict) and row.get("source_family_id") == "FA3-KHRONOS-OPEN-STANDARDS-001"
    ), {})
    profile_binding = profile.get("open_standards_reuse_binding", {})
    adapter_binding = khronos_adapter_registry.get("reuse_discovery_binding", {})
    integration_binding = khronos_integration.get("reuse_discovery_binding", {})
    khronos_profile_binding = khronos_profile.get("reuse_discovery_binding", {})
    open_standard_contract = contract.get("contracts", {}).get("OpenStandardsReuseProjection", {})
    expected_sources = {
        "canonical/profiles/FA3-KHRONOS-OPEN-STANDARDS-001.json",
        KHRONOS_ADAPTER_REGISTRY,
        KHRONOS_INTEGRATION,
    }
    if not (
        set(source_review.get("sources", [])) == expected_sources
        and source_review.get("review") == "MANDATORY_BEFORE_IMPLEMENTATION"
        and source_review.get("selection_semantics") == "MATCH_ONLY_NON_AUTHORITATIVE"
        and source_review.get("no_match_disposition") == "REVIEWED_NO_MATCH"
        and source_review.get("authority") is False
        and source_review.get("automatic_selection") is False
        and profile_binding.get("review_required_for_every_new_application") is True
        and profile_binding.get("authority") is False
        and profile_binding.get("automatic_selection") is False
        and open_standard_contract.get("source_family_id_const") == "FA3-KHRONOS-OPEN-STANDARDS-001"
        and open_standard_contract.get("authority") is False
        and open_standard_contract.get("automatic_selection") is False
        and all(binding.get("source_family_id") == "FA3-KHRONOS-OPEN-STANDARDS-001" for binding in (adapter_binding, integration_binding, khronos_profile_binding))
        and all(binding.get("authority") is False and binding.get("automatic_selection") is False for binding in (adapter_binding, integration_binding, khronos_profile_binding))
    ):
        findings.append(finding("REUSE-026", "Khronos mandatory source-family binding drift"))

    if not (
        khronos_reuse_decision.get("new_capabilities") == 0
        and khronos_reuse_decision.get("new_architectural_authorities") == 0
        and khronos_reuse_decision.get("mandatory_review_scope") == "ALL_NEW_OR_MATERIALLY_MODIFIED_FA3_APPLICATION_INTENTS"
        and khronos_reuse_decision.get("automatic_selection") is False
        and khronos_reuse_decision.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(finding("REUSE-027", "Khronos reuse-source adoption decision boundary drift"))

    built = build_catalog(root)
    ids = {row["candidate_id"] for row in built["entries"]}
    for rid in ("FA3-HARDWARE-BASELINE-001", "FA3-DISTRIBUTION-COMPLIANCE-001", "FA3-HIERARCHICAL-HYBRID-RETRIEVAL-001", "FA3-INFERENCE-PORTABILITY-001"):
        if rid not in ids:
            findings.append(finding("REUSE-008", "derived catalog missed required canonical reuse source", record_id=rid))

    expected_donor_ids = {
        str(row.get("donor_id"))
        for row in donor_entries
        if row.get("donor_id")
        and row.get("discoverable_for_planning") is True
        and row.get("status") != "SUPERSEDED"
    }
    catalog_donors = {
        row["candidate_id"]: row
        for row in built["entries"]
        if row.get("candidate_class") == "DONOR_REFERENCE"
    }
    if set(catalog_donors) != expected_donor_ids:
        findings.append(finding(
            "REUSE-035",
            "Donor Registry is not fully federated into derived Reuse Catalog",
            missing=sorted(expected_donor_ids - set(catalog_donors)),
            unexpected=sorted(set(catalog_donors) - expected_donor_ids),
        ))
    for donor_id, row in catalog_donors.items():
        if not (
            row.get("authority") is False
            and row.get("distribution_class") == "REFERENCE_ONLY"
            and row.get("release_bundle_status") == "EXCLUDED"
            and row.get("automatic_selection") is False
            and row.get("automatic_fetch") is False
            and row.get("automatic_install") is False
            and row.get("automatic_activation") is False
            and row.get("automatic_dependency") is False
            and row.get("automatic_code_import") is False
            and row.get("automatic_provider_admission") is False
            and row.get("automatic_model_selection") is False
        ):
            findings.append(finding("REUSE-036", "Donor catalog candidate gained authority/adoption semantics", donor_id=donor_id))

    adapter_ids = {
        str(row.get("id"))
        for row in khronos_adapter_registry.get("adapters", [])
        if isinstance(row, dict) and row.get("id")
    }
    catalog_adapters = {
        row["candidate_id"]: row
        for row in built["entries"]
        if row.get("candidate_class") == "OPEN_STANDARD_ADAPTER"
    }
    binding_ids = {
        "FA3-KHRONOS-BINDING:" + str(row.get("layer"))
        for row in khronos_integration.get("bindings", [])
        if isinstance(row, dict) and row.get("layer")
    }
    catalog_bindings = {
        row["candidate_id"]: row
        for row in built["entries"]
        if row.get("candidate_class") == "OPEN_STANDARD_FABRIC_BINDING"
    }
    if adapter_ids != set(catalog_adapters) or binding_ids != set(catalog_bindings):
        findings.append(finding(
            "REUSE-028",
            "Khronos adapter/integration sources are not fully projected into reuse catalog",
            missing_adapters=sorted(adapter_ids - set(catalog_adapters)),
            missing_bindings=sorted(binding_ids - set(catalog_bindings)),
        ))
    for row in list(catalog_adapters.values()) + list(catalog_bindings.values()):
        if not (
            row.get("authority") is False
            and row.get("automatic_selection") is False
            and row.get("standard_family") == "KHRONOS"
        ):
            findings.append(finding("REUSE-029", "Khronos catalog candidate gained authority or automatic selection", row=row))

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
        and any(
            isinstance(row, dict)
            and row.get("source_family_id") == "FA3-KHRONOS-OPEN-STANDARDS-001"
            and row.get("review_status") in {"MATCHED", "REVIEWED_NO_MATCH"}
            and row.get("authority") is False
            and row.get("automatic_selection") is False
            for row in generated.get("mandatory_source_reviews", [])
        )
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
        and rec.get("donor_rejection_audit_id") == "FA3-DONOR-REJECTION-AUDIT-001"
        and rec.get("donor_lifecycle_decision_id") == "FA3-DEC-DONOR-LIFECYCLE-APPLICATION-SYNC-2026-09-30"
        and rec.get("application_donor_links_id") == "FA3-APPLICATION-DONOR-LINKS-001"
        and rec.get("donor_every_change_processed") is True
        and rec.get("donor_usage_reverse_traceability") is True
        and rec.get("donor_monthly_capability_refresh_days") == 31
        and rec.get("donor_security_change_propagation") is True
        and rec.get("donor_unsafe_active_registry_forbidden") is True
        and rec.get("application_scope_independent_of_declared_dependency") is True
        and rec.get("application_capability_non_regression_on_donor_change") is True
        and rec.get("application_capability_loss_only_for_verified_fa3_risk") is True
        and rec.get("application_current_host_alignment_when_affected") is True
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

    khronos_adoption = post_khronos_source_adoption_check(root)
    if khronos_adoption.get("result") != "PASS":
        findings.append(finding("REUSE-030", "post-adoption mandatory Khronos source review failed", adoption=khronos_adoption))

    donor_snapshot = donor_planning_snapshot_check(root)
    if donor_snapshot.get("result") != "PASS":
        findings.append(finding(
            "REUSE-031",
            "donor planning snapshot/shared-capability placement gate failed",
            donor_planning_snapshot=donor_snapshot,
        ))

    result = "PASS" if not findings else "FAIL"
    return {
        "schema": "fa3.reuse-discovery-gate-report.v1",
        "gate_id": "FA3-GATE-REUSE-DISCOVERY-001",
        "gateset_id": "FA3-REUSE-DISCOVERY-GATESET-001",
        "profile_id": "FA3-REUSE-DISCOVERY-001",
        "result": result,
        "findings": findings,
        "catalog_entry_count": built["entry_count"],
        "donor_registry_entry_count": len(donor_entries),
        "donor_catalog_candidate_count": len(catalog_donors),
        "golden_project": generated,
        "adoption_enforcement": adoption,
        "khronos_source_adoption_enforcement": khronos_adoption,
        "donor_planning_snapshot_enforcement": donor_snapshot,
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
