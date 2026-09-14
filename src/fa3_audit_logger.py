#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
import re


ZERO_HASH = "0" * 64
PII_KEYS = {
    "name", "speaker_name", "full_name", "first_name", "last_name",
    "email", "email_address", "phone", "phone_number", "address",
    "postal_address", "voice_sample", "audio_sample", "biometric",
    "biometric_data", "raw_voice", "transcript", "date_of_birth",
}
SAFE_DETAIL_SUFFIXES = ("_ref", "_digest", "_code", "_id_hash")
SAFE_DETAIL_KEYS = {"scope", "purpose", "policy_version", "model_family"}


class AuditError(RuntimeError):
    pass


class AuditIntegrityError(AuditError):
    pass


class AuditPolicyError(AuditError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _hash_entry(entry: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(entry)).hexdigest()


def _fsync_directory(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class FA3CryptographicAuditLogger:
    """Fail-closed, append-only, tamper-evident FA3 consent audit ledger.

    The ledger is JSONL and is never rewritten during normal operation. A local
    head checkpoint detects truncation as long as the checkpoint remains
    trustworthy. Production admission additionally requires a separately
    anchored checkpoint receipt (TPM/external/asymmetric signer); this class
    intentionally does not claim that a local HMAC file is immutable.
    """

    def __init__(
        self,
        log_file_path: str | os.PathLike[str],
        secret_key_path: str | os.PathLike[str],
        *,
        checkpoint_path: str | os.PathLike[str] | None = None,
        key_id: str | None = None,
        key_version: int = 1,
        verification_key_dir: str | os.PathLike[str] | None = None,
    ) -> None:
        self.log_path = Path(log_file_path)
        self.key_path = Path(secret_key_path)
        self.checkpoint_path = (
            Path(checkpoint_path)
            if checkpoint_path is not None
            else self.log_path.with_suffix(self.log_path.suffix + ".head.json")
        )
        self.lock_path = self.log_path.with_suffix(self.log_path.suffix + ".lock")
        self.verification_key_dir = (
            Path(verification_key_dir)
            if verification_key_dir is not None
            else self.key_path.parent
        )
        self.secret_key = self._load_audit_key(self.key_path)
        self.key_id = key_id or self.key_path.stem
        self._key_cache: dict[str, bytes] = {self.key_id: self.secret_key}
        self.key_version = int(key_version)
        if self.key_version < 1:
            raise AuditPolicyError("key_version must be >= 1")

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        with self._exclusive_lock():
            ledger_exists = self.log_path.exists()
            checkpoint_exists = self.checkpoint_path.exists()
            if not ledger_exists and checkpoint_exists:
                raise AuditIntegrityError(
                    "FAIL-CLOSED: checkpoint exists but audit ledger is missing"
                )
            if not ledger_exists:
                self._initialize_genesis_locked()
            elif not checkpoint_exists:
                raise AuditIntegrityError(
                    "FAIL-CLOSED: audit ledger exists but head checkpoint is missing"
                )
            self._verify_locked(raise_on_error=True)

    @staticmethod
    def _load_audit_key(key_path: Path) -> bytes:
        if not key_path.is_file():
            raise FileNotFoundError(
                f"FAIL-CLOSED: audit signing key is missing: {key_path}"
            )
        mode = key_path.stat().st_mode & 0o777
        if mode & 0o077:
            raise PermissionError(
                f"FAIL-CLOSED: audit key permissions must not grant group/other access: {oct(mode)}"
            )
        key = key_path.read_bytes().strip()
        if len(key) < 32:
            raise AuditPolicyError(
                "FAIL-CLOSED: audit HMAC key must contain at least 32 bytes"
            )
        return key

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+b") as handle:
            os.chmod(self.lock_path, 0o600)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _key_for(self, key_id: str) -> bytes:
        if key_id in self._key_cache:
            return self._key_cache[key_id]
        candidate = self.verification_key_dir / f"{key_id}.key"
        key = self._load_audit_key(candidate)
        self._key_cache[key_id] = key
        return key

    @staticmethod
    def _validate_opaque_ref(label: str, value: str) -> None:
        if not isinstance(value, str) or not value or len(value) > 256:
            raise AuditPolicyError(f"{label} must be a non-empty opaque reference <= 256 characters")
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", value) is None:
            raise AuditPolicyError(
                f"{label} must be an opaque identifier, not human-readable/raw personal data"
            )

    @staticmethod
    def _validate_nested_value(value: Any) -> None:
        if isinstance(value, Mapping):
            FA3CryptographicAuditLogger._validate_details(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                FA3CryptographicAuditLogger._validate_nested_value(item)

    @staticmethod
    def _validate_details(details: Mapping[str, Any]) -> None:
        if not isinstance(details, Mapping):
            raise AuditPolicyError("details must be a mapping")
        for key, value in details.items():
            lowered = str(key).strip().lower()
            if lowered in PII_KEYS:
                raise AuditPolicyError(
                    f"PII field is forbidden in immutable audit payload: {key}"
                )
            if not (
                lowered in SAFE_DETAIL_KEYS
                or any(lowered.endswith(suffix) for suffix in SAFE_DETAIL_SUFFIXES)
            ):
                raise AuditPolicyError(
                    f"detail field must be an opaque reference/digest/code, not raw data: {key}"
                )
            FA3CryptographicAuditLogger._validate_nested_value(value)

    def _sign_entry(self, entry_without_signature: Mapping[str, Any]) -> str:
        key_id = str(entry_without_signature["key_id"])
        key = self._key_for(key_id)
        return hmac.new(key, _canonical_json(entry_without_signature), hashlib.sha256).hexdigest()

    def _verify_entry_signature(self, entry: Mapping[str, Any]) -> bool:
        signature = entry.get("signature")
        if not isinstance(signature, str):
            return False
        unsigned = dict(entry)
        unsigned.pop("signature", None)
        try:
            expected = self._sign_entry(unsigned)
        except (AuditError, OSError):
            return False
        return hmac.compare_digest(signature, expected)

    def _checkpoint_unsigned(self, entry: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema": "fa3.audit-head-checkpoint.v1",
            "ledger": self.log_path.name,
            "index": entry["index"],
            "entry_hash": _hash_entry(entry),
            "key_id": entry["key_id"],
            "key_version": entry["key_version"],
        }

    def _write_checkpoint_locked(self, entry: Mapping[str, Any]) -> None:
        checkpoint = self._checkpoint_unsigned(entry)
        checkpoint_key = self._key_for(str(entry["key_id"]))
        checkpoint["checkpoint_hmac"] = hmac.new(
            checkpoint_key, _canonical_json(checkpoint), hashlib.sha256
        ).hexdigest()
        payload = json.dumps(
            checkpoint, sort_keys=True, indent=2, ensure_ascii=False
        ) + "\n"
        self._atomic_write(self.checkpoint_path, payload.encode("utf-8"), mode=0o600)

    @staticmethod
    def _atomic_write(path: Path, payload: bytes, *, mode: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        try:
            os.fchmod(fd, mode)
            with os.fdopen(fd, "wb", closefd=True) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
            _fsync_directory(path.parent)
        except Exception:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise

    def _append_line_locked(self, entry: Mapping[str, Any]) -> None:
        line = _canonical_json(entry) + b"\n"
        fd = os.open(
            str(self.log_path),
            os.O_WRONLY | os.O_APPEND | os.O_CREAT,
            0o600,
        )
        try:
            os.fchmod(fd, 0o600)
            view = memoryview(line)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise OSError("short write while appending audit record")
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_directory(self.log_path.parent)

    def _read_entries_locked(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        try:
            raw = self.log_path.read_bytes()
        except FileNotFoundError as exc:
            raise AuditIntegrityError("audit ledger disappeared") from exc
        if not raw:
            raise AuditIntegrityError("audit ledger is empty")
        if not raw.endswith(b"\n"):
            raise AuditIntegrityError("audit ledger ends with a partial record")
        for lineno, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                raise AuditIntegrityError(f"blank audit record at line {lineno}")
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuditIntegrityError(
                    f"invalid JSON audit record at line {lineno}"
                ) from exc
            if not isinstance(item, dict):
                raise AuditIntegrityError(
                    f"audit record at line {lineno} is not an object"
                )
            entries.append(item)
        return entries

    def _initialize_genesis_locked(self) -> None:
        genesis = {
            "schema": "fa3.audit-entry.v2",
            "index": 0,
            "timestamp": _utc_now(),
            "event_type": "GENESIS",
            "consent_ref": "SYSTEM",
            "operator_ref": "SYSTEM",
            "details": {},
            "previous_hash": ZERO_HASH,
            "key_id": self.key_id,
            "key_version": self.key_version,
        }
        genesis["signature"] = self._sign_entry(genesis)
        self._append_line_locked(genesis)
        self._write_checkpoint_locked(genesis)

    def _verify_checkpoint_locked(self, head: Mapping[str, Any]) -> None:
        try:
            checkpoint = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise AuditIntegrityError("invalid or missing audit head checkpoint") from exc

        signature = checkpoint.pop("checkpoint_hmac", None)
        if not isinstance(signature, str):
            raise AuditIntegrityError("checkpoint HMAC is missing")
        checkpoint_key = self._key_for(str(checkpoint.get("key_id", "")))
        expected = hmac.new(
            checkpoint_key, _canonical_json(checkpoint), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise AuditIntegrityError("checkpoint HMAC mismatch")

        expected_fields = self._checkpoint_unsigned(head)
        if checkpoint != expected_fields:
            raise AuditIntegrityError(
                "ledger head does not match trusted local checkpoint (possible truncation/rewrite)"
            )

    def _verify_locked(self, *, raise_on_error: bool) -> bool:
        try:
            entries = self._read_entries_locked()
            genesis = entries[0]
            if genesis.get("index") != 0:
                raise AuditIntegrityError("genesis index is not zero")
            if genesis.get("event_type") != "GENESIS":
                raise AuditIntegrityError("genesis event type mismatch")
            if genesis.get("previous_hash") != ZERO_HASH:
                raise AuditIntegrityError("genesis previous_hash mismatch")
            if genesis.get("consent_ref") != "SYSTEM":
                raise AuditIntegrityError("genesis consent_ref mismatch")
            if not self._verify_entry_signature(genesis):
                raise AuditIntegrityError("genesis signature mismatch")

            previous = genesis
            for expected_index, current in enumerate(entries[1:], 1):
                if current.get("index") != expected_index:
                    raise AuditIntegrityError(
                        f"non-contiguous audit index at {expected_index}"
                    )
                if current.get("previous_hash") != _hash_entry(previous):
                    raise AuditIntegrityError(
                        f"audit chain continuity failed at index {expected_index}"
                    )
                if not self._verify_entry_signature(current):
                    raise AuditIntegrityError(
                        f"audit signature failed at index {expected_index}"
                    )
                previous = current

            self._verify_checkpoint_locked(entries[-1])
            return True
        except (AuditError, OSError, ValueError, TypeError, KeyError):
            if raise_on_error:
                raise
            return False

    def verify_log_integrity(self) -> bool:
        with self._exclusive_lock():
            return self._verify_locked(raise_on_error=False)

    def log_consent_event(
        self,
        event_type: str,
        consent_id: str,
        operator_id: str,
        details: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not event_type or event_type == "GENESIS":
            raise AuditPolicyError("event_type must be non-empty and cannot be GENESIS")
        self._validate_opaque_ref("consent_ref", consent_id)
        self._validate_opaque_ref("operator_ref", operator_id)
        self._validate_details(details)

        with self._exclusive_lock():
            self._verify_locked(raise_on_error=True)
            entries = self._read_entries_locked()
            previous = entries[-1]
            new_entry: dict[str, Any] = {
                "schema": "fa3.audit-entry.v2",
                "index": int(previous["index"]) + 1,
                "timestamp": _utc_now(),
                "event_type": event_type,
                "consent_ref": consent_id,
                "operator_ref": operator_id,
                "details": dict(details),
                "previous_hash": _hash_entry(previous),
                "key_id": self.key_id,
                "key_version": self.key_version,
            }
            new_entry["signature"] = self._sign_entry(new_entry)
            self._append_line_locked(new_entry)
            self._write_checkpoint_locked(new_entry)
            return new_entry

    def rotate_key(
        self,
        new_key_path: str | os.PathLike[str],
        *,
        new_key_id: str,
        new_key_version: int,
    ) -> dict[str, Any]:
        """Record a rotation event under the old key, then activate the new key.

        Old verification keys must remain available (or cached in this process)
        so historic entries remain verifiable. Key material is never written to
        the ledger.
        """
        new_path = Path(new_key_path)
        new_key = self._load_audit_key(new_path)
        if not new_key_id or new_key_id == self.key_id:
            raise AuditPolicyError("new_key_id must be non-empty and different")
        if int(new_key_version) <= self.key_version:
            raise AuditPolicyError("new_key_version must increase monotonically")

        with self._exclusive_lock():
            self._verify_locked(raise_on_error=True)
            entries = self._read_entries_locked()
            previous = entries[-1]
            details = {
                "new_key_ref": new_key_id,
                "new_key_digest": hashlib.sha256(new_key).hexdigest(),
                "reason_code": "KEY_ROTATION",
            }
            event: dict[str, Any] = {
                "schema": "fa3.audit-entry.v2",
                "index": int(previous["index"]) + 1,
                "timestamp": _utc_now(),
                "event_type": "AUDIT_KEY_ROTATED",
                "consent_ref": "SYSTEM",
                "operator_ref": "SYSTEM",
                "details": details,
                "previous_hash": _hash_entry(previous),
                "key_id": self.key_id,
                "key_version": self.key_version,
            }
            event["signature"] = self._sign_entry(event)
            self._append_line_locked(event)
            self._write_checkpoint_locked(event)

            old_id, old_key = self.key_id, self.secret_key
            self._key_cache[old_id] = old_key
            self.key_path = new_path
            self.secret_key = new_key
            self.key_id = new_key_id
            self.key_version = int(new_key_version)
            self._key_cache[self.key_id] = new_key
            return event

    def head(self) -> dict[str, Any]:
        with self._exclusive_lock():
            self._verify_locked(raise_on_error=True)
            return self._read_entries_locked()[-1]

    def checkpoint_digest(self) -> str:
        """Digest to be anchored by a TPM/external/asymmetric production signer."""
        with self._exclusive_lock():
            self._verify_locked(raise_on_error=True)
            return hashlib.sha256(self.checkpoint_path.read_bytes()).hexdigest()
