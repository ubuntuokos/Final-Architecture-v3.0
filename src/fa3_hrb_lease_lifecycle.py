#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import select
import signal
import socket
import stat
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

HRB_AUTHORITY_ID = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
EVIDENCE_AUTHORITY_ID = "FA3-AUTH-OBS-EVIDENCE-001"
TRUST_PROFILE_ID = "FA3-TRUST-PKI-001"
LEASE_SCHEMA = "fa3.hrb-lease-lifecycle.v1"
EVENT_SCHEMA = "fa3.hrb-lease-lifecycle-event.v1"
HMAC_ALG = "HMAC-SHA256"
HMAC_SCOPE = "HRB_INTERNAL_EPHEMERAL_LEASE_AUTH"
CGROUP_ROOT = Path("/sys/fs/cgroup")

STATES = (
    "ISSUED",
    "ACTIVE",
    "REVOKING",
    "EVICTING",
    "VERIFYING",
    "EVICTED",
    "EVICTION_FAILED",
    "QUARANTINED",
)
TRANSITIONS = {
    "ISSUED": {"ACTIVE", "REVOKING"},
    "ACTIVE": {"REVOKING"},
    "REVOKING": {"EVICTING", "EVICTION_FAILED"},
    "EVICTING": {"VERIFYING", "EVICTION_FAILED"},
    "VERIFYING": {"EVICTED", "EVICTION_FAILED"},
    "EVICTION_FAILED": {"QUARANTINED"},
    "EVICTED": set(),
    "QUARANTINED": set(),
}

REQUIRED_BINDING_FIELDS = {
    "lease_id",
    "generation",
    "workload_identity",
    "runtime_instance_identity",
    "host_attestation_digest",
    "cgroup_v2_identity",
    "pidfd_subject_reference",
    "systemd_unit_scope",
    "runtime_backend",
    "backend_instance_id",
    "accelerator_assignments",
    "execution_path",
    "issued_at_utc",
    "expires_at_utc",
    "ttl_seconds",
}
SUPPORTED_RUNTIME_BACKENDS = {"SYSTEMD_CGROUPV2_SCOPE", "PODMAN"}
FORBIDDEN_GPU_RESET_TOKENS = (
    "--gpu-reset",
    "nvidia-smi -r",
    "cudaDeviceReset",
    "hipDeviceReset",
)


class LeaseError(RuntimeError):
    pass


class LeaseIntegrityError(LeaseError):
    pass


class LeaseStateError(LeaseError):
    pass


class LeaseBindingError(LeaseError):
    pass


class StaleGenerationError(LeaseError):
    pass


