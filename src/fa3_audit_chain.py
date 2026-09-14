#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Iterable

ZERO_HMAC = "0" * 64
MIN_KEY_BYTES = 32


class AuditChainError(RuntimeError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def normalize_key(key: bytes | str) -> bytes:
    if isinstance(key, str):
        try:
            key_bytes = bytes.fromhex(key)
        except ValueError as exc:
            raise AuditChainError("audit HMAC key must be hexadecimal") from exc
    else:
        key_bytes = bytes(key)
    if len(key_bytes) < MIN_KEY_BYTES:
        raise AuditChainError(f"audit HMAC key must be at least {MIN_KEY_BYTES} bytes")
    return key_bytes


def sign_record(sequence: int, event: dict[str, Any], previous_hmac: str, key: bytes | str) -> dict[str, Any]:
    if sequence < 1:
        raise AuditChainError("sequence must be >= 1")
    if len(previous_hmac) != 64:
        raise AuditChainError("previous_hmac must be a SHA-256 hex digest")
    key_bytes = normalize_key(key)
    signed = {"sequence": sequence, "previous_hmac": previous_hmac, "event": event}
    signed["hmac_sha256"] = hmac.new(key_bytes, _canonical_bytes(signed), hashlib.sha256).hexdigest()
    return signed


def verify_records(records: Iterable[dict[str, Any]], key: bytes | str) -> dict[str, Any]:
    key_bytes = normalize_key(key)
    previous = ZERO_HMAC
    count = 0
    for expected_sequence, record in enumerate(records, 1):
        count = expected_sequence
        if record.get("sequence") != expected_sequence:
            raise AuditChainError(f"audit sequence mismatch at record {expected_sequence}")
        if record.get("previous_hmac") != previous:
            raise AuditChainError(f"audit previous_hmac mismatch at record {expected_sequence}")
        event = record.get("event")
        if not isinstance(event, dict):
            raise AuditChainError(f"audit event is not an object at record {expected_sequence}")
        unsigned = {"sequence": expected_sequence, "previous_hmac": previous, "event": event}
        expected_hmac = hmac.new(key_bytes, _canonical_bytes(unsigned), hashlib.sha256).hexdigest()
        actual_hmac = str(record.get("hmac_sha256", ""))
        if not hmac.compare_digest(actual_hmac, expected_hmac):
            raise AuditChainError(f"audit HMAC mismatch at record {expected_sequence}")
        previous = actual_hmac
    return {"result": "PASS", "records": count, "head_hmac_sha256": previous}


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AuditChainError(f"invalid audit JSON at line {line_number}") from exc
        if not isinstance(value, dict):
            raise AuditChainError(f"audit record at line {line_number} is not an object")
        records.append(value)
    return records


def append_event(path: str | Path, event: dict[str, Any], key: bytes | str) -> dict[str, Any]:
    if not isinstance(event, dict) or not event:
        raise AuditChainError("audit event must be a non-empty object")
    key_bytes = normalize_key(key)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.seek(0)
            records: list[dict[str, Any]] = []
            for line_number, raw in enumerate(fh.read().splitlines(), 1):
                if not raw.strip():
                    continue
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise AuditChainError(f"invalid audit JSON at line {line_number}") from exc
                if not isinstance(value, dict):
                    raise AuditChainError(f"audit record at line {line_number} is not an object")
                records.append(value)
            verified = verify_records(records, key_bytes)
            record = sign_record(len(records) + 1, event, verified["head_hmac_sha256"], key_bytes)
            fh.seek(0, os.SEEK_END)
            fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            return record
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
