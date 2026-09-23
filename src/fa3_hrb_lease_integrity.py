#!/usr/bin/env python3
from __future__ import annotations

import copy
import datetime as dt
import errno
import fcntl
import hashlib
import hmac
import json
import os
import re
import select
import stat
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

AUTHORITY_ID = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
LEASE_SCHEMA = "fa3.hrb-lease-lifecycle-record.v1"
BINDING_SCHEMA = "fa3.hrb-runtime-binding.v1"
EVIDENCE_SCHEMA = "fa3.hrb-lease-lifecycle-evidence.v1"
HMAC_SCHEME = "HMAC-SHA256"
HMAC_SCOPE = "FA3_HRB_INTERNAL_LEASE_AUTH_V1"
EVIDENCE_AUTHORITY_ID = "FA3-AUTH-OBS-EVIDENCE-001"
TRUST_PKI_PROFILE_ID = "FA3-TRUST-PKI-001"
STATE_ORDER = (
    "ISSUED",
    "ACTIVE",
    "REVOKING",
    "EVICTING",
    "VERIFYING",
    "EVICTED",
)
FAILURE_STATES = ("EVICTION_FAILED", "QUARANTINED")
ALLOWED_TRANSITIONS = {
    "ISSUED": {"ACTIVE"},
    "ACTIVE": {"REVOKING"},
    "REVOKING": {"EVICTING", "EVICTION_FAILED"},
    "EVICTING": {"VERIFYING", "EVICTION_FAILED"},
    "VERIFYING": {"EVICTED", "EVICTION_FAILED"},
    "EVICTION_FAILED": {"QUARANTINED"},
    "EVICTED": set(),
    "QUARANTINED": set(),
}
LEASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
WORKLOAD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,255}$")
SYSTEMD_UNIT_RE = re.compile(r"^[A-Za-z0-9_.@:-]+\.(?:scope|service)$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
KNOWN_BACKENDS = {"process", "systemd-scope", "systemd-service", "podman", "docker", "containerd", "native"}


class LifecycleError(RuntimeError):
    pass


class IntegrityError(LifecycleError):
    pass


class StaleGenerationError(LifecycleError):
    pass


class BindingError(LifecycleError):
    pass


class TransitionError(LifecycleError):
    pass


class KeyringError(LifecycleError):
    pass


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_utc(value: dt.datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timezone-aware datetime required")
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return parsed.astimezone(dt.timezone.utc)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_boot_id(path: Path = Path("/proc/sys/kernel/random/boot_id")) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise BindingError("boot identity unavailable") from exc
    if not value:
        raise BindingError("boot identity is empty")
    return value


def _proc_starttime_ticks(pid: int, proc_root: Path = Path("/proc")) -> int:
    try:
        raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    except OSError as exc:
        raise BindingError("process identity unavailable") from exc
    close = raw.rfind(")")
    if close < 0:
        raise BindingError("malformed /proc stat")
    fields = raw[close + 2 :].split()
    if len(fields) < 20:
        raise BindingError("malformed /proc stat fields")
    try:
        return int(fields[19])
    except ValueError as exc:
        raise BindingError("invalid process start time") from exc


def capture_pid_subject(pid: int, *, proc_root: Path = Path("/proc"), boot_id: str | None = None) -> dict[str, Any]:
    if pid <= 0:
        raise BindingError("pid must be positive")
    return {
        "pid": pid,
        "starttime_ticks": _proc_starttime_ticks(pid, proc_root),
        "boot_id": boot_id or read_boot_id(),
    }


def _safe_relative(path: Path, root: Path) -> Path:
    root_abs = root.absolute()
    path_abs = path.absolute()
    try:
        return path_abs.relative_to(root_abs)
    except ValueError as exc:
        raise BindingError("path escapes cgroup root") from exc


def _reject_symlink_components(path: Path, root: Path) -> None:
    rel = _safe_relative(path, root)
    cursor = root.absolute()
    try:
        root_st = os.lstat(cursor)
    except OSError as exc:
        raise BindingError("cannot stat cgroup root") from exc
    if stat.S_ISLNK(root_st.st_mode) or not stat.S_ISDIR(root_st.st_mode):
        raise BindingError("invalid cgroup root")
    for part in rel.parts:
        cursor = cursor / part
        try:
            st = os.lstat(cursor)
        except OSError as exc:
            raise BindingError("cgroup path component unavailable") from exc
        if stat.S_ISLNK(st.st_mode):
            raise BindingError("symlink in cgroup path")


def capture_cgroup_identity(path: Path, *, cgroup_root: Path = Path("/sys/fs/cgroup")) -> dict[str, Any]:
    _reject_symlink_components(path, cgroup_root)
    try:
        st = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise BindingError("cgroup path unavailable") from exc
    if not stat.S_ISDIR(st.st_mode):
        raise BindingError("cgroup path is not a directory")
    rel = _safe_relative(path, cgroup_root)
    return {
        "path": "/" + str(rel) if str(rel) != "." else "/",
        "fs_dev": int(st.st_dev),
        "inode": int(st.st_ino),
        "owner_uid": int(st.st_uid),
    }


@dataclass(frozen=True)
class HMACKeyring:
    keys: Mapping[str, bytes]
    active_key_id: str
    scope: str = HMAC_SCOPE

    def __post_init__(self) -> None:
        if self.active_key_id not in self.keys:
            raise KeyringError("active HMAC key ID missing")
        if not self.scope:
            raise KeyringError("HMAC scope required")
        for key_id, secret in self.keys.items():
            if not key_id or not isinstance(secret, (bytes, bytearray)) or len(secret) < 32:
                raise KeyringError("HMAC keys require non-empty IDs and at least 256 bits")

    @classmethod
    def from_root_directory(
        cls,
        directory: Path,
        *,
        active_key_id: str,
        allowed_key_ids: Iterable[str] | None = None,
        require_euid_root: bool = True,
    ) -> "HMACKeyring":
        if require_euid_root and os.geteuid() != 0:
            raise KeyringError("HRB HMAC keyring may only be loaded inside root trust boundary")
        try:
            dst = os.lstat(directory)
        except OSError as exc:
            raise KeyringError("HMAC key directory unavailable") from exc
        if stat.S_ISLNK(dst.st_mode) or not stat.S_ISDIR(dst.st_mode):
            raise KeyringError("HMAC key directory must be a real directory")
        if dst.st_uid != 0 or (dst.st_mode & 0o077):
            raise KeyringError("HMAC key directory must be root-owned and owner-only")
        selected = set(allowed_key_ids or [active_key_id]) | {active_key_id}
        keys: dict[str, bytes] = {}
        for key_id in selected:
            if not LEASE_ID_RE.fullmatch(key_id):
                raise KeyringError("invalid HMAC key ID")
            path = directory / f"{key_id}.key"
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(path, flags)
            except OSError as exc:
                raise KeyringError(f"HMAC key unavailable: {key_id}") from exc
            try:
                st = os.fstat(fd)
                if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or (st.st_mode & 0o077):
                    raise KeyringError("HMAC key file ownership/mode invalid")
                secret = os.read(fd, 4096)
                if len(secret) > 1024:
                    raise KeyringError("HMAC key file too large")
                secret = secret.strip()
            finally:
                os.close(fd)
            if len(secret) < 32:
                raise KeyringError("HMAC key too short")
            keys[key_id] = secret
        return cls(keys=keys, active_key_id=active_key_id)

    def rotated(self, *, new_key_id: str, new_secret: bytes, retain_old: bool = True) -> "HMACKeyring":
        keys = dict(self.keys) if retain_old else {}
        keys[new_key_id] = bytes(new_secret)
        return HMACKeyring(keys=keys, active_key_id=new_key_id, scope=self.scope)

    def retire(self, key_id: str) -> "HMACKeyring":
        if key_id == self.active_key_id:
            raise KeyringError("active HMAC key cannot be retired")
        keys = dict(self.keys)
        keys.pop(key_id, None)
        return HMACKeyring(keys=keys, active_key_id=self.active_key_id, scope=self.scope)


def _auth_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(dict(record))
    payload.pop("authentication", None)
    return payload


def seal_record(record: Mapping[str, Any], keyring: HMACKeyring) -> dict[str, Any]:
    payload = _auth_payload(record)
    key = keyring.keys[keyring.active_key_id]
    mac = hmac.new(key, canonical_bytes(payload), hashlib.sha256).hexdigest()
    sealed = copy.deepcopy(payload)
    sealed["authentication"] = {
        "scheme": HMAC_SCHEME,
        "key_id": keyring.active_key_id,
        "scope": keyring.scope,
        "mac_hex": mac,
        "master_key_exposed": False,
    }
    return sealed


def verify_record(record: Mapping[str, Any], keyring: HMACKeyring) -> None:
    auth = record.get("authentication")
    if not isinstance(auth, dict):
        raise IntegrityError("lease authentication missing")
    if auth.get("scheme") != HMAC_SCHEME or auth.get("scope") != keyring.scope:
        raise IntegrityError("lease authentication scheme/scope mismatch")
    key_id = str(auth.get("key_id", ""))
    key = keyring.keys.get(key_id)
    if key is None:
        raise IntegrityError("lease HMAC key ID is unknown or retired")
    actual = str(auth.get("mac_hex", ""))
    expected = hmac.new(key, canonical_bytes(_auth_payload(record)), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(actual, expected):
        raise IntegrityError("lease HMAC verification failed")


