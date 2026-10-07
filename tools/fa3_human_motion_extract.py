#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch


def load_torch(path: Path):
    try: return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError: return torch.load(path, map_location="cpu")


def tensor(value) -> torch.Tensor:
    if isinstance(value, torch.Tensor): return value.detach().cpu().float()
    return torch.as_tensor(value).detach().cpu().float()


def time_major(value: torch.Tensor, *, name: str, trailing: tuple[int, ...] | None = None) -> torch.Tensor:
    x = tensor(value)
    if x.ndim >= 3 and x.shape[0] == 1: x = x[0]
    if trailing and tuple(x.shape[-len(trailing):]) != trailing: raise RuntimeError(f"{name}: unexpected trailing shape {tuple(x.shape)}; expected *{trailing}")
    return x


def get_body_params(pred: dict, key: str) -> dict:
    if key in pred:
        value = pred[key]
        if not isinstance(value, dict): raise RuntimeError(f"{key} is not a dict")
        return value
    suffix = key.replace("body_params_", ""); target_tail = f"_params_{suffix}"; matches = [v for k, v in pred.items() if str(k).endswith(target_tail) and isinstance(v, dict)]
    if len(matches) != 1: raise RuntimeError(f"cannot resolve {key}; matches={len(matches)}")
    return matches[0]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()


def select_indices(names: list[str], tokens: tuple[str, ...]) -> list[int]:
    return sorted(set(i for i, name in enumerate(names) if any(tok in name.lower() for tok in tokens)))


def rms(values: torch.Tensor) -> float:
    return 0.0 if values.numel() == 0 else float(torch.sqrt(torch.mean(values.float() ** 2)).item())


def metric_foot_slide(joints: torch.Tensor, indices: list[int]) -> float:
    if not indices or joints.shape[0] < 2: raise RuntimeError("cannot compute foot sliding: foot/ankle/toe joints not identified")
    pts = joints[:, indices, :]; vertical = pts[..., 1]; floor = torch.quantile(vertical.reshape(-1), 0.10); contact = vertical[:-1] <= (floor + 0.05)
    speed = torch.linalg.vector_norm(pts[1:, :, [0, 2]] - pts[:-1, :, [0, 2]], dim=-1); selected = speed[contact]
    return rms(selected if selected.numel() else speed)


