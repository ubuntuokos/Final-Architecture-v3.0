#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fa3_voice_synthesis_gate import VoicePolicyDenied, resolve_route

SCHEMA = "fa3.voice-workspace-state.v1"
PROFILE_ID = "FA3-VOICE-STUDIO-001"
VOICE_AUTHORITY = "FA3-VOICE-001"
MODEL_ROUTER = "FA3-AUTH-MODEL-ROUTER-001"
HRB = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
UAF = "FA3-UNIFIED-ACTION-FABRIC-001"
MCP = "FA3-AUTH-MCP-GATEWAY-001"
WORKFLOW = "Temporal"

JOB_TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}
JOB_STATES = {
    "QUEUED", "BLOCKED_NOT_ADMITTED", "ROUTE_READY", "DISPATCHED",
    "RUNNING", "COMPLETED", "FAILED", "CANCELLED",
}
ACTIVITY_STATES = {
    "IDLE", "LISTENING", "RECORDING", "TRANSCRIBING", "REFINING",
    "GENERATING", "SPEAKING", "PAUSED", "BLOCKED", "ERROR",
}


class VoiceWorkspaceDenied(RuntimeError):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _base_state() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": 1,
        "voice_profiles": {},
        "captures": {},
        "jobs": {},
        "handoffs": {},
        "quick_dub_plans": {},
        "activity": {
            "state": "IDLE",
            "application": "fa3.voice-studio",
            "actor": "",
            "voice_profile_id": "",
            "job_id": "",
            "visible": False,
        },
    }


