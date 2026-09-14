from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from fa3_audit_chain import AuditChainError, append_event, normalize_key, read_jsonl, verify_records
from fa3_blackhole_admission import AdmissionDenied, validate_request
from fa3_blackhole_kdenlive import PreparationRequest, prepare_media

APP_ID = "FA3-BLACKHOLE-API-001"


class VirtualProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cu: int = Field(gt=0)
    tu: int = Field(gt=0)


class ResourceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cpu_threads: int = Field(gt=0)
    ram_mb: int = Field(gt=0)
    vram_mb: int = Field(gt=0)
    gpu_devices: list[str] = Field(default_factory=list)
    virtual_profile: VirtualProfile


class BlackholePrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_media: str
    output_dir: str
    hrb_lease_id: str
    resource_profile: ResourceProfile
    zone_start_seconds: float = Field(default=0.0, ge=0.0)
    zone_end_seconds: float | None = None
    preprocessing: str = "none"
    kdenlive_project: str | None = None
    project_fps: float | None = Field(default=None, gt=0.0)
    timeout_seconds: float = Field(default=7200.0, gt=0.0)
    demucs: dict[str, Any] = Field(default_factory=dict)
    language: str = "auto"
    stt_command: list[str] = Field(default_factory=list)


app = FastAPI(title="FA3 Blackhole API", version="1.0.0", docs_url=None, redoc_url=None)


def _audit_key() -> bytes:
    raw = os.environ.get("FA3_AUDIT_HMAC_KEY_HEX", "")
    if not raw:
        raise RuntimeError("FA3_AUDIT_HMAC_KEY_HEX is required")
    return normalize_key(raw)


def _audit_path() -> Path:
    return Path(os.environ.get("FA3_AUDIT_LOG", "/var/lib/fa3/audit/blackhole-api.jsonl"))


def _lease_root() -> Path:
    return Path(os.environ.get("FA3_HRB_LEASE_ROOT", "/run/fa3/hrb-leases"))


def _input_root() -> Path:
    return Path(os.environ.get("FA3_INPUT_ROOT", "/data/raw"))


def _output_root() -> Path:
    return Path(os.environ.get("FA3_OUTPUT_ROOT", "/data/processed"))


def _assert_confined(path_value: str, root: Path, field: str) -> None:
    candidate = Path(path_value).expanduser().resolve()
    canonical_root = root.expanduser().resolve()
    if candidate != canonical_root and canonical_root not in candidate.parents:
        raise AdmissionDenied("PATH_OUTSIDE_ALLOWED_ROOT", f"{field} is outside the configured allowed root", 403)


def _verify_audit_chain() -> None:
    verify_records(read_jsonl(_audit_path()), _audit_key())


def _audit(request_id: str, outcome: str, code: str, lease_id: str | None = None, detail: str | None = None) -> None:
    event = {
        "schema": "fa3.blackhole-api-audit-event.v1",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "app_id": APP_ID,
        "request_id": request_id,
        "outcome": outcome,
        "code": code,
        "lease_id": lease_id,
        "detail": detail,
    }
    append_event(_audit_path(), event, _audit_key())


@app.on_event("startup")
def fail_closed_startup() -> None:
    _audit_key()
    _verify_audit_chain()
    _input_root().resolve()
    _output_root().resolve()


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"status": "PASS", "app_id": APP_ID, "zero_copy_claimed": False}


@app.post("/v1/blackhole/prepare")
def prepare(request: BlackholePrepareRequest) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    payload = request.model_dump()
    lease_id = request.hrb_lease_id
    try:
        _verify_audit_chain()
    except AuditChainError as exc:
        raise HTTPException(status_code=503, detail={"code": "AUDIT_CHAIN_FAILURE", "message": str(exc)}) from exc

    try:
        _assert_confined(request.input_media, _input_root(), "input_media")
        _assert_confined(request.output_dir, _output_root(), "output_dir")
        if request.kdenlive_project:
            _assert_confined(request.kdenlive_project, _input_root(), "kdenlive_project")
        admission = validate_request(payload, _lease_root())
    except AdmissionDenied as exc:
        try:
            _audit(request_id, "DENY", exc.code, lease_id=lease_id, detail=exc.message)
        except AuditChainError as audit_exc:
            raise HTTPException(status_code=503, detail={"code": "AUDIT_CHAIN_FAILURE", "message": str(audit_exc)}) from audit_exc
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message}) from exc

    try:
        _audit(request_id, "ALLOW", "ADMISSION_PASS", lease_id=lease_id)
    except AuditChainError as exc:
        raise HTTPException(status_code=503, detail={"code": "AUDIT_CHAIN_FAILURE", "message": str(exc)}) from exc

    preparation_payload = {
        "input_media": request.input_media,
        "output_dir": request.output_dir,
        "zone_start_seconds": request.zone_start_seconds,
        "zone_end_seconds": request.zone_end_seconds,
        "preprocessing": request.preprocessing,
        "kdenlive_project": request.kdenlive_project,
        "project_fps": request.project_fps,
        "ffmpeg_bin": os.environ.get("FA3_FFMPEG_BIN", "ffmpeg"),
        "ffprobe_bin": os.environ.get("FA3_FFPROBE_BIN", "ffprobe"),
        "timeout_seconds": request.timeout_seconds,
        "demucs": request.demucs,
        "language": request.language,
        "stt_command": request.stt_command,
    }
    try:
        result = prepare_media(Path("/opt/fa3"), PreparationRequest.from_dict(preparation_payload))
    except Exception as exc:
        try:
            _audit(request_id, "ERROR", "EXECUTION_FAILED", lease_id=lease_id, detail=type(exc).__name__)
        except AuditChainError as audit_exc:
            raise HTTPException(status_code=503, detail={"code": "AUDIT_CHAIN_FAILURE", "message": str(audit_exc)}) from audit_exc
        raise HTTPException(status_code=500, detail={"code": "EXECUTION_FAILED"}) from exc

    try:
        _audit(request_id, "ALLOW", "EXECUTION_PASS", lease_id=lease_id)
    except AuditChainError as exc:
        raise HTTPException(status_code=503, detail={"code": "AUDIT_CHAIN_FAILURE", "message": str(exc)}) from exc
    return {
        "request_id": request_id,
        "admission": {"result": admission["result"], "workload_id": admission["workload_id"]},
        "execution": result,
        "zero_copy_claimed": False,
    }
