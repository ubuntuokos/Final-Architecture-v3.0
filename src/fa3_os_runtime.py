#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import tempfile
import sys
import uuid
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-OS-RUNTIME-001"
PARENT_PROFILE_ID = "FA3-OS-001"
POLICY_ID = "FA3-OS-POLICY-001"
EVENT_CONTRACT_ID = "FA3-OS-EVENT-001"
JOURNAL_AUTHORITY = "FA3-JOURNAL-001"
JOURNAL_SCHEMA = "fa3.journal-event.v1"
DERIVED_SCHEMA = "fa3.os-derived-projection.v1"

ALLOWED_SOURCE_CLASSES = {
    "FA3_NATIVE",
    "AUTHORITATIVE_OS",
    "APPLICATION_ADAPTER",
    "SCOPED_OBSERVATION",
    "SEMANTIC_INFERENCE",
}
PROHIBITED_CAPTURE_KINDS = {
    "KEYLOGGER",
    "KEYSTROKE",
    "KEYSTROKES",
    "CLIPBOARD",
    "GENERIC_CLIPBOARD",
    "SCREENSHOT",
    "CONTINUOUS_SCREENSHOT",
    "SCREEN_CAPTURE",
    "GENERIC_SCREEN_CAPTURE",
}
PROHIBITED_INLINE_KEYS = {
    "raw_content",
    "clipboard_content",
    "keystrokes",
    "screenshot_bytes",
    "terminal_content",
    "secret",
    "credential",
    "password",
    "api_key",
    "auth_token",
    "access_token",
    "refresh_token",
}
TERMINAL_CONTENT_KEYS = {
    "command",
    "command_line",
    "stdin",
    "stdout",
    "stderr",
    "shell_text",
    "terminal_text",
    "terminal_content",
}
PASSWORD_MANAGER_IDS = {
    "keepassxc",
    "bitwarden",
    "1password",
    "vaultwarden",
    "kwalletmanager",
    "kwalletd",
}
SENSITIVE_PATH_MARKERS = (
    "/.ssh/",
    "/.gnupg/",
    "/.aws/credentials",
    "/.config/gcloud/credentials",
    "/.config/gh/hosts.yml",
    "/.password-store/",
)
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\b\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


