#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import load_active_release_baseline

GATE_ID = "FA3-STORY-PRESENTATION-GATESET-001"
PROFILE_ID = "FA3-STORY-PRESENTATION-FABRIC-001"
CONTRACT_ID = "FA3-STORY-PRESENTATION-CONTRACTS-001"
PRODUCTION_REGISTRY_ID = "FA3-STORY-PRODUCTION-PROFILE-REGISTRY-001"
PRESENTON_PROVIDER_ID = "FA3-PROVIDER-PRESENTON-001"
SUPERSEDING_DECISION_ID = "FA3-DEC-PRESENTON-SUPERSEDED-2026-09-27"
NATIVE_DECISION_ID = "FA3-DEC-STORY-PRESENTATION-NATIVE-2026-09-27"

REQUIRED_PRODUCTION_PROFILES = {
    "FEATURE_FILM",
    "TV_MOVIE",
    "EPISODIC_TV_SERIES",
    "COMMERCIAL_ADVERTISING",
    "LIVE_BROADCAST",
    "DUBBING_LOCALIZATION",
    "FUTURE_CUSTOM",
}
REQUIRED_FORMAT_FAMILIES = {
    "FINAL_DRAFT",
    "FOUNTAIN",
    "MICROSOFT_OFFICE",
    "LIBREOFFICE",
    "APACHE_OPENOFFICE",
    "WPS_OFFICE",
    "ONLYOFFICE",
}
REQUIRED_AUTHORING_FEATURES = {
    "WRITER_GOALS",
    "WRITING_STATISTICS",
    "SPRINT_TIMER",
    "MIDNIGHT_MODE",
    "TYPEWRITER_FOCUS_MODE",
    "ALTERNATIVE_CONTINUATIONS_NARRATIVE_BRANCHING",
}
REQUIRED_CAPABILITIES = {"CAP-018", "CAP-033", "CAP-170", "CAP-171"}
REQUIRED_PRODUCTION_CHAIN = [
    "screenplay",
    "scene",
    "script_passage",
    "shot",
    "camera_setup",
    "blocking",
    "lighting",
    "schedule",
    "production_editorial_handoff",
]
FORBIDDEN_ACTIVE_PRESENTON_PATHS = [
    "canonical/presenton-enforcement.json",
    "src/fa3_presenton_gate.py",
    "tests/test_presenton_gate.py",
    "evidence/collect-presenton-current-host.py",
    "bin/fa3-presenton-current-host.sh",
    ".github/workflows/fa3-presenton.yml",
    ".github/workflows/fa3-presenton-current-host.yml",
    "deployment/presenton/README.md",
    "deployment/presenton/ai-creative.target",
    "deployment/presenton/postgresql-bootstrap.sql",
    "deployment/presenton/presenton.caddy",
    "deployment/presenton/fa3-presenton.container",
    "deployment/presenton/presenton.container",
]


