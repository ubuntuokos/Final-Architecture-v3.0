#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_resource_evidence_normalization_gate import _canonical_payload_hash, validate_evidence_envelope
from fa3_runtime_hardening_current_host import (
    find_key, load_json, normalize_bdf, repo_head, sha256_file, utcnow, write_json,
)

GATE_ID = "FA3-RUNTIME-HARDENING-CURRENT-HOST-GATESET-001"
PCIE_PAYLOAD_KB_S_PER_LANE = {1: 250000.0, 2: 500000.0, 3: 984615.0, 4: 1969230.0, 5: 3938460.0}


def _run(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)


def _gpu_inventory() -> list[dict[str, Any]]:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return []
    proc = _run([smi, "--query-gpu=index,uuid,pci.bus_id", "--format=csv,noheader,nounits"])
    rows = []
    for line in proc.stdout.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) >= 3:
            try:
                rows.append({"index": int(parts[0]), "uuid": parts[1], "pci_bdf": normalize_bdf(parts[2])})
            except ValueError:
                pass
    return rows


def _frame_ptr(frame: Any) -> int | None:
    getter = getattr(frame, "GetPtrToPlane", None)
    if callable(getter):
        try:
            return int(getter(0))
        except Exception:
            pass
    cuda = getattr(frame, "cuda", None)
    if callable(cuda):
        try:
            views = cuda()
            if views:
                iface = getattr(views[0], "__cuda_array_interface__", None)
                if isinstance(iface, dict):
                    return int(iface["data"][0])
        except Exception:
            pass
    return None


def _dlpack_device(frame: Any) -> tuple[int, int] | None:
    for name in ("__dlpack_device__", "dlpack_device"):
        method = getattr(frame, name, None)
        if callable(method):
            try:
                d = method()
                return int(d[0]), int(d[1])
            except Exception:
                pass
    return None


def _resource_binding(path: Path) -> tuple[str, str, str]:
    env = load_json(path)
    errors = validate_evidence_envelope(env)
    if errors or env.get("evidence_class") != "CURRENT_HOST_ADMISSION" or env.get("result", {}).get("status") != "PASS":
        raise RuntimeError("resource-admission evidence envelope invalid: " + ",".join(errors))
    if "CURRENT_HOST_RESOURCE_ADMISSION_PASS" not in env.get("result", {}).get("claims", []):
        raise RuntimeError("resource-admission PASS claim missing")
    payload = env.get("payload", {})
    lease = payload.get("hrb_lease_identity", {})
    uuid = str(lease.get("accelerator_uuid") or "")
    bdf = normalize_bdf(lease.get("pci_bus_id"))
    host_ref = str(env.get("execution_context", {}).get("host_attestation_ref") or "")
    if not uuid or not bdf or not host_ref:
        raise RuntimeError("resource-admission stable GPU or host attestation binding missing")
    return uuid, bdf, host_ref


def _nvml_transfer_telemetry(gpu_uuid: str, workload, *, interval: float) -> tuple[dict[str, Any], str]:
    import pynvml
    pynvml.nvmlInit()
    try:
        handle = None
        for i in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            if str(pynvml.nvmlDeviceGetUUID(h)) == gpu_uuid:
                handle = h
                break
        if handle is None:
            raise RuntimeError("NVML could not resolve HRB GPU UUID")
        tx_kind = getattr(pynvml, "NVML_PCIE_UTIL_TX_BYTES", getattr(pynvml, "NVML_PCIE_UTIL_TX_THROUGHPUT"))
        rx_kind = getattr(pynvml, "NVML_PCIE_UTIL_RX_BYTES", getattr(pynvml, "NVML_PCIE_UTIL_RX_THROUGHPUT"))
        samples: list[dict[str, Any]] = []
        start = time.monotonic()
        workload_started = False
        while time.monotonic() - start < 1.0:
            if not workload_started:
                workload()
                workload_started = True
            tx = int(pynvml.nvmlDeviceGetPcieThroughput(handle, tx_kind))
            rx = int(pynvml.nvmlDeviceGetPcieThroughput(handle, rx_kind))
            gen = int(pynvml.nvmlDeviceGetCurrPcieLinkGeneration(handle))
            width = int(pynvml.nvmlDeviceGetCurrPcieLinkWidth(handle))
            samples.append({"tx_kb_s": tx, "rx_kb_s": rx, "generation": gen, "width": width})
            time.sleep(interval)
        if len(samples) < 10:
            raise RuntimeError("insufficient PCIe samples")
        capacities = [PCIE_PAYLOAD_KB_S_PER_LANE.get(s["generation"], 0.0) * s["width"] for s in samples]
        capacity = max(capacities)
        if capacity <= 0:
            raise RuntimeError("unsupported PCIe link generation")
        max_tx = max(s["tx_kb_s"] for s in samples)
        max_rx = max(s["rx_kb_s"] for s in samples)
        return {
            "present": True,
            "scope": "NEURAL_SEGMENT_AFTER_DEVICE_MEMORY_DECODE",
            "semantics": "ADVISORY_TRANSFER_TELEMETRY_NOT_ZERO_COPY_PROOF",
            "capacity_source": "LIVE_NEGOTIATED_PCIE_LINK_GEN_WIDTH",
            "sampling_interval_seconds": interval,
            "max_tx_kb_s": max_tx,
            "max_rx_kb_s": max_rx,
            "max_observed_link_ratio": max(max_tx, max_rx) / capacity,
            "samples": samples,
            "status": "OBSERVED_NOT_ADMISSION_DECISION",
        }, ""
    finally:
        pynvml.nvmlShutdown()


