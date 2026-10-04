#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fa3_uaf import CallableProvider, ProviderDescriptor, ProviderRegistry
from fa3_voice_workspace import VoiceWorkspaceDenied, VoiceWorkspaceStore
from fa3_whisper_stt_provider import RuntimeOptions, execute_transcription

NATIVE_PROVIDER_ID = "FA3-PROVIDER-VOICE-STUDIO-NATIVE-001"
WHISPER_PROVIDER_ID = "FA3-PROVIDER-WHISPER-001"
NATIVE_ACTIONS = (
    "voice.profile.list", "voice.profile.get", "voice.profile.upsert",
    "voice.capture", "voice.speak", "voice.stop", "voice.status",
    "voice.generate.submit", "voice.generate.dispatch",
    "voice.fit-to-clip.plan", "voice.quick-dub.plan", "voice.timeline.insert",
)


def _lease_ref(resource_lease: Any) -> str:
    if isinstance(resource_lease, dict):
        for key in ("lease_id", "grant_id", "id"):
            value = str(resource_lease.get(key) or "").strip()
            if value:
                return value
    for key in ("lease_id", "grant_id", "id"):
        value = str(getattr(resource_lease, key, "") or "").strip()
        if value:
            return value
    return ""


def _evidence(*refs: str) -> list[str]:
    return [ref for ref in refs if str(ref).strip()]


def build_native_provider(store: VoiceWorkspaceStore) -> CallableProvider:
    descriptor = ProviderDescriptor(
        provider_id=NATIVE_PROVIDER_ID,
        action_ids=NATIVE_ACTIONS,
        capabilities=("voice-workspace", "voice-profile", "fit-to-clip", "quick-dub", "timeline-handoff"),
        priority=20,
        state="CONNECTED",
        metadata={
            "architectural_authority": False,
            "provider_selection_authority": False,
            "device_selection_authority": False,
            "voice_authority": "FA3-VOICE-001",
        },
    )

    def handler(request: Any, resource_lease: Any, _secret_leases: tuple[Any, ...]) -> dict[str, Any]:
        action = request.action_id
        args = request.arguments
        if action == "voice.profile.list":
            return {"status": "PASS", "profiles": store.list_profiles(str(args.get("query") or "")), "evidence_refs": []}
        if action == "voice.profile.get":
            return {"status": "PASS", "profile": store.get_profile(str(args["voice_profile_id"])), "evidence_refs": []}
        if action == "voice.profile.upsert":
            row = store.upsert_profile(dict(args["voice_profile"]))
            return {"status": "PASS", "voice_profile_id": row["voice_profile_id"], "evidence_refs": []}
        if action == "voice.capture":
            row = store.create_capture(str(args["language"]), str(args["source_ref"]), str(args.get("transcript") or ""), str(args.get("purpose") or ""))
            return {"status": "PASS", "capture_id": row["capture_id"], "artifact": row, "evidence_refs": []}
        if action in {"voice.generate.submit", "voice.speak"}:
            if action == "voice.speak":
                voice_request = {
                    "request_id": str(args["request_id"]),
                    "text": str(args["text"]),
                    "language": str(args["language"]),
                    "mode": "plain",
                    "voice_identity_ref": str(args["voice_identity_ref"]),
                    "execution_mode": "OFFLINE_LOCAL",
                    "output_intent": "INTERACTIVE",
                    "style_intent": "PERSONALITY" if args.get("personality") is True else "NATURAL",
                    "silent_fallback": False,
                }
                row = store.submit_generation(voice_request, {})
                return {"status": row["status"], "job_id": row["job_id"], "evidence_refs": []}
            row = store.submit_generation(dict(args["request"]), dict(args.get("quickclip_context") or {}))
            return {"status": row["status"], "job_id": row["job_id"], "route_state": row["route_state"], "evidence_refs": []}
        if action == "voice.generate.dispatch":
            lease_ref = _lease_ref(resource_lease)
            if not lease_ref:
                raise VoiceWorkspaceDenied("voice generation dispatch requires fresh UAF HRB lease")
            row = store.authorize_dispatch(str(args["job_id"]), f"uaf:{request.request_id}", lease_ref)
            return {"status": row["status"], "job_id": row["job_id"], "temporal_dispatch": row["temporal_dispatch"], "evidence_refs": [f"uaf:{request.request_id}", lease_ref]}
        if action == "voice.fit-to-clip.plan":
            plan = __import__("fa3_voice_workspace").fit_to_clip_plan(int(args["target_duration_ms"]), int(args["generated_duration_ms"]))
            return {"status": "PASS", "plan": plan, "evidence_refs": []}
        if action == "voice.quick-dub.plan":
            plan = store.quick_dub_plan(str(args["source_language"]), str(args["target_language"]), list(args["speaker_mappings"]), bool(args.get("translation_enabled", False)))
            return {"status": plan["status"], "plan": plan, "evidence_refs": []}
        if action == "voice.timeline.insert":
            row = store.timeline_handoff(str(args["job_id"]), str(args["clip_id"]), str(args.get("caption_alignment_ref") or ""), bool(args.get("music_ducking", True)))
            return {"status": "HANDOFF_STAGED", "handoff": row, "evidence_refs": []}
        if action == "voice.stop":
            row = store.cancel_job(str(args["job_id"]), str(args.get("reason") or ""))
            return {"status": row["status"], "job_id": row["job_id"], "evidence_refs": []}
        if action == "voice.status":
            return {"status": "PASS", "activity": store.status(str(args.get("job_id") or "")), "evidence_refs": []}
        raise VoiceWorkspaceDenied(f"unsupported native Voice action: {action}")

    return CallableProvider(descriptor, handler)


