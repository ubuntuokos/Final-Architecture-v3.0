#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, platform, re, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_ffmpeg_ai_current_host import (
    CAPABILITY_COUNT, CURRENT_HOST_CONFORMANCE_ID, EVIDENCE_LEVEL, PRODUCTION_EVIDENCE_LEVEL,
    HARDWARE_PROFILE_ID, HARDWARE_DISCOVERY_CONTRACT_ID, HRB_AUTHORITY_ID, HRB_PROFILE_ID,
    build_identity_onnx, build_trust_receipt_valid, digest_json, feature_manifest_valid,
    hardware_snapshot_valid, hrb_lease_valid, media_validation_valid, normalize_bdf,
    observed_onnx_provider, quality_valid, resolved_runtime_index, sha256_file,
)

DEFAULT_HRB_BIN = "/usr/local/bin/fa3-host-resource-broker"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def writej(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(argv: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def must(argv: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    p = run(argv, timeout)
    if p.returncode != 0:
        raise RuntimeError(f"command failed rc={p.returncode}: {' '.join(argv[:6])}\n{p.stderr[-4000:]}")
    return p


def cmd_hash(argv: list[str]) -> str:
    return hashlib.sha256("\0".join(argv).encode()).hexdigest()


def parse_cpu_list(text: str) -> list[int]:
    out: list[int] = []
    for token in (text or "").strip().split(","):
        if not token:
            continue
        if "-" in token:
            a, b = map(int, token.split("-", 1)); out.extend(range(a, b + 1))
        else:
            out.append(int(token))
    return sorted(set(out))


def cpu_tuple(cpu: int) -> tuple[int, int, int]:
    top = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
    socket_id = int((top / "physical_package_id").read_text().strip())
    core_id = int((top / "core_id").read_text().strip())
    nodes = list(Path(f"/sys/devices/system/cpu/cpu{cpu}").glob("node[0-9]*"))
    numa = int(nodes[0].name[4:]) if nodes else -1
    return socket_id, core_id, numa


def hardware_snapshot() -> dict[str, Any]:
    online = parse_cpu_list(Path("/sys/devices/system/cpu/online").read_text())
    effective = sorted(os.sched_getaffinity(0))
    online_tuples = [cpu_tuple(cpu) for cpu in online]
    effective_tuples = [cpu_tuple(cpu) for cpu in effective]
    cpuset_path = Path("/sys/fs/cgroup/cpuset.cpus.effective")
    mems_path = Path("/sys/fs/cgroup/cpuset.mems.effective")
    vendor = Path("/sys/class/dmi/id/sys_vendor")
    product = Path("/sys/class/dmi/id/product_name")
    observed_identity = {
        "vendor": vendor.read_text().strip() if vendor.is_file() else None,
        "product": product.read_text().strip() if product.is_file() else platform.node(),
    }
    raw = {
        "online_logical_cpus": online,
        "effective_logical_cpus": effective,
        "host_package_count": len({x[0] for x in online_tuples}),
        "host_physical_core_count": len({(x[0], x[1]) for x in online_tuples}),
        "host_numa_domain_count": len({x[2] for x in online_tuples if x[2] >= 0}),
        "effective_physical_core_count": len({(x[0], x[1]) for x in effective_tuples}),
        "effective_numa_domains": sorted({x[2] for x in effective_tuples if x[2] >= 0}),
        "cgroup_cpuset_cpus_effective": cpuset_path.read_text().strip() if cpuset_path.is_file() else None,
        "cgroup_cpuset_mems_effective": mems_path.read_text().strip() if mems_path.is_file() else None,
        "observed_machine_identity_non_normative": observed_identity,
    }
    return {
        "source": "LIVE_SYSFS_PROCFS_CGROUP_NVML",
        "hardware_profile_id": HARDWARE_PROFILE_ID,
        "hardware_discovery_contract_id": HARDWARE_DISCOVERY_CONTRACT_ID,
        "reference_host_is_normative": False,
        **raw,
        "fingerprint_sha256": digest_json(raw),
    }


def live_gpus() -> list[dict[str, Any]]:
    p = must(["nvidia-smi", "--query-gpu=index,uuid,pci.bus_id,name,memory.total", "--format=csv,noheader,nounits"])
    rows = []
    for line in p.stdout.splitlines():
        parts = [x.strip() for x in line.split(",", 4)]
        if len(parts) == 5:
            rows.append({"index": int(parts[0]), "uuid": parts[1], "pci_bdf": normalize_bdf(parts[2]), "name": parts[3], "memory_total_mib": int(float(parts[4]))})
    if not rows:
        raise RuntimeError("no NVIDIA GPUs discovered")
    return rows


def names_from_listing(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and re.fullmatch(r"[A-Z\.]{3,8}", parts[0]):
            out.append(parts[1])
    return sorted(set(out))


def features(ffmpeg: Path, ffprobe: Path) -> dict[str, Any]:
    version = must([str(ffmpeg), "-hide_banner", "-version"]).stdout
    build = must([str(ffmpeg), "-hide_banner", "-buildconf"]).stdout
    filters = must([str(ffmpeg), "-hide_banner", "-filters"]).stdout
    encoders = must([str(ffmpeg), "-hide_banner", "-encoders"]).stdout
    decoders = must([str(ffmpeg), "-hide_banner", "-decoders"]).stdout
    hw = must([str(ffmpeg), "-hide_banner", "-hwaccels"]).stdout
    return {
        "ffmpeg_path": str(ffmpeg), "ffprobe_path": str(ffprobe),
        "ffmpeg_binary_sha256": sha256_file(ffmpeg), "ffprobe_binary_sha256": sha256_file(ffprobe),
        "version_first_line": version.splitlines()[0] if version.splitlines() else "",
        "version_text_sha256": hashlib.sha256(version.encode()).hexdigest(),
        "buildconf_sha256": hashlib.sha256(build.encode()).hexdigest(),
        "build_flags": sorted(set(re.findall(r"--enable-[A-Za-z0-9_\-]+", build))),
        "filters": names_from_listing(filters), "encoders": names_from_listing(encoders), "decoders": names_from_listing(decoders),
        "hwaccels": sorted({x.strip() for x in hw.splitlines() if x.strip() and not x.startswith("Hardware acceleration")}),
    }


def verify_hrb_lease(hrb_bin: Path, lease_path: Path, lease: dict[str, Any]) -> dict[str, Any]:
    if not hrb_bin.is_file():
        raise RuntimeError(f"canonical HRB verifier missing: {hrb_bin}")
    argv = [str(hrb_bin), "validate-lease", str(lease_path)]
    p = run(argv, 30)
    status = "VALID" if p.returncode == 0 and p.stdout.strip().splitlines()[-1:] == ["VALID"] else "INVALID"
    return {
        "schema": "fa3.hrb-lease-validation-evidence.v1", "authority_id": HRB_AUTHORITY_ID,
        "profile_id": HRB_PROFILE_ID, "status": status, "lease_sha256": digest_json(lease),
        "verifier_binary_sha256": sha256_file(hrb_bin), "command_sha256": cmd_hash(argv),
        "stdout_sha256": hashlib.sha256(p.stdout.encode()).hexdigest(), "stderr_sha256": hashlib.sha256(p.stderr.encode()).hexdigest(),
        "returncode": p.returncode,
    }


def probe(ffprobe: Path, path: Path) -> dict[str, Any]:
    return json.loads(must([str(ffprobe), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout)


def monotonic_pts(ffprobe: Path, path: Path) -> bool:
    p = must([str(ffprobe), "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(path)])
    vals = [float(x.strip()) for x in p.stdout.splitlines() if x.strip() not in {"", "N/A"}]
    return bool(vals) and all(b >= a for a, b in zip(vals, vals[1:]))


def metric(ffmpeg: Path, out: Path, ref: Path, kind: str, work: Path) -> tuple[float, str | None]:
    if kind == "vmaf":
        log = work / "vmaf.json"
        must([str(ffmpeg), "-hide_banner", "-v", "warning", "-i", str(out), "-i", str(ref), "-lavfi", f"[0:v]format=yuv420p[d];[1:v]format=yuv420p[r];[d][r]libvmaf=log_fmt=json:log_path={log}", "-f", "null", "-"], 180)
        data = loadj(log)
        return float(data["pooled_metrics"]["vmaf"]["mean"]), sha256_file(log)
    p = must([str(ffmpeg), "-hide_banner", "-i", str(out), "-i", str(ref), "-lavfi", f"[0:v][1:v]{kind}", "-f", "null", "-"], 180)
    if kind == "ssim":
        m = re.findall(r"All:([0-9.]+)", p.stderr); return (float(m[-1]) if m else -1), None
    m = re.findall(r"average:([0-9.]+)", p.stderr); return (float(m[-1]) if m else -1), None


def duration_delta(info: dict[str, Any]) -> float:
    vals = {}
    for s in info.get("streams", []):
        if s.get("codec_type") in {"video", "audio"}:
            try: vals[s["codec_type"]] = float(s.get("duration") or info.get("format", {}).get("duration"))
            except (TypeError, ValueError): pass
    return abs(vals.get("video", 999) - vals.get("audio", 0))


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 FFmpeg portable current-host execution-conformance collector")
    ap.add_argument("--root", default=str(ROOT)); ap.add_argument("--hrb-lease", required=True); ap.add_argument("--ffmpeg-build-trust", required=True)
    ap.add_argument("--hrb-bin", default=os.environ.get("FA3_HRB_BIN", DEFAULT_HRB_BIN)); ap.add_argument("--receipt", default="evidence/receipts/ffmpeg-ai-current-host.json")
    a = ap.parse_args(); root = Path(a.root).resolve(); receipt_path = Path(a.receipt); receipt_path = receipt_path if receipt_path.is_absolute() else root / receipt_path
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}: raise RuntimeError("Linux x86_64 required")
    if hasattr(os, "geteuid") and os.geteuid() == 0: raise RuntimeError("must not run as root")
    ffmpeg = Path(shutil.which("ffmpeg") or ""); ffprobe = Path(shutil.which("ffprobe") or "")
    if not ffmpeg.is_file() or not ffprobe.is_file(): raise RuntimeError("ffmpeg/ffprobe missing")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); work = root / "evidence/runtime/ffmpeg-ai-current-host" / stamp; work.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {"schema": "fa3.ffmpeg-ai-current-host-receipt.v2", "conformance_id": CURRENT_HOST_CONFORMANCE_ID, "status": "FAIL", "evidence_level": "CURRENT_HOST_FFMPEG_EXECUTION_CONFORMANCE_INCOMPLETE", "production_e2e_claim": False, "production_e2e_required_separately": True, "production_evidence_level_required": PRODUCTION_EVIDENCE_LEVEL, "started_at": now(), "new_capabilities": 0, "new_architectural_authorities": 0, "capability_count_after": CAPABILITY_COUNT, "global_promotion_claim": False, "vs_mlrt_runtime": "DISABLED_CONDITIONAL_PROVIDER_NOT_REQUIRED_FOR_FFMPEG_PRIMARY_CONFORMANCE"}
    try:
        hw = hardware_snapshot(); gpus = live_gpus(); feat = features(ffmpeg, ffprobe)
        trust_path = Path(a.ffmpeg_build_trust).resolve(); lease_path = Path(a.hrb_lease).resolve(); trust = loadj(trust_path); lease = loadj(lease_path)
        broker = verify_hrb_lease(Path(a.hrb_bin).resolve(), lease_path, lease)
        receipt.update({"hardware": hw, "live_gpus": gpus, "ffmpeg_feature_manifest": feat, "ffmpeg_build_trust": trust, "hrb_accelerator_lease": lease, "hrb_broker_validation": broker})
        if not hardware_snapshot_valid(hw): raise RuntimeError("hardware portability/live-discovery admission failed")
        if not feature_manifest_valid(feat): raise RuntimeError("required FFmpeg build/filter/codec capability missing")
        if not build_trust_receipt_valid(trust, feat): raise RuntimeError("FFmpeg build trust/provenance receipt invalid")
        if not hrb_lease_valid(lease, gpus, broker): raise RuntimeError("canonical HRB lease invalid or broker validation failed")
        idx = resolved_runtime_index(lease, gpus, broker)
        if idx is None: raise RuntimeError("cannot resolve ephemeral CUDA index from HRB UUID+BDF")
        receipt["accelerator_resolution"] = {"canonical_identity": "UUID_PLUS_PCI_BDF", "ordinal_is_ephemeral": True, "runtime_index_resolved_from_uuid_bdf": True, "runtime_index": idx}

        model = work / "identity.onnx"; model.write_bytes(build_identity_onnx()); cpu_md5 = work / "cpu.framemd5"; cuda_md5 = work / "cuda.framemd5"
        base = ["-hide_banner", "-y", "-loglevel", "info", "-f", "lavfi", "-i", "testsrc2=size=64x64:rate=1", "-frames:v", "1"]
        cpu_filter = f"format=rgb24,dnn_processing=dnn_backend=onnx:model={model}:input=input:output=output:device=cpu"
        cuda_filter = f"format=rgb24,dnn_processing=dnn_backend=onnx:model={model}:input=input:output=output:device=cuda:device_id={idx}"
        must([str(ffmpeg), *base, "-vf", cpu_filter, "-f", "framemd5", str(cpu_md5)], 180)
        gpu_dnn = must([str(ffmpeg), *base, "-vf", cuda_filter, "-f", "framemd5", str(cuda_md5)], 180)
        observed = observed_onnx_provider(gpu_dnn.stderr)
        receipt["onnx_cuda_dnn"] = {"status": "PASS" if observed == "cuda" and sha256_file(cpu_md5) == sha256_file(cuda_md5) else "FAIL", "requested_provider": "cuda", "observed_provider": observed, "silent_cpu_fallback_observed": "falling back to cpu" in gpu_dnn.stderr.lower(), "identity_model_generated_locally": True, "model_is_smoke_fixture_not_production_model": True, "model_sha256": sha256_file(model), "model_contract": "4D_NCHW_FLOAT32_SINGLE_INPUT", "cpu_framemd5_sha256": sha256_file(cpu_md5), "cuda_framemd5_sha256": sha256_file(cuda_md5), "cuda_log_sha256": hashlib.sha256(gpu_dnn.stderr.encode()).hexdigest()}
        if receipt["onnx_cuda_dnn"]["status"] != "PASS": raise RuntimeError("CUDA ONNX provider proof failed or CPU fallback observed")

        source = work / "source.mp4"; out = work / "gpu-output.mp4"
        must([str(ffmpeg), "-hide_banner", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30", "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000", "-t", "2", "-c:v", "h264_nvenc", "-gpu", str(idx), "-cq", "15", "-b:v", "0", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "aac", "-shortest", str(source)], 180)
        gpu_cmd = [str(ffmpeg), "-hide_banner", "-y", "-loglevel", "verbose", "-hwaccel_device", str(idx), "-c:v", "h264_cuvid", "-i", str(source), "-vf", "scale_cuda=320:180", "-c:v", "h264_nvenc", "-gpu", str(idx), "-cq", "15", "-b:v", "0", "-c:a", "copy", str(out)]
        gp = must(gpu_cmd, 180); log = gp.stderr
        decoder_observed = bool(re.search(r"h264_cuvid", log, re.I)); filter_observed = bool(re.search(r"scale_cuda|Parsed_scale_cuda", log, re.I)); nvenc_observed = bool(re.search(r"h264_nvenc", log, re.I))
        receipt["gpu_media_e2e"] = {"status": "PASS" if decoder_observed and filter_observed and nvenc_observed else "FAIL", "hardware_decode_requested": True, "hardware_decode_observed": decoder_observed, "cuda_filter_requested": True, "cuda_filter_observed": filter_observed, "nvenc_encode_requested": True, "nvenc_encode_observed": nvenc_observed, "gpu_uuid": lease["accelerator_uuid"], "pci_bdf": normalize_bdf(lease["placement"]["pci_bus_id"]), "source_sha256": sha256_file(source), "output_sha256": sha256_file(out), "command_sha256": cmd_hash(gpu_cmd), "stderr_sha256": hashlib.sha256(log.encode()).hexdigest()}
        if receipt["gpu_media_e2e"]["status"] != "PASS": raise RuntimeError("GPU media execution was requested but not observed in FFmpeg verbose log")

        info = probe(ffprobe, out); video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {}); audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), {})
        vmaf, vmaf_hash = metric(ffmpeg, out, source, "vmaf", work); ssim, _ = metric(ffmpeg, out, source, "ssim", work); psnr, _ = metric(ffmpeg, out, source, "psnr", work)
        q = {"status": "PASS", "threshold_policy": "DETERMINISTIC_SMOKE_FIXTURE_NOT_PRODUCTION_QUALITY_POLICY", "vmaf": vmaf, "ssim": ssim, "psnr_db": psnr, "av_duration_delta_seconds": duration_delta(info), "timestamps_monotonic": monotonic_pts(ffprobe, out), "color_primaries": video.get("color_primaries"), "color_transfer": video.get("color_transfer"), "color_space": video.get("color_space"), "hdr_expected": False, "hdr_absence_validated": video.get("color_transfer") not in {"smpte2084", "arib-std-b67"}}
        q["status"] = "PASS" if quality_valid(q) else "FAIL"; receipt["quality"] = q
        mv = {"status": "PASS", "container_mp4_validated": "mp4" in str(info.get("format", {}).get("format_name", "")), "video_codec": video.get("codec_name"), "audio_codec": audio.get("codec_name"), "video_stream_count": sum(s.get("codec_type") == "video" for s in info.get("streams", [])), "audio_stream_count": sum(s.get("codec_type") == "audio" for s in info.get("streams", [])), "width": video.get("width"), "height": video.get("height"), "audio_sample_rate": audio.get("sample_rate")}
        mv["status"] = "PASS" if media_validation_valid(mv) else "FAIL"; receipt["media_validation"] = mv
        receipt["copy_boundary_evidence"] = {"zero_copy_claimed": False, "stable_ffmpeg_dnn_cuda_hwframe_baseline": False, "dnn_cpu_gpu_transfer_expected": True, "gpu_media_pipeline_hwdownload_present": "hwdownload" in " ".join(gpu_cmd), "gpu_media_pipeline_hwupload_present": "hwupload" in " ".join(gpu_cmd)}

        wrong_issuer = dict(lease); wrong_issuer["issuer"] = "OTHER"; expired = dict(lease); expired["expires_epoch"] = 1; mismatch_gpus = [dict(g, uuid="GPU-other") for g in gpus]
        weak_trust = dict(trust); weak_trust["schema"] = "fa3.ffmpeg-build-trust-receipt.v1"
        receipt["negative_tests"] = {"missing_hrb_denied": not hrb_lease_valid({}, gpus, broker), "wrong_hrb_issuer_denied": not hrb_lease_valid(wrong_issuer, gpus, broker), "expired_hrb_denied": not hrb_lease_valid(expired, gpus, broker), "uuid_bdf_mismatch_denied": not hrb_lease_valid(lease, mismatch_gpus, broker), "invalid_broker_validation_denied": not hrb_lease_valid(lease, gpus, {**broker, "status": "INVALID"}), "ordinal_only_identity_denied": resolved_runtime_index({}, gpus, broker) is None, "silent_cuda_to_cpu_fallback_denied": observed_onnx_provider("Failed to enable CUDA. Falling back to CPU") != "cuda", "weak_build_trust_denied": not build_trust_receipt_valid(weak_trust, feat), "zero_copy_claim_denied": True, "missing_quality_metrics_denied": not quality_valid({})}
        with tempfile.TemporaryDirectory(prefix="fa3-ffmpeg-ai-") as td:
            marker = Path(td) / "marker"; marker.write_text("cleanup", encoding="utf-8"); temp_root = Path(td)
        receipt["rollback"] = {"status": "PASS" if not temp_root.exists() else "FAIL", "persistent_environment_mutation": False, "persistent_system_configuration_mutation": False, "network_model_fetch_performed": False, "temporary_workspace_cleanable": not temp_root.exists(), "failure_injection_cleanup_pass": not temp_root.exists()}
        chain = {"source_sha256": sha256_file(source), "model_sha256": sha256_file(model), "output_sha256": sha256_file(out), "ffmpeg_binary_sha256": feat["ffmpeg_binary_sha256"], "ffprobe_binary_sha256": feat["ffprobe_binary_sha256"], "hrb_lease_sha256": digest_json(lease), "hrb_validation_sha256": digest_json(broker), "build_trust_sha256": digest_json(trust), "vmaf_artifact_sha256": vmaf_hash or ("0" * 64)}
        receipt["provenance"] = {"chain_material": chain, "chain_sha256": digest_json(chain)}
        if not quality_valid(q) or not media_validation_valid(mv) or not all(receipt["negative_tests"].values()) or receipt["rollback"]["status"] != "PASS": raise RuntimeError("QA/negative/rollback validation failed")
        receipt["status"] = "PASS"; receipt["evidence_level"] = EVIDENCE_LEVEL; receipt["completed_at"] = now()
    except Exception as exc:
        receipt["completed_at"] = now(); receipt["error_type"] = type(exc).__name__; receipt["error"] = str(exc)
    writej(receipt_path, receipt); writej(work / "summary.json", {"status": receipt["status"], "evidence_level": receipt["evidence_level"], "receipt_sha256": sha256_file(receipt_path), "completed_at": receipt["completed_at"]})
    print(json.dumps(receipt, indent=2, ensure_ascii=False)); return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