def metric_hand_jitter(joints: torch.Tensor, indices: list[int]) -> float:
    if not indices or joints.shape[0] < 3: raise RuntimeError("cannot compute hand jitter: hand/wrist/finger joints not identified")
    pts = joints[:, indices, :]; second = pts[2:] - 2.0 * pts[1:-1] + pts[:-2]
    return rms(torch.linalg.vector_norm(second, dim=-1))


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--gem-root", required=True); ap.add_argument("--hpe", required=True); ap.add_argument("--vitpose", required=True); ap.add_argument("--camera", required=True); ap.add_argument("--gem-soma-assets", required=True); ap.add_argument("--fps", type=float, required=True); ap.add_argument("--video-frames", type=int, required=True); ap.add_argument("--soma-npz", required=True); ap.add_argument("--metrics", required=True); a = ap.parse_args()
    gem_root = Path(a.gem_root).resolve(); sys.path.insert(0, str(gem_root)); from gem.utils.soma_utils.soma_layer import SomaLayer
    pred = load_torch(Path(a.hpe))
    if not isinstance(pred, dict): raise RuntimeError("GEM-X hpe_results is not a dict")
    body = get_body_params(pred, "body_params_global"); global_orient = time_major(body["global_orient"], name="global_orient"); body_pose = time_major(body["body_pose"], name="body_pose"); transl = time_major(body["transl"], name="transl", trailing=(3,)); identity = time_major(body["identity_coeffs"], name="identity_coeffs"); scale = time_major(body["scale_params"], name="scale_params")
    if body_pose.ndim == 2 and body_pose.shape[-1] == 76 * 3: body_pose = body_pose.reshape(body_pose.shape[0], 76, 3)
    if body_pose.ndim != 3 or body_pose.shape[1:] != (76, 3): raise RuntimeError(f"body_pose must be (F,76,3), got {tuple(body_pose.shape)}")
    if global_orient.ndim != 2 or global_orient.shape[-1] != 3: raise RuntimeError(f"global_orient must be (F,3), got {tuple(global_orient.shape)}")
    frame_count = int(global_orient.shape[0])
    for name, x in (("body_pose", body_pose), ("transl", transl)):
        if int(x.shape[0]) != frame_count: raise RuntimeError(f"{name} frame count mismatch")
    if frame_count != a.video_frames: raise RuntimeError(f"prediction/video frame mismatch {frame_count}!={a.video_frames}")
    if not (a.fps > 0 and math.isfinite(a.fps)): raise RuntimeError("invalid FPS")
    def expand_time(x: torch.Tensor) -> torch.Tensor:
        if x.ndim == 1: x = x[None, :]
        if x.ndim == 2 and x.shape[0] == 1: return x.repeat(frame_count, 1)
        if x.ndim == 2 and x.shape[0] == frame_count: return x
        if x.ndim == 3 and x.shape[0] == 1:
            x = x[0]
            if x.shape[0] == frame_count: return x
        raise RuntimeError(f"cannot normalize identity/scale shape {tuple(x.shape)}")
    identity_t = expand_time(identity); scale_t = expand_time(scale); poses = torch.cat([global_orient[:, None, :], body_pose], dim=1)
    if poses.shape != (frame_count, 77, 3): raise RuntimeError(f"77-joint pose shape failed: {tuple(poses.shape)}")
    if not all(torch.isfinite(x).all().item() for x in (poses, transl, identity_t, scale_t)): raise RuntimeError("non-finite GEM-X body parameters")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1: raise RuntimeError(f"collector expects exactly one HRB-exposed CUDA device, got {torch.cuda.device_count()}")
    soma = SomaLayer(data_root=str(Path(a.gem_soma_assets).resolve()), low_lod=True, device="cuda:0", identity_model_type="mhr", mode="warp")
    with torch.no_grad(): out = soma(global_orient[None].cuda(), body_pose[None].cuda(), identity_t[None].cuda(), scale_t[None].cuda(), transl[None].cuda())
    joints = out["joints"][0].detach().cpu().float()
    if joints.shape[:2] != (frame_count, 77): raise RuntimeError(f"SOMA joints must be (F,77,3), got {tuple(joints.shape)}")
    if not torch.isfinite(joints).all(): raise RuntimeError("non-finite SOMA joints")
    public_names = list(getattr(soma.soma, "public_joint_names", ()))
    if len(public_names) != 77: raise RuntimeError(f"SOMA public joint schema must have 77 joints, got {len(public_names)}")
    vit = load_torch(Path(a.vitpose)); vit = vit[0] if isinstance(vit, tuple) else vit; vit = time_major(vit, name="vitpose")
    if vit.ndim != 3 or vit.shape[1] != 77 or vit.shape[2] < 2: raise RuntimeError(f"VitPose output must be (F,77,C), got {tuple(vit.shape)}")
    if int(vit.shape[0]) != frame_count or not torch.isfinite(vit).all(): raise RuntimeError("VitPose frame count/finite check failed")
    camera = tensor(load_torch(Path(a.camera))); camera = camera[0] if camera.ndim == 4 and camera.shape[0] == 1 else camera
    if camera.shape != (frame_count, 4, 4) or not torch.isfinite(camera).all(): raise RuntimeError(f"camera trajectory must be (F,4,4), got {tuple(camera.shape)}")
    cam_delta = torch.linalg.vector_norm((camera[1:] - camera[:-1]).reshape(max(frame_count - 1, 0), -1), dim=-1); dynamic_camera = bool(cam_delta.numel() and float(cam_delta.max()) > 1e-6)
    root_delta = torch.linalg.vector_norm(transl[1:] - transl[:-1], dim=-1); continuity = float(root_delta.max().item()) if root_delta.numel() else 0.0
    foot_idx = select_indices(public_names, ("foot", "ankle", "toe", "heel")); hand_idx = select_indices(public_names, ("hand", "wrist", "thumb", "index", "middle", "ring", "pinky", "finger")); foot_slide = metric_foot_slide(joints, foot_idx); hand_jitter = metric_hand_jitter(joints, hand_idx)
    identity_mean = identity_t.mean(dim=0, keepdim=True).numpy().astype(np.float32); scale_mean = scale_t.mean(dim=0, keepdim=True)
    if scale_mean.shape[1] < 2: raise RuntimeError("GEM-X scale_params missing global/local scale split")
    global_scale = np.float32(scale_mean[0, 0].item()); local_scale = scale_mean[:, 1:].numpy().astype(np.float32); joint_orient = getattr(soma.soma, "_t_pose_orient", None)
    if joint_orient is None: raise RuntimeError("SOMA T-pose joint orientation unavailable")
    joint_orient = tensor(joint_orient).numpy().astype(np.float32)
    if joint_orient.shape[0] != 77: raise RuntimeError(f"joint_orient must have 77 joints, got {joint_orient.shape}")
    soma_npz = Path(a.soma_npz); soma_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(soma_npz, poses=poses.numpy().astype(np.float32), transl=transl.numpy().astype(np.float32), joint_names=np.asarray(public_names), identity_model_type=np.asarray("mhr"), identity_coeffs=identity_mean, scale_params=local_scale, joint_orient=joint_orient, global_scale=global_scale, keep_root=np.bool_(False), absolute_pose=np.bool_(False), rotation_repr=np.asarray("rotvec"), unit=np.asarray("meters"), source_provider=np.asarray("FA3-PROVIDER-GEM-X-001"), source_revision=np.asarray("32992550dba114c62243fb55e361311972dce8f9"))
    timestamps = torch.arange(frame_count, dtype=torch.float64) / float(a.fps); metrics = {"keypoints_2d": {"joint_count": 77, "frame_count": frame_count, "finite": True}, "motion": {"finite": True, "nan_inf_count": 0, "frame_count": frame_count, "timestamps_monotonic": bool(frame_count <= 1 or torch.all(timestamps[1:] > timestamps[:-1]).item()), "world_space_present": bool(torch.isfinite(joints).all().item() and joints.numel() > 0), "dynamic_camera_trajectory_present": dynamic_camera, "continuity_max_step_m": continuity, "foot_sliding_rms_m": foot_slide, "hand_jitter_rms_m": hand_jitter, "foot_joint_indices": foot_idx, "hand_joint_indices": hand_idx, "camera_max_matrix_step": float(cam_delta.max().item()) if cam_delta.numel() else 0.0}, "soma_npz": {"path": str(soma_npz), "sha256": sha256_file(soma_npz), "joint_count": 77, "frame_count": frame_count, "rotation_repr": "rotvec", "absolute_pose": False}}
    out_path = Path(a.metrics); out_path.parent.mkdir(parents=True, exist_ok=True); out_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); print(json.dumps(metrics, indent=2, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
