#!/usr/bin/env python3
"""Privacy-bounded, deterministic donor ingestion from user-supplied ChatGPT exports.

This is an import adapter, NOT a ChatGPT event subscription. It does not call
ChatGPT, scrape an account, upload conversation text or install donor software.
"""
from __future__ import annotations

import argparse
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
MAX_URLS_PER_MESSAGE = 16
_POSITIVE = re.compile(
    r"(?i)(?:\bdonornak\b|\bdonorként\b|\bdonorjelölt\b|\bdonor\s*:"
    r"|\bpotential\s+donor\b|\bdonor\s+candidate\b|\breference\s+candidate\b"
    r"|\breuse\s+candidate\b|\bcould\s+be\s+a\s+donor\b|\breferenciajelölt\b)"
)
_OWNER_DIRECT = re.compile(r"(?i)\b(?:donornak|donor)\s*:")
_NEGATIVE = re.compile(
    r"(?i)\b(?:nem\s+(?:alkalmas\s+)?donor|not\s+(?:a\s+)?donor|"
    r"donornak\s+alkalmatlan|rejected\s+donor)\b"
)
_GITHUB = re.compile(r"(?<![\w@])(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:\.git)?", re.I)
_BARE = re.compile(r"(?<![/\w.])([A-Za-z0-9][A-Za-z0-9_.-]{1,38})/([A-Za-z0-9][A-Za-z0-9_.-]{1,79})(?![/\w.])")
_NAMED = [
    re.compile(r"(?i)\bdonor(?:jelölt|\s+candidate)?\s*[:\-]\s*([^\n;,]{2,90})"),
    re.compile(r"(?i)\bdonornak\s+alkalmas\s+lehet\s*[:\-]\s*([^\n;,]{2,90})"),
    re.compile(r"(?i)\bpotential\s+donor\s*[:\-]\s*([^\n;,]{2,90})"),
]
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