def _load(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {rel}")
    return value


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def interchange_contract_valid(contract: dict[str, Any]) -> bool:
    rows = contract.get("contracts", {}).get("CanonicalDocumentInterchange", {}).get("admitted_file_types", [])
    if not rows:
        return False
    families = {str(row.get("family")) for row in rows if isinstance(row, dict)}
    if not REQUIRED_FORMAT_FAMILIES.issubset(families):
        return False
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            return False
        key = (str(row.get("family")), str(row.get("file_type")))
        if key in seen:
            continue
        seen.add(key)
        if row.get("import") is not True or row.get("export") is not True:
            return False
    cfg = contract.get("contracts", {}).get("CanonicalDocumentInterchange", {})
    return bool(
        cfg.get("one_way_codec_admission") is False
        and cfg.get("round_trip_required") is True
        and cfg.get("structural_meaning_preservation_required") is True
        and cfg.get("provenance_required") is True
        and cfg.get("lineage_required") is True
        and cfg.get("versioning_required") is True
        and cfg.get("explicit_loss_reporting_required") is True
        and cfg.get("silent_data_loss") is False
    )


def presenton_superseded(provider: dict[str, Any]) -> bool:
    classes = set(provider.get("classification", []))
    return bool(
        provider.get("id") == PRESENTON_PROVIDER_ID
        and provider.get("status") == "SUPERSEDED"
        and provider.get("active_runtime_provider") is False
        and provider.get("runtime_admitted") is False
        and provider.get("architectural_authority") is False
        and provider.get("canonical_authority") is False
        and provider.get("activation_mode") == "NOT_ADMITTED"
        and {"REFERENCE_ONLY", "SELECTIVE_CODE_DONOR"}.issubset(classes)
        and provider.get("required_for_story") is False
        and provider.get("required_for_presentation") is False
        and provider.get("current_host_runtime_promotion_claim") is False
        and provider.get("evidence_transfer", {}).get("historical_presenton_current_host_to_fa3_native") is False
    )


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    capability_count = load_active_release_baseline(root).capability_count
    findings: list[dict[str, Any]] = []
    required = [
        "canonical/profiles/FA3-STORY-PRESENTATION-FABRIC-001.json",
        "canonical/contracts/FA3-STORY-PRESENTATION-CONTRACTS-001.json",
        "canonical/FA3-STORY-PRODUCTION-PROFILE-REGISTRY-001.json",
        "canonical/story-presentation-enforcement.json",
        "canonical/decisions/FA3-DEC-STORY-PRESENTATION-NATIVE-2026-09-27.json",
        "canonical/decisions/FA3-DEC-PRESENTON-SUPERSEDED-2026-09-27.json",
        "canonical/providers/FA3-PROVIDER-PRESENTON-001.json",
        "canonical/decisions/FA3-DEC-PRESENTON-2026-08-30.json",
        "canonical/references/FA3-PRESENTON-UPSTREAM-REFERENCE-2026-08-30.json",
        "evidence/reference/presenton-provider-ci-2026-08-30.json",
        "canonical/intents/FA3-STORY-PRESENTATION-FABRIC-APPLICATION-INTENT-001.json",
        "canonical/assessments/FA3-STORY-PRESENTATION-FABRIC-REUSE-ASSESSMENT-001.json",
        "canonical/assessments/FA3-STORY-PRESENTATION-DECISION-ASSESSMENT-2026-09-27.json",
        "canonical/enforcement-policy.json",
        "canonical/conformance-matrix.csv",
        "evidence/evidence-registry.json",
    ]
    for rel in required:
        if not (root / rel).is_file():
            findings.append(_finding("STORY-PRES-001", "required canonical materialization missing", path=rel))
    if findings:
        return {"schema": "fa3.story-presentation-gate-report.v1", "gate_id": GATE_ID, "result": "FAIL", "findings": findings}

    profile = _load(root, required[0])
    contract = _load(root, required[1])
    production = _load(root, required[2])
    enforcement = _load(root, required[3])
    native_decision = _load(root, required[4])
    superseding_decision = _load(root, required[5])
    provider = _load(root, required[6])
    historical_decision = _load(root, required[7])
    historical_reference = _load(root, required[8])
    historical_evidence = _load(root, required[9])
    intent = _load(root, required[10])
    reuse = _load(root, required[11])
    decision_assessment = _load(root, required[12])
    policy = _load(root, required[13])
    evidence_registry = _load(root, required[15])

    if capability_count != 175:
        findings.append(_finding("STORY-PRES-002", "canonical capability baseline is not 175", actual=capability_count))

    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("status") == "CANONICAL"
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == capability_count
        and set(profile.get("capability_projection", [])) == REQUIRED_CAPABILITIES
        and profile.get("canonical_components", {}).get("story_studio") == "ONE_FA3_STORY_STUDIO"
        and profile.get("canonical_components", {}).get("story_ir") == "ONE_CANONICAL_STORY_SCREENPLAY_IR"
    ):
        findings.append(_finding("STORY-PRES-003", "Story/Presentation canonical profile or capability mapping drift"))

    projection = profile.get("story_presentation_projection", {})
    if not (
        projection.get("story_to_presentation") == "CANONICAL_PROJECTION_WITH_LINEAGE_AND_PROVENANCE"
        and projection.get("presentation_to_story") == "CHANGE_PROPOSAL_REVIEW_COMPARE_EXPLICIT_HUMAN_APPLY"
        and projection.get("silent_writeback") is False
        and projection.get("external_worker_may_mutate_story") is False
    ):
        findings.append(_finding("STORY-PRES-004", "bidirectional Story/Presentation projection boundary drift"))

    if not REQUIRED_AUTHORING_FEATURES.issubset(set(profile.get("story_authoring_features", []))):
        findings.append(_finding("STORY-PRES-005", "mandatory Story Studio authoring features missing"))

    branching = profile.get("narrative_branching", {})
    if not (
        branching.get("any_story_point_may_branch") is True
        and branching.get("common_canonical_story_graph") is True
        and branching.get("independently_editable") is True
        and branching.get("independently_versioned") is True
        and branching.get("lineage_preserved") is True
    ):
        findings.append(_finding("STORY-PRES-006", "alternative continuation lineage semantics drift"))

    if profile.get("production_graph_handoff") != REQUIRED_PRODUCTION_CHAIN or profile.get("presentation_relation_to_production_graph") != "SEPARATE_DERIVED_ARTIFACT_NOT_REPLACEMENT":
        findings.append(_finding("STORY-PRES-007", "production graph handoff or Presentation separation drift"))

    if not interchange_contract_valid(contract):
        findings.append(_finding("STORY-PRES-008", "document interchange is not bidirectional/loss-explicit for every admitted file type"))

    if production.get("id") != PRODUCTION_REGISTRY_ID:
        findings.append(_finding("STORY-PRES-009", "production profile registry identity drift"))
    prod_rows = {row.get("id"): row for row in production.get("profiles", []) if isinstance(row, dict)}
    if not REQUIRED_PRODUCTION_PROFILES.issubset(set(prod_rows)):
        findings.append(_finding("STORY-PRES-010", "required production profiles missing", missing=sorted(REQUIRED_PRODUCTION_PROFILES - set(prod_rows))))
    dubbing = prod_rows.get("DUBBING_LOCALIZATION", {})
    if not (dubbing.get("first_class") is True and dubbing.get("video_bound") is True and dubbing.get("timecode_bound") is True):
        findings.append(_finding("STORY-PRES-011", "DUBBING_LOCALIZATION is not first-class video/timecode-bound"))

    hw = profile.get("hardware_audit", {})
    if not (
        hw.get("vendor_neutral") is True
        and hw.get("cpu_only_viable") is True
        and hw.get("accelerator_cardinality") == "0..N"
        and hw.get("global_accelerator_requirement") is False
        and hw.get("live_discovery_authority") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
    ):
        findings.append(_finding("STORY-PRES-012", "mandatory Hardware Audit boundary drift"))

    if not presenton_superseded(provider):
        findings.append(_finding("STORY-PRES-013", "Presenton remains or can become an active runtime/provider dependency"))

    if any((root / rel).exists() for rel in FORBIDDEN_ACTIVE_PRESENTON_PATHS):
        findings.append(_finding("STORY-PRES-014", "active Presenton runtime/deployment/current-host surface remains", paths=[rel for rel in FORBIDDEN_ACTIVE_PRESENTON_PATHS if (root / rel).exists()]))

    if not (
        superseding_decision.get("id") == SUPERSEDING_DECISION_ID
        and superseding_decision.get("runtime_admitted") is False
        and superseding_decision.get("current_host_evidence_transfer_to_native_layer") is False
        and superseding_decision.get("new_capabilities") == 0
        and superseding_decision.get("new_architectural_authorities") == 0
        and native_decision.get("id") == NATIVE_DECISION_ID
        and native_decision.get("new_capabilities") == 0
        and native_decision.get("new_architectural_authorities") == 0
        and native_decision.get("current_host_status") == "PENDING_CURRENT_HOST"
    ):
        findings.append(_finding("STORY-PRES-015", "supersedence/native decision truth boundary drift"))

    if not (
        historical_decision.get("id") == "FA3-DEC-PRESENTON-2026-08-30"
        and historical_decision.get("provider_id") == PRESENTON_PROVIDER_ID
        and historical_reference.get("id") == "FA3-PRESENTON-UPSTREAM-REFERENCE-2026-08-30"
        and historical_evidence.get("provider_id") == PRESENTON_PROVIDER_ID
        and historical_evidence.get("status") == "PASS"
        and historical_evidence.get("evidence_scope") == "LOCAL_EXECUTABLE_CONFORMANCE_NOT_CURRENT_HOST_PRODUCTION"
        and historical_evidence.get("current_host_production_e2e", {}).get("status") == "PENDING_REAL_CURRENT_HOST_EXECUTION"
    ):
        findings.append(_finding("STORY-PRES-016", "historical Presenton decision/reference evidence was lost or reclassified"))

    policy_gates = set(policy.get("mandatory_reference_gates", []))
    if GATE_ID not in policy_gates or "FA3-PRESENTON-GATESET-001" in policy_gates:
        findings.append(_finding("STORY-PRES-017", "global enforcement still binds active Presenton gate or misses native gate"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("mandatory_rule_count") == len(enforcement.get("p0_invariants", []))
        and policy.get("story_presentation_mandatory_p0_rules") == enforcement.get("p0_invariants")
    ):
        findings.append(_finding("STORY-PRES-018", "Story/Presentation enforcement inventory drift"))

    if not (
        decision_assessment.get("schema") == "fa3.decision-fabric-assessment.v1"
        and decision_assessment.get("project_id") == PROFILE_ID
        and decision_assessment.get("project_radar_checked") is True
        and decision_assessment.get("capability_delta") == 0
        and decision_assessment.get("authority_delta") == 0
    ):
        findings.append(_finding("STORY-PRES-019", "Decision Fabric assessment boundary drift"))

    if not (
        intent.get("proposed_authority_roles") == []
        and intent.get("declared_new_capabilities") == []
        and reuse.get("result") == "PASS"
        and reuse.get("new_capabilities") == 0
        and reuse.get("new_architectural_authorities") == 0
        and reuse.get("current_host_runtime_promotion_claim") is False
        and PROFILE_ID in reuse.get("covered_ids", [])
        and PRESENTON_PROVIDER_ID in reuse.get("covered_ids", [])
    ):
        findings.append(_finding("STORY-PRES-020", "Reuse Discovery / authority boundary drift"))

    matrix_rows: dict[str, list[str]] = {}
    with (root / "canonical/conformance-matrix.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh):
            if len(row) > 2 and row[1] in REQUIRED_CAPABILITIES:
                matrix_rows[row[1]] = row
    if set(matrix_rows) != REQUIRED_CAPABILITIES:
        findings.append(_finding("STORY-PRES-021", "canonical capability rows missing"))
    else:
        if "Presenton self-hosted adapter" in ",".join(matrix_rows["CAP-033"]) or "FA3 Presentation Layer / Presentation Studio" not in ",".join(matrix_rows["CAP-033"]):
            findings.append(_finding("STORY-PRES-022", "CAP-033 still maps to Presenton rather than native Presentation Studio"))
        if "FA3 Canonical Document/Interchange Fabric" not in ",".join(matrix_rows["CAP-018"]):
            findings.append(_finding("STORY-PRES-023", "CAP-018 does not map to canonical Document/Interchange Fabric"))

    registry_rows = {row.get("subject_id"): row for row in evidence_registry.get("records", []) if isinstance(row, dict)}
    for cap in sorted(REQUIRED_CAPABILITIES):
        row = registry_rows.get(cap, {})
        if (
            row.get("status") != "PENDING_CURRENT_HOST"
            or row.get("promotion_state") != "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
            or row.get("story_presentation_projection_status", {}).get("current_host_runtime_promotion_claim") is not False
            or row.get("story_presentation_projection_status", {}).get("presenton_historical_evidence_reused_as_native_runtime_proof") is not False
        ):
            findings.append(_finding("STORY-PRES-024", "current-host truth boundary drift", capability=cap))

    return {
        "schema": "fa3.story-presentation-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "capability_count": capability_count,
        "capability_delta": 0,
        "authority_delta": 0,
        "presenton_status": provider.get("status"),
        "presenton_runtime_admitted": provider.get("runtime_admitted"),
        "current_host_status": "PENDING_CURRENT_HOST",
        "runtime_promotion_claim": False,
        "historical_presenton_evidence_promotes_native_runtime": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--report", default="reports/story-presentation-gate-report.json")
    ns = ap.parse_args()
    root = Path(ns.root).resolve()
    report = gate(root)
    out = root / ns.report
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
