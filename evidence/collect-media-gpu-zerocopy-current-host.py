#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable

from fa3_runtime_hardening_current_host import (
    load_json,
    repo_head,
    sha256_file,
    utcnow,
    write_json,
)
from fa3_runtime_hardening_evidence import (
    PCIE_PAYLOAD_KB_S_PER_LANE,
    build_embedded_evidence_envelope,
    frame_copy_trace_reasons,
    normalize_bdf,
    pcie_copy_budget_reasons,
    resource_admission_binding,
)

COLLECTOR_ID = "FA3-MEDIA-GPU-ZEROCOPY-CURRENT-HOST-COLLECTOR-001"
COLLECTOR_VERSION = "2.0.0"


def _run(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)


def _gpu_inventory() -> list[dict[str, Any]]:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return []
    proc = _run([
        smi,
        "--query-gpu=index,uuid,pci.bus_id,driver_version",
        "--format=csv,noheader,nounits",
    ])
    if proc.returncode != 0:
        return []
    rows = []
    for line in proc.stdout.splitlines():
        parts = [x.strip() for x in line.split(",", 3)]
        if len(parts) != 4:
            continue
        try:
            idx = int(parts[0])
        except ValueError:
            continue
        rows.append({
            "index": idx,
            "uuid": parts[1],
            "pci_bdf": normalize_bdf(parts[2]),
            "driver_version": parts[3],
        })
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


def _nvml_counter_constant(pynvml: Any, primary: str, legacy: str) -> Any:
    if hasattr(pynvml, primary):
        return getattr(pynvml, primary)
    if hasattr(pynvml, legacy):
        return getattr(pynvml, legacy)
    raise RuntimeError(f"pynvml lacks {primary}/{legacy}")


