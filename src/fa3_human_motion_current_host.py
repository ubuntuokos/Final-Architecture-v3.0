#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GEM_REV = "32992550dba114c62243fb55e361311972dce8f9"
SOMA_REV = "d29dbe5a3f5a0b2632ecac91e8d5125f243a7e36"
CAPABILITY_COUNT = 143
CONFORMANCE_ID = "FA3-HUMAN-MOTION-CURRENT-HOST-CONFORMANCE-001"
GATE_ID = "FA3-GATE-HUMAN-MOTION-CURRENT-HOST-001"
EVIDENCE_LEVEL = "CURRENT_HOST_REAL_VIDEO_GEM_X_SOMA_X_DCC_E2E"
RECEIPT_SCHEMA = "fa3.human-motion-current-host-receipt.v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def normalize_bdf(value: str) -> str:
    s = value.strip().lower()
    m = re.fullmatch(r"(?:[0-9a-f]{4,8}:)?([0-9a-f]{2}):([0-9a-f]{2})\.([0-7])", s)
    if not m:
        return s
    return f"0000:{m.group(1)}:{m.group(2)}.{m.group(3)}"


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def validate_receipt(r: dict[str, Any], *, now: datetime | None = None) -> list[dict[str, str]]:
    now = now or datetime.now(timezone.utc)
    findings: list[dict[str, str]] = []
    def check(code: str, ok: bool, message: str) -> None:
        if not ok:
            findings.append(finding(code, message))

    check("HM-HOST-001", r.get("schema") == RECEIPT_SCHEMA and r.get("conformance_id") == CONFORMANCE_ID, "receipt schema/conformance identity mismatch")
    check("HM-HOST-002", r.get("status") == "PASS" and r.get("evidence_level") == EVIDENCE_LEVEL and r.get("real_current_host_execution") is True, "real current-host PASS evidence missing")
    check("HM-HOST-003", r.get("capability_count_after") == CAPABILITY_COUNT and r.get("new_capabilities") == 0 and r.get("new_architectural_authorities") == 0 and r.get("global_promotion_claim") is False, "baseline capability/authority invariant drift")

    src = r.get("sources", {})
    check("HM-HOST-004", src.get("gem_x", {}).get("revision") == GEM_REV, "GEM-X exact revision mismatch")
    check("HM-HOST-005", src.get("soma_x", {}).get("revision") == SOMA_REV, "SOMA-X exact revision mismatch")
    check("HM-HOST-006", src.get("gem_x", {}).get("clean") is True and src.get("soma_x", {}).get("clean") is True, "source checkout is dirty")

    checkpoint = r.get("checkpoint", {})
    admission = checkpoint.get("admission", {})
    check("HM-HOST-007", bool(re.fullmatch(r"[0-9a-f]{64}", str(checkpoint.get("sha256", "")))) and checkpoint.get("sha256") == admission.get("artifact_sha256") and admission.get("admitted") is True, "checkpoint SHA256/admission mismatch")
    lic = r.get("model_license", {})
    check("HM-HOST-008", lic.get("license_name") == "NVIDIA Open Model License Agreement" and lic.get("accepted") is True and lic.get("artifact_sha256") == checkpoint.get("sha256"), "separate NVIDIA model license receipt missing or mismatched")

    soma_assets = r.get("soma_assets", {})
    check("HM-HOST-009", soma_assets.get("admitted") is True and bool(re.fullmatch(r"[0-9a-f]{64}", str(soma_assets.get("tree_sha256", "")))), "SOMA-X asset admission missing")
    smplx = r.get("smplx", {})
    check("HM-HOST-010", smplx.get("license_receipt_valid") is True and smplx.get("model_assets_present") is True and bool(re.fullmatch(r"[0-9a-f]{64}", str(smplx.get("asset_sha256", "")))), "SMPL-X licensed model asset evidence missing")

    hrb = r.get("hrb", {})
    gpu = r.get("gpu", {})
    check("HM-HOST-011", hrb.get("valid") is True and hrb.get("device_uuid") == gpu.get("uuid") and normalize_bdf(str(hrb.get("pci_bdf", ""))) == normalize_bdf(str(gpu.get("pci_bdf", ""))), "HRB lease is not bound to observed GPU UUID/BDF")
    exp = _parse_time(hrb.get("expires_at"))
    check("HM-HOST-012", exp is not None and exp > now, "HRB lease missing or expired")

    video = r.get("input_video", {})
    vadm = video.get("admission", {})
    check("HM-HOST-013", vadm.get("artifact_sha256") == video.get("sha256") and vadm.get("synthetic") is False and vadm.get("rights_or_consent_confirmed") is True and video.get("frames", 0) >= 8 and video.get("duration_seconds", 0) > 0, "real input video rights/non-synthetic admission failed")
    check("HM-HOST-014", r.get("runtime_policy", {}).get("network_fetch_disabled") is True and r.get("runtime_policy", {}).get("automatic_model_download_observed") is False, "runtime network/model fetch policy not proven")

    execution = r.get("execution", {})
    check("HM-HOST-015", execution.get("requested_backend") == "cuda" and execution.get("observed_cuda") is True and execution.get("silent_cpu_fallback_observed") is False and execution.get("gpu_uuid") == gpu.get("uuid"), "CUDA execution identity/fallback proof failed")
    kp = r.get("keypoints_2d", {})
    check("HM-HOST-016", kp.get("joint_count") == 77 and kp.get("frame_count") == video.get("frames") and kp.get("finite") is True, "77-joint keypoint evidence failed")
    motion = r.get("motion", {})
    check("HM-HOST-017", motion.get("finite") is True and motion.get("nan_inf_count") == 0, "non-finite motion output detected")
    check("HM-HOST-018", motion.get("frame_count") == video.get("frames") and motion.get("timestamps_monotonic") is True, "frame/timestamp consistency failed")
    check("HM-HOST-019", motion.get("world_space_present") is True and motion.get("dynamic_camera_trajectory_present") is True, "world-space/dynamic-camera evidence missing")
    check("HM-HOST-020", isinstance(motion.get("continuity_max_step_m"), (int, float)) and 0 <= motion.get("continuity_max_step_m", -1) < 5.0, "motion continuity metric missing/out of bound")
    check("HM-HOST-021", isinstance(motion.get("foot_sliding_rms_m"), (int, float)) and motion.get("foot_sliding_rms_m", -1) >= 0 and isinstance(motion.get("hand_jitter_rms_m"), (int, float)) and motion.get("hand_jitter_rms_m", -1) >= 0, "foot sliding/hand jitter metrics missing")

    interchange = r.get("interchange", {})
    check("HM-HOST-022", interchange.get("soma_npz_valid") is True and interchange.get("soma_npz_joint_count") == 77 and bool(interchange.get("soma_npz_sha256")), "SOMA NPZ projection evidence missing")
    check("HM-HOST-023", interchange.get("smplx_roundtrip_pass") is True and interchange.get("usd_export_pass") is True and bool(interchange.get("usd_sha256")), "SOMA->SMPL-X/USD evidence missing")
    dcc = r.get("dcc_smoke", {})
    check("HM-HOST-024", dcc.get("status") == "PASS" and dcc.get("application") in {"Bforartists", "Blender"} and dcc.get("imported_object_count", 0) > 0, "Bforartists/Blender import smoke failed")
    return findings


def digest_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