def whisper_current_host_binding(root: Path) -> dict[str, Any] | None:
    receipt_path = root / "evidence/receipts/whisper-stt-current-host.json"
    if not receipt_path.is_file():
        return None
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not (
        receipt.get("schema") == "fa3.whisper-stt-current-host-evidence.v1"
        and receipt.get("status") == "CURRENT_HOST_WHISPER_STT_E2E_PASS"
        and receipt.get("provider_id") == WHISPER_PROVIDER_ID
        and receipt.get("current_host") is True
        and receipt.get("ci") is False
        and str(receipt.get("model") or "").strip()
        and receipt.get("device") == "cpu"
        and str(receipt.get("model_artifact_sha256") or "").strip()
    ):
        return None
    return {"receipt_path": str(receipt_path), "receipt": receipt}


def build_whisper_provider(store: VoiceWorkspaceStore, root: Path) -> CallableProvider:
    binding = whisper_current_host_binding(root)
    state = "CONNECTED" if binding else "BLOCKED"
    descriptor = ProviderDescriptor(
        provider_id=WHISPER_PROVIDER_ID,
        action_ids=("voice.transcribe",),
        capabilities=("speech-transcription", "offline-cpu", "word-timestamps"),
        priority=20,
        state=state,
        metadata={
            "architectural_authority": False,
            "provider_selection_authority": False,
            "current_host_binding": bool(binding),
            "cpu_only_voice_studio_baseline": True,
        },
    )

    def handler(request: Any, _resource_lease: Any, _secret_leases: tuple[Any, ...]) -> dict[str, Any]:
        if binding is None:
            raise VoiceWorkspaceDenied("Whisper STT lacks CPU current-host admission receipt")
        capture_id = str(request.arguments["capture_id"])
        capture = store.state["captures"].get(capture_id)
        if not isinstance(capture, dict):
            raise VoiceWorkspaceDenied("unknown capture")
        audio_path = Path(str(capture.get("source_ref") or "")).expanduser().resolve()
        if not audio_path.is_file():
            raise VoiceWorkspaceDenied("capture audio artifact is not a local file")
        digest = hashlib.sha256(audio_path.read_bytes()).hexdigest()
        store.stage_transcription(capture_id, str(request.arguments["language"]), bool(request.arguments.get("refine", False)))
        store.begin_transcription(capture_id, f"uaf:{request.request_id}")
        receipt = binding["receipt"]
        provider_request = {
            "schema": "fa3.stt-media-request.v1",
            "audio_path": str(audio_path),
            "audio_hash": digest,
            "language": str(request.arguments["language"]),
            "time_origin": "RELATIVE_ZERO",
            "required_result_schema": "fa3.stt-media-result.v1",
            "task": "transcribe",
        }
        try:
            result = execute_transcription(
                root,
                provider_request,
                RuntimeOptions(
                    model=str(receipt["model"]),
                    device="cpu",
                    offline=True,
                    word_timestamps=True,
                ),
            )
        except Exception as exc:
            store.fail_transcription(capture_id, str(exc))
            raise
        updated = store.accept_transcription_result(capture_id, result)
        return {
            "status": "PASS",
            "capture_id": capture_id,
            "transcript_ref": f"voice-capture:{capture_id}#raw_transcript",
            "evidence_refs": [str(binding["receipt_path"]), f"provider-result:{result.get('provider_id')}:{result.get('model_id')}"],
        }

    return CallableProvider(descriptor, handler)


def register_voice_providers(registry: ProviderRegistry, store: VoiceWorkspaceStore, root: Path) -> None:
    registry.register(build_native_provider(store))
    registry.register(build_whisper_provider(store, root))
