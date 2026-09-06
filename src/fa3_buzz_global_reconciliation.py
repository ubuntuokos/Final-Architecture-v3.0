#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-BUZZ-001"
DECISION_ID = "FA3-DEC-BUZZ-2026-08-30"
GATE_ID = "FA3-BUZZ-GATESET-001"
PROFILE_ID = "FA3-DESKTOP-AGENT-WORKBENCH-001"
CAPABILITY_ID = "CAP-008"
CAPABILITY_COUNT = 143
REFERENCE_EVIDENCE_PATH = "evidence/reference/buzz-ci-2026-08-30.json"
GLOBAL_EVIDENCE_PATH = "evidence/reference/buzz-global-reconciliation-ci-2026-09-06.json"
GLOBAL_EVIDENCE_ID = "FA3-EVID-BUZZ-GLOBAL-RECONCILIATION-CI-2026-09-06"
RELEASE_PROJECTION_PATH = "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
REGISTRY_PATH = "evidence/evidence-registry.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def expected_capability_projection() -> dict[str, Any]:
    return {
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "gate_id": GATE_ID,
        "reference_gate_status": "PASS",
        "runtime_activation_status": "OPTIONAL_DISABLED_BY_DEFAULT_REFERENCE_ONLY",
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "provider_runtime_required_for_global_promotion_when_disabled": False,
        "global_reconciliation_evidence_id": GLOBAL_EVIDENCE_ID,
    }


def expected_release_binding() -> dict[str, Any]:
    return {
        "subject_id": CAPABILITY_ID,
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "decision_id": DECISION_ID,
        "reference_evidence": [REFERENCE_EVIDENCE_PATH, GLOBAL_EVIDENCE_PATH],
        "runtime_status": "PENDING_CURRENT_HOST",
        "provider_runtime_status": "OPTIONAL_DISABLED_BY_DEFAULT_REFERENCE_ONLY",
        "current_host_runtime_evidence": "NOT_CLAIMED",
    }


def expected_reconciliation_record() -> dict[str, Any]:
    return {
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "gate_id": GATE_ID,
        "capability_id": CAPABILITY_ID,
        "classification": "OPTIONAL_HUMAN_AGENT_COLLABORATIVE_WORKSPACE_REFERENCE_PROVIDER",
        "reconciliation_status": "GLOBAL_RELEASE_INVENTORY_EVIDENCE_RECONCILED_REFERENCE_RUNTIME_NOT_PROMOTED",
        "provider_inventory_reconciled": True,
        "evidence_registry_reconciled": True,
        "unified_projections_regenerated": True,
        "deterministic_regeneration_pass": True,
        "runtime_activation_status": "OPTIONAL_DISABLED_BY_DEFAULT_REFERENCE_ONLY",
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "provider_runtime_required_for_global_promotion_when_disabled": False,
        "reference_gate_status": "PASS",
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": CAPABILITY_COUNT,
    }


