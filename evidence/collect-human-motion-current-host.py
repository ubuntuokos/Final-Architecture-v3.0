#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_human_motion_current_host import (
    CAPABILITY_COUNT,
    CONFORMANCE_ID,
    EVIDENCE_LEVEL,
    GEM_REV,
    SOMA_REV,
    normalize_bdf,
    sha256_file,
    validate_receipt,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def loadj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path.name}")
    return value


def writej(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=str(cwd) if cwd else None, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def must(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    p = run(argv, cwd=cwd, env=env, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"command failed rc={p.returncode}: {' '.join(argv[:8])}\nstdout={p.stdout[-3000:]}\nstderr={p.stderr[-5000:]}")
    return p


def digest_tree(path: Path) -> str:
    if not path.is_dir():
        raise RuntimeError(f"asset directory missing: {path.name}")
    h = hashlib.sha256(); count = 0
    for p in sorted(x for x in path.rglob("*") if x.is_file() and ".git" not in x.parts):
        rel = p.relative_to(path).as_posix()
        h.update(rel.encode("utf-8") + b"\0"); h.update(bytes.fromhex(sha256_file(p))); count += 1
    if count == 0:
        raise RuntimeError(f"asset directory is empty: {path.name}")
    return h.hexdigest()


def git_state(repo: Path, expected: str) -> dict[str, Any]:
    if not (repo / ".git").exists():
        raise RuntimeError(f"not a Git checkout: {repo.name}")
    head = must(["git", "-C", str(repo), "rev-parse", "HEAD"], timeout=30).stdout.strip()
    status = must(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"], timeout=30).stdout
    sub = must(["git", "-C", str(repo), "submodule", "status", "--recursive"], timeout=60).stdout
    bad_submodule = any(line and line[0] in {"-", "+", "U"} for line in sub.splitlines())
    clean = not status.strip() and not bad_submodule
    if head != expected:
        raise RuntimeError(f"{repo.name} revision mismatch: {head} != {expected}")
    if not clean:
        raise RuntimeError(f"{repo.name} checkout is not clean")
    return {"revision": head, "clean": True, "submodules_clean": True}


def parse_cpulist(value: Any) -> set[int]:
    if isinstance(value, list):
        try:
            return {int(x) for x in value}
        except (TypeError, ValueError):
            return set()
    if not isinstance(value, str) or not value.strip():
        return set()
    out: set[int] = set()
    try:
        for token in value.split(","):
            token = token.strip()
            if not token:
                continue
            if "-" in token:
                lo, hi = (int(x) for x in token.split("-", 1))
                if hi < lo:
                    return set()
                out.update(range(lo, hi + 1))
            else:
                out.add(int(token))
    except ValueError:
        return set()
    return out


def online_numa_nodes() -> list[int]:
    p = Path("/sys/devices/system/node/online")
    if not p.is_file():
        return [0]
    nodes = sorted(parse_cpulist(p.read_text(encoding="utf-8").strip()))
    return nodes or [0]


def node_cpus(node: int) -> set[int]:
    p = Path(f"/sys/devices/system/node/node{node}/cpulist")
    if not p.is_file():
        return set()
    return parse_cpulist(p.read_text(encoding="utf-8").strip())


def pci_numa_node(bdf: str) -> int:
    p = Path("/sys/bus/pci/devices") / normalize_bdf(bdf) / "numa_node"
    if not p.is_file():
        return -1
    try:
        return int(p.read_text(encoding="utf-8").strip())
    except ValueError:
        return -1


def live_gpus() -> list[dict[str, Any]]:
    p = must(["nvidia-smi", "--query-gpu=index,uuid,pci.bus_id,name,memory.total,display_active", "--format=csv,noheader,nounits"], timeout=30)
    rows = []
    for line in p.stdout.splitlines():
        parts = [x.strip() for x in line.split(",", 5)]
        if len(parts) == 6:
            bdf = normalize_bdf(parts[2])
            display_active = parts[5].lower() in {"enabled", "active", "yes", "on", "1", "true"}
            rows.append({"index": int(parts[0]), "uuid": parts[1], "pci_bdf": bdf, "name": parts[3], "memory_total_mib": int(float(parts[4])), "display_active": display_active, "numa_node": pci_numa_node(bdf)})
    if not rows:
        raise RuntimeError("no NVIDIA GPU discovered")
    return rows


def parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise RuntimeError("missing expiry")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_hrb(value: dict[str, Any], gpus: list[dict[str, Any]]) -> dict[str, Any]:
    if not (
        value.get("schema") == "fa3.hrb-placement-receipt.v1"
        and value.get("authority_id") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        and value.get("status") in {"ADMITTED", "ACTIVE"}
        and value.get("lease_id")
        and value.get("device_uuid")
        and value.get("pci_bdf")
        and value.get("placement_source") == "LIVE_TOPOLOGY"
        and value.get("static_runtime_ordinal_as_identity") is False
    ):
        raise RuntimeError("invalid HRB placement receipt")
    if not (value.get("accelerator_role") == "COMPUTE" and value.get("compute_eligible") is True and value.get("display_role") is False):
        raise RuntimeError("HRB compute-role/non-display admission missing")
    if value.get("topology_revalidated_at_admission") is not True or value.get("cpu_memory_accelerator_one_placement") is not True:
        raise RuntimeError("HRB topology/locality revalidation evidence missing")

    expires = parse_time(value.get("expires_at"))
    if expires <= datetime.now(timezone.utc):
        raise RuntimeError("HRB lease expired")
    uuid = str(value["device_uuid"]).strip(); bdf = normalize_bdf(str(value["pci_bdf"]))
    matches = [g for g in gpus if g["uuid"] == uuid and normalize_bdf(g["pci_bdf"]) == bdf]
    if len(matches) != 1:
        raise RuntimeError("HRB UUID/BDF does not resolve to exactly one live GPU")
    gpu = matches[0]
    if gpu.get("display_active") is not False:
        raise RuntimeError("HRB selected an accelerator with an active display")

    nodes = online_numa_nodes()
    live_node = int(gpu.get("numa_node", -1))
    if live_node < 0:
        if len(nodes) != 1:
            raise RuntimeError("GPU NUMA locality is unknown on a multi-NUMA-node host")
        live_node = nodes[0]
    if live_node not in nodes:
        raise RuntimeError("GPU NUMA node is not online")
    if value.get("accelerator_numa_node") != live_node:
        raise RuntimeError("HRB accelerator NUMA node does not match live PCI locality")

    cpus = parse_cpulist(value.get("compute_cpu_set"))
    local_cpus = node_cpus(live_node)
    if not cpus or not local_cpus or not cpus.issubset(local_cpus):
        raise RuntimeError("HRB compute CPU set is not NUMA-local to selected accelerator")
    try:
        memory_nodes = sorted({int(x) for x in value.get("memory_numa_nodes", [])})
    except (TypeError, ValueError):
        memory_nodes = []
    if memory_nodes != [live_node]:
        raise RuntimeError("HRB memory placement is not local to selected accelerator")
    locality_mode = value.get("locality_mode")
    expected_modes = {"SINGLE_NUMA_HOST", "NUMA_LOCAL"} if len(nodes) == 1 else {"NUMA_LOCAL"}
    if locality_mode not in expected_modes:
        raise RuntimeError("HRB locality mode is not admissible for live topology")

    return {
        "valid": True,
        "authority_id": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "lease_id_sha256": hashlib.sha256(str(value["lease_id"]).encode("utf-8")).hexdigest(),
        "device_uuid": uuid,
        "pci_bdf": bdf,
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "workload_class": value.get("workload_class"),
        "placement_source": "LIVE_TOPOLOGY",
        "static_runtime_ordinal_as_identity": False,
        "compute_role_admitted": True,
        "accelerator_role": "COMPUTE",
        "compute_eligible": True,
        "display_role": False,
        "topology_revalidated_at_admission": True,
        "cpu_memory_accelerator_one_placement": True,
        "accelerator_numa_node": live_node,
        "compute_cpu_set": sorted(cpus),
        "memory_numa_nodes": memory_nodes,
        "locality_mode": locality_mode,
        "online_numa_nodes": nodes,
    }


def require_schema(value: dict[str, Any], schema: str, label: str) -> None:
    if value.get("schema") != schema:
        raise RuntimeError(f"{label}: schema must be {schema}")


def resolved_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"{label}: path missing")
    p = Path(os.path.expandvars(os.path.expanduser(value))).resolve()
    if not p.exists():
        raise RuntimeError(f"{label}: path does not exist")
    return p


def verify_checkpoint(checkpoint: Path, admission: dict[str, Any], license_receipt: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    require_schema(admission, "fa3.model-artifact-admission-receipt.v1", "checkpoint admission")
    digest = sha256_file(checkpoint)
    if not (admission.get("admitted") is True and admission.get("artifact_sha256") == digest and admission.get("malware_security_admission") in {True, "PASS", "ADMITTED"}):
        raise RuntimeError("checkpoint admission/hash/security mismatch")
    require_schema(license_receipt, "fa3.model-license-receipt.v1", "model license")
    if not (license_receipt.get("license_name") == "NVIDIA Open Model License Agreement" and license_receipt.get("accepted") is True and license_receipt.get("artifact_sha256") == digest):
        raise RuntimeError("NVIDIA model license receipt missing/mismatched")
    return digest, {"artifact_sha256": digest, "admitted": True}, {"license_name": "NVIDIA Open Model License Agreement", "accepted": True, "artifact_sha256": digest}


def verify_runtime_assets(value: dict[str, Any]) -> dict[str, Any]:
    require_schema(value, "fa3.human-motion-runtime-assets-admission.v1", "runtime assets")
    if not (value.get("admitted") is True and value.get("all_third_party_assets_admitted") is True):
        raise RuntimeError("runtime assets are not admitted")
    gem_assets = resolved_path(value.get("gem_soma_assets_path"), "GEM SOMA assets"); soma_root = resolved_path(value.get("soma_x_data_root"), "SOMA-X data root")
    sam3d_ckpt = resolved_path(value.get("sam3d_ckpt_path"), "SAM3D checkpoint"); sam3d_mhr = resolved_path(value.get("sam3d_mhr_path"), "SAM3D MHR asset")
    observed = {"gem_soma_assets_tree_sha256": digest_tree(gem_assets), "soma_x_data_root_sha256": digest_tree(soma_root), "sam3d_ckpt_sha256": sha256_file(sam3d_ckpt), "sam3d_mhr_sha256": sha256_file(sam3d_mhr)}
    for field, actual in observed.items():
        if value.get(field) != actual:
            raise RuntimeError(f"runtime asset hash mismatch: {field}")
    combined = hashlib.sha256(json.dumps(observed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"gem_soma_assets_path": gem_assets, "soma_x_data_root": soma_root, "sam3d_ckpt_path": sam3d_ckpt, "sam3d_mhr_path": sam3d_mhr, "tree_sha256": combined, "admitted": True}


def verify_smplx(value: dict[str, Any], soma_data_root: Path) -> dict[str, Any]:
    require_schema(value, "fa3.smplx-license-asset-receipt.v1", "SMPL-X license/assets")
    root = resolved_path(value.get("data_root"), "SMPL-X data root")
    if root != soma_data_root:
        raise RuntimeError("SMPL-X and SOMA-X converter data roots must be identical")
    digest = digest_tree(root)
    if not (value.get("accepted") is True and value.get("model_assets_present") is True and value.get("asset_sha256") == digest):
        raise RuntimeError("SMPL-X license/asset receipt mismatch")
    return {"license_receipt_valid": True, "model_assets_present": True, "asset_sha256": digest}


def ffprobe_video(path: Path) -> dict[str, Any]:
    p = must(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames,avg_frame_rate,duration:format=duration", "-of", "json", str(path)], timeout=120)
    data = json.loads(p.stdout); streams = data.get("streams", [])
    if not streams:
        raise RuntimeError("input video has no video stream")
    s = streams[0]; frames = int(s.get("nb_read_frames") or 0); duration = float(s.get("duration") or data.get("format", {}).get("duration") or 0)
    num, den = (int(x) for x in str(s.get("avg_frame_rate") or "0/1").split("/", 1)); fps = num / den if den else 0.0
    if frames < 8 or duration <= 0 or fps <= 0:
        raise RuntimeError("validation video is too short or has invalid timing")
    return {"frames": frames, "duration_seconds": duration, "fps": fps}


def verify_video(path: Path, admission: dict[str, Any]) -> dict[str, Any]:
    require_schema(admission, "fa3.media-input-admission-receipt.v1", "video admission"); digest = sha256_file(path)
    if not (admission.get("artifact_sha256") == digest and admission.get("synthetic") is False and admission.get("rights_or_consent_confirmed") is True):
        raise RuntimeError("video rights/consent/non-synthetic admission mismatch")
    return {"sha256": digest, **ffprobe_video(path), "admission": {"artifact_sha256": digest, "synthetic": False, "rights_or_consent_confirmed": True}}


def offline_env(gpu_uuid: str) -> dict[str, str]:
    env = os.environ.copy(); env.update({"CUDA_VISIBLE_DEVICES": gpu_uuid, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PIP_NO_INDEX": "1", "WANDB_MODE": "disabled", "NO_PROXY": "*", "no_proxy": "*"})
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        env.pop(key, None)
    return env


def bwrap(argv: list[str], cwd: Path) -> list[str]:
    return ["bwrap", "--die-with-parent", "--unshare-net", "--bind", "/", "/", "--chdir", str(cwd), "--", *argv]


def inspect_smplx(soma_py: Path, npz: Path, env: dict[str, str]) -> dict[str, Any]:
    code = '''import json, numpy as np, sys\nd=np.load(sys.argv[1], allow_pickle=False)\nrequired=["target_rotations","target_root_translation","per_vertex_error","reconstructed_vertices"]\nmissing=[k for k in required if k not in d]\nfinite=(not missing) and all(np.isfinite(d[k]).all() for k in required)\nerr=d["per_vertex_error"] if "per_vertex_error" in d else np.asarray([np.inf])\nprint(json.dumps({"finite":bool(finite),"missing":missing,"error_mean":float(np.mean(err)),"error_max":float(np.max(err))}))'''
    p = must(bwrap([str(soma_py), "-c", code, str(npz)], npz.parent), env=env, timeout=120); result = json.loads(p.stdout.strip().splitlines()[-1])
    if not result.get("finite"):
        raise RuntimeError(f"SMPL-X roundtrip contains invalid arrays: {result}")
    return result


def dcc_smoke(usd: Path, env: dict[str, str], runtime_dir: Path) -> dict[str, Any]:
    candidates = [("Bforartists", shutil.which("bforartists") or shutil.which("bforartists-bin")), ("Blender", shutil.which("blender"))]
    for app, exe in candidates:
        if not exe:
            continue
        expr = "import bpy;bpy.ops.wm.read_factory_settings(use_empty=True);" + f"bpy.ops.wm.usd_import(filepath={str(usd)!r});" + "print('FA3_DCC_OBJECT_COUNT='+str(len(bpy.data.objects)))"
        p = run(bwrap([exe, "--background", "--factory-startup", "--python-expr", expr], runtime_dir), env=env, timeout=300); log = (p.stdout or "") + "\n" + (p.stderr or "")
        (runtime_dir / "dcc-smoke.log").write_text(log[-20000:], encoding="utf-8", errors="replace"); m = re.search(r"FA3_DCC_OBJECT_COUNT=(\d+)", log); count = int(m.group(1)) if m else 0
        if p.returncode == 0 and count > 0:
            return {"status": "PASS", "application": app, "imported_object_count": count, "log_sha256": hashlib.sha256(log.encode("utf-8", errors="replace")).hexdigest()}
    raise RuntimeError("no successful Bforartists/Blender headless USD import")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=str(ROOT)); ap.add_argument("--gem-root", required=True); ap.add_argument("--soma-x-root", required=True); ap.add_argument("--checkpoint", required=True); ap.add_argument("--checkpoint-admission", required=True); ap.add_argument("--model-license", required=True); ap.add_argument("--soma-assets-admission", required=True); ap.add_argument("--smplx-license", required=True); ap.add_argument("--hrb-receipt", required=True); ap.add_argument("--video", required=True); ap.add_argument("--video-admission", required=True); ap.add_argument("--receipt", default="evidence/receipts/human-motion-current-host.json"); a = ap.parse_args()
    root = Path(a.root).resolve(); receipt_path = Path(a.receipt); receipt_path = receipt_path if receipt_path.is_absolute() else root / receipt_path
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); runtime_dir = root / "evidence/runtime/human-motion-current-host" / stamp; runtime_dir.mkdir(parents=True, exist_ok=True)
    receipt = {"schema": "fa3.human-motion-current-host-receipt.v1", "conformance_id": CONFORMANCE_ID, "status": "FAIL", "evidence_level": "CURRENT_HOST_REAL_VIDEO_GEM_X_SOMA_X_DCC_E2E_INCOMPLETE", "real_current_host_execution": True, "started_at": now(), "new_capabilities": 0, "new_architectural_authorities": 0, "capability_count_after": CAPABILITY_COUNT, "global_promotion_claim": False, "runtime_policy": {"network_fetch_disabled": True, "automatic_model_download_observed": False}}
    try:
        if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
            raise RuntimeError("Linux x86_64 current host required")
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            raise RuntimeError("current-host E2E must not run as root")
        for cmd in ("git", "ffprobe", "nvidia-smi", "bwrap"):
            if not shutil.which(cmd):
                raise RuntimeError(f"required executable missing: {cmd}")
        gem_root = Path(a.gem_root).resolve(); soma_root = Path(a.soma_x_root).resolve(); checkpoint = Path(a.checkpoint).resolve(); video = Path(a.video).resolve()
        for path, label in ((checkpoint, "GEM-X checkpoint"), (video, "input video")):
            if not path.is_file():
                raise RuntimeError(f"{label} missing")
        gem_py = gem_root / ".venv/bin/python"; soma_py = soma_root / ".venv/bin/python"
        if not gem_py.is_file() or not soma_py.is_file():
            raise RuntimeError("pre-provisioned GEM-X and SOMA-X venv Python executables are required")
        sources = {"gem_x": git_state(gem_root, GEM_REV), "soma_x": git_state(soma_root, SOMA_REV)}
        checkpoint_sha, checkpoint_out, model_license_out = verify_checkpoint(checkpoint, loadj(Path(a.checkpoint_admission).resolve()), loadj(Path(a.model_license).resolve()))
        assets = verify_runtime_assets(loadj(Path(a.soma_assets_admission).resolve())); smplx = verify_smplx(loadj(Path(a.smplx_license).resolve()), assets["soma_x_data_root"])
        gpus = live_gpus(); hrb = validate_hrb(loadj(Path(a.hrb_receipt).resolve()), gpus); gpu = next(g for g in gpus if g["uuid"] == hrb["device_uuid"] and normalize_bdf(g["pci_bdf"]) == hrb["pci_bdf"])
        video_info = verify_video(video, loadj(Path(a.video_admission).resolve())); env = offline_env(gpu["uuid"])
        cuda_probe = must(bwrap([str(gem_py), "-c", "import json,torch; print(json.dumps({'available':torch.cuda.is_available(),'count':torch.cuda.device_count(),'name':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))"], gem_root), env=env, timeout=120); cuda = json.loads(cuda_probe.stdout.strip().splitlines()[-1])
        if not (cuda.get("available") is True and cuda.get("count") == 1):
            raise RuntimeError(f"HRB-scoped CUDA probe failed: {cuda}")
        hardware_conformance = {
            "hrb_compute_role_admitted": True,
            "non_display_gpu": gpu["display_active"] is False and hrb["display_role"] is False,
            "uuid_bdf_live_identity": True,
            "numa_locality_evidence": True,
            "cuda_execution": True,
            "no_fallback": True,
            "topology_revalidated_at_admission": hrb["topology_revalidated_at_admission"],
            "cpu_memory_accelerator_one_placement": hrb["cpu_memory_accelerator_one_placement"],
            "accelerator_numa_node": hrb["accelerator_numa_node"],
            "compute_cpu_set": hrb["compute_cpu_set"],
            "memory_numa_nodes": hrb["memory_numa_nodes"],
            "locality_mode": hrb["locality_mode"],
        }
        gem_output = runtime_dir / "gem-output"; gem_cmd = [str(gem_py), str(gem_root / "scripts/demo/demo_soma.py"), "--video", str(video), "--output_root", str(gem_output), "--ckpt", str(checkpoint), "--sam3d_ckpt_path", str(assets["sam3d_ckpt_path"]), "--sam3d_mhr_path", str(assets["sam3d_mhr_path"])]
        gem_run = must(bwrap(gem_cmd, gem_root), env=env, timeout=3600); gem_log = (gem_run.stdout or "") + "\n" + (gem_run.stderr or ""); (runtime_dir / "gem-x.log").write_text(gem_log[-100000:], encoding="utf-8", errors="replace")
        if re.search(r"\bdownload(?:ing|ed)?\b.*huggingface|\[checkpoint\].*download", gem_log, re.I):
            raise RuntimeError("GEM-X attempted runtime model/network download")
        if re.search(r"fall(?:ing)? back to cpu|using cpu execution provider", gem_log, re.I):
            raise RuntimeError("silent CPU fallback observed")
        hpe = sorted(gem_output.rglob("hpe_results.pt")); vitpose = sorted(gem_output.rglob("vitpose.pt")); camera = sorted(gem_output.rglob("camera.pt"))
        if not (len(hpe) == len(vitpose) == len(camera) == 1):
            raise RuntimeError(f"unexpected GEM-X output cardinality hpe={len(hpe)} vitpose={len(vitpose)} camera={len(camera)}")
        soma_npz = runtime_dir / "motion.soma.npz"; metrics_path = runtime_dir / "motion-metrics.json"
        helper_cmd = [str(gem_py), str(root / "tools/fa3_human_motion_extract.py"), "--gem-root", str(gem_root), "--hpe", str(hpe[0]), "--vitpose", str(vitpose[0]), "--camera", str(camera[0]), "--gem-soma-assets", str(assets["gem_soma_assets_path"]), "--fps", str(video_info["fps"]), "--video-frames", str(video_info["frames"]), "--soma-npz", str(soma_npz), "--metrics", str(metrics_path)]
        must(bwrap(helper_cmd, gem_root), env=env, timeout=900); metrics = loadj(metrics_path)
        if not metrics.get("motion", {}).get("dynamic_camera_trajectory_present"):
            raise RuntimeError("dynamic-camera validation failed; static/identity trajectory detected")
        smplx_npz = runtime_dir / "motion.smplx.npz"; inspect_dir = runtime_dir / "smplx-inspect"
        convert_cmd = [str(soma_py), str(soma_root / "tools/pose_converter.py"), "--data-root", str(assets["soma_x_data_root"]), "--source", "soma", "--target", "smplx", "--input", str(soma_npz), "--output", str(smplx_npz), "--device", "cuda", "--inspect-dir", str(inspect_dir), "--export-usd", "--fps", str(video_info["fps"])]
        conversion = must(bwrap(convert_cmd, soma_root), env=env, timeout=3600); conversion_log = (conversion.stdout or "") + "\n" + (conversion.stderr or ""); (runtime_dir / "soma-to-smplx.log").write_text(conversion_log[-100000:], encoding="utf-8", errors="replace")
        if re.search(r"fall(?:ing)? back to cpu", conversion_log, re.I):
            raise RuntimeError("SOMA-X conversion fell back to CPU")
        smplx_stats = inspect_smplx(soma_py, smplx_npz, env); usds = sorted(inspect_dir.rglob("*.usd")) + sorted(inspect_dir.rglob("*.usda")) + sorted(inspect_dir.rglob("*.usdc"))
        if not usds:
            raise RuntimeError("SOMA-X pose converter did not export USD")
        preferred = [p for p in usds if p.name == "target_reconstruction_skeleton.usda"]; usd = preferred[0] if preferred else usds[0]; dcc = dcc_smoke(usd, env, runtime_dir)
        receipt.update({
            "status": "PASS", "evidence_level": EVIDENCE_LEVEL, "completed_at": now(), "sources": sources,
            "checkpoint": {"sha256": checkpoint_sha, "admission": checkpoint_out}, "model_license": model_license_out,
            "soma_assets": {"admitted": True, "tree_sha256": assets["tree_sha256"]}, "smplx": smplx, "hrb": hrb,
            "gpu": {"uuid": gpu["uuid"], "pci_bdf": gpu["pci_bdf"], "name": gpu["name"], "memory_total_mib": gpu["memory_total_mib"], "display_active": gpu["display_active"], "numa_node": hrb["accelerator_numa_node"]},
            "hardware_conformance": hardware_conformance,
            "input_video": video_info,
            "runtime_policy": {"network_fetch_disabled": True, "automatic_model_download_observed": False, "network_namespace": "BUBBLEWRAP_UNSHARE_NET"},
            "execution": {"requested_backend": "cuda", "observed_cuda": True, "silent_cpu_fallback_observed": False, "cross_accelerator_fallback_observed": False, "gpu_uuid": gpu["uuid"], "cuda_device_count_inside_sandbox": cuda["count"], "gem_x_log_sha256": hashlib.sha256(gem_log.encode("utf-8", errors="replace")).hexdigest()},
            "keypoints_2d": metrics["keypoints_2d"], "motion": metrics["motion"],
            "interchange": {"soma_npz_valid": True, "soma_npz_joint_count": metrics["soma_npz"]["joint_count"], "soma_npz_sha256": sha256_file(soma_npz), "smplx_roundtrip_pass": bool(smplx_stats.get("finite")), "smplx_npz_sha256": sha256_file(smplx_npz), "smplx_error_mean": smplx_stats.get("error_mean"), "smplx_error_max": smplx_stats.get("error_max"), "usd_export_pass": True, "usd_sha256": sha256_file(usd)},
            "dcc_smoke": dcc,
        })
        findings = validate_receipt(receipt)
        if findings:
            raise RuntimeError("final current-host receipt failed gate contract: " + json.dumps(findings))
    except Exception as exc:
        receipt["status"] = "FAIL"; receipt["completed_at"] = now(); receipt["error"] = {"type": type(exc).__name__, "message": str(exc)[-6000:]}; writej(receipt_path, receipt); print(json.dumps(receipt, indent=2, ensure_ascii=False)); return 2
    writej(receipt_path, receipt); print(json.dumps(receipt, indent=2, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
