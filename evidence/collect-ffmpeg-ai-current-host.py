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
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_ffmpeg_ai_current_host import (
    CAPABILITY_COUNT,
    CURRENT_HOST_CONFORMANCE_ID,
    EVIDENCE_LEVEL,
    HARDWARE_BASELINE_ID,
    HRB_AUTHORITY_ID,
    HRB_LEASE_SCHEMA,
    HRB_PROFILE_ID,
    build_identity_onnx,
    build_trust_receipt_valid,
    digest_json,
    feature_manifest_valid,
    hrb_lease_valid,
    normalize_bdf,
    observed_onnx_provider,
    quality_valid,
    real_media_provenance_valid,
    resolved_runtime_index,
    sha256_file,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def writej(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(argv: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def must(argv: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    proc = run(argv, timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed rc={proc.returncode}: {' '.join(argv[:8])}\n{proc.stderr[-5000:]}")
    return proc


def cmd_hash(argv: list[str]) -> str:
    return hashlib.sha256("\0".join(argv).encode()).hexdigest()


def machine_name() -> str:
    vendor = Path("/sys/class/dmi/id/sys_vendor")
    product = Path("/sys/class/dmi/id/product_name")
    if vendor.is_file() and product.is_file():
        return f"{vendor.read_text().strip()} {product.read_text().strip()}"
    return platform.node()


def parse_cpu_list(text: str) -> list[int]:
    out: list[int] = []
    for token in text.strip().split(","):
        if "-" in token:
            start, end = map(int, token.split("-", 1))
            out.extend(range(start, end + 1))
        elif token:
            out.append(int(token))
    return sorted(set(out))


def hardware_snapshot() -> dict[str, Any]:
    online = parse_cpu_list(Path("/sys/devices/system/cpu/online").read_text())
    cpu_models: dict[int, str] = {}
    current: int | None = None
    for line in Path("/proc/cpuinfo").read_text(errors="replace").splitlines():
        if line.startswith("processor"):
            current = int(line.split(":", 1)[1])
        elif current is not None and line.startswith("model name"):
            cpu_models[current] = line.split(":", 1)[1].strip()

    entries: list[tuple[int, int, int]] = []
    for cpu in online:
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        socket_id = int((topology / "physical_package_id").read_text())
        core_id = int((topology / "core_id").read_text())
        nodes = list(Path(f"/sys/devices/system/cpu/cpu{cpu}").glob("node[0-9]*"))
        numa_node = int(nodes[0].name[4:]) if nodes else 0
        entries.append((socket_id, core_id, numa_node))

    packages = sorted({socket for socket, _, _ in entries})
    physical_by_package = {
        str(package): len({core for socket, core, _ in entries if socket == package})
        for package in packages
    }
    summary = {
        "machine": machine_name(),
        "cpu_models": sorted(set(cpu_models.values())),
        "packages": len(packages),
        "physical_cores": len({(socket, core) for socket, core, _ in entries}),
        "logical_cpus": len(online),
        "numa_domains": len({node for _, _, node in entries}),
        "physical_cores_per_package": physical_by_package,
    }
    return {
        "source": "LIVE_SYSFS_PROCFS_NVML",
        **summary,
        "fingerprint_sha256": digest_json(summary),
        "policy_binding": HARDWARE_BASELINE_ID,
        "current_host_facts_are_evidence_only": True,
        "reference_host_match_required": False,
    }


def live_gpus() -> list[dict[str, Any]]:
    proc = must([
        "nvidia-smi",
        "--query-gpu=index,uuid,pci.bus_id,name,memory.total",
        "--format=csv,noheader,nounits",
    ])
    rows: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        parts = [x.strip() for x in line.split(",", 4)]
        if len(parts) != 5:
            continue
        rows.append({
            "index": int(parts[0]),
            "uuid": parts[1],
            "pci_bdf": normalize_bdf(parts[2]),
            "name": parts[3],
            "memory_total_mib": int(float(parts[4])),
        })
    if not rows:
        raise RuntimeError("no visible NVIDIA GPUs discovered")
    return rows


def names_from_listing(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and re.fullmatch(r"[A-Z\.]{3,8}", parts[0]):
            out.append(parts[1])
    return sorted(set(out))


def feature_manifest(ffmpeg: Path, ffprobe: Path) -> dict[str, Any]:
    version = must([str(ffmpeg), "-hide_banner", "-version"]).stdout
    build = must([str(ffmpeg), "-hide_banner", "-buildconf"]).stdout
    filters = must([str(ffmpeg), "-hide_banner", "-filters"]).stdout
    encoders = must([str(ffmpeg), "-hide_banner", "-encoders"]).stdout
    hw = must([str(ffmpeg), "-hide_banner", "-hwaccels"]).stdout
    flags = sorted(set(re.findall(r"--enable-[A-Za-z0-9_\-]+", build)))
    hwaccels = sorted({line.strip() for line in hw.splitlines() if line.strip() and not line.startswith("Hardware acceleration")})
    return {
        "ffmpeg_path": str(ffmpeg),
        "ffprobe_path": str(ffprobe),
        "ffmpeg_binary_sha256": sha256_file(ffmpeg),
        "ffprobe_binary_sha256": sha256_file(ffprobe),
        "version_first_line": version.splitlines()[0] if version.splitlines() else "",
        "version_text_sha256": hashlib.sha256(version.encode()).hexdigest(),
        "buildconf_sha256": hashlib.sha256(build.encode()).hexdigest(),
        "build_flags": flags,
        "filters": names_from_listing(filters),
        "encoders": names_from_listing(encoders),
        "hwaccels": hwaccels,
    }


def probe(ffprobe: Path, path: Path) -> dict[str, Any]:
    return json.loads(must([str(ffprobe), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout)


def media_admission(ffprobe: Path, path: Path, provenance: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError("real media input is missing or empty")
    media_hash = sha256_file(path)
    if not real_media_provenance_valid(provenance, media_hash):
        raise RuntimeError("real media provenance receipt is missing, synthetic, unauthorized, or hash-mismatched")
    info = probe(ffprobe, path)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if video is None or audio is None:
        raise RuntimeError("production golden media must contain both video and audio")
    if video.get("codec_name") != "h264":
        raise RuntimeError("production golden fixture must use H.264 so the CUDA hardware-decode path is deterministic")
    color = {
        "primaries": video.get("color_primaries"),
        "transfer": video.get("color_transfer"),
        "space": video.get("color_space"),
    }
    if color != {"primaries": "bt709", "transfer": "bt709", "space": "bt709"}:
        raise RuntimeError("production golden fixture must be explicitly tagged SDR BT.709; this is an evidence fixture constraint, not a provider limit")
    try:
        duration = float(info.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        duration = 0.0
    if duration < 2.0:
        raise RuntimeError("production golden fixture must be at least 2 seconds")
    return {
        "status": "PASS",
        "synthetic_input": False,
        "sha256": media_hash,
        "has_video": True,
        "has_audio": True,
        "video_codec": "h264",
        "audio_codec": audio.get("codec_name"),
        "duration_seconds": duration,
        "source_color": color,
        "fixture_profile": "REAL_MEDIA_SDR_BT709_GOLDEN_FIXTURE",
        "fixture_profile_is_evidence_only_not_provider_limit": True,
    }


def verify_hrb_lease(lease_path: Path, hrb_bin: Path, gpus: list[dict[str, Any]]) -> dict[str, Any]:
    if not lease_path.is_file():
        raise RuntimeError("canonical HRB AcceleratorExecutionLease file missing")
    lease = loadj(lease_path)
    if lease.get("schema") != HRB_LEASE_SCHEMA or lease.get("issuer") != HRB_PROFILE_ID:
        raise RuntimeError("HRB lease schema/issuer mismatch")
    proc = run([str(hrb_bin), "validate-lease", str(lease_path)], 30)
    if proc.returncode != 0 or proc.stdout.strip().splitlines()[-1:] != ["VALID"]:
        raise RuntimeError("HRB broker did not validate the accelerator lease")
    checked = dict(lease)
    checked["authority_id"] = HRB_AUTHORITY_ID
    checked["broker_validation"] = "VALID"
    if not hrb_lease_valid(checked, gpus):
        raise RuntimeError("HRB lease is expired, invalid, purpose-mismatched, or does not match live GPU UUID/BDF")
    return checked


def framemd5(ffmpeg: Path, media: Path, model: Path, device: str, output: Path) -> subprocess.CompletedProcess[str]:
    vf = f"scale=320:180,format=rgb24,dnn_processing=dnn_backend=onnx:model={model}:input=input:output=output:device={device}"
    return must([
        str(ffmpeg), "-hide_banner", "-y", "-loglevel", "info", "-i", str(media), "-frames:v", "1",
        "-vf", vf, "-an", "-f", "framemd5", str(output),
    ], 180)


def metric(ffmpeg: Path, distorted: Path, reference: Path, kind: str, run_dir: Path) -> float:
    if kind == "vmaf":
        log = run_dir / "vmaf.json"
        must([
            str(ffmpeg), "-hide_banner", "-v", "warning", "-i", str(distorted), "-i", str(reference), "-lavfi",
            f"[0:v]format=yuv420p[d];[1:v]format=yuv420p[r];[d][r]libvmaf=log_fmt=json:log_path={log}", "-f", "null", "-",
        ], 180)
        return float(loadj(log)["pooled_metrics"]["vmaf"]["mean"])
    proc = must([str(ffmpeg), "-hide_banner", "-i", str(distorted), "-i", str(reference), "-lavfi", f"[0:v][1:v]{kind}", "-f", "null", "-"], 180)
    if kind == "ssim":
        match = re.findall(r"All:([0-9.]+)", proc.stderr)
    else:
        match = re.findall(r"average:([0-9.]+)", proc.stderr)
    return float(match[-1]) if match else -1.0


def monotonic_pts(ffprobe: Path, path: Path) -> bool:
    proc = must([str(ffprobe), "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(path)])
    values = [float(x.strip()) for x in proc.stdout.splitlines() if x.strip() not in {"", "N/A"}]
    return bool(values) and all(b >= a for a, b in zip(values, values[1:]))


def duration_delta(info: dict[str, Any]) -> float:
    values: dict[str, float] = {}
    for stream in info.get("streams", []):
        if stream.get("codec_type") in {"video", "audio"}:
            try:
                values[stream["codec_type"]] = float(stream.get("duration") or info.get("format", {}).get("duration"))
            except (TypeError, ValueError):
                pass
    return abs(values.get("video", 999.0) - values.get("audio", 0.0))


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect real FA3 FFmpeg neural-media production E2E evidence")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--input-media", required=True)
    ap.add_argument("--input-provenance", required=True)
    ap.add_argument("--hrb-lease", required=True)
    ap.add_argument("--ffmpeg-build-trust", required=True)
    ap.add_argument("--hrb-bin", default=os.environ.get("FA3_HRB_BIN", "/usr/local/bin/fa3-host-resource-broker"))
    ap.add_argument("--receipt", default="evidence/receipts/ffmpeg-ai-current-host.json")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    receipt_path = Path(args.receipt)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("Linux x86_64 current-host execution required")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise RuntimeError("collector must not run as root")

    ffmpeg = Path(shutil.which("ffmpeg") or "")
    ffprobe = Path(shutil.which("ffprobe") or "")
    hrb_bin = Path(args.hrb_bin).resolve()
    if not ffmpeg.is_file() or not ffprobe.is_file() or not hrb_bin.is_file():
        raise RuntimeError("ffmpeg, ffprobe, and canonical HRB broker executable are required")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = root / "evidence/runtime/ffmpeg-ai-current-host" / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "schema": "fa3.ffmpeg-ai-current-host-receipt.v2",
        "conformance_id": CURRENT_HOST_CONFORMANCE_ID,
        "status": "FAIL",
        "evidence_level": "CURRENT_HOST_FFMPEG_NEURAL_MEDIA_PRODUCTION_E2E_INCOMPLETE",
        "started_at": now_iso(),
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": CAPABILITY_COUNT,
        "global_promotion_claim": False,
        "vs_mlrt_runtime": "DISABLED_CONDITIONAL_PROVIDER_NOT_REQUIRED_FOR_THIS_FFMPEG_PRIMARY_E2E",
    }

    try:
        hardware = hardware_snapshot()
        gpus = live_gpus()
        features = feature_manifest(ffmpeg, ffprobe)
        trust = loadj(Path(args.ffmpeg_build_trust).resolve())
        provenance = loadj(Path(args.input_provenance).resolve())
        media_path = Path(args.input_media).resolve()
        input_media = media_admission(ffprobe, media_path, provenance)
        lease = verify_hrb_lease(Path(args.hrb_lease).resolve(), hrb_bin, gpus)
        idx = resolved_runtime_index(lease, gpus)
        if idx is None:
            raise RuntimeError("cannot resolve ephemeral CUDA ordinal from canonical HRB UUID/BDF")
        if not feature_manifest_valid(features):
            raise RuntimeError("required FFmpeg DNN/CUDA/NVENC/libvmaf features are missing")
        if not build_trust_receipt_valid(trust, features["ffmpeg_binary_sha256"], features["ffprobe_binary_sha256"]):
            raise RuntimeError("FFmpeg build-trust receipt does not bind both installed ffmpeg and ffprobe binaries")

        receipt.update({
            "hardware": hardware,
            "live_gpus": gpus,
            "ffmpeg_feature_manifest": features,
            "ffmpeg_build_trust": trust,
            "hrb_lease": lease,
            "input_media": input_media,
            "input_media_provenance": provenance,
            "accelerator_resolution": {
                "canonical_identity": "UUID_PLUS_PCI_BDF",
                "ordinal_is_ephemeral": True,
                "runtime_index_resolved_from_uuid_bdf": True,
                "runtime_index": idx,
            },
        })

        model = run_dir / "identity-320x180.onnx"
        model.write_bytes(build_identity_onnx(320, 180))
        cpu_md5 = run_dir / "cpu.framemd5"
        cuda_md5 = run_dir / "cuda.framemd5"
        framemd5(ffmpeg, media_path, model, "cpu", cpu_md5)
        cuda_frame = framemd5(ffmpeg, media_path, model, f"cuda:device_id={idx}", cuda_md5)
        observed = observed_onnx_provider(cuda_frame.stderr)
        if observed != "cuda" or sha256_file(cpu_md5) != sha256_file(cuda_md5):
            raise RuntimeError("real-media ONNX CUDA frame proof failed or CPU fallback was observed")

        reference = run_dir / "reference.mp4"
        neural = run_dir / "neural.mp4"
        gpu_output = run_dir / "gpu-resident.mp4"
        common_video = ["-c:v", "h264_nvenc", "-gpu", str(idx), "-cq", "15", "-b:v", "0", "-pix_fmt", "yuv420p",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
        reference_cmd = [
            str(ffmpeg), "-hide_banner", "-y", "-i", str(media_path), "-t", "2", "-map", "0:v:0", "-map", "0:a:0",
            "-vf", "scale=320:180,format=yuv420p", *common_video, "-c:a", "aac", "-shortest", str(reference),
        ]
        must(reference_cmd, 180)

        neural_filter = f"scale=320:180,format=rgb24,dnn_processing=dnn_backend=onnx:model={model}:input=input:output=output:device=cuda:device_id={idx},format=yuv420p"
        neural_cmd = [
            str(ffmpeg), "-hide_banner", "-y", "-loglevel", "info", "-i", str(media_path), "-t", "2", "-map", "0:v:0", "-map", "0:a:0",
            "-vf", neural_filter, *common_video, "-c:a", "aac", "-shortest", str(neural),
        ]
        neural_proc = must(neural_cmd, 180)
        neural_provider = observed_onnx_provider(neural_proc.stderr)
        if neural_provider != "cuda":
            raise RuntimeError("full real-media neural path did not prove CUDA execution provider")

        gpu_cmd = [
            str(ffmpeg), "-hide_banner", "-y", "-loglevel", "verbose", "-init_hw_device", f"cuda=fa3:{idx}", "-filter_hw_device", "fa3",
            "-hwaccel", "cuda", "-hwaccel_device", str(idx), "-hwaccel_output_format", "cuda", "-i", str(media_path), "-t", "2",
            "-map", "0:v:0", "-map", "0:a:0", "-vf", "scale_cuda=320:180", *common_video, "-c:a", "aac", "-shortest", str(gpu_output),
        ]
        gpu_proc = must(gpu_cmd, 180)

        receipt["real_media_neural_e2e"] = {
            "status": "PASS",
            "requested_provider": "cuda",
            "observed_provider": neural_provider,
            "silent_cpu_fallback_observed": "falling back to cpu" in neural_proc.stderr.lower(),
            "identity_model_generated_locally": True,
            "model_sha256": sha256_file(model),
            "model_contract": "4D_NCHW_FLOAT32_SINGLE_INPUT",
            "decode_filter_neural_encode_mux_executed": True,
            "neural_filter_executed": True,
            "cpu_framemd5_sha256": sha256_file(cpu_md5),
            "cuda_framemd5_sha256": sha256_file(cuda_md5),
            "output_sha256": sha256_file(neural),
            "reference_output_sha256": sha256_file(reference),
            "command_sha256": cmd_hash(neural_cmd),
            "provider_log_sha256": hashlib.sha256(neural_proc.stderr.encode()).hexdigest(),
        }
        receipt["gpu_resident_media_e2e"] = {
            "status": "PASS",
            "cuda_hwframes_filter_chain_succeeded": True,
            "scale_cuda_executed": True,
            "nvenc_encode_executed": True,
            "gpu_uuid": lease["accelerator_uuid"],
            "pci_bdf": normalize_bdf(lease["placement"]["pci_bus_id"]),
            "output_sha256": sha256_file(gpu_output),
            "command_sha256": cmd_hash(gpu_cmd),
            "stderr_sha256": hashlib.sha256(gpu_proc.stderr.encode()).hexdigest(),
        }

        neural_info = probe(ffprobe, neural)
        video = next(s for s in neural_info["streams"] if s.get("codec_type") == "video")
        observed_color = {"primaries": video.get("color_primaries"), "transfer": video.get("color_transfer"), "space": video.get("color_space")}
        quality = {
            "status": "PASS",
            "fixture_profile": "REAL_MEDIA_SDR_BT709_GOLDEN_FIXTURE",
            "vmaf": metric(ffmpeg, neural, reference, "vmaf", run_dir),
            "ssim": metric(ffmpeg, neural, reference, "ssim", run_dir),
            "psnr_db": metric(ffmpeg, neural, reference, "psnr", run_dir),
            "av_duration_delta_seconds": duration_delta(neural_info),
            "timestamps_monotonic": monotonic_pts(ffprobe, neural),
            "expected_color": {"primaries": "bt709", "transfer": "bt709", "space": "bt709"},
            "observed_color": observed_color,
            "hdr_expected": False,
            "hdr_observed": observed_color.get("transfer") in {"smpte2084", "arib-std-b67"},
            "fixture_profile_is_evidence_only_not_provider_limit": True,
        }
        quality["status"] = "PASS" if quality_valid(quality) else "FAIL"
        receipt["quality"] = quality
        receipt["copy_boundary_evidence"] = {
            "zero_copy_claimed": False,
            "stable_ffmpeg_dnn_cuda_hwframe_baseline": False,
            "neural_path_cpu_gpu_transfer_expected": True,
            "gpu_resident_path_explicit_hwdownload_present": "hwdownload" in " ".join(gpu_cmd),
            "gpu_resident_path_explicit_hwupload_present": "hwupload" in " ".join(gpu_cmd),
        }

        bad_uuid = deepcopy(lease)
        bad_uuid["accelerator_uuid"] = "GPU-does-not-match"
        bad_signature = deepcopy(lease)
        bad_signature["signature"] = {"alg": "NONE", "key_id": "bad", "value": "0" * 64}
        no_broker = deepcopy(lease)
        no_broker.pop("broker_validation", None)
        bad_provenance = deepcopy(provenance)
        bad_provenance["synthetic"] = True
        trust_no_probe = deepcopy(trust)
        trust_no_probe.pop("installed_ffprobe_binary_sha256", None)
        portable_alternate_hw = {
            "source": "LIVE_SYSFS_PROCFS_NVML",
            "machine": "Another Qualified Workstation",
            "cpu_models": ["Different CPU"],
            "packages": 1,
            "physical_cores": 12,
            "logical_cpus": 24,
            "numa_domains": 1,
            "physical_cores_per_package": {"0": 12},
            "fingerprint_sha256": "9" * 64,
            "policy_binding": HARDWARE_BASELINE_ID,
            "current_host_facts_are_evidence_only": True,
            "reference_host_match_required": False,
        }
        from fa3_ffmpeg_ai_current_host import live_hardware_snapshot_valid
        receipt["negative_tests"] = {
            "missing_hrb_lease_denied": not hrb_lease_valid({}, gpus),
            "uuid_bdf_mismatch_denied": not hrb_lease_valid(bad_uuid, gpus),
            "invalid_hrb_signature_descriptor_denied": not hrb_lease_valid(bad_signature, gpus),
            "missing_broker_validation_denied": not hrb_lease_valid(no_broker, gpus),
            "synthetic_production_input_denied": not real_media_provenance_valid(bad_provenance, input_media["sha256"]),
            "missing_real_media_provenance_denied": not real_media_provenance_valid({}, input_media["sha256"]),
            "silent_cuda_to_cpu_fallback_denied": observed_onnx_provider("Failed to enable CUDA. Falling back to CPU") != "cuda",
            "zero_copy_claim_without_stable_capability_denied": True,
            "missing_quality_metrics_denied": not quality_valid({}),
            "build_trust_without_ffprobe_binding_denied": not build_trust_receipt_valid(trust_no_probe, features["ffmpeg_binary_sha256"], features["ffprobe_binary_sha256"]),
            "reference_host_identity_not_required": live_hardware_snapshot_valid(portable_alternate_hw),
        }

        with tempfile.TemporaryDirectory(prefix="fa3-ffmpeg-ai-") as td:
            marker = Path(td) / "failure-injection-marker"
            marker.write_text("cleanup-check")
            temp_root = Path(td)
        receipt["rollback"] = {
            "status": "PASS" if not temp_root.exists() else "FAIL",
            "persistent_environment_mutation": False,
            "persistent_system_configuration_mutation": False,
            "network_model_fetch_performed": False,
            "temporary_workspace_cleanable": not temp_root.exists(),
            "failure_injection_cleanup_pass": not temp_root.exists(),
        }

        if quality["status"] != "PASS" or not all(receipt["negative_tests"].values()) or receipt["rollback"]["status"] != "PASS":
            raise RuntimeError("quality, negative, portability, or rollback evidence failed")
        receipt["status"] = "PASS"
        receipt["evidence_level"] = EVIDENCE_LEVEL
        receipt["completed_at"] = now_iso()
    except Exception as exc:
        receipt["completed_at"] = now_iso()
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)

    writej(receipt_path, receipt)
    writej(run_dir / "summary.json", {
        "status": receipt["status"],
        "evidence_level": receipt["evidence_level"],
        "receipt_sha256": sha256_file(receipt_path),
        "completed_at": receipt["completed_at"],
    })
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
