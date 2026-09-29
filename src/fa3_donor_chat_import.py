#!/usr/bin/env python3
"""Privacy-bounded, deterministic donor ingestion from user-supplied ChatGPT exports.

This is an import adapter, NOT a ChatGPT event subscription. It does not call
ChatGPT, scrape an account, upload conversation text or install donor software.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from fa3_donor_registry import REGISTRY_REL, _atomic_write, _load, _normalized_key, capture_candidate

MAX_JSON_BYTES = 256 * 1024 * 1024
MAX_EXPORT_BYTES = 512 * 1024 * 1024
MAX_MESSAGE_CHARS = 20000
MAX_URLS_PER_MESSAGE = 128
# Only a user-authored DONORNAK label preceding the URL authorizes intake.
_OWNER_DIRECT = re.compile(r"(?i)\bdonornak\b(?:\s*:\s*|\s+(?=https?://|\[https?://|<https?://))")
_LINK = re.compile(r'https?://[^\s<>\[\]()"]+', re.I)

_EXPORT_NAME = re.compile(r"conversations(?:[_-]?\d+)?\.json", re.I)
_SELF_REPO = "github:ubuntuokos/final-architecture-v3.0"


def _json_bytes(data: bytes) -> list[dict[str, Any]]:
    if len(data) > MAX_JSON_BYTES:
        raise ValueError("conversation file exceeds size limit; split the export")
    value = json.loads(data.decode("utf-8-sig"))
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError("expected a ChatGPT conversations JSON array")
    return value


def read_export(path: Path) -> Iterable[dict[str, Any]]:
    """Read only conversations JSON; never extract other ZIP contents to disk."""
    if zipfile.is_zipfile(path):
        total = 0
        with zipfile.ZipFile(path) as archive:
            matches = [
                member for member in archive.infolist()
                if not member.is_dir() and _EXPORT_NAME.fullmatch(
                    PurePosixPath(member.filename).name
                )
            ]
            if not matches:
                raise ValueError("ZIP does not contain conversations JSON")
            for member in sorted(matches, key=lambda item: item.filename):
                if member.file_size > MAX_JSON_BYTES:
                    raise ValueError("conversation file exceeds size limit; split the export")
                total += member.file_size
                if total > MAX_EXPORT_BYTES:
                    raise ValueError("export exceeds aggregate size limit")
                with archive.open(member) as handle:
                    rows = _json_bytes(handle.read(MAX_JSON_BYTES + 1))
                yield from rows
    else:
        if path.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("conversation file exceeds size limit; split the export")
        yield from _json_bytes(path.read_bytes())


def _message_text(node: dict[str, Any], roles: set[str]) -> str | None:
    message = node.get("message")
    if not isinstance(message, dict):
        return None
    author = message.get("author") or {}
    if not isinstance(author, dict) or author.get("role") not in roles:
        return None
    content = message.get("content") or {}
    if not isinstance(content, dict):
        return None
    parts = content.get("parts")
    if isinstance(parts, list):
        text = "\n".join(part for part in parts if isinstance(part, str))
    else:
        text = content.get("text", "")
    return text if isinstance(text, str) and len(text) <= MAX_MESSAGE_CHARS else None


def _candidate_sources(text: str, *, owner_direct: bool = False) -> tuple[list[tuple[str, str, str]], bool]:
    """Only links AFTER an authenticated owner's literal 'donornak:' qualify."""
    if not owner_direct:
        return [], False
    marker = _OWNER_DIRECT.search(text)
    if marker is None:
        return [], False
    after = text[marker.end():]
    urls = set()
    for found in _LINK.findall(after):
        locator = found.rstrip(".,;:!?}\\\\")
        if not locator:
            continue
        urls.add(locator)
    if len(urls) > MAX_URLS_PER_MESSAGE:
        return [], True
    sources = []
    for url in sorted(urls, key=str.lower):
        if re.match(r"https?://(?:www\.)?github\.com/", url, re.I):
            path = re.sub(r"^https?://(?:www\.)?github\.com/", "", url, flags=re.I)
            kind, name = "GITHUB", path.rstrip("/")
            if path.lower().split("?")[0].strip("/") == "ubuntuokos/Final-Architecture-v3.0".lower():
                continue
        else:
            kind, name = "REFERENCE", url
        sources.append((name, kind, url))
    return sources, False

def _conversations(path: Path, roles: set[str], *, include_roles: bool = False) -> Iterable[str | dict[str, str]]:
    for conversation in read_export(path):
        mapping = conversation.get("mapping")
        if not isinstance(mapping, dict):
            continue
        for node in mapping.values():
            if not isinstance(node, dict):
                continue
            text = _message_text(node, roles)
            if text:
                role = node.get("message", {}).get("author", {}).get("role")
                yield {"text": text, "speaker_role": role} if include_roles else text


def _events(path: str) -> Iterable[str | dict[str, Any]]:
    """Approved third-party adapters may emit newline-delimited local events."""
    stream = sys.stdin if path == "-" else open(path, encoding="utf-8")
    try:
        for index, line in enumerate(stream, 1):
            if len(line) > MAX_MESSAGE_CHARS * 2:
                raise ValueError(f"event {index}: too long")
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"event {index}: object required")
            if row.get("potential_donor") is True and isinstance(row.get("name"), str) and isinstance(row.get("source"), str):
                yield row
            elif isinstance(row.get("text"), str):
                yield row
            else:
                raise ValueError(f"event {index}: text or approved donor metadata required")
    finally:
        if stream is not sys.stdin:
            stream.close()


