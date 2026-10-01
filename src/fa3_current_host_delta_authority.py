#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from fa3_evidence_validation import git_head

TEST_KINDS = ("positive", "negative", "rollback")
REQUEST_SCHEMA = "fa3.current-host-change-request.v1"
RECEIPT_SCHEMA = "fa3.current-host-delta-receipt.v1"
BASE_SCHEMA = "fa3.current-host-base-state.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _cap_sort_key(capability_id: str) -> tuple[int, str]:
    try:
        return (int(capability_id.split("-", 1)[1]), capability_id)
    except Exception:
        return (10**9, capability_id)


def canonical_capabilities(root: Path) -> list[str]:
    registry = load_json(root / "evidence/evidence-registry.json")
    ids = [
        row.get("subject_id")
        for row in registry.get("records", [])
        if isinstance(row, dict)
        and isinstance(row.get("subject_id"), str)
        and row["subject_id"].startswith("CAP-")
    ]
    expected = registry.get("canonical_capability_count")
    if not isinstance(expected, int) or expected <= 0:
        raise ValueError("evidence registry canonical_capability_count missing")
    if len(ids) != expected or len(set(ids)) != expected:
        raise ValueError("evidence registry capability set/cardinality mismatch")
    return sorted(ids, key=_cap_sort_key)


def _list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def canonical_binding_index(root: Path) -> dict[str, list[str]]:
    bindings: dict[str, set[str]] = {}
    for path in (root / "canonical").rglob("*.json"):
        try:
            row = load_json(path)
        except Exception:
            continue
        record_id = row.get("id")
        values = row.get("capability_bindings")
        if (
            isinstance(record_id, str)
            and isinstance(values, list)
            and all(isinstance(value, str) and value.startswith("CAP-") for value in values)
        ):
            bindings.setdefault(record_id, set()).update(values)
    return {key: sorted(values, key=_cap_sort_key) for key, values in bindings.items()}


def shared_component_scope(
    root: Path,
    component_ids: list[str],
) -> tuple[set[str], set[str], list[dict[str, Any]], list[str]]:
    if not component_ids:
        return set(), set(), [], []
    findings: list[str] = []
    declaration_path = root / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
    if not declaration_path.is_file():
        return set(), set(), [], ["application/shared capability declaration is missing"]
    declaration = load_json(declaration_path)
    rows = declaration.get("shared_capabilities")
    if not isinstance(rows, list):
        return set(), set(), [], ["shared_capabilities declaration must be a list"]

    by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            continue
        sid = row["id"]
        if sid in by_id:
            duplicate_ids.add(sid)
        by_id[sid] = row
    if duplicate_ids:
        findings.append(f"duplicate shared capability IDs: {sorted(duplicate_ids)}")

    bindings = canonical_binding_index(root)
    capabilities: set[str] = set()
    applications: set[str] = set()
    projection: list[dict[str, Any]] = []
    for sid in component_ids:
        row = by_id.get(sid)
        if row is None:
            findings.append(f"unknown shared capability: {sid}")
            continue
        refs: list[str] = []
        fa3_bindings = row.get("fa3_bindings")
        if not isinstance(fa3_bindings, dict):
            findings.append(f"shared capability fa3_bindings missing: {sid}")
            fa3_bindings = {}
        for key in ("profile_ids", "contract_ids"):
            values = fa3_bindings.get(key, [])
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                findings.append(f"shared capability binding list invalid: {sid}/{key}")
                values = []
            refs.extend(values)
        unresolved = sorted({ref for ref in refs if ref not in bindings})
        derived = sorted(
            {capability for ref in refs for capability in bindings.get(ref, [])},
            key=_cap_sort_key,
        )
        if unresolved:
            findings.append(f"shared capability has unresolved canonical bindings: {sid}: {unresolved}")
        if not derived:
            findings.append(f"shared capability has no derived capability scope: {sid}")
        consumers = row.get("consumer_applications", [])
        if not isinstance(consumers, list) or any(not isinstance(value, str) for value in consumers):
            findings.append(f"shared capability consumer applications invalid: {sid}")
            consumers = []
        capabilities.update(derived)
        applications.update(consumers)
        projection.append({
            "shared_component_id": sid,
            "binding_refs": sorted(set(refs)),
            "derived_capabilities": derived,
            "consumer_applications": sorted(set(consumers)),
        })
    return capabilities, applications, projection, findings


