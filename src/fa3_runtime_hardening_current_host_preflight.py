#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fa3_host_attestation import canonical_sha256, load_artifact
from fa3_hu_aqc_input import validate_bundle
from fa3_resource_evidence_normalization_gate import validate_evidence_envelope
from fa3_runtime_hardening_current_host import repo_head, sha256_file, utcnow, write_json

REQUIRED_COMMANDS = ("git", "podman", "wasmtime", "runsc")
NVIDIA_MEDIA_COMMANDS = ("nvidia-smi",)
NVIDIA_MEDIA_PYTHON_MODULES = ("pynvml", "PyNvVideoCodec", "torch")
FRAME_TRACE_COLLECTORS = {
    "CUPTI", "NSIGHT_SYSTEMS", "CUDA_ACTIVITY_TRACE",
    "ROCPROFILER", "LEVEL_ZERO_TRACE", "VULKAN_TRACE", "PROVIDER_NATIVE_TRACE",
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _command(argv: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def validate_quadlet(path: Path) -> list[str]:
    if not path.is_file():
        return ["installed Quadlet missing"]
    text = path.read_text(encoding="utf-8")
    checks = {
        "Network=none": re.search(r"(?mi)^\s*Network\s*=\s*none\s*$", text),
        "ReadOnly=true": re.search(r"(?mi)^\s*ReadOnly\s*=\s*true\s*$", text),
        "NoNewPrivileges=true": re.search(r"(?mi)^\s*NoNewPrivileges\s*=\s*true\s*$", text),
        "DropCapability=all": re.search(r"(?mi)^\s*DropCapability\s*=.*\ball\b.*$", text),
        "Pull=never": re.search(r"(?mi)^\s*Pull\s*=\s*never\s*$", text),
        "digest-pinned image": re.search(r"(?mi)^\s*Image\s*=.*@sha256:[0-9a-f]{64}\s*$", text),
        "runsc runtime": re.search(r"(?mi)^\s*GlobalArgs\s*=.*(?:--runtime=runsc|--runtime\s+runsc).*$", text),
    }
    return [f"Quadlet requirement missing: {name}" for name, ok in checks.items() if not ok]


def validate_resource_admission(path: Path) -> tuple[list[str], dict[str, Any]]:
    if not path.is_file():
        return ["resource-admission receipt missing"], {}
    try:
        env = _load_json(path)
    except Exception as exc:
        return [f"resource-admission receipt unreadable: {exc}"], {}
    findings = list(validate_evidence_envelope(env))
    if env.get("evidence_class") != "CURRENT_HOST_ADMISSION":
        findings.append("resource-admission evidence_class must be CURRENT_HOST_ADMISSION")
    result = env.get("result", {})
    if result.get("status") != "PASS":
        findings.append("resource-admission receipt is not PASS")
    if "CURRENT_HOST_RESOURCE_ADMISSION_PASS" not in result.get("claims", []):
        findings.append("resource-admission PASS claim missing")
    execution = env.get("execution_context", {})
    host_ref = str(execution.get("host_attestation_ref") or "")
    if not host_ref:
        findings.append("resource-admission host_attestation_ref missing")
    payload = env.get("payload", {})
    attestation = payload.get("host_attestation")
    if isinstance(attestation, dict):
        expected_ref = "sha256:" + canonical_sha256(attestation)
        if host_ref != expected_ref:
            findings.append("resource-admission host_attestation_ref is not bound to the inline attestation digest")
    else:
        findings.append("resource-admission inline host attestation missing")
    lease = payload.get("hrb_lease_identity", {})
    if not lease.get("accelerator_uuid") or not lease.get("pci_bus_id"):
        findings.append("resource-admission HRB accelerator UUID/BDF binding missing")
    return findings, env


def validate_frame_trace(path: Path) -> tuple[list[str], dict[str, Any]]:
    if not path.is_file():
        return ["frame-copy trace missing"], {}
    try:
        trace = _load_json(path)
    except Exception as exc:
        return [f"frame-copy trace unreadable: {exc}"], {}
    findings: list[str] = []
    if trace.get("schema") != "fa3.accelerator-copy-trace.v1":
        findings.append("frame-copy trace schema mismatch")
    if trace.get("status") != "PASS":
        findings.append("frame-copy trace is not PASS")
    collector = trace.get("collector", {})
    if collector.get("kind") not in FRAME_TRACE_COLLECTORS or not collector.get("version"):
        findings.append("frame-copy trace collector unsupported or unversioned")
    segment = trace.get("neural_segment", {})
    try:
        frame_count = int(segment.get("frame_count", 0))
        h2d = int(segment.get("host_to_device_frame_copy_count", -1))
        d2h = int(segment.get("device_to_host_frame_copy_count", -1))
        round_trips = int(segment.get("host_frame_round_trips", -1))
    except (TypeError, ValueError):
        return findings + ["frame-copy trace counters invalid"], trace
    if frame_count <= 0:
        findings.append("frame-copy trace contains no neural frames")
    if h2d != 0 or d2h != 0 or round_trips != 0:
        findings.append("frame-copy trace reports host frame transfer")
    if segment.get("shared_accelerator_memory") is not True:
        findings.append("frame-copy trace does not prove shared accelerator memory")
    if trace.get("full_pipeline_zero_copy_claim") is True and trace.get("full_pipeline_zero_copy_proven") is not True:
        findings.append("unproven full-pipeline zero-copy claim")
    return findings, trace


def validate_file(path: Path, label: str) -> list[str]:
    if not path.is_file():
        return [f"{label} missing"]
    if path.stat().st_size <= 0:
        return [f"{label} empty"]
    return []


def validate_json_file(path: Path, label: str) -> list[str]:
    findings = validate_file(path, label)
    if findings:
        return findings
    try:
        _load_json(path)
    except Exception as exc:
        findings.append(f"{label} unreadable JSON: {exc}")
    return findings


def inspect_running_container(name: str) -> tuple[list[str], dict[str, Any]]:
    podman = shutil.which("podman")
    if not podman:
        return ["podman unavailable"], {}
    proc = _command([podman, "inspect", "--type", "container", name])
    if proc.returncode != 0:
        return [f"agent container not inspectable: {name}"], {}
    try:
        rows = json.loads(proc.stdout)
    except Exception as exc:
        return [f"podman inspect JSON invalid: {exc}"], {}
    if not isinstance(rows, list) or len(rows) != 1:
        return ["podman inspect did not resolve exactly one agent container"], {}
    raw = proc.stdout.lower()
    if "runsc" not in raw:
        return ["running agent container does not resolve to runsc"], rows[0]
    return [], rows[0]


def validate_nvproxy(driver_version: str, required: bool) -> tuple[list[str], dict[str, Any]]:
    if not required:
        return [], {"required": False, "status": "NOT_REQUIRED"}
    runsc = shutil.which("runsc")
    if not runsc:
        return ["runsc unavailable for nvproxy validation"], {}
    proc = _command([runsc, "nvproxy", "list-supported-drivers"])
    text = proc.stdout + "\n" + proc.stderr
    versions = sorted(set(re.findall(r"\b\d{3,4}\.\d+(?:\.\d+)?\b", text)))
    ok = proc.returncode == 0 and driver_version in versions
    return ([] if ok else ["host NVIDIA driver is not admitted by runsc nvproxy"]), {
        "required": True,
        "status": "PASS" if ok else "BLOCKED",
        "host_driver": driver_version,
        "supported_driver_count": len(versions),
        "probe_returncode": proc.returncode,
    }


def host_driver_version() -> str:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return ""
    proc = _command([smi, "--query-gpu=driver_version", "--format=csv,noheader,nounits"])
    if proc.returncode != 0 or not proc.stdout.splitlines():
        return ""
    return proc.stdout.splitlines()[0].strip()


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    findings: list[str] = []

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        findings.append("current-host execution must be rootless")

    required_commands = list(REQUIRED_COMMANDS)
    if args.require_media_claim or args.sandbox_gpu:
        required_commands.extend(NVIDIA_MEDIA_COMMANDS)
    commands = {name: shutil.which(name) for name in required_commands}
    missing_commands = [name for name, path in commands.items() if not path]
    findings.extend(f"required command missing: {name}" for name in missing_commands)

    required_modules = list(NVIDIA_MEDIA_PYTHON_MODULES) if args.require_media_claim else []
    python_modules = {name: importlib.util.find_spec(name) is not None for name in required_modules}
    findings.extend(
        f"required Python module missing: {name}"
        for name, present in python_modules.items()
        if not present
    )

    quadlet = Path(args.quadlet).expanduser().resolve()
    findings.extend(validate_quadlet(quadlet))

    image = str(args.oci_image or "").strip()
    image_preloaded = False
    image_digest_pinned = bool(re.search(r"@sha256:[0-9a-f]{64}$", image, re.I))
    if not image:
        findings.append("OCI image input missing")
    elif not image_digest_pinned:
        findings.append("OCI image must be immutable digest-pinned")
    elif commands.get("podman"):
        image_preloaded = _command(["podman", "image", "exists", image]).returncode == 0
        if not image_preloaded:
            findings.append("OCI image is not preloaded locally; network pull is forbidden")

    container_findings, container_inspect = inspect_running_container(args.agent_container)
    findings.extend(container_findings)

    host_attestation_path = Path(args.host_attestation).expanduser().resolve()
    host_findings, host_attestation_ref, _, host_artifact = load_artifact(host_attestation_path)
    findings.extend(host_findings)

    resource_path = Path(args.resource_admission_receipt).expanduser().resolve() if args.resource_admission_receipt else None
    frame_trace_path = Path(args.frame_trace).expanduser().resolve() if args.frame_trace else None
    input_video = Path(args.input_video).expanduser().resolve() if args.input_video else None
    resource_env: dict[str, Any] = {}
    frame_trace: dict[str, Any] = {}
    if args.require_media_claim:
        if resource_path is None or frame_trace_path is None or input_video is None:
            findings.append("media claim requires resource admission, frame trace and input video")
        else:
            resource_findings, resource_env = validate_resource_admission(resource_path)
            findings.extend(resource_findings)
            resource_host_ref = str(resource_env.get("execution_context", {}).get("host_attestation_ref") or "")
            if host_attestation_ref and resource_host_ref and host_attestation_ref != resource_host_ref:
                findings.append("workflow host_attestation_ref does not match resource-admission evidence")
            frame_findings, frame_trace = validate_frame_trace(frame_trace_path)
            findings.extend(frame_findings)
            findings.extend(validate_file(input_video, "approved input video"))
    hu_audio = Path(args.hu_aqc_audio).expanduser().resolve()
    hu_metrics = Path(args.hu_aqc_metrics).expanduser().resolve()
    findings.extend(validate_file(hu_audio, "Hungarian AQC PCM16 WAV"))
    hu_json_findings = validate_json_file(hu_metrics, "Hungarian AQC scorer bundle")
    findings.extend(hu_json_findings)
    hu_bundle: dict[str, Any] = {}
    if not hu_json_findings:
        hu_bundle = _load_json(hu_metrics)
        findings.extend(validate_bundle(root, audio=hu_audio, bundle=hu_bundle))
        if host_attestation_ref and hu_bundle.get("host_attestation_ref") != host_attestation_ref:
            findings.append("HU-AQC bundle host_attestation_ref does not match preflight attestation")

    driver = host_driver_version() if args.sandbox_gpu else ""
    if args.sandbox_gpu and not driver:
        findings.append("NVIDIA driver version unavailable")
    nvproxy_findings, nvproxy = validate_nvproxy(driver, bool(args.sandbox_gpu))
    findings.extend(nvproxy_findings)

    doctor_path = root / ".fa3-current-host/runner/doctor.json"
    if not doctor_path.is_file():
        findings.append("runner doctor receipt missing; run bin/fa3-current-host-runner-doctor first")
        doctor = {}
    else:
        try:
            doctor = _load_json(doctor_path)
        except Exception as exc:
            doctor = {}
            findings.append(f"runner doctor receipt unreadable: {exc}")
        if doctor and doctor.get("result") != "PASS":
            findings.append("runner doctor receipt is not PASS")
        if doctor and doctor.get("runner_status") != "online":
            findings.append("runner doctor did not prove online status")
        if doctor and doctor.get("required_labels_present") is not True:
            findings.append("runner doctor did not prove required labels")

    passed = not findings
    receipt = {
        "schema": "fa3.runtime-hardening-current-host-preflight.v1",
        "result": "PASS" if passed else "BLOCKED",
        "status": "READY_FOR_REAL_EXECUTION" if passed else "BLOCKED_PRE_EXECUTION",
        "repository_head": repo_head(root),
        "checked_at": utcnow(),
        "execution_scope": "CURRENT_HOST",
        "synthetic": False,
        "global_promotion_claim": False,
        "runner": {
            "doctor_receipt": str(doctor_path),
            "doctor_result": doctor.get("result"),
            "runner_name": doctor.get("runner_name"),
            "runner_status": doctor.get("runner_status"),
            "runner_busy": doctor.get("runner_busy"),
        },
        "commands": commands,
        "python_modules": python_modules,
        "sandbox": {
            "quadlet": str(quadlet),
            "quadlet_sha256": sha256_file(quadlet) if quadlet.is_file() else None,
            "agent_container": args.agent_container,
            "runtime_inspect_present": bool(container_inspect),
            "oci_image": image,
            "oci_image_digest_pinned": image_digest_pinned,
            "oci_image_preloaded": image_preloaded,
            "sandbox_gpu": bool(args.sandbox_gpu),
            "nvproxy": nvproxy,
        },
        "evidence_inputs": {
            "host_attestation_ref": host_attestation_ref,
            "host_attestation": str(host_attestation_path),
            "host_attestation_artifact_sha256": sha256_file(host_attestation_path) if host_attestation_path.is_file() else None,
            "host_attestation_validated": not host_findings and bool(host_artifact),
            "media_claim_required": bool(args.require_media_claim),
            "resource_admission_receipt": str(resource_path) if resource_path else None,
            "resource_admission_sha256": sha256_file(resource_path) if resource_path and resource_path.is_file() else None,
            "frame_trace": str(frame_trace_path) if frame_trace_path else None,
            "frame_trace_sha256": sha256_file(frame_trace_path) if frame_trace_path and frame_trace_path.is_file() else None,
            "frame_trace_collector": frame_trace.get("collector", {}),
            "input_video": str(input_video) if input_video else None,
            "input_video_sha256": sha256_file(input_video) if input_video and input_video.is_file() else None,
            "hu_aqc_audio": str(hu_audio),
            "hu_aqc_audio_sha256": sha256_file(hu_audio) if hu_audio.is_file() else None,
            "hu_aqc_metrics": str(hu_metrics),
            "hu_aqc_metrics_sha256": sha256_file(hu_metrics) if hu_metrics.is_file() else None,
        },
        "findings": sorted(set(findings)),
        "truth_constraints": {
            "preflight_pass_is_runtime_hardening_pass": False,
            "preflight_pass_is_global_promotion": False,
            "network_pull_allowed": False,
            "current_host_collectors_still_required": True,
            "all_applicable_surface_gate_required": True,
            "media_surface_conditional_on_explicit_claim": True,
        },
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    write_json(output, receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fail-fast preflight for FA3 Runtime Hardening real current-host execution")
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--oci-image", required=True)
    p.add_argument("--quadlet", required=True)
    p.add_argument("--agent-container", required=True)
    p.add_argument("--host-attestation", required=True)
    p.add_argument("--sandbox-gpu", action="store_true")
    p.add_argument("--require-media-claim", action="store_true")
    p.add_argument("--resource-admission-receipt", default="")
    p.add_argument("--frame-trace", default="")
    p.add_argument("--input-video", default="")
    p.add_argument("--hu-aqc-audio", required=True)
    p.add_argument("--hu-aqc-metrics", required=True)
    p.add_argument("--output", default=".fa3-current-host/runtime-hardening/preflight.json")
    return p


def main() -> int:
    args = build_parser().parse_args()
    receipt = preflight(args)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
