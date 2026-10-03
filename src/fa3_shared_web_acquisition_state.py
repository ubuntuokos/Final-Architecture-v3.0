"""Provider-neutral shared web acquisition state reference core.

This module is deliberately non-authoritative. It models durable request/session
state and deterministic recovery semantics. Browser mutation remains owned by
FA3-BROWSER-ACTION-RUNTIME-001 and physical resource admission remains owned by
the Host Resource Broker.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import urlsplit


class AcquisitionStateError(ValueError):
    """Fail-closed state transition error."""


class Backend(str, Enum):
    HTTP = "HTTP"
    BROWSER = "BROWSER"


class RequestStatus(str, Enum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    RETRY_WAIT = "RETRY_WAIT"
    HANDLED = "HANDLED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AcquisitionRequest:
    request_id: str
    url: str
    dedupe_key: str
    backend: Backend
    policy_revision: str
    provenance_ref: str
    max_attempts: int = 3

    @property
    def origin(self) -> str:
        parts = urlsplit(self.url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise AcquisitionStateError("UNSUPPORTED_OR_INVALID_URL")
        return f"{parts.scheme.lower()}://{parts.netloc.lower()}"


@dataclass
class RequestRecord:
    request: AcquisitionRequest
    status: RequestStatus = RequestStatus.PENDING
    attempts: int = 0
    lease_owner: str | None = None
    lease_expires_at: int | None = None
    lease_generation: int = 0
    next_eligible_at: int = 0
    result_digest: str | None = None
    failure_code: str | None = None


@dataclass(frozen=True)
class RecoveryReceipt:
    request_id: str
    previous_owner: str
    expired_at: int
    recovered_at: int
    lease_generation: int
    action: str = "REQUEUE_EXPIRED_CLAIM"


@dataclass(frozen=True)
class AcquisitionResult:
    request_id: str
    backend: Backend
    status_code: int
    content_digest: str
    provenance_ref: str
    policy_revision: str


@dataclass
class SessionRecord:
    session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    generation: int = 1
    replacement_of: str | None = None


@dataclass(frozen=True)
class OriginPolicy:
    origin: str
    robots_allowed: bool
    min_interval_ms: int
    max_parallel_advisory: int

    def __post_init__(self) -> None:
        if self.min_interval_ms < 0 or self.max_parallel_advisory < 1:
            raise AcquisitionStateError("INVALID_ORIGIN_POLICY")


class AcquisitionStateStore:
    """Deterministic reference state store.

    Time is supplied by the caller as integer milliseconds so tests and durable
    recovery do not depend on wall-clock behavior.
    """

    SNAPSHOT_SCHEMA = "fa3.shared-web-acquisition-state.snapshot.v1"

    def __init__(self) -> None:
        self._records: dict[str, RequestRecord] = {}
        self._dedupe: dict[str, str] = {}
        self._sessions: dict[str, SessionRecord] = {}
        self._origin_last_start: dict[str, int] = {}

    def enqueue(self, request: AcquisitionRequest) -> RequestRecord:
        self._validate_request(request)
        existing_id = self._dedupe.get(request.dedupe_key)
        if existing_id is not None:
            existing = self._records[existing_id]
            if existing.request != request:
                raise AcquisitionStateError("DEDUPE_KEY_IDENTITY_CONFLICT")
            return existing
        if request.request_id in self._records:
            raise AcquisitionStateError("REQUEST_ID_ALREADY_EXISTS")
        rec = RequestRecord(request=request)
        self._records[request.request_id] = rec
        self._dedupe[request.dedupe_key] = request.request_id
        return rec

    def claim(
        self,
        request_id: str,
        worker_id: str,
        *,
        now_ms: int,
        lease_ms: int,
        origin_policy: OriginPolicy,
    ) -> RequestRecord:
        if not worker_id or lease_ms <= 0:
            raise AcquisitionStateError("INVALID_CLAIM")
        rec = self._get(request_id)
        self._recover_one_if_expired(rec, now_ms)
        if rec.status not in (RequestStatus.PENDING, RequestStatus.RETRY_WAIT):
            raise AcquisitionStateError("REQUEST_NOT_CLAIMABLE")
        if now_ms < rec.next_eligible_at:
            raise AcquisitionStateError("REQUEST_RETRY_NOT_YET_ELIGIBLE")
        if rec.request.origin != origin_policy.origin.lower():
            raise AcquisitionStateError("ORIGIN_POLICY_MISMATCH")
        if not origin_policy.robots_allowed:
            rec.status = RequestStatus.BLOCKED
            rec.failure_code = "ROBOTS_POLICY_DENIED"
            raise AcquisitionStateError("ROBOTS_POLICY_DENIED")
        last = self._origin_last_start.get(rec.request.origin)
        if last is not None and now_ms - last < origin_policy.min_interval_ms:
            raise AcquisitionStateError("ORIGIN_POLITENESS_DELAY")
        rec.status = RequestStatus.CLAIMED
        rec.lease_owner = worker_id
        rec.lease_expires_at = now_ms + lease_ms
        rec.lease_generation += 1
        rec.attempts += 1
        self._origin_last_start[rec.request.origin] = now_ms
        return rec

    def extend_lease(
        self, request_id: str, worker_id: str, *, now_ms: int, extension_ms: int
    ) -> RequestRecord:
        if extension_ms <= 0:
            raise AcquisitionStateError("INVALID_LEASE_EXTENSION")
        rec = self._get(request_id)
        self._assert_live_owner(rec, worker_id, now_ms)
        assert rec.lease_expires_at is not None
        rec.lease_expires_at += extension_ms
        return rec

    def complete(
        self, request_id: str, worker_id: str, result: AcquisitionResult, *, now_ms: int
    ) -> RequestRecord:
        rec = self._get(request_id)
        self._assert_live_owner(rec, worker_id, now_ms)
        if result.request_id != request_id:
            raise AcquisitionStateError("RESULT_REQUEST_ID_MISMATCH")
        if result.backend != rec.request.backend:
            raise AcquisitionStateError("BACKEND_PARITY_BINDING_MISMATCH")
        if result.provenance_ref != rec.request.provenance_ref:
            raise AcquisitionStateError("PROVENANCE_BINDING_MISMATCH")
        if result.policy_revision != rec.request.policy_revision:
            raise AcquisitionStateError("POLICY_BINDING_MISMATCH")
        if not result.content_digest:
            raise AcquisitionStateError("RESULT_DIGEST_REQUIRED")
        rec.status = RequestStatus.HANDLED
        rec.result_digest = result.content_digest
        rec.failure_code = None
        self._clear_lease(rec)
        return rec

    def fail(
        self,
        request_id: str,
        worker_id: str,
        *,
        now_ms: int,
        failure_code: str,
        retryable: bool,
        retry_after_ms: int = 0,
    ) -> RequestRecord:
        if not failure_code or retry_after_ms < 0:
            raise AcquisitionStateError("INVALID_FAILURE")
        rec = self._get(request_id)
        self._assert_live_owner(rec, worker_id, now_ms)
        rec.failure_code = failure_code
        self._clear_lease(rec)
        if retryable and rec.attempts < rec.request.max_attempts:
            rec.status = RequestStatus.RETRY_WAIT
            rec.next_eligible_at = now_ms + retry_after_ms
        else:
            rec.status = RequestStatus.FAILED
        return rec

    def recover_expired(self, *, now_ms: int) -> list[RecoveryReceipt]:
        receipts: list[RecoveryReceipt] = []
        for rec in self._records.values():
            receipt = self._recover_one_if_expired(rec, now_ms)
            if receipt is not None:
                receipts.append(receipt)
        return sorted(receipts, key=lambda r: r.request_id)

    def session_create(self, session_id: str, *, replacement_of: str | None = None) -> SessionRecord:
        if not session_id or session_id in self._sessions:
            raise AcquisitionStateError("SESSION_ID_INVALID_OR_EXISTS")
        generation = 1
        if replacement_of is not None:
            old = self._sessions.get(replacement_of)
            if old is None or old.status not in (SessionStatus.RETIRED, SessionStatus.BLOCKED):
                raise AcquisitionStateError("SESSION_REPLACEMENT_SOURCE_NOT_RETIRED")
            generation = old.generation + 1
        row = SessionRecord(session_id=session_id, generation=generation, replacement_of=replacement_of)
        self._sessions[session_id] = row
        return row

    def session_retire(self, session_id: str, *, blocked: bool = False) -> SessionRecord:
        row = self._sessions.get(session_id)
        if row is None:
            raise AcquisitionStateError("SESSION_NOT_FOUND")
        row.status = SessionStatus.BLOCKED if blocked else SessionStatus.RETIRED
        return row

    def hrb_load_observation(self) -> dict[str, Any]:
        claimed = sum(r.status == RequestStatus.CLAIMED for r in self._records.values())
        pending = sum(
            r.status in (RequestStatus.PENDING, RequestStatus.RETRY_WAIT)
            for r in self._records.values()
        )
        return {
            "schema": "fa3.shared-web-acquisition-state.hrb-observation.v1",
            "advisory_only": True,
            "claimed_requests": claimed,
            "pending_requests": pending,
            "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "may_change_concurrency": False,
        }

    def snapshot(self) -> str:
        body = {
            "schema": self.SNAPSHOT_SCHEMA,
            "requests": [
                {
                    **asdict(rec),
                    "request": {
                        **asdict(rec.request),
                        "backend": rec.request.backend.value,
                    },
                    "status": rec.status.value,
                }
                for rec in sorted(self._records.values(), key=lambda r: r.request.request_id)
            ],
            "sessions": [
                {**asdict(s), "status": s.status.value}
                for s in sorted(self._sessions.values(), key=lambda s: s.session_id)
            ],
            "origin_last_start": dict(sorted(self._origin_last_start.items())),
        }
        return json.dumps(body, sort_keys=True, separators=(",", ":"))

    def save_atomic(self, path: str | Path) -> None:
        """Persist one complete snapshot with same-directory atomic replacement."""
        target = Path(path)
        parent = target.parent
        if not parent.is_dir():
            raise AcquisitionStateError("STATE_DIRECTORY_NOT_FOUND")
        temp_path: Path | None = None
        payload = (self.snapshot() + "\n").encode("utf-8")
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, target)
        except OSError as exc:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise AcquisitionStateError("ATOMIC_STATE_WRITE_FAILED") from exc

    @classmethod
    def load_file(cls, path: str | Path) -> "AcquisitionStateStore":
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise AcquisitionStateError("STATE_FILE_READ_FAILED") from exc
        return cls.from_snapshot(raw)

    @classmethod
    def from_snapshot(cls, raw: str) -> "AcquisitionStateStore":
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AcquisitionStateError("SNAPSHOT_JSON_INVALID") from exc
        if body.get("schema") != cls.SNAPSHOT_SCHEMA:
            raise AcquisitionStateError("SNAPSHOT_SCHEMA_INVALID")
        store = cls()
        for item in body.get("requests", []):
            req = item["request"]
            request = AcquisitionRequest(
                request_id=req["request_id"],
                url=req["url"],
                dedupe_key=req["dedupe_key"],
                backend=Backend(req["backend"]),
                policy_revision=req["policy_revision"],
                provenance_ref=req["provenance_ref"],
                max_attempts=req["max_attempts"],
            )
            store._validate_request(request)
            rec = RequestRecord(
                request=request,
                status=RequestStatus(item["status"]),
                attempts=item["attempts"],
                lease_owner=item["lease_owner"],
                lease_expires_at=item["lease_expires_at"],
                lease_generation=item["lease_generation"],
                next_eligible_at=item["next_eligible_at"],
                result_digest=item["result_digest"],
                failure_code=item["failure_code"],
            )
            if request.request_id in store._records or request.dedupe_key in store._dedupe:
                raise AcquisitionStateError("SNAPSHOT_DUPLICATE_REQUEST")
            store._records[request.request_id] = rec
            store._dedupe[request.dedupe_key] = request.request_id
        for item in body.get("sessions", []):
            sid = item["session_id"]
            if sid in store._sessions:
                raise AcquisitionStateError("SNAPSHOT_DUPLICATE_SESSION")
            store._sessions[sid] = SessionRecord(
                session_id=sid,
                status=SessionStatus(item["status"]),
                generation=item["generation"],
                replacement_of=item["replacement_of"],
            )
        origin_last = body.get("origin_last_start", {})
        if not isinstance(origin_last, dict) or any(
            not isinstance(v, int) for v in origin_last.values()
        ):
            raise AcquisitionStateError("SNAPSHOT_ORIGIN_STATE_INVALID")
        store._origin_last_start = {str(k): int(v) for k, v in origin_last.items()}
        return store

    @staticmethod
    def content_digest(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def get(self, request_id: str) -> RequestRecord:
        return self._get(request_id)

    def _get(self, request_id: str) -> RequestRecord:
        try:
            return self._records[request_id]
        except KeyError as exc:
            raise AcquisitionStateError("REQUEST_NOT_FOUND") from exc

    @staticmethod
    def _validate_request(request: AcquisitionRequest) -> None:
        if not request.request_id or not request.dedupe_key:
            raise AcquisitionStateError("REQUEST_IDENTITY_REQUIRED")
        if not request.policy_revision or not request.provenance_ref:
            raise AcquisitionStateError("POLICY_AND_PROVENANCE_REQUIRED")
        if request.max_attempts < 1:
            raise AcquisitionStateError("MAX_ATTEMPTS_INVALID")
        _ = request.origin

    @staticmethod
    def _clear_lease(rec: RequestRecord) -> None:
        rec.lease_owner = None
        rec.lease_expires_at = None

    @staticmethod
    def _assert_live_owner(rec: RequestRecord, worker_id: str, now_ms: int) -> None:
        if rec.status != RequestStatus.CLAIMED or rec.lease_owner != worker_id:
            raise AcquisitionStateError("LEASE_OWNER_MISMATCH")
        if rec.lease_expires_at is None or now_ms >= rec.lease_expires_at:
            raise AcquisitionStateError("LEASE_EXPIRED")

    def _recover_one_if_expired(
        self, rec: RequestRecord, now_ms: int
    ) -> RecoveryReceipt | None:
        if rec.status != RequestStatus.CLAIMED or rec.lease_expires_at is None:
            return None
        if now_ms < rec.lease_expires_at:
            return None
        owner = rec.lease_owner or ""
        expired = rec.lease_expires_at
        generation = rec.lease_generation
        rec.status = RequestStatus.PENDING
        rec.failure_code = "LEASE_EXPIRED_REQUEUED"
        self._clear_lease(rec)
        return RecoveryReceipt(
            request_id=rec.request.request_id,
            previous_owner=owner,
            expired_at=expired,
            recovered_at=now_ms,
            lease_generation=generation,
        )
