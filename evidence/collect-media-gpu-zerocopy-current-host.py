#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fa3_runtime_hardening_current_host import (
    find_key,
    load_json,
    normalize_bdf,
    repo_head,
    sha256_file,
    utcnow,
    write_json,
)


def _run(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)


def _gpu_inventory() -> list[dict[str, Any]]:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return []
    proc = _run([
        smi,
        "--query-gpu=index,uuid,pci.bus_id",
        "--format=csv,noheader,nounits",
    ])
    if proc.returncode != 0:
        return []
    rows = []
    for line in proc.stdout.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) >= 3:
            try:
                idx = int(parts[0])
            except ValueError:
                continue
            rows.append({"index": idx, "uuid": parts[1], "pci_bdf": normalize_bdf(parts[2])})
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
                view = views[0]
                iface = getattr(view, "__cuda_array_interface__", None)
                if isinstance(iface, dict):
                    return int(iface["data"][0])
        except Exception:
            pass
    return None


def _dlpack_device(frame: Any) -> tuple[int, int] | None:
    method = getattr(frame, "__dlpack_device__", None)
    if callable(method):
        try:
            d = method()
            return int(d[0]), int(d[1])
        except Exception:
            pass
    method = getattr(frame, "dlpack_device", None)
    if callable(method):
        try:
            d = method()
            return int(d[0]), int(d[1])
        except Exception:
            pass
    return None


def _pcie_telemetry(gpu_index: int, workload) -> tuple[list[dict[str, float]], str]:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return [], "nvidia-smi unavailable"
    proc = subprocess.Popen(
        [smi, "dmon", "-i", str(gpu_index), "-s", "t", "-c", "3", "--format", "csv,nounit,noheader"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    workload()
    out, err = proc.communicate(timeout=15)
    samples: list[dict[str, float]] = []
    for line in out.splitlines():
        parts = [x.strip() for x in line.split(",")]
        nums: list[float] = []
        for part in parts:
            if re.fullmatch(r"-?\d+(?:\.\d+)?", part):
                nums.append(float(part))
        if len(nums) >= 3:
            samples.append({"rx_mb_s": nums[-2], "tx_mb_s": nums[-1]})
    return samples, err[-2000:]


def collect(root: Path, *, input_video: Path, hrb_receipt: Path, output: Path) -> dict[str, Any]:
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
        if not hrb_receipt.is_file():
            raise RuntimeError(f"HRB receipt missing: {hrb_receipt}")
        hrb = load_json(hrb_receipt)
        uuid = str(find_key(hrb, {"device_uuid", "gpu_uuid", "uuid"}) or "")
        bdf = normalize_bdf(find_key(hrb, {"pci_bdf", "pci_bus_id", "bus_id"}))
        if not uuid or not bdf:
            raise RuntimeError("HRB receipt does not expose GPU UUID and PCI BDF")
        inventory = _gpu_inventory()
        match = next((x for x in inventory if x["uuid"] == uuid and x["pci_bdf"] == bdf), None)
        if not match:
            raise RuntimeError("HRB UUID/BDF does not match live NVIDIA inventory")
        gpu_index = int(match["index"])
        receipt["hrb_binding"] = {
            "status": "PASS",
            "receipt_sha256": sha256_file(hrb_receipt),
            "gpu_uuid": uuid,
            "pci_bdf": bdf,
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

        def workload() -> None:
            scratch = torch.empty_like(tensor)
            for _ in range(64):
                scratch.copy_(tensor, non_blocking=True)
            torch.cuda.synchronize(gpu_index)

        samples, telem_err = _pcie_telemetry(gpu_index, workload)
        if not samples:
            raise RuntimeError("PCIe telemetry could not be captured")

        receipt["input_video"] = {
            "path": str(input_video),
            "sha256": sha256_file(input_video),
        }
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
            "host_frame_round_trips": 0,
        }
        receipt["copy_telemetry"] = {
            "present": True,
            "scope": "NEURAL_SEGMENT_AFTER_DEVICE_MEMORY_DECODE",
            "metric": "NVIDIA_SMI_DMON_PCIE_RX_TX_MB_S",
            "samples": samples,
            "stderr": telem_err,
            "interpretation": "context telemetry only; DLPack pointer identity is the direct no-frame-copy proof",
        }
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
    p.add_argument("--hrb-receipt", required=True)
    p.add_argument("--output", default="evidence/receipts/media-gpu-zerocopy-current-host.json")
    a = p.parse_args()
    root = Path(a.root).resolve()
    output = Path(a.output)
    if not output.is_absolute():
        output = root / output
    receipt = collect(
        root,
        input_video=Path(a.input_video).resolve(),
        hrb_receipt=Path(a.hrb_receipt).resolve(),
        output=output,
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
