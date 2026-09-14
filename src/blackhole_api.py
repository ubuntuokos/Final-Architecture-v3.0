#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

API_ID = "FA3-BLACKHOLE-API-001"
SCHEMA_VERSION = "fa3.blackhole.request.v3"
MANDATORY_FEATURES = frozenset({"cuda", "nvenc", "onnxruntime-gpu", "zero-copy"})
ALLOWED_FEATURES = MANDATORY_FEATURES
LEASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

MODEL_POLICY = {
    "FA3-MODEL-MEDIA-ENHANCER-V3": {
        "internal_model_ref": "media_enhancer_v3",
        "operation": "neural_media_enhance",
    }
}
OUTPUT_PROFILES = {"1080p-h264"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Requirements(StrictModel):
    minimum_tu: float = Field(gt=0.0, le=1024.0)
    required_features: list[Literal["cuda", "nvenc", "onnxruntime-gpu", "zero-copy"]]

    @field_validator("required_features")
    @classmethod
    def features_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("required_features must not contain duplicates")
        return value


class PipelineIntent(StrictModel):
    operation: Literal["neural_media_enhance"]
    model_id: str = Field(min_length=1, max_length=128, pattern=r"^FA3-MODEL-[A-Z0-9._-]+$")
    input_asset_id: str = Field(min_length=1, max_length=160, pattern=r"^FA3-ASSET-[A-Za-z0-9._-]+$")
    output_profile: Literal["1080p-h264"]


class BlackholeSubmitRequest(StrictModel):
    schema_version: Literal["fa3.blackhole.request.v3"]
    request_id: str = Field(min_length=36, max_length=36)
    lease_id: str = Field(min_length=1, max_length=128)
    requirements: Requirements
    pipeline: PipelineIntent

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        try:
            return str(UUID(value))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("request_id must be a UUID") from exc

    @field_validator("lease_id")
    @classmethod
    def validate_lease_id(cls, value: str) -> str:
        if not LEASE_ID_RE.fullmatch(value):
            raise ValueError("lease_id contains forbidden characters")
        return value


class JobReceipt(StrictModel):
    job_id: str
    state: Literal["ACCEPTED"]
    request_id: str
    status_uri: str
    idempotent_replay: bool = False


class Authenticator(Protocol):
    def authenticate(self, authorization: str | None) -> str: ...


class LeaseVerifier(Protocol):
    def verify(
        self,
        lease_id: str,
        *,
        minimum_tu: float,
        required_features: set[str],
    ) -> dict[str, Any]: ...


class AuthenticationDenied(PermissionError):
    pass


class LeaseDenied(PermissionError):
    pass


class ReplayConflict(RuntimeError):
    pass


class PolicyDenied(PermissionError):
    pass


@dataclass(frozen=True)
class Settings:
    token_vault_path: Path
    principal: str
    lease_dir: Path
    hrb_bin: Path
    db_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            token_vault_path=Path(os.environ.get("FA3_BLACKHOLE_TOKEN_VAULT", "/run/secrets/fa3-blackhole-vault.json")),
            principal=os.environ.get("FA3_BLACKHOLE_PRINCIPAL", "FA3-MARKETING-STUDIO"),
            lease_dir=Path(os.environ.get("FA3_HRB_LEASE_DIR", "/run/fa3/hrb/leases")),
            hrb_bin=Path(os.environ.get("FA3_HRB_BIN", "/usr/local/bin/fa3-host-resource-broker")),
            db_path=Path(os.environ.get("FA3_BLACKHOLE_DB", "/var/lib/fa3-blackhole/jobs.sqlite3")),
        )