def discover_admitted_voice_providers(root: Path) -> set[str]:
    path = root / "canonical/FA3-VOICE-PROVIDER-ADMISSION-001.json"
    if not path.is_file():
        return set()
    obj = json.loads(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for provider_id, row in (obj.get("providers") or {}).items():
        status = _clean((row or {}).get("production_status"))
        if status in {"PRODUCTION_ADMITTED", "CURRENT_HOST_PRODUCTION_ADMITTED"}:
            out.add(provider_id)
    return out


def validate_voice_profile(profile: dict[str, Any]) -> dict[str, Any]:
    profile_id = _clean(profile.get("voice_profile_id"))
    name = _clean(profile.get("name"))
    languages = profile.get("languages")
    identity_kind = _clean(profile.get("identity_kind")).upper()
    consent_status = _clean(profile.get("consent_status")).upper()
    if not profile_id or not name:
        raise VoiceWorkspaceDenied("voice_profile_id and name are required")
    if not isinstance(languages, list) or not languages or any(not _clean(x) for x in languages):
        raise VoiceWorkspaceDenied("languages must be a non-empty string list")
    if identity_kind not in {"SYNTHETIC", "HUMAN_AUTHORIZED", "PRESET"}:
        raise VoiceWorkspaceDenied("invalid identity_kind")
    consent_ref = _clean(profile.get("consent_proof_ref"))
    if identity_kind == "HUMAN_AUTHORIZED" and (consent_status != "GRANTED" or not consent_ref):
        raise VoiceWorkspaceDenied("HUMAN_AUTHORIZED requires GRANTED consent and consent_proof_ref")
    forbidden = {"provider_id", "model_id", "device", "cuda_device", "endpoint", "model_path"}
    if forbidden.intersection(profile):
        raise VoiceWorkspaceDenied("Voice Profile cannot pin provider/model/device/endpoint/path")
    now = utcnow()
    out = copy.deepcopy(profile)
    out["voice_profile_id"] = profile_id
    out["name"] = name
    out["languages"] = [_clean(x) for x in languages]
    out["identity_kind"] = identity_kind
    out["consent_status"] = consent_status or ("NOT_REQUIRED" if identity_kind != "HUMAN_AUTHORIZED" else "")
    out.setdefault("created_at", now)
    out["updated_at"] = now
    out.setdefault("styles", [])
    out.setdefault("effects_preset", "NONE")
    out.setdefault("rights_status", "UNVERIFIED")
    return out


def validate_generation_request(request: dict[str, Any]) -> dict[str, Any]:
    required = ["request_id", "text", "language", "mode", "voice_identity_ref", "execution_mode", "output_intent"]
    missing = [key for key in required if not _clean(request.get(key))]
    if missing:
        raise VoiceWorkspaceDenied(f"generation request missing: {','.join(missing)}")
    if request.get("silent_fallback") not in (None, False):
        raise VoiceWorkspaceDenied("silent fallback is forbidden")
    for forbidden in ("provider_id", "model_id", "device", "cuda_device", "endpoint", "model_path"):
        if forbidden in request:
            raise VoiceWorkspaceDenied(f"physical routing field forbidden in application request: {forbidden}")
    if request.get("execution_mode") not in {"OFFLINE_LOCAL", "ONLINE_ALLOWED"}:
        raise VoiceWorkspaceDenied("invalid execution_mode")
    if request.get("output_intent") not in {"INTERACTIVE", "MEDIA_MEZZANINE", "ARCHIVAL_MASTER"}:
        raise VoiceWorkspaceDenied("invalid output_intent")
    out = copy.deepcopy(request)
    out["silent_fallback"] = False
    return out


def fit_to_clip_plan(target_duration_ms: int, generated_duration_ms: int) -> dict[str, Any]:
    if target_duration_ms <= 0 or generated_duration_ms <= 0:
        raise VoiceWorkspaceDenied("durations must be positive")
    rate = generated_duration_ms / target_duration_ms
    options: list[dict[str, Any]] = []
    if 0.85 <= rate <= 1.15:
        options.append({
            "action": "BOUNDED_RATE_ADJUSTMENT",
            "speech_rate": round(rate, 4),
            "requires_text_change": False,
            "approval_required": False,
        })
    options += [
        {
            "action": "SCRIPT_SHORTENING_PROPOSAL",
            "requires_text_change": True,
            "approval_required": True,
            "silent_apply": False,
        },
        {
            "action": "EXTEND_VIDEO",
            "target_duration_ms": generated_duration_ms,
            "approval_required": True,
        },
        {
            "action": "KEEP_ORIGINAL_TIMING",
            "approval_required": False,
        },
    ]
    return {
        "schema": "fa3.voice-fit-to-clip-plan.v1",
        "target_duration_ms": target_duration_ms,
        "generated_duration_ms": generated_duration_ms,
        "measured_rate_ratio": round(rate, 4),
        "options": options,
        "silent_text_rewrite": False,
        "status": "READY",
    }


class VoiceWorkspaceStore:
    def __init__(self, state_path: Path, root: Path | None = None):
        self.state_path = Path(state_path)
        self.root = Path(root).resolve() if root else Path(__file__).resolve().parents[1]
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            return _base_state()
        obj = json.loads(self.state_path.read_text(encoding="utf-8"))
        if obj.get("schema") != SCHEMA:
            raise VoiceWorkspaceDenied("workspace state schema mismatch")
        for key in ("voice_profiles", "captures", "jobs", "handoffs", "quick_dub_plans"):
            if not isinstance(obj.get(key), dict):
                raise VoiceWorkspaceDenied(f"workspace state {key} must be an object")
        return obj

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state["version"] = int(self.state.get("version", 0)) + 1
        data = json.dumps(self.state, ensure_ascii=False, indent=2) + "\n"
        fd, tmp = tempfile.mkstemp(prefix=".voice-workspace-", dir=str(self.state_path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.state_path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)

    def list_profiles(self, query: str = "") -> list[dict[str, Any]]:
        q = query.casefold().strip()
        rows = list(self.state["voice_profiles"].values())
        if q:
            rows = [r for r in rows if q in f"{r.get('voice_profile_id','')} {r.get('name','')} {' '.join(r.get('languages',[]))}".casefold()]
        return sorted(copy.deepcopy(rows), key=lambda r: (r.get("name", ""), r.get("voice_profile_id", "")))

    def get_profile(self, voice_profile_id: str) -> dict[str, Any]:
        row = self.state["voice_profiles"].get(_clean(voice_profile_id))
        if not row:
            raise VoiceWorkspaceDenied("unknown Voice Profile")
        return copy.deepcopy(row)

    def upsert_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        row = validate_voice_profile(profile)
        existing = self.state["voice_profiles"].get(row["voice_profile_id"])
        if existing:
            row["created_at"] = existing.get("created_at", row["created_at"])
        self.state["voice_profiles"][row["voice_profile_id"]] = row
        self._save()
        return copy.deepcopy(row)

    def create_capture(self, language: str, source_ref: str, transcript: str = "", purpose: str = "") -> dict[str, Any]:
        language = _clean(language)
        source_ref = _clean(source_ref)
        if not language or not source_ref:
            raise VoiceWorkspaceDenied("capture language and source_ref are required")
        capture_id = _id("capture")
        row = {
            "schema": "fa3.voice-capture-record.v1",
            "capture_id": capture_id,
            "language": language,
            "source_ref": source_ref,
            "raw_transcript": transcript,
            "refined_transcript": "",
            "purpose": _clean(purpose),
            "created_at": utcnow(),
            "status": "TRANSCRIBED" if transcript else "CAPTURED",
            "provenance": {
                "source_ref_sha256": sha256_text(source_ref),
                "local_first": True,
                "network_egress_authorized": False,
            },
        }
        self.state["captures"][capture_id] = row
        self._save()
        return copy.deepcopy(row)

    def submit_generation(self, request: dict[str, Any], quickclip_context: dict[str, Any] | None = None,
                          admitted_providers: set[str] | None = None) -> dict[str, Any]:
        req = validate_generation_request(request)
        admitted = discover_admitted_voice_providers(self.root) if admitted_providers is None else set(admitted_providers)
        job_id = _id("voice-job")
        route_state = "BLOCKED_NOT_ADMITTED"
        decision: dict[str, Any] | None = None
        try:
            decision = resolve_route(req, admitted)
            decision["request_id"] = req["request_id"]
            decision["selected_model_id"] = "RESOLVED_BY_MODEL_ROUTER_RUNTIME"
            decision["license_status"] = "REQUIRES_EXECUTION_TIME_ADMISSION"
            decision["resource_admission_ref"] = "REQUIRED_AT_DISPATCH"
            decision["decision_reason"] = "CANONICAL_VOICE_POLICY_CANDIDATE_FILTER"
            route_state = "ROUTE_READY"
        except VoicePolicyDenied:
            decision = None
        row = {
            "schema": "fa3.voice-generation-job.v1",
            "job_id": job_id,
            "request": req,
            "quickclip_context": copy.deepcopy(quickclip_context or {}),
            "status": route_state,
            "route_state": route_state,
            "provider_decision": decision,
            "created_at": utcnow(),
            "updated_at": utcnow(),
            "result": None,
            "authority_bindings": {
                "voice": VOICE_AUTHORITY,
                "model_router": MODEL_ROUTER,
                "resource": HRB,
                "uaf": UAF,
                "workflow": WORKFLOW,
            },
            "execution_requested": False,
            "runtime_execution_allowed": route_state == "ROUTE_READY",
            "evidence_refs": [],
        }
        self.state["jobs"][job_id] = row
        self.state["activity"] = {
            "state": "BLOCKED" if route_state == "BLOCKED_NOT_ADMITTED" else "PAUSED",
            "application": "fa3.voice-studio",
            "actor": "",
            "voice_profile_id": req["voice_identity_ref"],
            "job_id": job_id,
            "visible": route_state == "BLOCKED_NOT_ADMITTED",
        }
        self._save()
        return copy.deepcopy(row)

    def cancel_job(self, job_id: str, reason: str = "") -> dict[str, Any]:
        job = self.state["jobs"].get(_clean(job_id))
        if not job:
            raise VoiceWorkspaceDenied("unknown job")
        if job["status"] not in JOB_TERMINAL:
            job["status"] = "CANCELLED"
            job["updated_at"] = utcnow()
            job["cancel_reason"] = _clean(reason)
            self.state["activity"]["state"] = "IDLE"
            self.state["activity"]["visible"] = False
            self._save()
        return copy.deepcopy(job)

    def authorize_dispatch(self, job_id: str, uaf_execution_ref: str, resource_admission_ref: str) -> dict[str, Any]:
        job = self.state["jobs"].get(_clean(job_id))
        if not job:
            raise VoiceWorkspaceDenied("unknown job")
        if job["status"] != "ROUTE_READY" or not isinstance(job.get("provider_decision"), dict):
            raise VoiceWorkspaceDenied("dispatch requires ROUTE_READY job and provider decision")
        if not _clean(uaf_execution_ref) or not _clean(resource_admission_ref):
            raise VoiceWorkspaceDenied("UAF execution and resource admission references are required")
        job["status"] = "DISPATCHED"
        job["updated_at"] = utcnow()
        job["execution_requested"] = True
        job["runtime_execution_allowed"] = True
        job["uaf_execution_ref"] = _clean(uaf_execution_ref)
        job["resource_admission_ref"] = _clean(resource_admission_ref)
        job["temporal_dispatch"] = {
            "schema": "fa3.voice-temporal-dispatch.v1",
            "workflow_type": "fa3.voice.generate",
            "workflow_id": f"voice-generation::{job_id}",
            "idempotency_key": job["request"]["request_id"],
            "job_id": job_id,
            "uaf_execution_ref": job["uaf_execution_ref"],
            "resource_admission_ref": job["resource_admission_ref"],
            "provider_decision": copy.deepcopy(job["provider_decision"]),
            "execution_authority": UAF,
            "workflow_authority": WORKFLOW,
        }
        self.state["activity"] = {
            "state": "GENERATING",
            "application": "fa3.voice-studio",
            "actor": "",
            "voice_profile_id": job["request"]["voice_identity_ref"],
            "job_id": job_id,
            "visible": True,
        }
        self._save()
        return copy.deepcopy(job)

    def stage_transcription(self, capture_id: str, language: str, refine: bool = False) -> dict[str, Any]:
        capture = self.state["captures"].get(_clean(capture_id))
        if not capture:
            raise VoiceWorkspaceDenied("unknown capture")
        if not _clean(language):
            raise VoiceWorkspaceDenied("transcription language is required")
        request_id = _id("stt-request")
        capture["transcription_request"] = {
            "schema": "fa3.voice-transcription-stage.v1",
            "request_id": request_id,
            "action_id": "voice.transcribe",
            "capture_id": capture_id,
            "language": _clean(language),
            "refine": bool(refine),
            "provider_profile": "FA3-STT-MEDIA-001",
            "provider_id": "FA3-PROVIDER-WHISPER-001",
            "model_router_authority": MODEL_ROUTER,
            "uaf_authority": UAF,
            "execution_requested": False,
        }
        capture["status"] = "TRANSCRIPTION_STAGED_UAF"
        capture["updated_at"] = utcnow()
        self.state["activity"] = {
            "state": "PAUSED",
            "application": "fa3.voice-studio",
            "actor": "user",
            "voice_profile_id": "",
            "job_id": request_id,
            "visible": False,
        }
        self._save()
        return copy.deepcopy(capture)

    def begin_transcription(self, capture_id: str, uaf_execution_ref: str) -> dict[str, Any]:
        capture = self.state["captures"].get(_clean(capture_id))
        if not capture or capture.get("status") != "TRANSCRIPTION_STAGED_UAF":
            raise VoiceWorkspaceDenied("transcription execution requires staged capture")
        if not _clean(uaf_execution_ref):
            raise VoiceWorkspaceDenied("UAF execution reference required for transcription")
        capture["status"] = "TRANSCRIBING"
        capture["updated_at"] = utcnow()
        capture["transcription_request"]["execution_requested"] = True
        capture["transcription_request"]["uaf_execution_ref"] = _clean(uaf_execution_ref)
        self.state["activity"] = {
            "state": "TRANSCRIBING", "application": "fa3.voice-studio", "actor": "user",
            "voice_profile_id": "", "job_id": capture["transcription_request"]["request_id"], "visible": True,
        }
        self._save()
        return copy.deepcopy(capture)

    def fail_transcription(self, capture_id: str, reason: str) -> dict[str, Any]:
        capture = self.state["captures"].get(_clean(capture_id))
        if not capture:
            raise VoiceWorkspaceDenied("unknown capture")
        capture["status"] = "BLOCKED"
        capture["updated_at"] = utcnow()
        capture["transcription_error"] = _clean(reason)
        self.state["activity"] = {
            "state": "ERROR", "application": "fa3.voice-studio", "actor": "user",
            "voice_profile_id": "", "job_id": str((capture.get("transcription_request") or {}).get("request_id") or ""), "visible": True,
        }
        self._save()
        return copy.deepcopy(capture)

    def accept_transcription_result(self, capture_id: str, result: dict[str, Any]) -> dict[str, Any]:
        capture = self.state["captures"].get(_clean(capture_id))
        if not capture:
            raise VoiceWorkspaceDenied("unknown capture")
        request = capture.get("transcription_request")
        if not isinstance(request, dict):
            raise VoiceWorkspaceDenied("capture has no staged transcription request")
        if result.get("status") != "PASS" or result.get("provider_id") != "FA3-PROVIDER-WHISPER-001":
            raise VoiceWorkspaceDenied("transcription result is not an admitted Whisper PASS")
        if not isinstance(result.get("segments"), list) or not isinstance(result.get("execution_evidence"), dict):
            raise VoiceWorkspaceDenied("transcription result evidence is incomplete")
        transcript = " ".join(
            _clean(segment.get("text"))
            for segment in result["segments"]
            if isinstance(segment, dict) and _clean(segment.get("text"))
        ).strip()
        capture["raw_transcript"] = transcript
        capture["transcription_result"] = copy.deepcopy(result)
        capture["status"] = "TRANSCRIBED"
        capture["updated_at"] = utcnow()
        self.state["activity"] = {
            "state": "IDLE", "application": "fa3.voice-studio", "actor": "user",
            "voice_profile_id": "", "job_id": request["request_id"], "visible": False,
        }
        self._save()
        return copy.deepcopy(capture)

    def accept_generation_result(self, job_id: str, result: dict[str, Any]) -> dict[str, Any]:
        job = self.state["jobs"].get(_clean(job_id))
        if not job:
            raise VoiceWorkspaceDenied("unknown job")
        if job["status"] not in {"DISPATCHED", "RUNNING"}:
            raise VoiceWorkspaceDenied("job must be DISPATCHED/RUNNING before accepting provider result")
        required = ["provider_id", "model_id", "model_revision", "audio_path", "audio_sha256",
                    "sample_rate_hz", "channels", "voice_identity_ref", "language",
                    "synthetic_disclosure", "license_and_rights_ref", "execution_evidence"]
        missing = [key for key in required if result.get(key) in (None, "", [])]
        if missing:
            raise VoiceWorkspaceDenied(f"provider result missing: {','.join(missing)}")
        expected = job.get("provider_decision") or {}
        if expected.get("selected_provider_id") and result.get("provider_id") != expected["selected_provider_id"]:
            raise VoiceWorkspaceDenied("provider result does not match provider decision")
        if result.get("voice_identity_ref") != job["request"]["voice_identity_ref"]:
            raise VoiceWorkspaceDenied("provider result voice identity mismatch")
        job["result"] = copy.deepcopy(result)
        job["status"] = "COMPLETED"
        job["updated_at"] = utcnow()
        self.state["activity"] = {
            "state": "IDLE", "application": "fa3.voice-studio", "actor": "",
            "voice_profile_id": job["request"]["voice_identity_ref"], "job_id": job_id, "visible": False,
        }
        self._save()
        return copy.deepcopy(job)

    def quick_dub_plan(self, source_language: str, target_language: str,
                       speaker_mappings: list[dict[str, Any]], translation_enabled: bool = False) -> dict[str, Any]:
        if not _clean(source_language) or not _clean(target_language):
            raise VoiceWorkspaceDenied("source and target language are required")
        if not isinstance(speaker_mappings, list) or not speaker_mappings:
            raise VoiceWorkspaceDenied("speaker_mappings are required")
        normalized = []
        for row in speaker_mappings:
            speaker = _clean(row.get("speaker"))
            voice_profile_id = _clean(row.get("voice_profile_id"))
            if not speaker or not voice_profile_id:
                raise VoiceWorkspaceDenied("speaker mapping requires speaker and voice_profile_id")
            self.get_profile(voice_profile_id)
            normalized.append({"speaker": speaker, "voice_profile_id": voice_profile_id})
        plan_id = _id("quick-dub")
        plan = {
            "schema": "fa3.voice-quick-dub-plan.v1",
            "plan_id": plan_id,
            "source_language": _clean(source_language),
            "target_language": _clean(target_language),
            "speaker_mappings": normalized,
            "translation_enabled": bool(translation_enabled),
            "stages": [
                "STT", "SPEAKER_SEGMENTATION",
                "OPTIONAL_TRANSLATION" if translation_enabled else "TRANSLATION_SKIPPED",
                "VOICE_PROFILE_MAPPING", "TTS", "ALIGNMENT", "EDITABLE_MIX",
            ],
            "status": "PLAN_READY",
            "authority_bindings": {
                "voice": VOICE_AUTHORITY, "model_router": MODEL_ROUTER,
                "resource": HRB, "uaf": UAF, "workflow": WORKFLOW,
            },
            "created_at": utcnow(),
        }
        self.state["quick_dub_plans"][plan_id] = plan
        self._save()
        return copy.deepcopy(plan)

    def timeline_handoff(self, job_id: str, clip_id: str, caption_alignment_ref: str = "",
                         music_ducking: bool = True) -> dict[str, Any]:
        job = self.state["jobs"].get(_clean(job_id))
        if not job or job.get("status") != "COMPLETED" or not isinstance(job.get("result"), dict):
            raise VoiceWorkspaceDenied("timeline handoff requires a completed generation job")
        clip_id = _clean(clip_id)
        if not clip_id:
            raise VoiceWorkspaceDenied("clip_id is required")
        handoff_id = _id("voice-handoff")
        result = job["result"]
        row = {
            "schema": "fa3.voice-timeline-handoff.v1",
            "handoff_id": handoff_id,
            "job_id": job_id,
            "clip_id": clip_id,
            "audio_asset_ref": result["audio_path"],
            "tracks": {
                "voice": {"asset_ref": result["audio_path"], "editable": True},
                "captions": {"alignment_ref": _clean(caption_alignment_ref), "editable": True},
                "music_ducking": {"enabled": bool(music_ducking), "editable": True},
            },
            "editable": True,
            "host_mutation_authorized": False,
            "provenance": {
                "job_id": job_id,
                "audio_sha256": result["audio_sha256"],
                "provider_id": result["provider_id"],
                "model_revision": result["model_revision"],
            },
            "created_at": utcnow(),
        }
        self.state["handoffs"][handoff_id] = row
        self._save()
        return copy.deepcopy(row)

    def status(self, job_id: str = "") -> dict[str, Any]:
        job = copy.deepcopy(self.state["jobs"].get(_clean(job_id))) if _clean(job_id) else None
        return {
            "schema": "fa3.voice-workspace-status.v1",
            "status": "READY",
            "activity": copy.deepcopy(self.state["activity"]),
            "job": job,
            "profile_count": len(self.state["voice_profiles"]),
            "capture_count": len(self.state["captures"]),
            "job_count": len(self.state["jobs"]),
            "handoff_count": len(self.state["handoffs"]),
        }


def _load_json_arg(value: str) -> Any:
    if value == "-":
        return json.load(__import__("sys").stdin)
    path = Path(value)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Voice Studio local workspace controller")
    parser.add_argument("--state", required=True)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = parser.add_subparsers(dest="operation", required=True)

    p = sub.add_parser("profile-upsert"); p.add_argument("profile")
    p = sub.add_parser("profile-list"); p.add_argument("--query", default="")
    p = sub.add_parser("capture"); p.add_argument("language"); p.add_argument("source_ref"); p.add_argument("--transcript", default=""); p.add_argument("--purpose", default="")
    p = sub.add_parser("submit"); p.add_argument("request"); p.add_argument("--quickclip-context", default="{}")
    p = sub.add_parser("cancel"); p.add_argument("job_id"); p.add_argument("--reason", default="")
    p = sub.add_parser("fit"); p.add_argument("target_ms", type=int); p.add_argument("generated_ms", type=int)
    p = sub.add_parser("quick-dub"); p.add_argument("source_language"); p.add_argument("target_language"); p.add_argument("speaker_mappings"); p.add_argument("--translation", action="store_true")
    p = sub.add_parser("dispatch"); p.add_argument("job_id"); p.add_argument("uaf_execution_ref"); p.add_argument("resource_admission_ref")
    p = sub.add_parser("transcribe-stage"); p.add_argument("capture_id"); p.add_argument("language"); p.add_argument("--refine", action="store_true")
    p = sub.add_parser("transcribe-result"); p.add_argument("capture_id"); p.add_argument("result")
    p = sub.add_parser("accept-result"); p.add_argument("job_id"); p.add_argument("result")
    p = sub.add_parser("handoff"); p.add_argument("job_id"); p.add_argument("clip_id"); p.add_argument("--caption-alignment-ref", default=""); p.add_argument("--no-ducking", action="store_true")
    p = sub.add_parser("status"); p.add_argument("--job-id", default="")

    args = parser.parse_args()
    store = VoiceWorkspaceStore(Path(args.state), Path(args.root))
    try:
        if args.operation == "profile-upsert":
            out = store.upsert_profile(_load_json_arg(args.profile))
        elif args.operation == "profile-list":
            out = {"profiles": store.list_profiles(args.query)}
        elif args.operation == "capture":
            out = store.create_capture(args.language, args.source_ref, args.transcript, args.purpose)
        elif args.operation == "submit":
            out = store.submit_generation(_load_json_arg(args.request), _load_json_arg(args.quickclip_context))
        elif args.operation == "cancel":
            out = store.cancel_job(args.job_id, args.reason)
        elif args.operation == "fit":
            out = fit_to_clip_plan(args.target_ms, args.generated_ms)
        elif args.operation == "quick-dub":
            out = store.quick_dub_plan(args.source_language, args.target_language, _load_json_arg(args.speaker_mappings), args.translation)
        elif args.operation == "dispatch":
            out = store.authorize_dispatch(args.job_id, args.uaf_execution_ref, args.resource_admission_ref)
        elif args.operation == "transcribe-stage":
            out = store.stage_transcription(args.capture_id, args.language, args.refine)
        elif args.operation == "transcribe-result":
            out = store.accept_transcription_result(args.capture_id, _load_json_arg(args.result))
        elif args.operation == "accept-result":
            out = store.accept_generation_result(args.job_id, _load_json_arg(args.result))
        elif args.operation == "handoff":
            out = store.timeline_handoff(args.job_id, args.clip_id, args.caption_alignment_ref, not args.no_ducking)
        else:
            out = store.status(args.job_id)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    except (VoiceWorkspaceDenied, VoicePolicyDenied, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "DENIED", "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
