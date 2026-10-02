#!/usr/bin/env python3
"""Read-only source projectors into CHIF ChangeRecord objects."""
from __future__ import annotations

import fnmatch
from typing import Any

from fa3_change_history import build_record, redact, sha256_json


def _timestamp(value: Any) -> str:
    text = str(value or "").strip()
    return text or "1970-01-01T00:00:00Z"


def project_journal_event(event: dict[str, Any], source_ref: str) -> dict[str, Any]:
    object_id = str(event.get("project_id") or event.get("component_id") or event.get("id") or "unknown")
    return build_record(
        record_id="JRN:" + str(event.get("id") or sha256_json(event)[:16]),
        timestamp=_timestamp(event.get("timestamp")),
        source_kind="JOURNAL_EVENT", source_ref=source_ref,
        object_type=str(event.get("domain") or "JOURNAL"),
        object_id=object_id, operation=str(event.get("lifecycle") or "EVENT"),
        payload=event, truth_class="FACT",
        details={"summary": event.get("summary"), "correlation_id": event.get("correlation_id")},
    )


def project_canonical_document(document: dict[str, Any], source_ref: str,
                               timestamp: str = "1970-01-01T00:00:00Z") -> dict[str, Any]:
    object_id = str(document.get("id") or document.get("profile_id") or document.get("gate_id") or source_ref)
    return build_record(
        record_id="CAN:" + sha256_json({"source": source_ref, "document": document})[:24],
        timestamp=_timestamp(timestamp), source_kind="CANONICAL_JSON", source_ref=source_ref,
        object_type=str(document.get("schema") or "CANONICAL_RECORD"), object_id=object_id,
        operation="SNAPSHOT", payload=document, truth_class="FACT",
        details={"status": document.get("status")},
    )


def project_git_change(change: dict[str, Any]) -> dict[str, Any]:
    commit = str(change.get("commit") or "")
    path = str(change.get("path") or "")
    if not commit or not path:
        raise ValueError("git change requires commit and path")
    payload = redact(change)
    return build_record(
        record_id=f"GIT:{commit}:{sha256_json(path)[:12]}",
        timestamp=_timestamp(change.get("timestamp")), source_kind="GIT_CHANGE",
        source_ref=f"{commit}:{path}", object_type="PATH", object_id=path,
        operation=str(change.get("status") or "MODIFIED"), payload=payload, truth_class="FACT",
        details={"commit": commit, "author": change.get("author"), "message": change.get("message")},
    )


def project_evidence(evidence: dict[str, Any], source_ref: str) -> dict[str, Any]:
    eid = str(evidence.get("id") or evidence.get("evidence_id") or source_ref)
    return build_record(
        record_id="EVID:" + sha256_json({"source": source_ref, "id": eid, "body": evidence})[:24],
        timestamp=_timestamp(evidence.get("timestamp") or evidence.get("generated_at")),
        source_kind="EVIDENCE", source_ref=source_ref, object_type="EVIDENCE",
        object_id=eid, operation=str(evidence.get("result") or evidence.get("status") or "OBSERVED"),
        payload=evidence, truth_class="FACT",
        details={"evidence_level": evidence.get("evidence_level")},
    )


def classify_scope(changed_paths: list[str], allowed_patterns: list[str],
                   justification_required_patterns: list[str] | None = None) -> dict[str, str]:
    justification_required_patterns = justification_required_patterns or []
    result: dict[str, str] = {}
    for path in changed_paths:
        if any(fnmatch.fnmatch(path, pat) for pat in allowed_patterns):
            result[path] = "EXPECTED"
        elif any(fnmatch.fnmatch(path, pat) for pat in justification_required_patterns):
            result[path] = "JUSTIFICATION_REQUIRED"
        else:
            result[path] = "OUT_OF_SCOPE"
    return result