def _canonical_context(root: Path) -> dict[str, str]:
    baseline = load_json(root / "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json")
    projection = root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
    return {
        "architecture_release": baseline["current_release"],
        "release_baseline_id": baseline["id"],
        "release_manifest_digest": "sha256:" + sha256_file(projection),
    }


def collect(
    root: Path,
    *,
    input_video: Path,
    resource_admission_receipt: Path,
    frame_trace: Path,
    output: Path,
    sampling_interval: float,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": "fa3.media-accelerator-residency-current-host-receipt.v1",
        "surface": "MEDIA_ACCELERATOR_MEMORY_RESIDENCY",
        "provider_id": "FA3-PROVIDER-PYNVVIDEOCODEC-001",
        "repository_head": repo_head(root),
        "captured_at": utcnow(),
        "synthetic": False,
        "global_promotion_claim": False,
        "full_pipeline_zero_copy_claim": False,
    }
    try:
        if not input_video.is_file() or not frame_trace.is_file():
            raise RuntimeError("input video or frame-copy trace missing")
        uuid, bdf, host_ref = _resource_binding(resource_admission_receipt)
        inventory = _gpu_inventory()
        match = next((x for x in inventory if x["uuid"] == uuid and x["pci_bdf"] == bdf), None)
        if not match:
            raise RuntimeError("HRB UUID/BDF does not match live NVIDIA inventory")
        gpu_index = int(match["index"])
        receipt["hrb_binding"] = {
            "status": "PASS", "receipt_sha256": sha256_file(resource_admission_receipt),
            "gpu_uuid": uuid, "pci_bdf": bdf, "gpu_index": gpu_index,
            "stable_accelerator_id": uuid,
            "provider_binding": "NVIDIA_UUID_PLUS_PCI_BDF",
        }

        import PyNvVideoCodec as nvc
        import torch
        module_path = Path(inspect.getfile(nvc)).resolve()
        version = str(getattr(nvc, "__version__", getattr(nvc, "version", "UNKNOWN")))
        decoder = nvc.SimpleDecoder(
            str(input_video), gpu_id=gpu_index, use_device_memory=True, output_color_type=nvc.OutputColorType.RGBP
        )
        frame = decoder[0]
        dev = _dlpack_device(frame)
        if dev is None:
            raise RuntimeError("DecodedFrame does not expose DLPack device")
        tensor = torch.from_dlpack(frame)
        if not tensor.is_cuda:
            raise RuntimeError("DLPack tensor is not CUDA-resident")
        torch.cuda.synchronize(gpu_index)
        frame_ptr = _frame_ptr(frame)
        tensor_ptr = int(tensor.data_ptr())
        if frame_ptr is None or frame_ptr != tensor_ptr:
            raise RuntimeError("DLPack pointer identity not proven")

        def workload() -> None:
            scratch = torch.empty_like(tensor)
            for _ in range(256):
                torch.add(tensor, 1, out=scratch)
                tensor.add_(0)
            torch.cuda.synchronize(gpu_index)

        telemetry, _ = _nvml_transfer_telemetry(uuid, workload, interval=sampling_interval)
        trace = load_json(frame_trace)
        segment = trace.get("neural_segment", {})
        trace_ok = (
            trace.get("schema") == "fa3.accelerator-copy-trace.v1"
            and trace.get("status") == "PASS"
            and trace.get("collector", {}).get("kind") in {"CUPTI", "NSIGHT_SYSTEMS", "CUDA_ACTIVITY_TRACE"}
            and int(segment.get("frame_count", 0)) > 0
            and int(segment.get("host_to_device_frame_copy_count", -1)) == 0
            and int(segment.get("device_to_host_frame_copy_count", -1)) == 0
            and int(segment.get("host_frame_round_trips", -1)) == 0
            and segment.get("shared_accelerator_memory") is True
        )
        if not trace_ok:
            raise RuntimeError("frame-copy trace does not prove zero host round-trips")

        receipt["input_video"] = {"path": str(input_video), "sha256": sha256_file(input_video)}
        receipt["pynvvideocodec"] = {
            "status": "PASS", "version": version, "module_path": str(module_path),
            "module_sha256": sha256_file(module_path), "device_memory_decode": True, "output_color_type": "RGBP",
        }
        receipt["dlpack"] = {
            "status": "PASS", "device_type": dev[0], "device_id": dev[1], "cuda_device_type": dev[0] == 2,
            "frame_pointer": frame_ptr, "tensor_pointer": tensor_ptr, "pointer_identity": frame_ptr == tensor_ptr,
            "torch_tensor_is_cuda": bool(tensor.is_cuda), "torch_device_index": tensor.device.index,
            "torch_cuda_device_match": tensor.device.index == gpu_index, "host_frame_round_trips": 0,
        }
        receipt["memory_residency"] = {
            "status": "PASS",
            "provider_memory_domain": "CUDA_DEVICE_MEMORY",
            "shared_buffer_identity": frame_ptr == tensor_ptr,
            "host_frame_round_trips": 0,
        }
        receipt["copy_telemetry"] = telemetry
        receipt["frame_copy_trace"] = trace
        receipt["classification"] = "ZERO_COPY_PROVEN"

        payload = {
            "repository_head": receipt["repository_head"],
            "hrb_binding": receipt["hrb_binding"],
            "dlpack": receipt["dlpack"],
            "copy_telemetry": telemetry,
            "frame_copy_trace_sha256": sha256_file(frame_trace),
        }
        passed = trace_ok
        receipt["evidence_envelope"] = {
            "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
            "schema_version": "1.0.0",
            "evidence_id": "FA3-MEDIA-ZERO-HOST-" + repo_head(root)[:12],
            "evidence_class": "CURRENT_HOST_RUNTIME",
            "subject": {
                "profile_id": "FA3-MEDIA-GPU-ZEROCOPY-001",
                "provider_id": "FA3-PROVIDER-PYNVVIDEOCODEC-001",
                "gate_id": GATE_ID,
            },
            "canonical_context": _canonical_context(root),
            "execution_context": {
                "host_attestation_ref": host_ref,
                "compute_profile_ref": None,
                "workload_resource_envelope_ref": None,
                "hrb_lease_ref": str(resource_admission_receipt),
                "diagnostics": {},
            },
            "provenance": {
                "collector_id": "FA3-MEDIA-ZERO-HOST-CURRENT-HOST-COLLECTOR-002",
                "collector_revision": "2.0.0",
                "generated_at": utcnow(),
                "artifact_digests": [
                    {"kind": "resource_admission", "sha256": sha256_file(resource_admission_receipt)},
                    {"kind": "frame_copy_trace", "sha256": sha256_file(frame_trace)},
                ],
            },
            "integrity": {"payload_sha256": _canonical_payload_hash(payload)},
            "result": {
                "status": "PASS" if passed else "BLOCKED",
                "scope": "MEDIA_ACCELERATOR_MEMORY_RESIDENCY",
                "claims": ["CURRENT_HOST_PROVIDER_SCOPED_ZERO_COPY_PROVEN"] if passed else [],
                "non_claims": ["GLOBAL_FA3_PROMOTION", "FULL_PIPELINE_TRUE_ZERO_COPY"],
            },
            "payload_schema_id": "fa3.media-zero-host-envelope-payload.v1",
            "payload": payload,
            "promotion_authority": False,
        }
        receipt["result"] = "PASS" if passed else "PENDING"
        receipt["status"] = "CURRENT_HOST_PASS" if passed else "PENDING_CURRENT_HOST"
    except Exception as exc:
        receipt["result"] = "PENDING"
        receipt["status"] = "PENDING_CURRENT_HOST"
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
    receipt["completed_at"] = utcnow()
    write_json(output, receipt)
    return receipt


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(ROOT))
    p.add_argument("--input-video", required=True)
    p.add_argument("--resource-admission-receipt", required=True)
    p.add_argument("--frame-trace", required=True)
    p.add_argument("--sampling-interval", type=float, default=0.02)
    p.add_argument("--output", default="evidence/receipts/media-gpu-zerocopy-current-host.json")
    a = p.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise SystemExit("collector must run rootless")
    if not (0 < a.sampling_interval <= 0.025):
        raise SystemExit("--sampling-interval must be <= 0.025")
    root = Path(a.root).resolve()
    output = Path(a.output)
    if not output.is_absolute():
        output = root / output
    receipt = collect(
        root,
        input_video=Path(a.input_video).resolve(),
        resource_admission_receipt=Path(a.resource_admission_receipt).resolve(),
        frame_trace=Path(a.frame_trace).resolve(),
        output=output,
        sampling_interval=a.sampling_interval,
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