def _pcie_copy_budget(
    *,
    gpu_uuid: str,
    pci_bdf: str,
    workload: Callable[[], None],
    interval: float = 0.02,
    budget_ratio: float = 0.05,
) -> dict[str, Any]:
    try:
        import pynvml
    except Exception as exc:
        raise RuntimeError(f"pynvml unavailable: {exc!r}") from exc

    if not (0 < interval <= 0.025):
        raise ValueError("sampling interval must be <=25 ms")
    if not (0 < budget_ratio <= 0.05):
        raise ValueError("PCIe budget ratio must be <=5 percent")

    pynvml.nvmlInit()
    try:
        handle = None
        for idx in range(pynvml.nvmlDeviceGetCount()):
            candidate = pynvml.nvmlDeviceGetHandleByIndex(idx)
            if str(pynvml.nvmlDeviceGetUUID(candidate)) == gpu_uuid:
                handle = candidate
                break
        if handle is None:
            raise RuntimeError("NVML could not resolve HRB-assigned GPU UUID")

        tx_kind = _nvml_counter_constant(pynvml, "NVML_PCIE_UTIL_TX_BYTES", "NVML_PCIE_UTIL_TX_THROUGHPUT")
        rx_kind = _nvml_counter_constant(pynvml, "NVML_PCIE_UTIL_RX_BYTES", "NVML_PCIE_UTIL_RX_THROUGHPUT")

        failure: list[BaseException] = []

        def runner() -> None:
            try:
                workload()
            except BaseException as exc:
                failure.append(exc)

        thread = threading.Thread(target=runner, name="fa3-media-gpu-workload", daemon=True)
        thread.start()
        samples: list[dict[str, Any]] = []
        while thread.is_alive():
            generation = int(pynvml.nvmlDeviceGetCurrPcieLinkGeneration(handle))
            width = int(pynvml.nvmlDeviceGetCurrPcieLinkWidth(handle))
            samples.append({
                "tx_kb_s": int(pynvml.nvmlDeviceGetPcieThroughput(handle, tx_kind)),
                "rx_kb_s": int(pynvml.nvmlDeviceGetPcieThroughput(handle, rx_kind)),
                "generation": generation,
                "width": width,
            })
            time.sleep(interval)
        thread.join()
        if failure:
            raise RuntimeError(f"GPU workload failed: {failure[0]!r}")
        if len(samples) < 10:
            raise RuntimeError("GPU workload completed before 10 PCIe samples were captured")

        capacities = []
        for sample in samples:
            per_lane = PCIE_PAYLOAD_KB_S_PER_LANE.get(int(sample["generation"]))
            if per_lane:
                capacities.append(per_lane * int(sample["width"]))
        if not capacities:
            raise RuntimeError("live negotiated PCIe generation is not supported by capacity model")

        capacity = max(capacities)
        budget = capacity * budget_ratio
        max_tx = max(int(x["tx_kb_s"]) for x in samples)
        max_rx = max(int(x["rx_kb_s"]) for x in samples)
        status = "PASS" if max_tx < budget and max_rx < budget else "FAIL"
        raw_digest = hashlib.sha256(
            json.dumps(samples, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return {
            "present": True,
            "status": status,
            "scope": "NEURAL_SEGMENT_AFTER_DEVICE_MEMORY_DECODE",
            "semantics": "SUPPORTING_COPY_BUDGET_NOT_ZERO_COPY_PROOF",
            "gpu_uuid": gpu_uuid,
            "pci_bdf": normalize_bdf(pci_bdf),
            "sampling_interval_seconds": interval,
            "sample_count": len(samples),
            "max_tx_kb_s": max_tx,
            "max_rx_kb_s": max_rx,
            "budget_kb_s": round(budget, 3),
            "budget_ratio": budget_ratio,
            "capacity_source": "LIVE_NEGOTIATED_PCIE_LINK_GEN_WIDTH",
            "capacity_model": "PCIE_STANDARD_EFFECTIVE_PAYLOAD_APPROXIMATION_V1",
            "observed_link_gen_width": sorted({
                (int(x["generation"]), int(x["width"])) for x in samples
            }),
            "raw_samples_sha256": raw_digest,
            "interpretation": "supporting copy-budget telemetry only; never zero-copy proof",
        }
    finally:
        pynvml.nvmlShutdown()


def collect(
    root: Path,
    *,
    input_video: Path,
    resource_admission_receipt: Path,
    frame_copy_trace_path: Path,
    output: Path,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": "fa3.media-gpu-zerocopy-current-host-receipt.v1",
        "surface": "MEDIA_GPU_ZERO_HOST_ROUND_TRIP",
        "repository_head": repo_head(root),
        "captured_at": utcnow(),
        "synthetic": False,
        "global_promotion_claim": False,
        "full_pipeline_zero_copy_claim": False,
    }
    try:
        if not input_video.is_file():
            raise RuntimeError(f"input video missing: {input_video}")
        if not resource_admission_receipt.is_file():
            raise RuntimeError(f"resource-admission receipt missing: {resource_admission_receipt}")
        if not frame_copy_trace_path.is_file():
            raise RuntimeError(f"frame-copy trace missing: {frame_copy_trace_path}")

        resource_admission = load_json(resource_admission_receipt)
        binding, binding_reasons = resource_admission_binding(resource_admission)
        if binding_reasons or binding is None:
            raise RuntimeError("invalid current-host resource admission: " + "; ".join(binding_reasons))

        inventory = _gpu_inventory()
        match = next(
            (
                x for x in inventory
                if x["uuid"] == binding["gpu_uuid"]
                and x["pci_bdf"] == binding["pci_bdf"]
            ),
            None,
        )
        if not match:
            raise RuntimeError("resource-admission UUID/BDF does not match live NVIDIA inventory")
        gpu_index = int(match["index"])
        receipt["hrb_binding"] = {
            "status": "PASS",
            "resource_admission_receipt_sha256": sha256_file(resource_admission_receipt),
            "resource_admission_evidence_id": binding["resource_admission_evidence_id"],
            "broker_validation": True,
            "gpu_uuid": binding["gpu_uuid"],
            "pci_bdf": binding["pci_bdf"],
            "gpu_index": gpu_index,
        }

        import PyNvVideoCodec as nvc
        import torch

        module_path = Path(inspect.getfile(nvc)).resolve()
        version = str(getattr(nvc, "__version__", getattr(nvc, "version", "UNKNOWN")))
        decoder = nvc.SimpleDecoder(
            str(input_video),
            gpu_id=gpu_index,
            use_device_memory=True,
            output_color_type=nvc.OutputColorType.RGBP,
        )
        frame = decoder[0]
        dev = _dlpack_device(frame)
        if dev is None:
            raise RuntimeError("DecodedFrame does not expose a DLPack device")
        tensor = torch.from_dlpack(frame)
        if not tensor.is_cuda:
            raise RuntimeError("DLPack tensor is not CUDA-resident")
        torch.cuda.synchronize(gpu_index)
        frame_ptr = _frame_ptr(frame)
        tensor_ptr = int(tensor.data_ptr())
        if frame_ptr is None or frame_ptr != tensor_ptr:
            raise RuntimeError("DLPack pointer identity could not be proven")
        if tensor.device.index != gpu_index:
            raise RuntimeError("DLPack tensor CUDA device does not match HRB-selected GPU")

        scratch = torch.empty_like(tensor)

        def workload() -> None:
            deadline = time.monotonic() + 0.50
            while time.monotonic() < deadline:
                torch.add(tensor, 1, out=scratch)
            torch.cuda.synchronize(gpu_index)

        telemetry = _pcie_copy_budget(
            gpu_uuid=binding["gpu_uuid"],
            pci_bdf=binding["pci_bdf"],
            workload=workload,
        )
        telemetry_reasons = pcie_copy_budget_reasons(
            telemetry,
            gpu_uuid=binding["gpu_uuid"],
            pci_bdf=binding["pci_bdf"],
        )
        if telemetry_reasons:
            raise RuntimeError("PCIe copy-budget validation failed: " + "; ".join(telemetry_reasons))

        frame_trace = load_json(frame_copy_trace_path)
        trace_reasons = frame_copy_trace_reasons(
            frame_trace,
            gpu_uuid=binding["gpu_uuid"],
            pci_bdf=binding["pci_bdf"],
        )
        if trace_reasons:
            raise RuntimeError("frame-copy trace validation failed: " + "; ".join(trace_reasons))

        receipt["input_video"] = {"path": str(input_video), "sha256": sha256_file(input_video)}
        receipt["pynvvideocodec"] = {
            "status": "PASS",
            "version": version,
            "cuda_version": str(getattr(nvc, "__cuda_version__", "UNKNOWN")),
            "video_codec_sdk_version": str(getattr(nvc, "__video_codec_sdk_version__", "UNKNOWN")),
            "module_path": str(module_path),
            "module_sha256": sha256_file(module_path),
            "device_memory_decode": True,
            "output_color_type": "RGBP",
        }
        receipt["dlpack"] = {
            "status": "PASS",
            "device_type": dev[0],
            "device_id": dev[1],
            "cuda_device_type": dev[0] == 2,
            "frame_pointer": frame_ptr,
            "tensor_pointer": tensor_ptr,
            "pointer_identity": frame_ptr == tensor_ptr,
            "torch_tensor_is_cuda": bool(tensor.is_cuda),
            "torch_device_index": tensor.device.index,
            "torch_cuda_device_match": tensor.device.index == gpu_index,
        }
        receipt["copy_telemetry"] = telemetry
        receipt["frame_copy_trace"] = frame_trace

        evidence_payload = {
            "schema": "fa3.media-gpu-zerocopy-current-host.payload.v2",
            "resource_admission_evidence_id": binding["resource_admission_evidence_id"],
            "gpu_uuid": binding["gpu_uuid"],
            "pci_bdf": binding["pci_bdf"],
            "pynvvideocodec_module_sha256": sha256_file(module_path),
            "dlpack_pointer_identity": frame_ptr == tensor_ptr,
            "frame_copy_trace_sha256": sha256_file(frame_copy_trace_path),
            "pcie_copy_budget": {
                "max_tx_kb_s": telemetry["max_tx_kb_s"],
                "max_rx_kb_s": telemetry["max_rx_kb_s"],
                "budget_kb_s": telemetry["budget_kb_s"],
                "sample_count": telemetry["sample_count"],
                "sampling_interval_seconds": telemetry["sampling_interval_seconds"],
            },
            "claim_semantics": "ZERO_HOST_FRAME_ROUND_TRIP_DURING_NEURAL_SEGMENT",
            "pcie_copy_budget_is_zero_copy_proof": False,
        }
        receipt["evidence_payload"] = evidence_payload
        receipt["evidence_envelope"] = build_embedded_evidence_envelope(
            resource_admission=resource_admission,
            payload_schema_id=evidence_payload["schema"],
            payload=evidence_payload,
            subject={
                "profile_id": "FA3-MEDIA-GPU-ZEROCOPY-001",
                "provider_id": "FA3-PROVIDER-PYNVVIDEOCODEC-001",
                "gate_id": "FA3-GATE-RUNTIME-HARDENING-CURRENT-HOST-001",
            },
            collector_id=COLLECTOR_ID,
            collector_revision=COLLECTOR_VERSION,
            generated_at=receipt["captured_at"],
            claims=[
                "CURRENT_HOST_GPU_ZERO_HOST_ROUND_TRIP_PASS",
                "CURRENT_HOST_PCIE_COPY_BUDGET_PASS",
            ],
            non_claims=["GLOBAL_FA3_PROMOTION", "FULL_PIPELINE_TRUE_ZERO_COPY"],
            artifact_digests=[
                {"kind": "resource_admission", "sha256": sha256_file(resource_admission_receipt)},
                {"kind": "input_video", "sha256": sha256_file(input_video)},
                {"kind": "frame_copy_trace", "sha256": sha256_file(frame_copy_trace_path)},
            ],
        )
        receipt["result"] = "PASS"
        receipt["status"] = "CURRENT_HOST_PASS"
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
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--input-video", required=True)
    p.add_argument(
        "--resource-admission-receipt",
        "--hrb-receipt",
        dest="resource_admission_receipt",
        required=True,
        help="FA3-EVIDENCE-ENVELOPE-001 CURRENT_HOST_ADMISSION PASS; --hrb-receipt kept as compatibility alias",
    )
    p.add_argument("--frame-copy-trace", required=True)
    p.add_argument("--output", default="evidence/receipts/media-gpu-zerocopy-current-host.json")
    a = p.parse_args()
    root = Path(a.root).resolve()
    output = Path(a.output)
    if not output.is_absolute():
        output = root / output
    receipt = collect(
        root,
        input_video=Path(a.input_video).resolve(),
        resource_admission_receipt=Path(a.resource_admission_receipt).resolve(),
        frame_copy_trace_path=Path(a.frame_copy_trace).resolve(),
        output=output,
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