class VaultTokenAuthenticator:
    def __init__(self, vault_path: Path, principal: str):
        self.vault_path = Path(vault_path)
        self.principal = principal

    def authenticate(self, authorization: str | None) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationDenied("Bearer credential required")
        presented = authorization[7:].strip()
        if not presented:
            raise AuthenticationDenied("Bearer credential required")
        try:
            data = json.loads(self.vault_path.read_text(encoding="utf-8"))
            expected = data["api_tokens"]["blackhole_bridge"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise AuthenticationDenied("credential authority unavailable") from exc
        if not isinstance(expected, str) or not expected or not hmac.compare_digest(presented, expected):
            raise AuthenticationDenied("invalid credential")
        return self.principal


class BrokerLeaseFileVerifier:
    """Read-only HRB adapter. It never issues, renews or revokes leases."""

    def __init__(self, lease_dir: Path, hrb_bin: Path, *, timeout_seconds: float = 5.0):
        self.lease_dir = Path(lease_dir)
        self.hrb_bin = Path(hrb_bin)
        self.timeout_seconds = timeout_seconds

    def verify(
        self,
        lease_id: str,
        *,
        minimum_tu: float,
        required_features: set[str],
    ) -> dict[str, Any]:
        if not LEASE_ID_RE.fullmatch(lease_id):
            raise LeaseDenied("invalid lease identifier")
        if not self.hrb_bin.is_file() or not os.access(self.hrb_bin, os.X_OK):
            raise LeaseDenied("canonical HRB verifier unavailable")

        base = self.lease_dir.resolve()
        raw_candidate = base / f"{lease_id}.json"
        if raw_candidate.is_symlink():
            raise LeaseDenied("HRB lease symlinks are forbidden")
        candidate = raw_candidate.resolve()
        if candidate.parent != base or not candidate.is_file():
            raise LeaseDenied("HRB lease not found")

        try:
            result = subprocess.run(
                [str(self.hrb_bin), "validate-lease", str(candidate)],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise LeaseDenied("HRB validation unavailable") from exc
        if result.returncode != 0:
            raise LeaseDenied("HRB rejected lease")

        try:
            lease = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LeaseDenied("HRB lease unreadable") from exc
        if not isinstance(lease, dict) or lease.get("lease_id") != lease_id:
            raise LeaseDenied("HRB lease identity mismatch")

        expires_at = lease.get("expires_at")
        if expires_at:
            try:
                expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            except ValueError as exc:
                raise LeaseDenied("HRB lease expiry malformed") from exc
            if expiry.tzinfo is None or expiry.astimezone(timezone.utc) <= datetime.now(timezone.utc):
                raise LeaseDenied("HRB lease expired")

        admitted_tu = lease.get("virtual_tu")
        if not isinstance(admitted_tu, (int, float)) or isinstance(admitted_tu, bool):
            raise LeaseDenied("HRB lease lacks virtual_tu admission evidence")
        if float(admitted_tu) < minimum_tu:
            raise LeaseDenied("HRB lease does not satisfy minimum_tu")
        admitted_features = set(lease.get("capabilities") or [])
        if not required_features.issubset(admitted_features):
            raise LeaseDenied("HRB lease lacks required accelerator/media capabilities")

        purpose_scope = set(lease.get("purpose_scope") or [])
        purpose = str(lease.get("purpose") or "")
        if "BLACKHOLE_NEURAL_MEDIA" not in purpose_scope and "BLACKHOLE" not in purpose.upper():
            raise LeaseDenied("HRB lease purpose does not authorize Blackhole execution")
        return lease


class SQLiteJobStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=FULL;
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL UNIQUE,
                    request_sha256 TEXT NOT NULL,
                    principal TEXT NOT NULL,
                    state TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    policy_json TEXT NOT NULL,
                    lease_json TEXT NOT NULL
                );
                """
            )
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def accept(
        self,
        request: BlackholeSubmitRequest,
        principal: str,
        policy: dict[str, Any],
        lease: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        request_json = self._canonical_json(request.model_dump(mode="json"))
        request_hash = hashlib.sha256(request_json.encode("utf-8")).hexdigest()
        request_id = str(request.request_id)

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT job_id, request_sha256, state FROM jobs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if existing is not None:
                conn.execute("COMMIT")
                if existing["request_sha256"] != request_hash:
                    raise ReplayConflict("request_id replayed with different payload")
                return {
                    "job_id": existing["job_id"],
                    "state": existing["state"],
                    "request_id": request_id,
                }, True

            job_id = f"JOB-BH-{uuid4().hex.upper()}"
            submitted_at = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO jobs
                    (job_id, request_id, request_sha256, principal, state, submitted_at,
                     request_json, policy_json, lease_json)
                VALUES (?, ?, ?, ?, 'ACCEPTED', ?, ?, ?, ?)
                """,
                (
                    job_id,
                    request_id,
                    request_hash,
                    principal,
                    submitted_at,
                    request_json,
                    self._canonical_json(policy),
                    self._canonical_json(lease),
                ),
            )
            conn.execute("COMMIT")
            return {"job_id": job_id, "state": "ACCEPTED", "request_id": request_id}, False
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def get(self, job_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT job_id, request_id, principal, state, submitted_at FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def derive_server_policy(request: BlackholeSubmitRequest) -> dict[str, Any]:
    requested = set(request.requirements.required_features)
    if requested != MANDATORY_FEATURES:
        raise PolicyDenied("operation requires the complete canonical accelerator feature set")
    model = MODEL_POLICY.get(request.pipeline.model_id)
    if not model or model["operation"] != request.pipeline.operation:
        raise PolicyDenied("model is not admitted for requested operation")
    if request.pipeline.output_profile not in OUTPUT_PROFILES:
        raise PolicyDenied("output profile is not admitted")

    return {
        "policy_id": "FA3-BLACKHOLE-REST-CONTROL-PLANE-001",
        "hardware_policy_ref": "FA3-HARDWARE-BASELINE-001",
        "hrb_authority_ref": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "bridge_ref": "FA3-BLACKHOLE-FFMPEG-BRIDGE-001",
        "minimum_tu": request.requirements.minimum_tu,
        "required_capabilities": sorted(MANDATORY_FEATURES),
        "operation": request.pipeline.operation,
        "internal_model_ref": model["internal_model_ref"],
        "output_profile": request.pipeline.output_profile,
        "runtime_profile": "PRODUCTION",
        "cuda_launch_blocking": False,
        "ffmpeg_binary_source": "SERVER_CANONICAL_POLICY",
        "environment_source": "SERVER_CANONICAL_POLICY",
        "worker_gpu_assignment_source": "HRB_RUNTIME_LEASE",
        "dispatch_backend": "SQLITE_DURABLE_QUEUE",
        "zero_copy_claim_scope": "FRAME_TO_TENSOR_ONLY",
        "end_to_end_gpu_resident_claim": False,
    }


def create_app(
    *,
    authenticator: Authenticator | None = None,
    lease_verifier: LeaseVerifier | None = None,
    store: SQLiteJobStore | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    cfg = settings or Settings.from_env()
    app = FastAPI(title="FA3 Blackhole API", version="3.0", docs_url=None, redoc_url=None)
    app.state.authenticator = authenticator or VaultTokenAuthenticator(cfg.token_vault_path, cfg.principal)
    app.state.lease_verifier = lease_verifier or BrokerLeaseFileVerifier(cfg.lease_dir, cfg.hrb_bin)
    app.state.store = store

    def get_store() -> SQLiteJobStore:
        if app.state.store is None:
            app.state.store = SQLiteJobStore(cfg.db_path)
        return app.state.store

    def authenticate(authorization: str | None) -> str:
        try:
            return app.state.authenticator.authenticate(authorization)
        except AuthenticationDenied as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "api_id": API_ID}

    @app.post("/api/v3/bridge/submit", response_model=JobReceipt, status_code=status.HTTP_202_ACCEPTED)
    def submit(
        request: BlackholeSubmitRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> JobReceipt:
        principal = authenticate(authorization)
        try:
            policy = derive_server_policy(request)
            lease = app.state.lease_verifier.verify(
                request.lease_id,
                minimum_tu=request.requirements.minimum_tu,
                required_features=set(request.requirements.required_features),
            )
            record, replay = get_store().accept(request, principal, policy, lease)
        except (LeaseDenied, PolicyDenied) as exc:
            raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(exc)) from exc
        except ReplayConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        return JobReceipt(
            job_id=record["job_id"],
            state="ACCEPTED",
            request_id=request.request_id,
            status_uri=f"/api/v3/jobs/{record['job_id']}",
            idempotent_replay=replay,
        )

    @app.get("/api/v3/jobs/{job_id}")
    def get_job(
        job_id: str,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        principal = authenticate(authorization)
        record = get_store().get(job_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        if record["principal"] != principal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        return record

    return app


app = create_app()