class LeaseExpiredError(LeaseError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _without_authentication(lease: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in lease.items() if k != "authentication"}


def _proc_stat_fields(pid: int) -> list[str]:
    text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    close = text.rfind(")")
    if close < 0:
        raise LeaseBindingError("malformed /proc stat")
    fields = text[close + 2 :].split()
    if len(fields) < 20:
        raise LeaseBindingError("short /proc stat")
    return fields


def _proc_start_ticks(pid: int) -> int:
    return int(_proc_stat_fields(pid)[19])


def _proc_state(pid: int) -> str:
    return str(_proc_stat_fields(pid)[0])


def _cgroup_unpopulated(path: Path) -> bool:
    events = path / "cgroup.events"
    if events.is_file():
        values = {}
        for line in events.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2:
                values[parts[0]] = parts[1]
        if "populated" in values:
            return values["populated"] == "0"
    procs = path / "cgroup.procs"
    return procs.is_file() and not procs.read_text(encoding="utf-8").strip()


def _read_boot_id() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()


def _safe_cgroup_path(relative: str, root: Path = CGROUP_ROOT) -> Path:
    if not isinstance(relative, str) or not relative.startswith("/"):
        raise LeaseBindingError("cgroup path must be absolute within cgroup2 mount")
    root = root.resolve(strict=True)
    current = root
    for part in [p for p in relative.split("/") if p]:
        candidate = current / part
        try:
            st = candidate.lstat()
        except FileNotFoundError as exc:
            raise LeaseBindingError("cgroup path missing") from exc
        if stat.S_ISLNK(st.st_mode):
            raise LeaseBindingError("symlink in cgroup path")
        current = candidate
    resolved = current.resolve(strict=True)
    if resolved != root and root not in resolved.parents:
        raise LeaseBindingError("cgroup path escapes cgroup2 mount")
    return resolved


def validate_runtime_binding(binding: dict[str, Any]) -> None:
    if not isinstance(binding, dict):
        raise LeaseBindingError("runtime binding must be object")
    missing = REQUIRED_BINDING_FIELDS.difference(binding)
    if missing:
        raise LeaseBindingError("runtime binding missing: " + ",".join(sorted(missing)))
    if not isinstance(binding.get("lease_id"), str) or not binding["lease_id"]:
        raise LeaseBindingError("lease_id invalid")
    if not isinstance(binding.get("generation"), int) or binding["generation"] < 1:
        raise LeaseBindingError("generation invalid")
    for key in ("workload_identity", "runtime_instance_identity", "systemd_unit_scope", "runtime_backend", "backend_instance_id"):
        if not isinstance(binding.get(key), str) or not binding[key]:
            raise LeaseBindingError(f"{key} invalid")
    if binding["runtime_backend"] not in SUPPORTED_RUNTIME_BACKENDS:
        raise LeaseBindingError("unknown runtime backend")
    if binding["runtime_backend"] == "PODMAN" and not re.fullmatch(r"[0-9a-f]{64}", binding["backend_instance_id"]):
        raise LeaseBindingError("podman backend_instance_id must be immutable full container id")
    digest = str(binding.get("host_attestation_digest", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise LeaseBindingError("host attestation digest invalid")
    cg = binding.get("cgroup_v2_identity")
    if not isinstance(cg, dict) or not all(k in cg for k in ("path", "st_dev", "st_ino", "owner_uid", "owner_gid")):
        raise LeaseBindingError("cgroup identity incomplete")
    pidref = binding.get("pidfd_subject_reference")
    if not isinstance(pidref, dict) or not isinstance(pidref.get("pid"), int) or pidref["pid"] <= 0 or not isinstance(pidref.get("start_time_ticks"), int):
        raise LeaseBindingError("pidfd subject reference invalid")
    accels = binding.get("accelerator_assignments")
    if not isinstance(accels, list):
        raise LeaseBindingError("accelerator assignments must be list")
    for item in accels:
        if not isinstance(item, dict) or not str(item.get("stable_id", "")).strip():
            raise LeaseBindingError("accelerator assignment lacks stable device identity")
        mode = item.get("mode", "EXCLUSIVE")
        if mode not in {"EXCLUSIVE", "SHARED"}:
            raise LeaseBindingError("accelerator assignment mode invalid")
        if mode == "SHARED" and not str(item.get("share_group_id", "")).strip():
            raise LeaseBindingError("shared accelerator requires share_group_id")
    if not isinstance(binding.get("execution_path"), dict) or not binding["execution_path"]:
        raise LeaseBindingError("execution path invalid")
    ttl = binding.get("ttl_seconds")
    if not isinstance(ttl, (int, float)) or ttl <= 0:
        raise LeaseBindingError("ttl invalid")


@dataclass(frozen=True)
class LeaseKey:
    key_id: str
    secret: bytes
    scope: str = HMAC_SCOPE

    def __post_init__(self) -> None:
        if not self.key_id or len(self.secret) < 32 or self.scope != HMAC_SCOPE:
            raise ValueError("invalid HRB lease key")


class LeaseKeyring:
    """HRB-internal keyring. Production loading is root-only and never serialized."""

    def __init__(self, keys: list[LeaseKey], active_key_id: str):
        self._keys = {k.key_id: k for k in keys}
        if active_key_id not in self._keys:
            raise ValueError("active key missing")
        self._active_key_id = active_key_id
        self._lock = threading.RLock()

    @property
    def active_key_id(self) -> str:
        return self._active_key_id

    @classmethod
    def from_root_key_file(cls, path: Path) -> "LeaseKeyring":
        path = Path(path)
        st = path.lstat()
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            raise PermissionError("HRB key file must be regular and non-symlink")
        if st.st_uid != 0:
            raise PermissionError("HRB key file must be root-owned")
        if stat.S_IMODE(st.st_mode) & 0o077:
            raise PermissionError("HRB key file must not be group/world accessible")
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("scope") != HMAC_SCOPE:
            raise LeaseIntegrityError("HRB key scope mismatch")
        keys = []
        for item in doc.get("keys", []):
            if not isinstance(item, dict):
                raise LeaseIntegrityError("malformed key entry")
            raw = bytes.fromhex(str(item.get("secret_hex", "")))
            keys.append(LeaseKey(str(item.get("key_id", "")), raw, HMAC_SCOPE))
        return cls(keys, str(doc.get("active_key_id", "")))

    def sign(self, lease: dict[str, Any]) -> dict[str, str]:
        with self._lock:
            key = self._keys[self._active_key_id]
            mac = hmac.new(key.secret, _canonical(_without_authentication(lease)), hashlib.sha256).hexdigest()
            return {"alg": HMAC_ALG, "key_id": key.key_id, "scope": key.scope, "mac": mac}

    def verify(self, lease: dict[str, Any]) -> None:
        auth = lease.get("authentication")
        if not isinstance(auth, dict) or auth.get("alg") != HMAC_ALG or auth.get("scope") != HMAC_SCOPE:
            raise LeaseIntegrityError("lease authentication descriptor invalid")
        key_id = str(auth.get("key_id", ""))
        with self._lock:
            key = self._keys.get(key_id)
            if key is None:
                raise LeaseIntegrityError("unknown or retired lease key")
            expected = hmac.new(key.secret, _canonical(_without_authentication(lease)), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, str(auth.get("mac", ""))):
            raise LeaseIntegrityError("forged or corrupted lease MAC")

    def rotate(self, key: LeaseKey) -> None:
        with self._lock:
            self._keys[key.key_id] = key
            self._active_key_id = key.key_id

    def retire(self, key_id: str) -> None:
        with self._lock:
            if key_id == self._active_key_id:
                raise LeaseIntegrityError("cannot retire active lease key")
            self._keys.pop(key_id, None)


class SecretProjectionHook(Protocol):
    def revoke_and_zeroize(self, lease: dict[str, Any]) -> bool: ...


def _safe_projection_target(descriptor: dict[str, Any]) -> tuple[Path, os.stat_result]:
    if not isinstance(descriptor, dict):
        raise LeaseBindingError("projection zeroize descriptor must be object")
    raw = str(descriptor.get("path", ""))
    path = Path(raw)
    if not path.is_absolute():
        raise LeaseBindingError("projection target path must be absolute")
    run_root = Path("/run").resolve(strict=True)
    current = run_root
    try:
        rel = path.relative_to("/run")
    except ValueError as exc:
        raise LeaseBindingError("projection target must be below /run") from exc
    for part in rel.parts:
        candidate = current / part
        st = candidate.lstat()
        if stat.S_ISLNK(st.st_mode):
            raise LeaseBindingError("symlink in projection target path")
        current = candidate
    resolved = current.resolve(strict=True)
    if run_root not in resolved.parents:
        raise LeaseBindingError("projection target escapes /run")
    st = resolved.stat()
    expected = (
        int(descriptor.get("st_dev", -1)),
        int(descriptor.get("st_ino", -1)),
        int(descriptor.get("owner_uid", -1)),
        int(descriptor.get("owner_gid", -1)),
    )
    actual = (st.st_dev, st.st_ino, st.st_uid, st.st_gid)
    if expected != actual:
        raise LeaseBindingError("projection target identity changed")
    if not stat.S_ISREG(st.st_mode):
        raise LeaseBindingError("projection target must be a regular file")
    declared_size = int(descriptor.get("size", -1))
    if declared_size < 0 or declared_size != st.st_size or declared_size > 512 * 1024:
        raise LeaseBindingError("projection target size invalid")
    return resolved, st


def _zeroize_projection_target(descriptor: dict[str, Any]) -> None:
    path, expected_st = _safe_projection_target(descriptor)
    flags = os.O_WRONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        st = os.fstat(fd)
        if (st.st_dev, st.st_ino, st.st_uid, st.st_gid) != (
            expected_st.st_dev, expected_st.st_ino, expected_st.st_uid, expected_st.st_gid
        ):
            raise LeaseBindingError("projection target changed after open")
        remaining = st.st_size
        chunk = b"\x00" * min(65536, max(1, remaining))
        os.lseek(fd, 0, os.SEEK_SET)
        while remaining > 0:
            part = chunk if remaining >= len(chunk) else b"\x00" * remaining
            written = os.write(fd, part)
            if written <= 0:
                raise LeaseBindingError("projection zeroize short write")
            remaining -= written
        os.fsync(fd)
    finally:
        os.close(fd)
    post = path.lstat()
    if (post.st_dev, post.st_ino) != (expected_st.st_dev, expected_st.st_ino):
        raise LeaseBindingError("projection target substituted before unlink")
    path.unlink()


class SecretBrokerProjectionLifecycleHook:
    """Revoke only SecretProjectionLease handles; never revoke/delete the underlying credential object."""

    def __init__(
        self,
        socket_path: Path = Path("/run/fa3-secret-broker/broker.sock"),
        *,
        request_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.socket_path = Path(socket_path)
        self._request_fn = request_fn

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._request_fn is not None:
            return self._request_fn(payload)
        raw = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(self.socket_path))
            sock.sendall(raw)
            data = b""
            while not data.endswith(b"\n"):
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
                if len(data) > 1024 * 1024:
                    raise LeaseBindingError("oversized Secret Broker lifecycle response")
        response = json.loads(data)
        if not isinstance(response, dict):
            raise LeaseBindingError("invalid Secret Broker lifecycle response")
        return response

    def revoke_and_zeroize(self, lease: dict[str, Any]) -> bool:
        refs = lease.get("secret_projection_leases", [])
        if refs is None:
            refs = []
        if not isinstance(refs, list):
            return False
        runtime_digest = _sha256_hex(_canonical(lease.get("runtime_binding", {})))
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != {"projection_lease_id"}:
                return False
            projection_lease_id = str(ref.get("projection_lease_id", ""))
            if not re.fullmatch(r"spl-[0-9a-f]{32}", projection_lease_id):
                return False
            revoke = self._request({
                "op": "projection_revoke",
                "projection_lease_id": projection_lease_id,
                "hrb_lease_id": lease.get("lease_id"),
                "hrb_generation": lease.get("generation"),
                "runtime_binding_sha256": runtime_digest,
                "consumer_id": "FA3-HRB-LEASE-LIFECYCLE",
                "projection": "OPAQUE_SECRET_PROJECTION_LEASE",
            })
            if revoke.get("ok") is not True or revoke.get("state") != "REVOKED":
                return False
            target = revoke.get("zeroize_target")
            if target is not None:
                _zeroize_projection_target(target)
            ack = self._request({
                "op": "projection_zeroized",
                "projection_lease_id": projection_lease_id,
                "hrb_lease_id": lease.get("lease_id"),
                "hrb_generation": lease.get("generation"),
                "runtime_binding_sha256": runtime_digest,
                "consumer_id": "FA3-HRB-LEASE-LIFECYCLE",
                "projection": "OPAQUE_SECRET_PROJECTION_LEASE",
            })
            if ack.get("ok") is not True or ack.get("state") != "ZEROIZED":
                return False
        return True


class RuntimeAdapter(Protocol):
    backend: str
    def block_restart(self, binding: dict[str, Any]) -> bool: ...
    def verify_binding(self, binding: dict[str, Any]) -> tuple[bool, str]: ...
    def terminate(self, binding: dict[str, Any]) -> bool: ...
    def group_kill(self, binding: dict[str, Any]) -> str: ...
    def verify_dead(self, binding: dict[str, Any], timeout: float = 8.0) -> bool: ...
    def cleanup(self, binding: dict[str, Any]) -> bool: ...
    def release_resources(self, binding: dict[str, Any]) -> bool: ...


class RuntimeAdapterRegistry:
    def __init__(self, adapters: list[RuntimeAdapter]):
        self._adapters = {a.backend: a for a in adapters}

    def for_binding(self, binding: dict[str, Any]) -> RuntimeAdapter:
        backend = str(binding.get("runtime_backend", ""))
        adapter = self._adapters.get(backend)
        if adapter is None:
            raise LeaseBindingError("no admitted runtime adapter for backend")
        return adapter


class HashChainEvidenceSink:
    """Typed immutable handoff log; durable signature remains owned by existing Evidence/PKI authority."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        previous = self.events[-1]["event_sha256"] if self.events else "0" * 64
        event = {
            "schema": EVENT_SCHEMA,
            "authority": HRB_AUTHORITY_ID,
            "durable_signing_authority": EVIDENCE_AUTHORITY_ID,
            "trust_profile": TRUST_PROFILE_ID,
            "external_asymmetric_signature_required": True,
            "index": len(self.events),
            "previous_event_sha256": previous,
            **payload,
        }
        event["event_sha256"] = _sha256_hex(_canonical(event))
        self.events.append(event)
        return event

    def verify_chain(self) -> bool:
        previous = "0" * 64
        for index, item in enumerate(self.events):
            if item.get("index") != index or item.get("previous_event_sha256") != previous:
                return False
            supplied = item.get("event_sha256")
            raw = {k: v for k, v in item.items() if k != "event_sha256"}
            expected = _sha256_hex(_canonical(raw))
            if not hmac.compare_digest(str(supplied), expected):
                return False
            if item.get("durable_signing_authority") != EVIDENCE_AUTHORITY_ID or item.get("external_asymmetric_signature_required") is not True:
                return False
            previous = str(supplied)
        return True


class LeaseLedger:
    def __init__(
        self,
        keyring: LeaseKeyring,
        *,
        boot_id_reader: Callable[[], str] = _read_boot_id,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        wall_utc: Callable[[], str] = utc_now,
    ) -> None:
        self._keyring = keyring
        self._boot_id_reader = boot_id_reader
        self._monotonic_ns = monotonic_ns
        self._wall_utc = wall_utc
        self._records: dict[tuple[str, int], dict[str, Any]] = {}
        self._current: dict[str, int] = {}
        self._lock = threading.RLock()

    def _resign(self, record: dict[str, Any]) -> None:
        record["authentication"] = self._keyring.sign(record)

    def _transition(self, record: dict[str, Any], target: str) -> None:
        source = str(record.get("state", ""))
        if target not in TRANSITIONS.get(source, set()):
            raise LeaseStateError(f"forbidden lease transition {source}->{target}")
        if source == "EVICTING" and target == "ACTIVE":
            raise LeaseStateError("EVICTING generation can never become ACTIVE")
        record["state"] = target
        changed = self._wall_utc()
        record["state_changed_at_utc"] = changed
        record.setdefault("state_history", []).append({"state": target, "at_utc": changed})
        self._resign(record)

    def issue(
        self,
        binding_seed: dict[str, Any],
        ttl_seconds: float,
        lease_id: str | None = None,
        generation: int = 1,
        secret_projection_leases: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        if ttl_seconds <= 0:
            raise ValueError("ttl must be positive")
        lease_id = lease_id or f"lease-{os.urandom(12).hex()}"
        now_mono = self._monotonic_ns()
        issued = self._wall_utc()
        expires_epoch = time.time() + float(ttl_seconds)
        expires = datetime.fromtimestamp(expires_epoch, timezone.utc).isoformat().replace("+00:00", "Z")
        binding = dict(binding_seed)
        binding.update({
            "lease_id": lease_id,
            "generation": generation,
            "issued_at_utc": issued,
            "expires_at_utc": expires,
            "ttl_seconds": float(ttl_seconds),
        })
        validate_runtime_binding(binding)
        record = {
            "schema": LEASE_SCHEMA,
            "authority_id": HRB_AUTHORITY_ID,
            "lease_id": lease_id,
            "generation": generation,
            "state": "ISSUED",
            "state_history": [{"state": "ISSUED", "at_utc": issued}],
            "boot_id": self._boot_id_reader(),
            "issued_monotonic_ns": now_mono,
            "expires_monotonic_ns": now_mono + int(ttl_seconds * 1_000_000_000),
            "runtime_binding": binding,
            "secret_projection_leases": list(secret_projection_leases or []),
            "admission_restart_blocked": False,
            "record_retention": "IMMUTABLE_UNTIL_EVIDENCE_RETENTION_POLICY",
            "authentication": {},
        }
        with self._lock:
            key = (lease_id, generation)
            if key in self._records:
                raise LeaseStateError("lease generation already exists")
            self._resign(record)
            self._records[key] = record
            self._current[lease_id] = generation
        return json.loads(json.dumps(record))

    def activate(self, lease_id: str, generation: int) -> dict[str, Any]:
        with self._lock:
            record = self._require_current(lease_id, generation)
            self._keyring.verify(record)
            self._transition(record, "ACTIVE")
            return json.loads(json.dumps(record))

    def _require_current(self, lease_id: str, generation: int) -> dict[str, Any]:
        if self._current.get(lease_id) != generation:
            raise StaleGenerationError("stale lease generation")
        try:
            return self._records[(lease_id, generation)]
        except KeyError as exc:
            raise LeaseError("lease generation not found") from exc

    def get(self, lease_id: str, generation: int) -> dict[str, Any]:
        with self._lock:
            record = self._records.get((lease_id, generation))
            if record is None:
                raise LeaseError("lease generation not found")
            return json.loads(json.dumps(record))

    def assert_current_valid(self, lease_id: str, generation: int, *, allow_expired: bool = False) -> dict[str, Any]:
        with self._lock:
            record = self._require_current(lease_id, generation)
            self._keyring.verify(record)
            if record.get("boot_id") != self._boot_id_reader():
                raise LeaseExpiredError("boot identity changed; lease cannot survive reboot")
            if not allow_expired and self._monotonic_ns() >= int(record.get("expires_monotonic_ns", 0)):
                raise LeaseExpiredError("lease expired")
            return record

    def renew(self, lease_id: str, generation: int, ttl_seconds: float) -> dict[str, Any]:
        with self._lock:
            current = self.assert_current_valid(lease_id, generation)
            if current.get("state") != "ACTIVE":
                raise LeaseStateError("only current ACTIVE lease can renew")
            seed = {
                k: v for k, v in current["runtime_binding"].items()
                if k not in {"lease_id", "generation", "issued_at_utc", "expires_at_utc", "ttl_seconds"}
            }
            new_generation = generation + 1
            new_record = self.issue(seed, ttl_seconds, lease_id=lease_id, generation=new_generation)
            old = self._records[(lease_id, generation)]
            old["state"] = "REVOKING"
            old["superseded_by_generation"] = new_generation
            changed = self._wall_utc()
            old["state_changed_at_utc"] = changed
            old.setdefault("state_history", []).append({"state": "REVOKING", "at_utc": changed, "reason": "RENEWAL_SUPERSEDED"})
            self._resign(old)
            activated = self._records[(lease_id, new_generation)]
            self._transition(activated, "ACTIVE")
            return json.loads(json.dumps(activated))

    def attach_secret_projection_lease(self, lease_id: str, generation: int, projection_lease_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"spl-[0-9a-f]{32}", projection_lease_id):
            raise LeaseBindingError("invalid opaque SecretProjectionLease id")
        with self._lock:
            record = self.assert_current_valid(lease_id, generation)
            if record.get("state") != "ACTIVE":
                raise LeaseStateError("SecretProjectionLease may attach only to current ACTIVE generation")
            refs = record.setdefault("secret_projection_leases", [])
            if any(x.get("projection_lease_id") == projection_lease_id for x in refs if isinstance(x, dict)):
                return json.loads(json.dumps(record))
            refs.append({"projection_lease_id": projection_lease_id})
            self._resign(record)
            return json.loads(json.dumps(record))

    def begin_revoke(self, lease_id: str, generation: int) -> dict[str, Any]:
        with self._lock:
            record = self._require_current(lease_id, generation)
            self._keyring.verify(record)
            if record["state"] in {"ISSUED", "ACTIVE"}:
                self._transition(record, "REVOKING")
            elif record["state"] != "REVOKING":
                raise LeaseStateError("lease cannot enter revoke from current state")
            record["admission_restart_blocked"] = True
            self._resign(record)
            return record

    def fail_and_quarantine(self, record: dict[str, Any], reason: str) -> None:
        if record["state"] not in {"REVOKING", "EVICTING", "VERIFYING"}:
            raise LeaseStateError("failure transition outside eviction path")
        self._transition(record, "EVICTION_FAILED")
        record["failure_reason"] = reason
        self._resign(record)
        self._transition(record, "QUARANTINED")

    def evict(
        self,
        lease_id: str,
        generation: int,
        *,
        secret_hook: SecretProjectionHook,
        adapters: RuntimeAdapterRegistry,
        evidence: HashChainEvidenceSink,
    ) -> dict[str, Any]:
        with self._lock:
            record = self.begin_revoke(lease_id, generation)
            binding = record["runtime_binding"]
            adapter = adapters.for_binding(binding)
            failures: list[str] = []

            if not adapter.block_restart(binding):
                self.fail_and_quarantine(record, "SYSTEMD_RESTART_BLOCK_FAILED")
                event = evidence.append(self._event(record, failures + ["SYSTEMD_RESTART_BLOCK_FAILED"]))
                record["final_evidence_event_sha256"] = event["event_sha256"]
                self._resign(record)
                return json.loads(json.dumps(record))

            try:
                if not secret_hook.revoke_and_zeroize(json.loads(json.dumps(record))):
                    failures.append("SECRET_REVOKE_OR_ZEROIZE_FAILED")
            except Exception:
                failures.append("SECRET_REVOKE_OR_ZEROIZE_FAILED")

            ok, reason = adapter.verify_binding(binding)
            if not ok:
                self.fail_and_quarantine(record, "RUNTIME_BINDING_MISMATCH:" + reason)
                event = evidence.append(self._event(record, failures + ["RUNTIME_BINDING_MISMATCH:" + reason]))
                record["final_evidence_event_sha256"] = event["event_sha256"]
                self._resign(record)
                return json.loads(json.dumps(record))

            self._transition(record, "EVICTING")
            try:
                if not adapter.terminate(binding):
                    failures.append("SYSTEMD_TERMINATION_FAILED")
                record["group_kill_method"] = adapter.group_kill(binding)
            except Exception as exc:
                failures.append("RUNTIME_TERMINATION_FAILURE:" + type(exc).__name__)

            self._transition(record, "VERIFYING")
            dead = False
            try:
                dead = adapter.verify_dead(binding)
            except Exception:
                dead = False
            if not dead:
                failures.append("PIDFD_OR_CGROUP_DEATH_VERIFICATION_FAILED")

            cleanup_ok = False
            release_ok = False
            if dead:
                try:
                    cleanup_ok = adapter.cleanup(binding)
                except Exception:
                    cleanup_ok = False
                if not cleanup_ok:
                    failures.append("RUNTIME_ADAPTER_CLEANUP_FAILED")
                try:
                    release_ok = adapter.release_resources(binding)
                except Exception:
                    release_ok = False
                if not release_ok:
                    failures.append("RESOURCE_RELEASE_FAILED")

            if failures:
                self.fail_and_quarantine(record, "|".join(failures))
            else:
                self._transition(record, "EVICTED")

            event = evidence.append(self._event(record, failures))
            record["final_evidence_event_sha256"] = event["event_sha256"]
            self._resign(record)
            return json.loads(json.dumps(record))

    @staticmethod
    def _event(record: dict[str, Any], failures: list[str]) -> dict[str, Any]:
        return {
            "event_type": "HRB_LEASE_EVICTION_FINAL",
            "lease_id": record["lease_id"],
            "generation": record["generation"],
            "state": record["state"],
            "runtime_binding_sha256": _sha256_hex(_canonical(record["runtime_binding"])),
            "failures": list(failures),
            "lease_record_deleted": False,
            "hmac_is_durable_evidence_signature": False,
            "timestamp_utc": utc_now(),
        }


class SystemdCgroupV2ScopeAdapter:
    backend = "SYSTEMD_CGROUPV2_SCOPE"

    def __init__(self, *, user_manager: bool = True) -> None:
        self.user_manager = user_manager
        self._pidfds: dict[str, int] = {}

    def _systemctl(self, *args: str) -> subprocess.CompletedProcess[str]:
        cmd = ["systemctl"]
        if self.user_manager:
            cmd.append("--user")
        cmd.extend(args)
        return subprocess.run(cmd, text=True, capture_output=True, check=False)

    def block_restart(self, binding: dict[str, Any]) -> bool:
        unit = binding["systemd_unit_scope"]
        return unit.endswith(".scope") and binding["backend_instance_id"] == unit

    def verify_binding(self, binding: dict[str, Any]) -> tuple[bool, str]:
        try:
            validate_runtime_binding(binding)
            cg = binding["cgroup_v2_identity"]
            path = _safe_cgroup_path(cg["path"])
            st = path.stat()
            if (st.st_dev, st.st_ino, st.st_uid, st.st_gid) != (
                int(cg["st_dev"]), int(cg["st_ino"]), int(cg["owner_uid"]), int(cg["owner_gid"])
            ):
                return False, "CGROUP_SUBSTITUTION_OR_OWNERSHIP_CHANGE"
            pidref = binding["pidfd_subject_reference"]
            pid = int(pidref["pid"])
            if _proc_start_ticks(pid) != int(pidref["start_time_ticks"]):
                return False, "PID_REUSE"
            proc = self._systemctl("show", binding["systemd_unit_scope"], "--property=ControlGroup", "--value")
            if proc.returncode != 0 or proc.stdout.strip() != cg["path"]:
                return False, "SYSTEMD_SCOPE_CGROUP_MISMATCH"
            pids = {int(x) for x in (path / "cgroup.procs").read_text().split() if x.strip()}
            if pid not in pids:
                return False, "PID_NOT_IN_BOUND_CGROUP"
            self._pidfds[binding["runtime_instance_identity"]] = os.pidfd_open(pid, 0)
            return True, "BOUND"
        except Exception as exc:
            return False, type(exc).__name__

    def terminate(self, binding: dict[str, Any]) -> bool:
        proc = self._systemctl("kill", "--kill-whom=all", "--signal=TERM", binding["systemd_unit_scope"])
        return proc.returncode == 0

    def group_kill(self, binding: dict[str, Any]) -> str:
        try:
            path = _safe_cgroup_path(binding["cgroup_v2_identity"]["path"])
        except LeaseBindingError:
            pid = int(binding["pidfd_subject_reference"]["pid"])
            try:
                current_start = _proc_start_ticks(pid)
            except Exception:
                return "CGROUP_ALREADY_DEAD_AFTER_SYSTEMD_TERMINATION"
            if current_start != int(binding["pidfd_subject_reference"]["start_time_ticks"]):
                return "CGROUP_ALREADY_DEAD_AFTER_SYSTEMD_TERMINATION"
            raise
        kill_file = path / "cgroup.kill"
        if kill_file.is_file() and os.access(kill_file, os.W_OK):
            kill_file.write_text("1\n", encoding="ascii")
            return "CGROUP_V2_CGROUP_KILL"
        proc = self._systemctl("kill", "--kill-whom=all", "--signal=KILL", binding["systemd_unit_scope"])
        if proc.returncode != 0:
            try:
                if not (path / "cgroup.procs").read_text().strip():
                    return "CGROUP_ALREADY_DEAD_AFTER_SYSTEMD_TERMINATION"
            except Exception:
                pass
            raise LeaseBindingError("group-level kill failed")
        return "SYSTEMD_KILL_ALL_CGROUP_SCOPE"

    def verify_dead(self, binding: dict[str, Any], timeout: float = 8.0) -> bool:
        ident = binding["runtime_instance_identity"]
        fd = self._pidfds.get(ident)
        pidref = binding["pidfd_subject_reference"]
        pid = int(pidref["pid"])
        expected_start = int(pidref["start_time_ticks"])
        deadline = time.monotonic() + timeout

        poller = None
        if fd is not None:
            try:
                poller = select.poll()
                poller.register(fd, select.POLLIN | select.POLLHUP | select.POLLERR)
            except Exception:
                poller = None

        try:
            while time.monotonic() < deadline:
                pid_dead = False
                if poller is not None:
                    try:
                        pid_dead = bool(poller.poll(0))
                    except Exception:
                        pid_dead = False

                if not pid_dead:
                    try:
                        current_start = _proc_start_ticks(pid)
                        if current_start != expected_start:
                            pid_dead = True
                        elif _proc_state(pid) == "Z":
                            pid_dead = True
                    except Exception:
                        pid_dead = True

                try:
                    path = _safe_cgroup_path(binding["cgroup_v2_identity"]["path"])
                    cgroup_dead = _cgroup_unpopulated(path)
                except LeaseBindingError:
                    cgroup_dead = True

                if pid_dead and cgroup_dead:
                    return True
                time.sleep(0.05)
            return False
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                self._pidfds.pop(ident, None)

    def cleanup(self, binding: dict[str, Any]) -> bool:
        proc = self._systemctl("reset-failed", binding["systemd_unit_scope"])
        return proc.returncode in {0, 1, 5}

    def release_resources(self, binding: dict[str, Any]) -> bool:
        return True


def capture_systemd_scope_binding(
    *,
    lease_id: str,
    generation: int,
    workload_identity: str,
    unit_scope: str,
    host_attestation_digest: str,
    accelerator_assignments: list[dict[str, Any]] | None = None,
    user_manager: bool = True,
) -> dict[str, Any]:
    cmd = ["systemctl"]
    if user_manager:
        cmd.append("--user")
    cmd += ["show", unit_scope, "--property=ControlGroup", "--value"]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise LeaseBindingError("cannot resolve transient scope cgroup")
    relative = proc.stdout.strip()
    path = _safe_cgroup_path(relative)
    pids = [int(x) for x in (path / "cgroup.procs").read_text().split() if x.strip()]
    if not pids:
        raise LeaseBindingError("scope has no subject process")
    subject = None
    for pid in pids:
        try:
            comm = Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if comm in {"sleep", "python", "python3", "sh", "bash"}:
            subject = pid
            break
    if subject is None:
        subject = pids[-1]
    st = path.stat()
    start = _proc_start_ticks(subject)
    runtime_instance_identity = f"pid:{subject}:start:{start}:cgroup:{st.st_ino}"
    return {
        "lease_id": lease_id,
        "generation": generation,
        "workload_identity": workload_identity,
        "runtime_instance_identity": runtime_instance_identity,
        "host_attestation_digest": host_attestation_digest,
        "cgroup_v2_identity": {
            "path": relative,
            "st_dev": st.st_dev,
            "st_ino": st.st_ino,
            "owner_uid": st.st_uid,
            "owner_gid": st.st_gid,
        },
        "pidfd_subject_reference": {"pid": subject, "start_time_ticks": start},
        "systemd_unit_scope": unit_scope,
        "runtime_backend": "SYSTEMD_CGROUPV2_SCOPE",
        "backend_instance_id": unit_scope,
        "accelerator_assignments": list(accelerator_assignments or []),
        "execution_path": {
            "systemd_manager": "USER" if user_manager else "SYSTEM",
            "cgroup_version": 2,
            "pidfd_required": True,
            "group_kill_required": True,
        },
        "issued_at_utc": utc_now(),
        "expires_at_utc": utc_now(),
        "ttl_seconds": 1.0,
    }