def reconciliation_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "registry": root / REGISTRY_PATH,
        "release": root / RELEASE_PROJECTION_PATH,
        "reference_evidence": root / REFERENCE_EVIDENCE_PATH,
        "global_evidence": root / GLOBAL_EVIDENCE_PATH,
    }
    for name, path in paths.items():
        if not path.exists():
            findings.append(_finding("BUZZ-REC-001", f"Missing Buzz reconciliation artifact: {name}", file=str(path.relative_to(root))))
    if findings:
        return {"result": "FAIL", "findings": findings}

    registry = _load(paths["registry"])
    release = _load(paths["release"])
    reference_evidence = _load(paths["reference_evidence"])
    global_evidence = _load(paths["global_evidence"])

    if not (
        registry.get("canonical_capability_count") == CAPABILITY_COUNT
        and registry.get("record_count") == CAPABILITY_COUNT
    ):
        findings.append(_finding("BUZZ-REC-002", "Evidence Registry capability-count invariant drift"))

    cap = next((item for item in registry.get("records", []) if item.get("subject_id") == CAPABILITY_ID), None)
    required_evidence = {REFERENCE_EVIDENCE_PATH, GLOBAL_EVIDENCE_PATH}
    if not cap:
        findings.append(_finding("BUZZ-REC-003", "CAP-008 Agent Workspace record missing from Evidence Registry"))
    else:
        projection = cap.get("buzz_provider_projection_status", {})
        if not (
            DECISION_ID in cap.get("source_decision_ids", [])
            and required_evidence <= set(cap.get("evidence_artifacts", []))
            and cap.get("runtime_conformance") == "EVIDENCE-PENDING"
            and cap.get("status") == "PENDING_CURRENT_HOST"
            and cap.get("promotion_state") == "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
            and projection == expected_capability_projection()
        ):
            findings.append(_finding("BUZZ-REC-004", "CAP-008 Buzz Evidence Registry reconciliation drift"))

    if not (
        reference_evidence.get("provider_id") == PROVIDER_ID
        and reference_evidence.get("gate_id") == GATE_ID
        and reference_evidence.get("status") == "PASS"
        and reference_evidence.get("runtime_provider_required") is False
        and reference_evidence.get("new_capabilities") == 0
        and reference_evidence.get("new_architectural_authorities") == 0
        and reference_evidence.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(_finding("BUZZ-REC-005", "Base Buzz executable PASS evidence drift"))

    recon = global_evidence.get("reconciliation", {})
    if not (
        global_evidence.get("id") == GLOBAL_EVIDENCE_ID
        and global_evidence.get("provider_id") == PROVIDER_ID
        and global_evidence.get("profile_id") == PROFILE_ID
        and global_evidence.get("capability_id") == CAPABILITY_ID
        and global_evidence.get("gate_id") == GATE_ID
        and global_evidence.get("status") == "PASS"
        and global_evidence.get("evidence_scope") == "CI_CANONICAL_RECONCILIATION_NOT_CURRENT_HOST"
        and global_evidence.get("conclusion") == "GLOBAL_RELEASE_INVENTORY_EVIDENCE_RECONCILIATION_PASS"
        and global_evidence.get("runtime_provider_required") is False
        and global_evidence.get("current_host_runtime_evidence_required") is False
        and global_evidence.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and global_evidence.get("new_capabilities") == 0
        and global_evidence.get("new_architectural_authorities") == 0
        and global_evidence.get("capability_count_after") == CAPABILITY_COUNT
        and recon.get("provider_inventory_reconciled") is True
        and recon.get("evidence_registry_reconciled") is True
        and recon.get("unified_projections_regenerated") is True
        and recon.get("deterministic_regeneration_pass") is True
    ):
        findings.append(_finding("BUZZ-REC-006", "Buzz global reconciliation PASS evidence drift"))

    inventory = release.get("overlay_inventory", {})
    release_evidence = set(inventory.get("reference_evidence_records", []))
    if not (
        "canonical/providers/FA3-PROVIDER-BUZZ-001.json" in inventory.get("provider_records", [])
        and "canonical/decisions/FA3-DEC-BUZZ-2026-08-30.json" in inventory.get("decision_records", [])
        and required_evidence <= release_evidence
        and GATE_ID in release.get("mandatory_reference_gates", [])
    ):
        findings.append(_finding("BUZZ-REC-007", "Buzz release provider/evidence inventory drift"))

    binding = release.get("evidence_registry", {}).get("buzz_capability_binding", {})
    if binding != expected_release_binding():
        findings.append(_finding("BUZZ-REC-008", "Buzz unified release Evidence Registry binding drift"))

    release_reconciliation = release.get("buzz_reconciliation", {})
    expected_recon = expected_reconciliation_record()
    if any(release_reconciliation.get(key) != value for key, value in expected_recon.items()):
        findings.append(_finding("BUZZ-REC-009", "Buzz top-level unified reconciliation projection drift"))

    manifest = release.get("manifest", [])
    manifest_paths = [item.get("path") for item in manifest]
    required_paths = {
        "canonical/providers/FA3-PROVIDER-BUZZ-001.json",
        "canonical/decisions/FA3-DEC-BUZZ-2026-08-30.json",
        "canonical/buzz-enforcement.json",
        "src/fa3_buzz_gate.py",
        "src/fa3_buzz_global_reconciliation.py",
        "tests/test_buzz_gate.py",
        "tests/test_buzz_global_reconciliation.py",
        "tools/fa3_buzz_global_reconcile.py",
        REFERENCE_EVIDENCE_PATH,
        GLOBAL_EVIDENCE_PATH,
        REGISTRY_PATH,
    }
    if release.get("manifest_entry_count") != len(manifest) or len(manifest_paths) != len(set(manifest_paths)):
        findings.append(_finding("BUZZ-REC-010", "Release manifest count/uniqueness drift"))
    if not required_paths <= set(manifest_paths):
        findings.append(_finding("BUZZ-REC-011", "Buzz materialization missing from unified release manifest", missing=sorted(required_paths - set(manifest_paths))))

    if release_reconciliation.get("current_host_runtime_evidence") != "NOT_CLAIMED" or release_reconciliation.get("provider_runtime_required_for_global_promotion_when_disabled") is not False:
        findings.append(_finding("BUZZ-REC-012", "Buzz reconciliation incorrectly escalated to current-host/runtime dependency"))

    return {
        "result": "PASS" if not findings else "FAIL",
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "capability_id": CAPABILITY_ID,
        "global_evidence_id": GLOBAL_EVIDENCE_ID,
        "findings": findings,
    }