def ingest(
    root: Path,
    records: Iterable[str | dict[str, Any]],
    *,
    origin: str,
    allow_unlinked_names: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Analysis is non-mutating; only verified owner-marked links enter the registry.

    This local nonblocking lease prevents two imports into the same checkout.
    Cross-host publication also requires the live GitHub donor-intake PR gate.
    """
    root = root.resolve()
    target = root / REGISTRY_REL
    stats = {
        "records_scanned": 0, "signal_records": 0, "created": 0, "merged": 0,
        "unlinked_skipped": 0, "ambiguous_skipped": 0, "excluded_self": 0,
        "analysis_only": 0, "dry_run": dry_run, "origin": origin,
    }
    approved = []
    for record in records:
        stats["records_scanned"] += 1
        if isinstance(record, str):
            # Raw strings have no trustworthy speaker attribution.
            stats["analysis_only"] += 1
            continue
        if not isinstance(record, dict):
            raise ValueError("conversation event must be text or an object")
        marked = False
        if isinstance(record.get("text"), str):
            source_is_owner = (
                (origin == "chatgpt-export" and record.get("speaker_role") == "user")
                or (origin == "approved-chat-event"
                    and record.get("speaker_role") == "user"
                    and record.get("owner_submitted_link") is True)
            )
            marked = source_is_owner and bool(_OWNER_DIRECT.search(record["text"]))
            sources, ambiguous = _candidate_sources(record["text"], owner_direct=marked)
        elif record.get("potential_donor") is True:
            # Structured events must attest BOTH the owner identity and the
            # explicit preceding marker. A generic candidate flag cannot enroll.
            marked = (origin == "approved-chat-event"
                      and record.get("speaker_role") == "user"
                      and record.get("owner_submitted_link") is True
                      and record.get("owner_donor_marker") == "donornak")
            if marked and isinstance(record.get("source"), str) and re.match(
                    r"^https?://", record["source"].strip(), re.I):
                locator = record["source"].strip()
                name = record.get("name") or locator
                kind = "GITHUB" if re.match(r"^https?://(?:www\.)?github\.com/", locator, re.I) else "REFERENCE"
                sources, ambiguous = [(name, kind, locator)], False
            else:
                sources, ambiguous = [], False
        else:
            raise ValueError("event lacks text or potential_donor metadata")
        if not marked:
            stats["analysis_only"] += 1
            continue
        if ambiguous:
            stats["ambiguous_skipped"] += 1
            continue
        if sources:
            stats["signal_records"] += 1
            approved.extend(sources)
        else:
            stats["analysis_only"] += 1
    if not approved:
        return stats

    # Filesystem lock serializes imports within the same host/checkouts using
    # the same repository path. GitHub PR preflight serializes across hosts.
    lock_name = "fa3-donor-" + hashlib.sha256(str(root).encode()).hexdigest()[:20] + ".lock"
    lock_path = Path(tempfile.gettempdir()) / lock_name
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("DONOR_INTAKE_ALREADY_ACTIVE_WAIT_FOR_COMPLETION") from exc
        original = _load(target)
        if original.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001":
            raise ValueError("unexpected canonical donor registry")
        with tempfile.TemporaryDirectory(prefix="fa3-donor-chat-") as directory:
            stage_root = Path(directory)
            stage = stage_root / REGISTRY_REL
            stage.parent.mkdir(parents=True)
            shutil.copyfile(target, stage)
            seen = set()
            for name, kind, locator in approved:
                key = _normalized_key(kind, locator)
                if key == _SELF_REPO:
                    stats["excluded_self"] += 1
                    continue
                if key in seen:
                    continue
                seen.add(key)
                result = capture_candidate(
                    stage_root, name=name, source_kind=kind, source_locator=locator,
                    tags=["explicit-owner-donornak"], discovered_from=origin,
                    owner_submitted_link=True, explicit_donor_marker=True,
                )
                stats["created" if result["created"] else "merged"] += 1
            if (stats["created"] or stats["merged"]) and not dry_run:
                _atomic_write(target, _load(stage))
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
    return stats

def main() -> int:
    parser = argparse.ArgumentParser(description="Import donor metadata from a local ChatGPT export or approved local event stream.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--export", type=Path, help="ChatGPT ZIP or conversations JSON file")
    source.add_argument("--events", help="JSONL from an approved adapter; '-' reads stdin")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--roles", default="user,assistant", help="Comma-separated export roles: user and/or assistant")
    parser.add_argument("--allow-unlinked-names", action="store_true", help="Explicit opt-in: publish source-less project names")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    roles = set(args.roles.split(","))
    if not roles or not roles.issubset({"user", "assistant"}):
        parser.error("--roles must select user and/or assistant")
    records = _conversations(args.export, roles, include_roles=True) if args.export else _events(args.events)
    try:
        result = ingest(
            args.root, records, origin="chatgpt-export" if args.export else "approved-chat-event",
            allow_unlinked_names=args.allow_unlinked_names, dry_run=args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print("Donor chat import BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