class PolicyViolation(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def default_journal_path() -> Path:
    override = os.environ.get("FA3_OS_JOURNAL_PATH")
    if override:
        return Path(override).expanduser()
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return data_home / "Final Architecture" / "FA3 Control Center" / "journal" / "events" / "active.jsonl"


def _walk(value: Any, path: tuple[str, ...] = ()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield path + (str(key),), child
            yield from _walk(child, path + (str(key),))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            yield from _walk(child, path + (str(idx),))


def _redact_text(value: str) -> str:
    out = value
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)"):
            out = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", out)
        else:
            out = pattern.sub("[REDACTED]", out)
    return out


def _sensitive_reference(value: str) -> bool:
    normalized = "/" + value.replace("\\", "/").lstrip("/")
    low = normalized.lower()
    return any(marker.lower() in low for marker in SENSITIVE_PATH_MARKERS)


def _terminal_like(request: dict[str, Any]) -> bool:
    source_kind = str(request.get("source_kind", "")).upper()
    if source_kind in {"TERMINAL", "SHELL", "CLI"}:
        return True
    app = str(request.get("application_id", "")).lower()
    return any(x in app for x in ("konsole", "terminal", "xterm", "kitty", "alacritty"))


def enforce_privacy(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise PolicyViolation("FA3-OS-PRIV-RUNTIME-001: capture request must be an object")

    capture_kind = str(request.get("capture_kind", request.get("source_kind", ""))).upper()
    if capture_kind in PROHIBITED_CAPTURE_KINDS:
        raise PolicyViolation(f"FA3-OS-PRIV-RUNTIME-002: capture kind {capture_kind} is denied")

    app_id = str(request.get("application_id", "")).strip()
    if app_id.lower() in PASSWORD_MANAGER_IDS:
        raise PolicyViolation("FA3-OS-PRIV-RUNTIME-003: password-manager capture is denied")

    for key_path, _ in _walk(request):
        key = key_path[-1].lower()
        if key in PROHIBITED_INLINE_KEYS:
            raise PolicyViolation(f"FA3-OS-PRIV-RUNTIME-004: inline sensitive field {'.'.join(key_path)} is denied")
        if _terminal_like(request) and key in TERMINAL_CONTENT_KEYS:
            raise PolicyViolation(f"FA3-OS-PRIV-RUNTIME-005: terminal content field {'.'.join(key_path)} is denied")

    refs: list[str] = []
    subject = request.get("subject")
    if isinstance(subject, dict) and subject.get("reference") is not None:
        refs.append(str(subject["reference"]))
    for name in ("uri_reference", "payload_reference"):
        if request.get(name) is not None:
            refs.append(str(request[name]))
    if any(_sensitive_reference(ref) for ref in refs):
        raise PolicyViolation("FA3-OS-PRIV-RUNTIME-006: sensitive path/reference capture is denied")

    source_kind = str(request.get("source_kind", "")).upper()
    if source_kind == "BROWSER" and request.get("browser_content_requested") is True:
        policy_context = request.get("policy_context", {})
        if not isinstance(policy_context, dict) or policy_context.get("browser_opt_in") is not True:
            raise PolicyViolation("FA3-OS-PRIV-RUNTIME-007: browser content requires explicit opt-in")

    return request


def _clean_optional_text(value: Any, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = _redact_text(str(value).strip())
    return cleaned[:max_length] if cleaned else None


def normalize_capture_request(request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    enforce_privacy(request)

    action = _redact_text(str(request.get("action", "")).strip())
    subject = request.get("subject")
    if not action:
        raise PolicyViolation("FA3-OS-RUNTIME-001: action is required")
    if not isinstance(subject, dict):
        raise PolicyViolation("FA3-OS-RUNTIME-002: subject object is required")

    subject_kind = _redact_text(str(subject.get("kind", "")).strip())
    subject_ref = _redact_text(str(subject.get("reference", "")).strip())
    if not subject_kind or not subject_ref:
        raise PolicyViolation("FA3-OS-RUNTIME-003: subject.kind and subject.reference are required")

    provenance = request.get("provenance", {})
    if not isinstance(provenance, dict):
        raise PolicyViolation("FA3-OS-RUNTIME-004: provenance object is required")
    source_class = str(provenance.get("source_class", "")).upper()
    if source_class not in ALLOWED_SOURCE_CLASSES:
        raise PolicyViolation("FA3-OS-RUNTIME-005: invalid provenance.source_class")

    confidence = request.get("confidence", 1.0)
    if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
        raise PolicyViolation("FA3-OS-RUNTIME-006: confidence must be in [0,1]")

    tags = sorted({_redact_text(str(tag).strip())[:128] for tag in request.get("tags", []) if str(tag).strip()})

    enrichment: dict[str, Any] = {
        "schema_version": "1.0.0",
        "action": action[:128],
        "subject": {
            "kind": subject_kind[:64],
            "reference": subject_ref[:4096],
            "content_hash": _clean_optional_text(subject.get("content_hash"), 256),
            "mime_type": _clean_optional_text(subject.get("mime_type"), 255),
        },
        "capture_policy_id": POLICY_ID,
        "provenance": {
            "source_class": source_class,
            "source_reference": _clean_optional_text(provenance.get("source_reference"), 4096),
        },
        "confidence": float(confidence),
        "tags": tags,
    }

    obj = request.get("object")
    if isinstance(obj, dict):
        enrichment["object"] = {
            "kind": _redact_text(str(obj.get("kind", "")))[:64],
            "reference": _redact_text(str(obj.get("reference", "")))[:4096],
            "content_hash": _clean_optional_text(obj.get("content_hash"), 256),
        }

    for name, limit in (
        ("application_id", 256), ("session_id", 256), ("workstream_id", 256), ("artifact_id", 256),
        ("uri_reference", 4096), ("model_reference", 1024), ("workflow_reference", 1024),
        ("prompt_reference", 1024), ("payload_reference", 4096),
    ):
        value = _clean_optional_text(request.get(name), limit)
        if value is not None:
            enrichment[name] = value

    for name in ("parent_event_ids", "parent_artifact_ids"):
        values = sorted({_redact_text(str(v).strip()) for v in request.get(name, []) if str(v).strip()})
        if values:
            enrichment[name] = values

    project_id = _clean_optional_text(request.get("project_id"), 256) or ""
    source = _clean_optional_text(request.get("source"), 256) or enrichment.get("application_id") or enrichment["provenance"].get("source_reference") or "FA3 OS"
    summary = _clean_optional_text(request.get("summary"), 512) or f"{enrichment['action']} · {enrichment['subject']['reference']}"
    correlation = enrichment.get("workstream_id") or enrichment.get("workflow_reference") or enrichment.get("session_id")

    journal_event: dict[str, Any] = {
        "schema": JOURNAL_SCHEMA,
        "id": "FA3-EVT-" + str(uuid.uuid4()).upper(),
        "timestamp": utc_now(),
        "event_type": "EVENT",
        "domain": str(request.get("domain", "PROJECT" if project_id else "SYSTEM")).upper(),
        "source": source,
        "project_id": project_id,
        "lifecycle": str(request.get("lifecycle", "RECORDED")).upper(),
        "summary": summary,
        "details": canonical_json({"fa3_os": enrichment}),
        "tags": sorted(set(["FA3_OS", *tags])),
        "integrity": "APPEND_ONLY",
    }
    if correlation:
        journal_event["correlation_id"] = correlation
    return enrichment, journal_event


def append_journal_event(journal_path: Path, event: dict[str, Any]) -> None:
    if event.get("schema") != JOURNAL_SCHEMA or event.get("integrity") != "APPEND_ONLY":
        raise ValueError("FA3-OS-JOURNAL-001: only append-only canonical Journal events may be appended")
    journal_path = Path(journal_path)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    payload = (canonical_json(event) + "\n").encode("utf-8")
    fd = os.open(journal_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(fd, "ab", closefd=False) as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        os.close(fd)


def ingest_event(request: dict[str, Any], journal_path: Path) -> dict[str, Any]:
    enrichment, event = normalize_capture_request(request)
    append_journal_event(Path(journal_path), event)
    return {
        "result": "PASS", "profile_id": PROFILE_ID, "ledger_authority": JOURNAL_AUTHORITY,
        "event_id": event["id"], "event_digest": stable_digest(event), "enrichment_digest": stable_digest(enrichment),
    }


def read_journal_events(journal_path: Path) -> list[dict[str, Any]]:
    path = Path(journal_path)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def extract_enrichment(event: dict[str, Any]) -> dict[str, Any] | None:
    details = event.get("details")
    if not isinstance(details, str):
        return None
    try:
        parsed = json.loads(details)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("fa3_os"), dict):
        return None
    return parsed["fa3_os"]


def _projection_key(event: dict[str, Any], enrichment: dict[str, Any]) -> tuple[str, str] | None:
    if enrichment.get("workstream_id"):
        return "WORKSTREAM", str(enrichment["workstream_id"])
    if event.get("project_id"):
        return "PROJECT", str(event["project_id"])
    if enrichment.get("workflow_reference"):
        return "WORKFLOW", str(enrichment["workflow_reference"])
    if enrichment.get("session_id"):
        return "SESSION", str(enrichment["session_id"])
    if enrichment.get("artifact_id"):
        return "ARTIFACT", str(enrichment["artifact_id"])
    return None


def build_derived_projection(journal_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    events = read_journal_events(journal_path)
    workstreams: dict[tuple[str, str], dict[str, Any]] = {}
    sessions: dict[str, dict[str, Any]] = {}
    for event in events:
        enrichment = extract_enrichment(event)
        if enrichment is None:
            continue
        key = _projection_key(event, enrichment)
        if key is not None:
            row = workstreams.setdefault(key, {
                "kind": key[0], "id": key[1], "event_ids": [], "artifact_ids": [], "applications": [],
                "first_timestamp": event.get("timestamp"), "last_timestamp": event.get("timestamp"),
            })
            row["event_ids"].append(event.get("id"))
            if enrichment.get("artifact_id"):
                row["artifact_ids"].append(enrichment["artifact_id"])
            if enrichment.get("application_id"):
                row["applications"].append(enrichment["application_id"])
            row["last_timestamp"] = event.get("timestamp")
        session_id = enrichment.get("session_id")
        if session_id:
            session = sessions.setdefault(str(session_id), {
                "session_id": str(session_id), "event_ids": [], "project_ids": [], "workstream_ids": [],
                "first_timestamp": event.get("timestamp"), "last_timestamp": event.get("timestamp"),
            })
            session["event_ids"].append(event.get("id"))
            if event.get("project_id"):
                session["project_ids"].append(event["project_id"])
            if enrichment.get("workstream_id"):
                session["workstream_ids"].append(enrichment["workstream_id"])
            session["last_timestamp"] = event.get("timestamp")

    normalized_workstreams = []
    for key in sorted(workstreams):
        row = workstreams[key]
        for field in ("event_ids", "artifact_ids", "applications"):
            row[field] = sorted({str(v) for v in row[field] if v})
        normalized_workstreams.append(row)
    normalized_sessions = []
    for key in sorted(sessions):
        row = sessions[key]
        for field in ("event_ids", "project_ids", "workstream_ids"):
            row[field] = sorted({str(v) for v in row[field] if v})
        normalized_sessions.append(row)

    projection = {
        "schema": DERIVED_SCHEMA, "profile_id": PROFILE_ID, "ledger_authority": JOURNAL_AUTHORITY,
        "authoritative_history": False, "rebuildable": True, "generated_at": utc_now(),
        "source_event_count": len(events), "workstreams": normalized_workstreams, "sessions": normalized_sessions,
    }
    projection["projection_digest"] = stable_digest({k: v for k, v in projection.items() if k not in {"generated_at", "projection_digest"}})
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, delete=False) as handle:
            handle.write(json.dumps(projection, indent=2, ensure_ascii=False) + "\n")
            temp_path = Path(handle.name)
        os.replace(temp_path, output)
    return projection


def query_events(journal_path: Path, *, text: str = "", project_id: str = "", workstream_id: str = "") -> list[dict[str, Any]]:
    needle = text.lower().strip()
    rows = []
    for event in read_journal_events(journal_path):
        enrichment = extract_enrichment(event)
        if project_id and event.get("project_id") != project_id:
            continue
        if workstream_id and (enrichment or {}).get("workstream_id") != workstream_id:
            continue
        if needle and needle not in canonical_json(event).lower():
            continue
        rows.append(event)
    return rows


def run_reference_conformance() -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="fa3-os-runtime-") as temp:
        journal = Path(temp) / "journal" / "events" / "active.jsonl"
        base = {
            "source_kind": "APPLICATION", "capture_kind": "APPLICATION_EVENT", "action": "FILE_SAVE",
            "subject": {"kind": "FILE", "reference": "/projects/demo/shot01.png", "content_hash": "sha256:demo"},
            "application_id": "Krita", "project_id": "DEMO", "session_id": "S-1", "workstream_id": "WS-1",
            "artifact_id": "ART-1", "provenance": {"source_class": "APPLICATION_ADAPTER", "source_reference": "krita-adapter"},
            "confidence": 1.0, "tags": ["save"], "summary": "Saved shot01.png",
        }
        try:
            receipt = ingest_event(base, journal)
            if receipt.get("result") != "PASS":
                findings.append({"code": "FA3-OS-RT-001", "message": "valid event did not ingest"})
        except Exception as exc:
            findings.append({"code": "FA3-OS-RT-001", "message": f"valid event failed: {exc}"})
        secret_case = dict(base)
        secret_case["subject"] = dict(base["subject"])
        secret_case["subject"]["reference"] = "/projects/demo/secret.txt"
        secret_case["summary"] = "api_key=SUPER_SECRET_VALUE"
        try:
            ingest_event(secret_case, journal)
            if "SUPER_SECRET_VALUE" in journal.read_text(encoding="utf-8"):
                findings.append({"code": "FA3-OS-RT-002", "message": "secret leaked into durable Journal"})
        except Exception as exc:
            findings.append({"code": "FA3-OS-RT-002", "message": f"redaction case failed unexpectedly: {exc}"})
        negative_cases = [
            ("KEYLOGGER", {"capture_kind": "KEYLOGGER"}), ("CLIPBOARD", {"capture_kind": "CLIPBOARD"}),
            ("SCREENSHOT", {"capture_kind": "SCREENSHOT"}),
            ("TERMINAL_CONTENT", {"source_kind": "TERMINAL", "command": "cat ~/.ssh/id_rsa"}),
            ("PASSWORD_MANAGER", {"application_id": "keepassxc"}),
        ]
        for label, patch in negative_cases:
            candidate = dict(base); candidate.update(patch)
            try:
                normalize_capture_request(candidate)
                findings.append({"code": f"FA3-OS-RT-DENY-{label}", "message": f"{label} was not denied"})
            except PolicyViolation:
                pass
        projection = build_derived_projection(journal)
        if projection.get("authoritative_history") is not False or projection.get("rebuildable") is not True:
            findings.append({"code": "FA3-OS-RT-003", "message": "derived projection authority boundary drift"})
        if not projection.get("workstreams"):
            findings.append({"code": "FA3-OS-RT-004", "message": "deterministic workstream projection missing"})
    return {
        "result": "PASS" if not findings else "FAIL", "profile_id": PROFILE_ID, "ledger_authority": JOURNAL_AUTHORITY,
        "privacy_policy_id": POLICY_ID, "reference_runtime": True, "current_host_admission_claimed": False, "findings": findings,
    }


def _load_input(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 OS provider-neutral reference runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest"); ingest.add_argument("--input", required=True); ingest.add_argument("--journal", default=str(default_journal_path()))
    project = sub.add_parser("project"); project.add_argument("--journal", default=str(default_journal_path())); project.add_argument("--output")
    query = sub.add_parser("query"); query.add_argument("--journal", default=str(default_journal_path())); query.add_argument("--text", default=""); query.add_argument("--project-id", default=""); query.add_argument("--workstream-id", default="")
    sub.add_parser("self-test")
    args = parser.parse_args()
    try:
        if args.command == "ingest":
            result = ingest_event(_load_input(args.input), Path(args.journal))
        elif args.command == "project":
            result = build_derived_projection(Path(args.journal), Path(args.output) if args.output else None)
        elif args.command == "query":
            result = {"result": "PASS", "events": query_events(Path(args.journal), text=args.text, project_id=args.project_id, workstream_id=args.workstream_id)}
        else:
            result = run_reference_conformance()
    except (PolicyViolation, ValueError, OSError, json.JSONDecodeError) as exc:
        result = {"result": "FAIL", "error": str(exc)}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("result") == "PASS" or args.command in {"project", "query"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
