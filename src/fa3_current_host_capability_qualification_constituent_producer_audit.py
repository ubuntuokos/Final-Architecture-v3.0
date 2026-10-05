#!/usr/bin/env python3
from __future__ import annotations

from fa3_release_baseline import module_active_capability_count

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from fa3_current_host_capability_test_qualification_audit import (
    CONSTITUENT_SCHEMA,
    QUALIFICATION_REGISTRY,
    audit as audit_qualifications,
)

CAPABILITY_COUNT = module_active_capability_count(__file__)
REGISTRY_SCHEMA = "fa3.current-host-capability-qualification-constituent-producer-registry.v1"
REPORT_SCHEMA = "fa3.current-host-capability-qualification-constituent-producer-audit.v1"
AUDITOR_ID = "FA3-CURRENT-HOST-QUALIFICATION-CONSTITUENT-PRODUCER-AUDIT-001"
PRODUCER_REGISTRY = "canonical/current-host-capability-qualification-constituent-producers.json"
EXECUTION_MODE = "REAL_CURRENT_HOST_EXECUTION"
PRODUCER_ID = re.compile(r"^FA3-QUAL-PRODUCER-[A-Z0-9._-]{3,128}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _repo_adapter(root: Path, rel: Any) -> tuple[Path | None, str | None]:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None, "adapter_path missing or absolute"
    unresolved = root / rel
    if unresolved.is_symlink():
        return None, "adapter_path may not be a symlink"
    candidate = unresolved.resolve()
    if candidate == root or root not in candidate.parents:
        return None, "adapter_path escapes repository"
    if not candidate.is_file():
        return None, f"adapter missing: {rel}"
    if not rel.startswith(("bin/", "src/", "evidence/", "tools/")):
        return None, "adapter_path is outside approved executable source roots"
    return candidate, None


def audit(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    qualification = audit_qualifications(root)
    registry = _load(root / PRODUCER_REGISTRY)
    findings: list[dict[str, Any]] = []

    if qualification.get("audit_integrity") != "PASS":
        findings.append({
            "code": "QCPA-001",
            "message": "Capability qualification registry audit failed",
            "findings": qualification.get("blocking_findings", []),
        })

    if registry.get("schema") != REGISTRY_SCHEMA:
        findings.append({"code": "QCPA-002", "message": "Producer registry schema mismatch"})
    if registry.get("capability_count") != CAPABILITY_COUNT:
        findings.append({"code": "QCPA-003", "message": "Producer registry capability_count mismatch"})
    if registry.get("execution_scope") != "CURRENT_HOST":
        findings.append({"code": "QCPA-004", "message": "Producer registry execution_scope must be CURRENT_HOST"})
    if registry.get("registration_semantics") != "EXPLICIT_ONLY_NO_INFERENCE":
        findings.append({"code": "QCPA-005", "message": "Producer registration must be explicit-only"})
    if registry.get("qualification_registry") != QUALIFICATION_REGISTRY:
        findings.append({"code": "QCPA-006", "message": "Producer registry must bind the canonical qualification registry"})
    if registry.get("constituent_schema") != CONSTITUENT_SCHEMA:
        findings.append({"code": "QCPA-007", "message": "Producer registry constituent schema mismatch"})

    invariants = registry.get("invariants")
    required_false = (
        "provider_receipt_substitution_allowed",
        "component_receipt_substitution_allowed",
        "generic_host_evidence_substitution_allowed",
        "hosted_ci_substitution_allowed",
        "static_reference_substitution_allowed",
        "synthetic_producer_allowed",
        "shell_command_registration_allowed",
        "unregistered_manifest_allowed",
        "automatic_capability_promotion",
        "automatic_global_promotion",
    )
    required_true = (
        "repository_local_adapter_required",
        "exact_qualification_constituent_identity_required",
        "source_artifact_scope_required",
        "adapter_digest_revalidation_required",
    )
    if not isinstance(invariants, dict):
        findings.append({"code": "QCPA-008", "message": "Producer registry invariants missing"})
    else:
        for key in required_false:
            if invariants.get(key) is not False:
                findings.append({"code": "QCPA-009", "message": f"Invariant must remain false: {key}"})
        for key in required_true:
            if invariants.get(key) is not True:
                findings.append({"code": "QCPA-010", "message": f"Invariant must remain true: {key}"})
        if invariants.get("new_capabilities") != 0 or invariants.get("new_architectural_authorities") != 0:
            findings.append({"code": "QCPA-011", "message": "Producer layer may not create capabilities or authorities"})

    qregistry = _load(root / QUALIFICATION_REGISTRY)
    accepted_qids = {
        row.get("qualification_id")
        for row in qualification.get("accepted_qualifications", [])
        if isinstance(row, dict)
    }
    required: dict[tuple[str, str], dict[str, Any]] = {}
    for definition in qregistry.get("entries", []):
        if not isinstance(definition, dict) or definition.get("qualification_id") not in accepted_qids:
            continue
        qid = definition["qualification_id"]
        for constituent in definition.get("required_constituents", []):
            if not isinstance(constituent, dict):
                continue
            cid = constituent.get("constituent_id")
            key = (qid, cid)
            required[key] = {
                "qualification_id": qid,
                "constituent_id": cid,
                "subject_id": definition.get("subject_id"),
                "test_kind": definition.get("test_kind"),
                "test_id": definition.get("test_id"),
                "source_evidence_class": constituent.get("source_evidence_class"),
                "covers_source_decision_ids": constituent.get("covers_source_decision_ids"),
                "max_constituent_ttl_seconds": definition.get("max_constituent_ttl_seconds"),
            }

    entries = registry.get("entries")
    if not isinstance(entries, list):
        findings.append({"code": "QCPA-012", "message": "Producer registry entries must be a list"})
        entries = []

    registered: dict[tuple[str, str], dict[str, Any]] = {}
    producer_ids: set[str] = set()
    entry_audit: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        entry_findings: list[str] = []
        if not isinstance(entry, dict):
            findings.append({"code": "QCPA-013", "message": "Producer entry is not an object", "index": index})
            continue

        producer_id = entry.get("producer_id")
        qid = entry.get("qualification_id")
        cid = entry.get("constituent_id")
        key = (qid, cid)
        expected = required.get(key)

        if not isinstance(producer_id, str) or not PRODUCER_ID.fullmatch(producer_id):
            entry_findings.append("producer_id invalid")
        elif producer_id in producer_ids:
            entry_findings.append("duplicate producer_id")
        else:
            producer_ids.add(producer_id)

        if expected is None:
            entry_findings.append("producer does not map to an accepted canonical qualification constituent")
        else:
            for field in (
                "qualification_id",
                "constituent_id",
                "subject_id",
                "test_kind",
                "test_id",
                "source_evidence_class",
                "covers_source_decision_ids",
            ):
                if entry.get(field) != expected.get(field):
                    entry_findings.append(f"{field} mismatch against canonical qualification constituent")

        if key in registered:
            entry_findings.append("duplicate qualification/constituent producer registration")
        if entry.get("execution_mode") != EXECUTION_MODE:
            entry_findings.append("execution_mode is not REAL_CURRENT_HOST_EXECUTION")
        if entry.get("synthetic") is not False:
            entry_findings.append("synthetic must be false")
        if entry.get("ci_reference_only") is not False:
            entry_findings.append("ci_reference_only must be false")
        if entry.get("provider_receipt_only") is not False:
            entry_findings.append("provider_receipt_only must be false")
        if entry.get("component_receipt_only") is not False:
            entry_findings.append("component_receipt_only must be false")
        if entry.get("generic_host_collection_only") is not False:
            entry_findings.append("generic_host_collection_only must be false")
        if entry.get("global_promotion_claim") is not False:
            entry_findings.append("global_promotion_claim must be false")

        timeout = entry.get("timeout_seconds", 300)
        if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
            entry_findings.append("timeout_seconds outside 1..3600")
        ttl = entry.get("ttl_seconds", 86400)
        max_ttl = expected.get("max_constituent_ttl_seconds") if expected else None
        if not isinstance(ttl, int) or ttl < 60 or ttl > 604800:
            entry_findings.append("ttl_seconds outside 60..604800")
        elif isinstance(max_ttl, int) and ttl > max_ttl:
            entry_findings.append("ttl_seconds exceeds canonical qualification maximum")

        adapter, adapter_error = _repo_adapter(root, entry.get("adapter_path"))
        if adapter_error:
            entry_findings.append(adapter_error)
        digest = entry.get("adapter_sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            entry_findings.append("adapter_sha256 missing/invalid")
        elif adapter is not None and _sha256(adapter) != digest:
            entry_findings.append("adapter digest mismatch")

        argv = entry.get("argv", [])
        if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
            entry_findings.append("argv must be a list of strings")
        if isinstance(argv, list) and any(item in {"sudo", "sh", "bash", "-c", "--shell"} for item in argv):
            entry_findings.append("shell/privilege escalation tokens are forbidden in argv")

        status = "REGISTERED" if not entry_findings else "REJECTED"
        entry_audit.append({
            "index": index,
            "producer_id": producer_id,
            "qualification_id": qid,
            "constituent_id": cid,
            "status": status,
            "findings": entry_findings,
        })
        if entry_findings:
            findings.append({
                "code": "QCPA-014",
                "message": "Qualification constituent producer registration rejected",
                "index": index,
                "producer_id": producer_id,
                "findings": entry_findings,
            })
        else:
            registered[key] = entry

    pending = [value for key, value in required.items() if key not in registered]
    accepted_rows = [
        required[key] | {
            "producer_id": entry.get("producer_id"),
            "adapter_path": entry.get("adapter_path"),
            "adapter_sha256": entry.get("adapter_sha256"),
            "ttl_seconds": entry.get("ttl_seconds", 86400),
        }
        for key, entry in sorted(registered.items())
    ]

    if findings:
        integrity = "FAIL"
        status = "BLOCKED_INVALID_CONSTITUENT_PRODUCER_REGISTRY"
    elif not required:
        integrity = "PASS"
        status = "PENDING_CAPABILITY_QUALIFICATION_DEFINITIONS"
    elif len(registered) == len(required):
        integrity = "PASS"
        status = "COMPLETE_EXPLICIT_CONSTITUENT_PRODUCER_COVERAGE"
    elif registered:
        integrity = "PASS"
        status = "PARTIAL_EXPLICIT_CONSTITUENT_PRODUCER_COVERAGE"
    else:
        integrity = "PASS"
        status = "PENDING_CONSTITUENT_PRODUCER_REGISTRATION"

    report = {
        "schema": REPORT_SCHEMA,
        "id": AUDITOR_ID,
        "producer_registry": PRODUCER_REGISTRY,
        "qualification_registry": QUALIFICATION_REGISTRY,
        "capability_count": CAPABILITY_COUNT,
        "qualification_audit_integrity": qualification.get("audit_integrity"),
        "qualified_definition_count": qualification.get("qualified_definition_count", 0),
        "required_constituent_count": len(required),
        "registered_producer_count": len(registered),
        "pending_producer_count": len(pending),
        "audit_integrity": integrity,
        "coverage_status": status,
        "accepted_producers": accepted_rows,
        "pending_constituents": pending,
        "entry_audit": entry_audit,
        "blocking_findings": findings,
        "provider_receipts_promoted": 0,
        "component_receipts_promoted": 0,
        "generic_host_evidence_promoted": 0,
        "global_promotion_claim": False,
        "truth_constraints": {
            "constituent_manifest_may_be_unregistered": False,
            "producer_may_be_inferred_from_provider": False,
            "producer_may_be_inferred_from_component_receipt": False,
            "producer_may_be_inferred_from_reference_artifact": False,
            "producer_registry_is_promotion_authority": False,
        },
    }
    _write(root / "reports/current-host-capability-qualification-constituent-producer-audit.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit FA3 current-host qualification constituent producer coverage")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = audit(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["audit_integrity"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