def _candidate_sources(text: str) -> tuple[list[tuple[str, str, str]], bool]:
    """Return (name, kind, locator), and an ambiguity flag."""
    matches = list(_POSITIVE.finditer(text))
    if not matches or (_NEGATIVE.search(text) and len(matches) == 1):
        return [], False
    # Avoid harvesting every unrelated link from long quoted articles or code.
    spans = [(0, len(text))] if len(text) <= 1400 else [
        (max(0, match.start() - 320), min(len(text), match.end() + 640))
        for match in matches
    ]
    segments = [text[start:end] for start, end in spans]
    github = set()
    for segment in segments:
        for match in _GITHUB.finditer(segment):
            owner, name = match.group(1), match.group(2).removesuffix(".git")
            github.add((owner, name.rstrip(".")))
    if len(github) > MAX_URLS_PER_MESSAGE:
        return [], True
    if github:
        sources = [
            (f"{owner}/{project}", "GITHUB", f"https://github.com/{owner}/{project}")
            for owner, project in sorted(github, key=lambda row: (row[0].lower(), row[1].lower()))
            if owner.lower() != "ubuntuokos" or project.lower() != "final-architecture-v3.0"
        ]
        return sources, False
    # A bare owner/repository token is useful when discussing GitHub donors
    # without a URL; refuse obvious file names and internal paths.
    bare = set()
    for segment in segments:
        for match in _BARE.finditer(segment):
            owner, project = match.groups()
            if owner.lower() in {"src", "docs", "tests", "canonical", "bin", "home", "usr"}:
                continue
            if project.lower().endswith((".py", ".md", ".json", ".yml", ".yaml", ".txt", ".sh")):
                continue
            bare.add((owner, project))
    if len(bare) > MAX_URLS_PER_MESSAGE:
        return [], True
    if bare:
        return [
            (f"{owner}/{project}", "GITHUB", f"https://github.com/{owner}/{project}")
            for owner, project in sorted(bare, key=lambda row: (row[0].lower(), row[1].lower()))
            if f"github:{owner}/{project}".lower() != _SELF_REPO
        ], False
    for segment in segments:
        for pattern in _NAMED:
            found = pattern.search(segment)
            if found:
                name = found.group(1).strip(" .:-\t")
                if 2 <= len(name) <= 90 and not re.search(r"https?://|[\\/]|[<>@]", name, re.I):
                    return [(name, "PROJECT", "project:" + name)], False
    return [], False


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
    target = root.resolve() / REGISTRY_REL
    original = _load(target)
    if original.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001":
        raise ValueError("unexpected canonical donor registry")
    stats = {
        "records_scanned": 0, "signal_records": 0, "created": 0, "merged": 0,
        "unlinked_skipped": 0, "ambiguous_skipped": 0, "excluded_self": 0,
        "dry_run": dry_run, "origin": origin,
    }
    with tempfile.TemporaryDirectory(prefix="fa3-donor-chat-") as directory:
        stage_root = Path(directory)
        stage = stage_root / REGISTRY_REL
        stage.parent.mkdir(parents=True)
        shutil.copyfile(target, stage)
        known = {
            row["source"]["normalized_key"]
            for row in original.get("entries", [])
            if isinstance(row, dict) and isinstance(row.get("source"), dict)
            and isinstance(row["source"].get("normalized_key"), str)
        }
        seen_in_batch: set[str] = set()
        finalized_in_batch: set[str] = set()
        for record in records:
            stats["records_scanned"] += 1
            direct_owner_link = False
            if isinstance(record, dict) and isinstance(record.get("text"), str):
                text = record["text"]
                if not _POSITIVE.search(text):
                    continue
                sources, ambiguous = _candidate_sources(text)
                # Explicit owner submissions are pre-reviewed for catalog inclusion.
                # Tentative research or assistant mentions remain candidates.
                direct_owner_link = bool(_OWNER_DIRECT.search(text)) and (
                    (origin == "chatgpt-export" and record.get("speaker_role") == "user")
                    or (origin == "approved-chat-event" and record.get("owner_submitted_link") is True)
                )
            elif isinstance(record, dict):
                if record.get("potential_donor") is not True:
                    raise ValueError("metadata event lacks explicit potential-donor signal")
                sources = [(record["name"].strip(),
                            "GITHUB" if record["source"].lower().startswith("https://github.com/")
                            else "PROJECT", record["source"].strip())]
                ambiguous = False
                if not sources[0][0] or not sources[0][2]:
                    raise ValueError("approved event metadata must contain nonempty name and source")
                direct_owner_link = (origin == "approved-chat-event"
                                     and record.get("owner_submitted_link") is True)
            else:
                if not _POSITIVE.search(record):
                    continue
                sources, ambiguous = _candidate_sources(record)
            if ambiguous:
                stats["ambiguous_skipped"] += 1
                continue
            if sources:
                stats["signal_records"] += 1
            for name, kind, locator in sources:
                key = _normalized_key(kind, locator)
                if key == _SELF_REPO:
                    stats["excluded_self"] += 1
                    continue
                if kind == "PROJECT" and not allow_unlinked_names and key not in known:
                    # A personal conversation may mention a private project:
                    # never publish its name into the public FA3 repository by default.
                    stats["unlinked_skipped"] += 1
                    continue
                if key in seen_in_batch and not (direct_owner_link and key not in finalized_in_batch):
                    continue
                seen_in_batch.add(key)
                if direct_owner_link:
                    finalized_in_batch.add(key)
                result = capture_candidate(
                    stage_root, name=name, source_kind=kind, source_locator=locator,
                    tags=["chat-history-import"], discovered_from=origin,
                    owner_submitted_link=direct_owner_link,
                )
                stats["created" if result["created"] else "merged"] += 1
        if (stats["created"] or stats["merged"]) and not dry_run:
            _atomic_write(target, _load(stage))
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
