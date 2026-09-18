#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count
from fa3_voice_capability_current_host import (
    CONFORMANCE_ID,
    GATE_ID,
    SUBJECTS,
    expected_source_decisions,
    sha256_file,
)

CAPABILITY_COUNT = module_active_capability_count(__file__)
PRODUCER = "src/fa3_voice_capability_current_host.py"
QUALIFIER = "src/fa3_current_host_capability_test_qualifier.py"

PATHS = {
    "conformance": "canonical/FA3-VOICE-CAPABILITY-CURRENT-HOST-CONFORMANCE-001.json",
    "gate": "canonical/FA3-GATE-VOICE-CAPABILITY-CURRENT-HOST-001.json",
    "enforcement": "canonical/voice-capability-current-host-enforcement.json",
    "decision": "canonical/decisions/FA3-DEC-VOICE-CAPABILITY-CURRENT-HOST-2026-09-19.json",
    "voice_profile": "canonical/profiles/FA3-VOICE-001.json",
    "policy": "canonical/enforcement-policy.json",
    "manifest": "fa3-current-host/manifest.json",
    "qualifications": "canonical/current-host-capability-test-qualifications.json",
    "producers": "canonical/current-host-capability-qualification-constituent-producers.json",
    "executors": "canonical/current-host-capability-test-executors.json",
    "producer_code": PRODUCER,
    "tests": "tests/test_voice_capability_current_host.py",
    "workflow": ".github/workflows/fa3-global-current-host-closure.yml",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def qualification_ids(subject_id: str) -> list[str]:
    return [
        f"FA3-QUAL-{subject_id}-POS-001",
        f"FA3-QUAL-{subject_id}-NEG-001",
        f"FA3-QUAL-{subject_id}-ROLLBACK-001",
    ]


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    data: dict[str, Any] = {}
    for key, rel in PATHS.items():
        path = root / rel
        if not path.is_file():
            findings.append(finding("VOICE-HOST-001", "required voice current-host materialization missing", path=rel))
            continue
        if path.suffix == ".json":
            try:
                data[key] = loadj(path)
            except Exception as exc:
                findings.append(finding("VOICE-HOST-002", "voice current-host JSON unreadable", path=rel, error=repr(exc)))
        else:
            data[key] = path.read_text(encoding="utf-8")
    if findings:
        return _report(root, findings)

    conformance = data["conformance"]
    if not (
        conformance.get("id") == CONFORMANCE_ID
        and conformance.get("status") == "REGISTERED_REAL_CURRENT_HOST_EXECUTION_PENDING"
        and conformance.get("capability_count") == CAPABILITY_COUNT
        and conformance.get("new_capabilities") == 0
        and conformance.get("new_architectural_authorities") == 0
        and conformance.get("architectural_authority") is False
        and conformance.get("global_promotion_claim") is False
        and list(conformance.get("capability_contracts", {})) == list(SUBJECTS)
    ):
        findings.append(finding("VOICE-HOST-003", "voice current-host conformance invariant drift"))

    bindings = conformance.get("provider_collector_bindings", {})
    if not (
        bindings.get("FA3-PROVIDER-COSYVOICE-001", {}).get("status") == "MATERIALIZED"
        and bindings.get("FA3-PROVIDER-COSYVOICE-001", {}).get("hu_HU_production_status")
        == "DENIED_EXPERIMENTAL_FOR_CAPABILITY_PASS"
        and bindings.get("FA3-PROVIDER-XTTS-001", {}).get("status") == "REQUIRED_NOT_YET_MATERIALIZED"
        and bindings.get("FA3-PROVIDER-PIPER-001", {}).get("status") == "REQUIRED_NOT_YET_MATERIALIZED"
    ):
        findings.append(finding("VOICE-HOST-004", "voice provider physical-evidence blocker semantics drift"))

    gate_record = data["gate"]
    if not (
        gate_record.get("gateset_id") == GATE_ID
        and gate_record.get("conformance_id") == CONFORMANCE_ID
        and gate_record.get("fail_closed") is True
        and gate_record.get("capability_bindings") == list(SUBJECTS)
        and gate_record.get("registered_obligation_delta") == 9
        and gate_record.get("registered_executor_count_after") == 27
        and gate_record.get("pending_executor_count_after") == 402
        and gate_record.get("global_promotion_claim") is False
    ):
        findings.append(finding("VOICE-HOST-005", "voice current-host gate record drift"))

    rules = data["enforcement"].get("rules", {})
    if not (
        data["enforcement"].get("gate_id") == GATE_ID
        and data["enforcement"].get("fail_closed") is True
        and rules.get("exact_evidence_registry_source_decision_coverage") == "REQUIRED"
        and rules.get("raw_provider_receipt_as_capability_pass") == "DENY"
        and rules.get("hosted_ci_current_host_substitution") == "DENY"
        and rules.get("hu_quality_profile") == "FA3-HU-AQC-001"
        and rules.get("hu_quality_pass") == "REQUIRED"
        and rules.get("cap116_real_time_factor_max") == 1.0
        and rules.get("global_promotion_effect") == "NONE"
    ):
        findings.append(finding("VOICE-HOST-006", "voice current-host enforcement drift"))

    decision = data["decision"]
    if not (
        decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("capability_bindings") == list(SUBJECTS)
        and decision.get("registered_obligation_delta") == 9
        and decision.get("registered_executor_count_before") == 18
        and decision.get("registered_executor_count_after") == 27
        and decision.get("pending_executor_count_after") == 402
        and decision.get("current_host_runtime_pass_claim") is False
        and decision.get("global_promotion_claim") is False
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(finding("VOICE-HOST-007", "voice current-host decision invariant drift"))

    profile_binding = data["voice_profile"].get("current_host_capability_qualification", {})
    expected_map = {subject: qualification_ids(subject) for subject in SUBJECTS}
    if not (
        profile_binding.get("conformance_id") == CONFORMANCE_ID
        and profile_binding.get("gate_id") == GATE_ID
        and profile_binding.get("subjects") == expected_map
        and profile_binding.get("producer_adapter") == PRODUCER
        and profile_binding.get("status") == "REGISTERED_REAL_CURRENT_HOST_EXECUTION_PENDING"
        and profile_binding.get("hosted_ci_substitution_allowed") is False
        and profile_binding.get("global_promotion_claim") is False
    ):
        findings.append(finding("VOICE-HOST-008", "FA3-VOICE-001 current-host qualification binding drift"))

    policy = data["policy"]
    if not (
        policy.get("voice_capability_current_host_conformance_id") == CONFORMANCE_ID
        and policy.get("voice_capability_current_host_gate_id") == GATE_ID
        and policy.get("voice_capability_current_host_subjects") == list(SUBJECTS)
        and policy.get("voice_capability_current_host_registered_executor_count") == 27
        and policy.get("voice_capability_current_host_pending_executor_count") == 402
        and policy.get("voice_capability_current_host_status") == "REGISTERED_REAL_CURRENT_HOST_EXECUTION_PENDING"
        and policy.get("voice_capability_current_host_global_promotion_claim") is False
    ):
        findings.append(finding("VOICE-HOST-009", "global policy voice current-host binding drift"))

    manifest = data["manifest"]
    surfaces = {row.get("name"): row for row in manifest.get("registered_current_host_surfaces", [])}
    surface = surfaces.get("voice-capabilities-115-116-117", {})
    if not (
        surface.get("gate") == "voice-capability-current-host"
        and surface.get("capability_ids") == list(SUBJECTS)
        and surface.get("registered_obligation_count") == 9
        and surface.get("collection_status") == "CAPABILITY_EXECUTORS_REGISTERED_REAL_EXECUTION_PENDING"
        and surface.get("global_promotion_claim") is False
    ):
        findings.append(finding("VOICE-HOST-010", "current-host manifest voice capability surface drift"))

    producer_sha = sha256_file(root / PRODUCER)
    qualifier_sha = sha256_file(root / QUALIFIER)
    qualifications = data["qualifications"].get("entries", [])
    producers = data["producers"].get("entries", [])
    executors = data["executors"].get("entries", [])

    for subject_id in SUBJECTS:
        expected_sources = expected_source_decisions(root, subject_id)
        qrows = [row for row in qualifications if row.get("subject_id") == subject_id]
        prows = [row for row in producers if row.get("subject_id") == subject_id]
        erows = [row for row in executors if row.get("subject_id") == subject_id]
        if len(qrows) != 3 or {row.get("test_kind") for row in qrows} != {"positive", "negative", "rollback"}:
            findings.append(finding("VOICE-HOST-011", "voice qualification definition coverage incomplete", subject_id=subject_id))
        if len(prows) != 3 or {row.get("test_kind") for row in prows} != {"positive", "negative", "rollback"}:
            findings.append(finding("VOICE-HOST-012", "voice constituent producer coverage incomplete", subject_id=subject_id))
        if len(erows) != 3 or {row.get("test_kind") for row in erows} != {"positive", "negative", "rollback"}:
            findings.append(finding("VOICE-HOST-013", "voice executor coverage incomplete", subject_id=subject_id))
        for row in qrows:
            basis = row.get("completeness_basis", {})
            constituents = row.get("required_constituents", [])
            if (
                row.get("coverage_semantics") != "COMPLETE_CAPABILITY_OBLIGATION"
                or basis.get("source_decision_ids") != expected_sources
                or len(constituents) != 1
                or constituents[0].get("covers_source_decision_ids") != expected_sources
                or row.get("provider_receipt_only") is not False
                or row.get("component_receipt_only") is not False
                or row.get("global_promotion_claim") is not False
            ):
                findings.append(finding("VOICE-HOST-014", "voice qualification exact coverage/authority drift", subject_id=subject_id))
        for row in prows:
            if (
                row.get("adapter_path") != PRODUCER
                or row.get("adapter_sha256") != producer_sha
                or row.get("covers_source_decision_ids") != expected_sources
                or row.get("execution_mode") != "REAL_CURRENT_HOST_EXECUTION"
                or row.get("synthetic") is not False
                or row.get("provider_receipt_only") is not False
                or row.get("component_receipt_only") is not False
                or row.get("global_promotion_claim") is not False
            ):
                findings.append(finding("VOICE-HOST-015", "voice producer identity/coverage drift", subject_id=subject_id))
        for row in erows:
            if (
                row.get("adapter_path") != QUALIFIER
                or row.get("adapter_sha256") != qualifier_sha
                or row.get("execution_mode") != "REAL_CURRENT_HOST_EXECUTION"
                or row.get("synthetic") is not False
                or row.get("provider_receipt_only") is not False
                or row.get("component_receipt_only") is not False
                or row.get("global_promotion_claim") is not False
            ):
                findings.append(finding("VOICE-HOST-016", "voice executor canonical qualifier drift", subject_id=subject_id))

    if len(executors) != 27 or len(producers) != 27 or len(qualifications) != 27:
        findings.append(
            finding(
                "VOICE-HOST-017",
                "explicit current-host registry cardinality is not 27 after voice batch",
                qualifications=len(qualifications),
                producers=len(producers),
                executors=len(executors),
            )
        )

    required_paths = set(manifest.get("required_repository_paths", []))
    mandatory = {
        PATHS["conformance"],
        PATHS["gate"],
        PATHS["enforcement"],
        PATHS["decision"],
        PRODUCER,
        PATHS["tests"],
        PATHS["workflow"],
    }
    if not mandatory.issubset(required_paths):
        findings.append(
            finding(
                "VOICE-HOST-018",
                "voice current-host paths are not bound into current-host manifest",
                missing=sorted(mandatory - required_paths),
            )
        )

    return _report(root, findings)


def _report(root: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    report = {
        "schema": "fa3.voice-capability-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "conformance_id": CONFORMANCE_ID,
        "capability_ids": list(SUBJECTS),
        "capability_count": CAPABILITY_COUNT,
        "registered_obligation_delta": 9,
        "registered_executor_count": 27,
        "pending_executor_count": 402,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "current_host_runtime_pass_claim": False,
        "global_promotion_claim": False,
        "production_promotion_gate_bypassed": False,
    }
    out = root / "reports/voice-capability-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 voice capability current-host materialization gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