def validate_request(root: Path, request: dict[str, Any], authority: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    caps = set(canonical_capabilities(root))

    if request.get("schema") != REQUEST_SCHEMA:
        findings.append("request schema mismatch")
    for key in ("request_id", "application_id", "rationale"):
        if not isinstance(request.get(key), str) or not request[key].strip():
            findings.append(f"{key} is required")

    source_commit = request.get("source_commit")
    if not isinstance(source_commit, str) or HEX40.fullmatch(source_commit) is None:
        findings.append("source_commit must be a lowercase 40-character git commit")

    for key in ("base_release_digest", "parent_effective_digest", "change_digest"):
        value = request.get(key)
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            findings.append(f"{key} must be a lowercase sha256 hex digest")

    impact = request.get("runtime_impact")
    allowed = set(authority.get("runtime_impact_classes", []))
    if impact not in allowed:
        findings.append("runtime_impact is unsupported")

    changed_paths = request.get("changed_paths")
    if not _list_of_strings(changed_paths) or not changed_paths:
        findings.append("changed_paths must be a non-empty string list")

    affected = request.get("affected_capabilities", [])
    consumers = request.get("consumer_capabilities", [])
    changed_shared = request.get("changed_shared_component_ids", [])
    for label, values in (
        ("affected_capabilities", affected),
        ("consumer_capabilities", consumers),
        ("changed_shared_component_ids", changed_shared),
    ):
        if not _list_of_strings(values):
            findings.append(f"{label} must be a string list")
            continue
        if len(values) != len(set(values)):
            findings.append(f"{label} contains duplicates")
        if label != "changed_shared_component_ids":
            unknown = sorted(set(values) - caps, key=_cap_sort_key)
            if unknown:
                findings.append(f"{label} contains unknown capability IDs: {unknown}")

    flags = request.get("flags")
    if not isinstance(flags, dict):
        findings.append("flags must be an object")
        flags = {}
    allowed_flags = set(authority.get("full_requalification_trigger_flags", [])) | {
        "hardware_surface_changed",
        "software_coexistence_surface_changed",
    }
    unknown_flags = sorted(set(flags) - allowed_flags)
    if unknown_flags:
        findings.append(f"flags contains unsupported keys: {unknown_flags}")
    for key, value in flags.items():
        if not isinstance(value, bool):
            findings.append(f"flags.{key} must be boolean")

    if request.get("global_promotion_claim") is not False:
        findings.append("global_promotion_claim must be false")

    full_trigger = impact == "GLOBAL" or any(
        flags.get(key) is True for key in authority.get("full_requalification_trigger_flags", [])
    )
    if impact == "LOCAL" and not affected and not full_trigger:
        findings.append("LOCAL runtime impact requires affected_capabilities")
    if impact == "SHARED" and not affected and not consumers and not changed_shared and not full_trigger:
        findings.append(
            "SHARED runtime impact requires affected_capabilities, consumer_capabilities, "
            "or changed_shared_component_ids"
        )
    if impact == "NONE" and any(flags.get(key) is True for key in allowed_flags):
        findings.append("NONE runtime impact cannot declare runtime/global change flags")

    return findings


def plan_request(root: Path, request: dict[str, Any], authority: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    authority = authority or load_json(root / "canonical/FA3-CURRENT-HOST-CHANGE-DELTA-AUTHORITY-001.json")
    findings = validate_request(root, request, authority)
    if findings:
        return {
            "schema": "fa3.current-host-delta-plan.v1",
            "status": "FAIL",
            "fail_closed": True,
            "findings": findings,
            "global_promotion_claim": False,
        }

    all_caps = canonical_capabilities(root)
    shared_caps, affected_apps, shared_projection, shared_findings = shared_component_scope(
        root, request.get("changed_shared_component_ids", [])
    )
    if shared_findings:
        return {
            "schema": "fa3.current-host-delta-plan.v1",
            "status": "FAIL",
            "fail_closed": True,
            "findings": shared_findings,
            "global_promotion_claim": False,
        }
    flags = request["flags"]
    full_trigger = request["runtime_impact"] == "GLOBAL" or any(
        flags.get(key) is True for key in authority["full_requalification_trigger_flags"]
    )

    if request["runtime_impact"] == "NONE":
        classification = "NO_RUNTIME_IMPACT"
        selected_caps: list[str] = []
    elif full_trigger:
        classification = "FULL_REQUALIFICATION"
        selected_caps = list(all_caps)
    elif (
        request["runtime_impact"] == "SHARED"
        or request.get("consumer_capabilities")
        or request.get("changed_shared_component_ids")
    ):
        classification = "IMPACT_REQUALIFICATION"
        selected_caps = sorted(
            set(request["affected_capabilities"])
            | set(request.get("consumer_capabilities", []))
            | shared_caps
            | set(authority.get("mandatory_runtime_delta_capabilities", [])),
            key=_cap_sort_key,
        )
    else:
        classification = "CAPABILITY_DELTA_REQUALIFICATION"
        selected_caps = sorted(
            set(request["affected_capabilities"])
            | set(authority.get("mandatory_runtime_delta_capabilities", [])),
            key=_cap_sort_key,
        )

    obligations = [
        {"capability_id": capability_id, "test_kind": test_kind}
        for capability_id in selected_caps
        for test_kind in TEST_KINDS
    ]
    required_shared_gates = [] if classification == "NO_RUNTIME_IMPACT" else list(
        authority.get("required_shared_gates", [])
    )
    plan = {
        "schema": "fa3.current-host-delta-plan.v1",
        "status": "PASS",
        "fail_closed": True,
        "authority_id": authority["id"],
        "request_id": request["request_id"],
        "application_id": request["application_id"],
        "classification": classification,
        "base_release_digest": request["base_release_digest"],
        "parent_effective_digest": request["parent_effective_digest"],
        "source_commit": request["source_commit"],
        "change_digest": request["change_digest"],
        "changed_paths": sorted(set(request["changed_paths"])),
        "changed_shared_component_ids": sorted(set(request.get("changed_shared_component_ids", []))),
        "affected_applications": sorted(affected_apps),
        "shared_capability_scope": shared_projection,
        "affected_capabilities": selected_caps,
        "affected_capability_count": len(selected_caps),
        "required_test_kinds": list(TEST_KINDS),
        "required_obligations": obligations,
        "required_obligation_count": len(obligations),
        "required_shared_gates": required_shared_gates,
        "hardware_surface_changed": bool(flags.get("hardware_surface_changed")),
        "software_coexistence_surface_changed": bool(flags.get("software_coexistence_surface_changed")),
        "base_full_closure_required_before_delta_activation": classification != "NO_RUNTIME_IMPACT",
        "unaffected_base_proof_semantics": "REMAINS_BOUND_TO_IMMUTABLE_BASE_ONLY_NOT_COPIED_OR_RELABELED_TO_DELTA",
        "physical_current_host_proof_required": classification != "NO_RUNTIME_IMPACT",
        "historical_evidence_reused": False,
        "synthetic_current_host_pass_allowed": False,
        "global_promotion_claim": False,
        "activation_status": (
            "NO_RUNTIME_ACTIVATION_REQUIRED"
            if classification == "NO_RUNTIME_IMPACT"
            else "PLANNED_REQUIRES_FRESH_PHYSICAL_DELTA_PROOF"
        ),
        "findings": [],
    }
    plan["plan_digest"] = _digest_json(plan)
    return plan



def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_file(root: Path, rel: Any) -> tuple[Path | None, str | None]:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None, "path missing/absolute"
    path = (root / rel).resolve()
    if path == root or root not in path.parents:
        return None, "path escapes repository"
    if not path.is_file():
        return None, f"file missing: {rel}"
    return path, None


def _shared_gate_statuses(plan: dict[str, Any], value: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    findings: list[str] = []
    statuses: dict[str, str] = {}
    for gate in plan.get("required_shared_gates", []):
        status = value.get(gate)
        if status != "PASS":
            findings.append(f"required shared gate is not PASS: {gate}")
        else:
            statuses[gate] = "PASS"
    return statuses, findings


def collect_delta_receipt(
    root: Path,
    plan: dict[str, Any],
    shared_gates: dict[str, Any],
) -> dict[str, Any]:
    root = root.resolve()
    findings: list[str] = []
    if plan.get("status") != "PASS" or plan.get("classification") == "NO_RUNTIME_IMPACT":
        findings.append("runtime PASS delta plan required")
    subjects = set(plan.get("affected_capabilities", []))
    expected_obligation_count = int(plan.get("required_obligation_count", -1))
    if expected_obligation_count != len(subjects) * len(TEST_KINDS):
        findings.append("plan obligation cardinality mismatch")

    gate_statuses, gate_findings = _shared_gate_statuses(plan, shared_gates)
    findings.extend(gate_findings)

    producer_report_path = root / "reports/current-host-capability-qualification-constituent-orchestrator.json"
    test_report_path = root / "reports/current-host-capability-test-orchestrator.json"
    if not producer_report_path.is_file():
        findings.append("qualification constituent orchestrator report missing")
        producer_report: dict[str, Any] = {}
    else:
        producer_report = load_json(producer_report_path)
    if not test_report_path.is_file():
        findings.append("capability test orchestrator report missing")
        test_report: dict[str, Any] = {}
    else:
        test_report = load_json(test_report_path)

    requested = sorted(subjects, key=_cap_sort_key)
    if producer_report:
        if producer_report.get("orchestrator_integrity") != "PASS":
            findings.append("qualification constituent orchestrator is not PASS")
        if producer_report.get("execution_requested") is not True:
            findings.append("qualification constituent execution was not requested")
        if producer_report.get("requested_subjects") != requested:
            findings.append("qualification constituent subject scope mismatch")
        if producer_report.get("selected_producer_count") != expected_obligation_count:
            findings.append("qualification constituent selected producer count mismatch")
        if producer_report.get("constituents_materialized") != expected_obligation_count:
            findings.append("qualification constituents are incomplete")
        if producer_report.get("global_promotion_claim") is not False:
            findings.append("qualification constituent report claims global promotion")
    if test_report:
        if test_report.get("orchestrator_integrity") != "PASS":
            findings.append("capability test orchestrator is not PASS")
        if test_report.get("execution_requested") is not True:
            findings.append("capability test execution was not requested")
        if test_report.get("requested_subjects") != requested:
            findings.append("capability test subject scope mismatch")
        if test_report.get("selected_executor_count") != expected_obligation_count:
            findings.append("capability test selected executor count mismatch")
        if test_report.get("results_materialized") != expected_obligation_count:
            findings.append("capability test results are incomplete")
        if test_report.get("source_commit") != plan.get("source_commit"):
            findings.append("capability test source commit does not match delta plan")
        if test_report.get("global_promotion_claim") is not False:
            findings.append("capability test report claims global promotion")

    producer_registry_path = root / "canonical/current-host-capability-qualification-constituent-producers.json"
    if not producer_registry_path.is_file():
        findings.append("qualification constituent producer registry missing")
        producer_entries: list[dict[str, Any]] = []
    else:
        registry = load_json(producer_registry_path)
        producer_entries = [
            row for row in registry.get("entries", [])
            if isinstance(row, dict)
        ]

    producer_by_obligation: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in producer_entries:
        key = (str(row.get("subject_id", "")), str(row.get("test_kind", "")))
        producer_by_obligation.setdefault(key, []).append(row)

    proofs: list[dict[str, str]] = []
    host_digest: str | None = None
    for obligation in plan.get("required_obligations", []):
        capability_id = obligation.get("capability_id")
        test_kind = obligation.get("test_kind")
        key = (capability_id, test_kind)
        producers = producer_by_obligation.get(key, [])
        if len(producers) != 1:
            findings.append(f"exactly one qualification producer required: {capability_id}/{test_kind}")
            continue
        producer = producers[0]
        qid = producer.get("qualification_id")
        cid = producer.get("constituent_id")
        constituent_path = root / ".fa3-current-host/qualification-constituents" / str(qid) / f"{cid}.json"
        result_path = root / ".fa3-current-host/test-results/capabilities" / str(capability_id) / f"{test_kind}.json"
        if not constituent_path.is_file():
            findings.append(f"qualification constituent missing: {capability_id}/{test_kind}")
            continue
        if not result_path.is_file():
            findings.append(f"capability test result missing: {capability_id}/{test_kind}")
            continue
        constituent = load_json(constituent_path)
        result = load_json(result_path)

        for label, row in (("qualification", constituent), ("test", result)):
            if row.get("subject_id") != capability_id or row.get("test_kind") != test_kind:
                findings.append(f"{label} obligation identity mismatch: {capability_id}/{test_kind}")
            if row.get("status") != "PASS":
                findings.append(f"{label} obligation is not PASS: {capability_id}/{test_kind}")
            if row.get("execution_scope") != "CURRENT_HOST" or row.get("current_host") is not True:
                findings.append(f"{label} is not physical CURRENT_HOST evidence: {capability_id}/{test_kind}")
            if row.get("synthetic") is not False or row.get("ci_reference_only") is not False:
                findings.append(f"{label} synthetic/CI evidence forbidden: {capability_id}/{test_kind}")
            if row.get("global_promotion_claim") is not False:
                findings.append(f"{label} global promotion claim forbidden: {capability_id}/{test_kind}")

        if result.get("source_commit") != plan.get("source_commit"):
            findings.append(f"test result source commit mismatch: {capability_id}/{test_kind}")

        result_host = result.get("host_fingerprint_sha256")
        constituent_host = constituent.get("host_fingerprint_sha256")
        if (
            not isinstance(result_host, str)
            or HEX64.fullmatch(result_host) is None
            or result_host != constituent_host
        ):
            findings.append(f"host fingerprint mismatch: {capability_id}/{test_kind}")
        elif host_digest is None:
            host_digest = result_host
        elif host_digest != result_host:
            findings.append(f"mixed host fingerprints in delta: {capability_id}/{test_kind}")

        test_artifact, test_error = _repo_file(root, result.get("artifact_path"))
        test_artifact_digest = result.get("artifact_sha256")
        if test_error:
            findings.append(f"test artifact {test_error}: {capability_id}/{test_kind}")
        if (
            not isinstance(test_artifact_digest, str)
            or HEX64.fullmatch(test_artifact_digest) is None
            or test_artifact is not None
            and _sha256_file(test_artifact) != test_artifact_digest
        ):
            findings.append(f"test artifact digest invalid: {capability_id}/{test_kind}")

        qualification_artifact, qualification_error = _repo_file(
            root, constituent.get("source_artifact_path")
        )
        qualification_digest = constituent.get("source_artifact_sha256")
        if qualification_error:
            findings.append(f"qualification artifact {qualification_error}: {capability_id}/{test_kind}")
        if (
            not isinstance(qualification_digest, str)
            or HEX64.fullmatch(qualification_digest) is None
            or qualification_artifact is not None
            and _sha256_file(qualification_artifact) != qualification_digest
        ):
            findings.append(f"qualification artifact digest invalid: {capability_id}/{test_kind}")

        if (
            isinstance(test_artifact_digest, str)
            and HEX64.fullmatch(test_artifact_digest) is not None
            and isinstance(qualification_digest, str)
            and HEX64.fullmatch(qualification_digest) is not None
        ):
            proofs.append({
                "capability_id": str(capability_id),
                "test_kind": str(test_kind),
                "status": "PASS",
                "artifact_sha256": test_artifact_digest,
                "qualification_artifact_sha256": qualification_digest,
            })

    host_path = root / ".fa3-current-host/global-closure/host/host-fingerprint.json"
    if host_digest is None:
        findings.append("delta host fingerprint was not established")
    elif not host_path.is_file() or _sha256_file(host_path) != host_digest:
        findings.append("delta host fingerprint artifact missing or digest mismatch")

    if findings:
        return {
            "schema": "fa3.current-host-delta-collection-report.v1",
            "result": "FAIL",
            "fail_closed": True,
            "plan_digest": plan.get("plan_digest"),
            "global_promotion_claim": False,
            "findings": findings,
        }

    return {
        "schema": RECEIPT_SCHEMA,
        "plan_digest": plan["plan_digest"],
        "base_release_digest": plan["base_release_digest"],
        "parent_effective_digest": plan["parent_effective_digest"],
        "source_commit": plan["source_commit"],
        "change_digest": plan["change_digest"],
        "host_fingerprint_sha256": host_digest,
        "physical_current_host_execution": True,
        "synthetic_current_host_pass": False,
        "historical_evidence_reused": False,
        "global_promotion_claim": False,
        "proofs": sorted(
            proofs,
            key=lambda row: (_cap_sort_key(row["capability_id"]), row["test_kind"]),
        ),
        "shared_gates": gate_statuses,
    }


def execute_delta(
    root: Path,
    plan: dict[str, Any],
    base: dict[str, Any],
    shared_gates: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    root = root.resolve()
    findings: list[str] = []
    base_check = compose_effective_host(base, [])
    if base_check.get("status") != "PASS":
        findings.append("admitted Current Host base is required before delta execution")
    elif base_check.get("base_release_digest") != plan.get("base_release_digest"):
        findings.append("delta plan base_release_digest does not match admitted base")
    elif base_check.get("effective_host_digest") != plan.get("parent_effective_digest"):
        findings.append("delta plan parent_effective_digest does not match effective base/overlay head")

    if plan.get("status") != "PASS" or plan.get("classification") == "NO_RUNTIME_IMPACT":
        findings.append("runtime PASS delta plan required")
    head = git_head(root)
    if head != plan.get("source_commit"):
        findings.append("repository HEAD does not match delta plan source_commit")
    gate_statuses, gate_findings = _shared_gate_statuses(plan, shared_gates)
    findings.extend(gate_findings)

    subjects = set(plan.get("affected_capabilities", []))
    expected = int(plan.get("required_obligation_count", -1))
    if expected != len(subjects) * len(TEST_KINDS):
        findings.append("delta plan obligation cardinality mismatch")

    if findings:
        return ({
            "schema": "fa3.current-host-delta-execution-report.v1",
            "result": "FAIL",
            "fail_closed": True,
            "plan_digest": plan.get("plan_digest"),
            "global_promotion_claim": False,
            "findings": findings,
        }, None)

    from fa3_current_host_capability_qualification_constituent_orchestrator import (
        orchestrate as orchestrate_producers,
    )
    from fa3_current_host_capability_test_orchestrator import orchestrate as orchestrate_tests

    producer_preflight = orchestrate_producers(root, execute=False, subjects=subjects)
    test_preflight = orchestrate_tests(root, execute=False, subjects=subjects)
    if (
        producer_preflight.get("orchestrator_integrity") != "PASS"
        or producer_preflight.get("selected_producer_count") != expected
        or test_preflight.get("orchestrator_integrity") != "PASS"
        or test_preflight.get("selected_executor_count") != expected
    ):
        return ({
            "schema": "fa3.current-host-delta-execution-report.v1",
            "result": "FAIL",
            "fail_closed": True,
            "plan_digest": plan.get("plan_digest"),
            "producer_preflight": producer_preflight,
            "test_preflight": test_preflight,
            "global_promotion_claim": False,
            "findings": ["selected Current Host producer/executor coverage is incomplete"],
        }, None)

    # Test results are transient execution workspace. Historical admitted evidence
    # remains immutable in its receipt/evidence chain and is never deleted here.
    for capability_id in subjects:
        shutil.rmtree(
            root / ".fa3-current-host/test-results/capabilities" / capability_id,
            ignore_errors=True,
        )

    producer_report = orchestrate_producers(root, execute=True, subjects=subjects)
    test_report = orchestrate_tests(root, execute=True, subjects=subjects)
    receipt = collect_delta_receipt(root, plan, gate_statuses)
    gate_report = (
        verify_delta_receipt(plan, receipt)
        if receipt.get("schema") == RECEIPT_SCHEMA
        else {
            "schema": "fa3.current-host-delta-gate-report.v1",
            "result": "FAIL",
            "fail_closed": True,
            "plan_digest": plan.get("plan_digest"),
            "global_promotion_claim": False,
            "findings": receipt.get("findings", ["delta receipt collection failed"]),
        }
    )
    result = "PASS" if gate_report.get("result") == "PASS" else "FAIL"
    return ({
        "schema": "fa3.current-host-delta-execution-report.v1",
        "result": result,
        "fail_closed": True,
        "plan_digest": plan["plan_digest"],
        "source_commit": plan["source_commit"],
        "affected_capabilities": sorted(subjects, key=_cap_sort_key),
        "required_obligation_count": expected,
        "producer_report_status": producer_report.get("status"),
        "test_report_status": test_report.get("status"),
        "verified_obligation_count": gate_report.get("verified_obligation_count", 0),
        "delta_digest": gate_report.get("delta_digest"),
        "effective_host_digest": gate_report.get("effective_host_digest"),
        "global_promotion_claim": False,
        "findings": gate_report.get("findings", []),
    }, receipt if result == "PASS" else None)



def verify_delta_receipt(plan: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    if plan.get("status") != "PASS":
        findings.append("delta plan is not PASS")
    if plan.get("classification") == "NO_RUNTIME_IMPACT":
        findings.append("NO_RUNTIME_IMPACT plan does not accept a runtime delta receipt")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("receipt schema mismatch")
    for key in ("plan_digest", "base_release_digest", "parent_effective_digest", "source_commit", "change_digest"):
        if receipt.get(key) != plan.get(key):
            findings.append(f"receipt {key} does not match plan")
    host_fingerprint_sha256 = receipt.get("host_fingerprint_sha256")
    if not isinstance(host_fingerprint_sha256, str) or HEX64.fullmatch(host_fingerprint_sha256) is None:
        findings.append("host_fingerprint_sha256 missing/invalid")
    if receipt.get("physical_current_host_execution") is not True:
        findings.append("physical_current_host_execution must be true")
    if receipt.get("synthetic_current_host_pass") is not False:
        findings.append("synthetic_current_host_pass must be false")
    if receipt.get("historical_evidence_reused") is not False:
        findings.append("historical_evidence_reused must be false")
    if receipt.get("global_promotion_claim") is not False:
        findings.append("global_promotion_claim must be false")

    expected = {
        (row["capability_id"], row["test_kind"])
        for row in plan.get("required_obligations", [])
        if isinstance(row, dict)
    }
    proofs = receipt.get("proofs")
    actual: set[tuple[str, str]] = set()
    proof_projection: list[dict[str, str]] = []
    if not isinstance(proofs, list):
        findings.append("proofs must be a list")
        proofs = []
    for row in proofs:
        if not isinstance(row, dict):
            findings.append("proof row must be an object")
            continue
        key = (row.get("capability_id"), row.get("test_kind"))
        if not all(isinstance(item, str) for item in key):
            findings.append("proof capability_id/test_kind missing")
            continue
        if key in actual:
            findings.append(f"duplicate proof obligation: {key[0]}/{key[1]}")
        actual.add(key)
        if row.get("status") != "PASS":
            findings.append(f"proof is not PASS: {key[0]}/{key[1]}")
        artifact = row.get("artifact_sha256")
        qualification_artifact = row.get("qualification_artifact_sha256")
        if not isinstance(artifact, str) or HEX64.fullmatch(artifact) is None:
            findings.append(f"proof artifact digest invalid: {key[0]}/{key[1]}")
        if not isinstance(qualification_artifact, str) or HEX64.fullmatch(qualification_artifact) is None:
            findings.append(f"qualification artifact digest invalid: {key[0]}/{key[1]}")
        if (
            isinstance(artifact, str)
            and HEX64.fullmatch(artifact) is not None
            and isinstance(qualification_artifact, str)
            and HEX64.fullmatch(qualification_artifact) is not None
        ):
            proof_projection.append(
                {
                    "capability_id": key[0],
                    "test_kind": key[1],
                    "artifact_sha256": artifact,
                    "qualification_artifact_sha256": qualification_artifact,
                }
            )
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            findings.append(f"missing proof obligations: {missing}")
        if extra:
            findings.append(f"unexpected proof obligations: {extra}")

    gates = receipt.get("shared_gates")
    if not isinstance(gates, dict):
        findings.append("shared_gates must be an object")
        gates = {}
    for gate in plan.get("required_shared_gates", []):
        if gates.get(gate) != "PASS":
            findings.append(f"required shared gate is not PASS: {gate}")

    if findings:
        return {
            "schema": "fa3.current-host-delta-gate-report.v1",
            "result": "FAIL",
            "fail_closed": True,
            "plan_digest": plan.get("plan_digest"),
            "global_promotion_claim": False,
            "findings": findings,
        }

    evidence_projection = {
        "plan_digest": plan["plan_digest"],
        "base_release_digest": plan["base_release_digest"],
        "parent_effective_digest": plan["parent_effective_digest"],
        "source_commit": plan["source_commit"],
        "change_digest": plan["change_digest"],
        "host_fingerprint_sha256": receipt["host_fingerprint_sha256"],
        "proofs": sorted(proof_projection, key=lambda x: (_cap_sort_key(x["capability_id"]), x["test_kind"])),
        "shared_gates": {key: gates[key] for key in sorted(plan["required_shared_gates"])},
    }
    delta_digest = _digest_json(evidence_projection)
    effective_host_digest = _digest_text(plan["parent_effective_digest"] + ":" + delta_digest)
    return {
        "schema": "fa3.current-host-delta-gate-report.v1",
        "result": "PASS",
        "fail_closed": True,
        "delta_status": "DELTA_ADMITTED",
        "request_id": plan["request_id"],
        "application_id": plan["application_id"],
        "classification": plan["classification"],
        "base_release_digest": plan["base_release_digest"],
        "parent_effective_digest": plan["parent_effective_digest"],
        "source_commit": plan["source_commit"],
        "change_digest": plan["change_digest"],
        "host_fingerprint_sha256": receipt["host_fingerprint_sha256"],
        "plan_digest": plan["plan_digest"],
        "delta_digest": delta_digest,
        "effective_host_digest": effective_host_digest,
        "affected_capabilities": plan["affected_capabilities"],
        "verified_obligation_count": len(expected),
        "historical_evidence_reused": False,
        "synthetic_current_host_pass": False,
        "global_promotion_claim": False,
        "findings": [],
    }


def compose_effective_host(base: dict[str, Any], deltas: list[dict[str, Any]]) -> dict[str, Any]:
    findings: list[str] = []
    if base.get("schema") != BASE_SCHEMA:
        findings.append("base state schema mismatch")
    if base.get("status") != "CURRENT_HOST_BASE_ADMITTED":
        findings.append("base Current Host is not admitted")
    if base.get("capability_count") != 175 or base.get("obligation_count") != 525:
        findings.append("base state is not the fixed 175/525 model")
    base_digest = base.get("base_release_digest")
    effective = base.get("effective_host_digest", base_digest)
    if not isinstance(base_digest, str) or HEX64.fullmatch(base_digest) is None:
        findings.append("base_release_digest invalid")
    if not isinstance(effective, str) or HEX64.fullmatch(effective) is None:
        findings.append("base effective_host_digest invalid")

    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not findings:
        for index, delta in enumerate(deltas, start=1):
            if delta.get("result") != "PASS" or delta.get("delta_status") != "DELTA_ADMITTED":
                findings.append(f"delta {index} is not admitted")
                break
            delta_digest = delta.get("delta_digest")
            if not isinstance(delta_digest, str) or HEX64.fullmatch(delta_digest) is None:
                findings.append(f"delta {index} digest invalid")
                break
            if delta_digest in seen:
                findings.append(f"delta {index} is duplicated")
                break
            seen.add(delta_digest)
            if delta.get("base_release_digest") != base_digest:
                findings.append(f"delta {index} base_release_digest mismatch")
                break
            if delta.get("parent_effective_digest") != effective:
                findings.append(f"delta {index} parent_effective_digest breaks overlay chain")
                break
            if delta.get("effective_host_digest") != _digest_text(effective + ":" + delta_digest):
                findings.append(f"delta {index} effective_host_digest mismatch")
                break
            effective = delta["effective_host_digest"]
            chain.append(
                {
                    "delta_digest": delta_digest,
                    "request_id": delta.get("request_id"),
                    "application_id": delta.get("application_id"),
                    "classification": delta.get("classification"),
                    "effective_host_digest": effective,
                }
            )

    return {
        "schema": "fa3.effective-current-host.v1",
        "status": "PASS" if not findings else "FAIL",
        "fail_closed": True,
        "base_release_digest": base_digest,
        "effective_host_digest": effective if not findings else None,
        "delta_count": len(chain),
        "ordered_deltas": chain,
        "capability_count": 175,
        "obligation_model": "POSITIVE_NEGATIVE_ROLLBACK_PER_AFFECTED_CAPABILITY",
        "historical_evidence_relabeling": "FORBIDDEN",
        "global_promotion_claim": False,
        "findings": findings,
    }


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Current Host Change & Delta Authority")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = parser.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan")
    plan_p.add_argument("--request", required=True)
    plan_p.add_argument("--output", required=True)

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--plan", required=True)
    verify_p.add_argument("--receipt", required=True)
    verify_p.add_argument("--output", required=True)

    collect_p = sub.add_parser("collect")
    collect_p.add_argument("--plan", required=True)
    collect_p.add_argument("--shared-gates", required=True)
    collect_p.add_argument("--output", required=True)

    execute_p = sub.add_parser("execute")
    execute_p.add_argument("--plan", required=True)
    execute_p.add_argument("--base", required=True)
    execute_p.add_argument("--shared-gates", required=True)
    execute_p.add_argument("--receipt-output", required=True)
    execute_p.add_argument("--output", required=True)

    compose_p = sub.add_parser("compose")
    compose_p.add_argument("--base", required=True)
    compose_p.add_argument("--delta", action="append", default=[])
    compose_p.add_argument("--output", required=True)

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if args.command == "plan":
        result = plan_request(root, load_json(Path(args.request)))
    elif args.command == "verify":
        result = verify_delta_receipt(load_json(Path(args.plan)), load_json(Path(args.receipt)))
    elif args.command == "collect":
        result = collect_delta_receipt(
            root,
            load_json(Path(args.plan)),
            load_json(Path(args.shared_gates)),
        )
    elif args.command == "execute":
        result, receipt = execute_delta(
            root,
            load_json(Path(args.plan)),
            load_json(Path(args.base)),
            load_json(Path(args.shared_gates)),
        )
        if receipt is not None:
            _write(Path(args.receipt_output), receipt)
    else:
        result = compose_effective_host(
            load_json(Path(args.base)),
            [load_json(Path(path)) for path in args.delta],
        )

    _write(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    state = result.get("status", result.get("result"))
    if args.command == "collect" and result.get("schema") == RECEIPT_SCHEMA:
        state = "PASS"
    return 0 if state == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
