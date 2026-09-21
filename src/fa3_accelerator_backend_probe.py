#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Iterable, Mapping

from fa3_hardware_discovery import (
    AcceleratorBackendDescriptor,
    AcceleratorDeviceDescriptor,
)


def _run(argv: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            argv,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", type(exc).__name__
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _normalize_bdf(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().lower()
    match = re.search(r"([0-9a-f]{4,8}):([0-9a-f]{2}):([0-9a-f]{2}\.[0-7])", text)
    if not match:
        return None
    domain = match.group(1)[-4:].zfill(4)
    return f"{domain}:{match.group(2)}:{match.group(3)}"


def _first_version(text: str) -> str | None:
    match = re.search(r"\b(\d+(?:\.\d+){1,3}(?:[-+._a-zA-Z0-9]*)?)\b", text or "")
    return match.group(1) if match else None


def _nvidia_cuda_by_bdf() -> dict[str, dict[str, str | None]]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {}
    rc, out, _ = _run([
        exe,
        "--query-gpu=pci.bus_id,uuid,driver_version",
        "--format=csv,noheader,nounits",
    ])
    if rc != 0:
        return {}
    cuda_version = None
    hrc, header, _ = _run([exe])
    if hrc == 0:
        match = re.search(r"CUDA Version:\s*([0-9.]+)", header)
        cuda_version = match.group(1) if match else None
    result: dict[str, dict[str, str | None]] = {}
    for line in out.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        bdf = _normalize_bdf(parts[0])
        if not bdf:
            continue
        result[bdf] = {
            "uuid": parts[1] or None,
            "driver_version": parts[2] or None,
            "runtime_version": cuda_version,
        }
    return result


def _tool_probe(executable: str, args: list[str]) -> dict[str, Any]:
    path = shutil.which(executable)
    if not path:
        return {
            "tool": executable,
            "detected": False,
            "usable": False,
            "version": None,
            "evidence": (),
        }
    rc, out, err = _run([path, *args])
    joined = "\n".join(part for part in (out, err) if part)
    return {
        "tool": executable,
        "detected": True,
        "usable": rc == 0,
        "version": _first_version(joined),
        "evidence": (f"command:{executable}:rc={rc}",),
    }


def _rocm_probe() -> dict[str, Any]:
    rocminfo = _tool_probe("rocminfo", [])
    hipconfig = _tool_probe("hipconfig", ["--version"])
    return {
        "detected": bool(rocminfo["detected"] or hipconfig["detected"]),
        "usable": bool(rocminfo["usable"]),
        "version": hipconfig["version"] or rocminfo["version"],
        "evidence": tuple(rocminfo["evidence"]) + tuple(hipconfig["evidence"]),
    }


def _level_zero_probe() -> dict[str, Any]:
    zeinfo = _tool_probe("zeinfo", [])
    sycl_ls = _tool_probe("sycl-ls", [])
    return {
        "detected": bool(zeinfo["detected"] or sycl_ls["detected"]),
        "usable": bool(zeinfo["usable"] or sycl_ls["usable"]),
        "version": zeinfo["version"] or sycl_ls["version"],
        "evidence": tuple(zeinfo["evidence"]) + tuple(sycl_ls["evidence"]),
    }


def _portable_probe(executable: str, args: list[str]) -> dict[str, Any]:
    value = _tool_probe(executable, args)
    return {
        "detected": bool(value["detected"]),
        "usable": bool(value["usable"]),
        "version": value["version"],
        "evidence": tuple(value["evidence"]),
    }


def _python_framework_probe(code: str) -> dict[str, Any]:
    rc, out, err = _run([sys.executable, "-c", code], timeout=15)
    return {
        "detected": rc == 0,
        "usable": rc == 0 and out.strip().splitlines()[-1:] == ["AVAILABLE"],
        "version": _first_version(out + "\n" + err),
        "evidence": (f"python-framework-probe:rc={rc}",),
    }


def _pytorch_xpu_probe() -> dict[str, Any]:
    return _python_framework_probe(
        "import torch; print(torch.__version__); "
        "print('AVAILABLE' if hasattr(torch,'xpu') and torch.xpu.is_available() else 'UNAVAILABLE')"
    )


def _openvino_gpu_probe() -> dict[str, Any]:
    return _python_framework_probe(
        "import openvino as ov; print(getattr(ov,'__version__','')); "
        "d=ov.Core().available_devices; print('AVAILABLE' if any(str(x).upper().startswith('GPU') for x in d) else 'UNAVAILABLE')"
    )


def _zluda_probe(environ: Mapping[str, str]) -> dict[str, Any]:
    configured = str(environ.get("FA3_ZLUDA_DIR", "")).strip()
    if not configured:
        return {
            "detected": False,
            "usable": False,
            "version": None,
            "path": None,
            "evidence": (),
        }
    root = Path(configured).expanduser()
    if not root.is_dir():
        return {
            "detected": True,
            "usable": False,
            "version": None,
            "path": str(root),
            "evidence": ("FA3_ZLUDA_DIR:not-a-directory",),
        }
    cuda_shims = list(root.glob("libcuda.so*"))
    return {
        "detected": True,
        "usable": bool(cuda_shims),
        "version": None,
        "path": str(root.resolve()),
        "evidence": (
            "explicit-provider-path:FA3_ZLUDA_DIR",
            f"cuda-shim-count:{len(cuda_shims)}",
        ),
    }


def _host_backend(
    *,
    name: str,
    backend_class: str,
    probe: dict[str, Any],
    bind_to_device: bool,
    framework_backends: tuple[str, ...] = (),
    experimental: bool = False,
) -> AcceleratorBackendDescriptor | None:
    if not probe.get("detected"):
        return None
    binding = "DEVICE" if bind_to_device and probe.get("usable") else "HOST_UNBOUND"
    available = bool(probe.get("usable") and binding == "DEVICE")
    return AcceleratorBackendDescriptor(
        name=name,
        backend_class=backend_class,
        detected=True,
        available=available,
        binding_scope=binding,
        runtime_version=probe.get("version"),
        framework_backends=framework_backends,
        experimental=experimental,
        evidence_sources=tuple(probe.get("evidence", ())),
    )


def enrich_accelerator_backends(
    devices: Iterable[AcceleratorDeviceDescriptor],
    *,
    include_framework_probes: bool = False,
    environ: Mapping[str, str] | None = None,
) -> list[AcceleratorDeviceDescriptor]:
    rows = list(devices)
    env = os.environ if environ is None else environ
    nvidia = _nvidia_cuda_by_bdf()
    rocm = _rocm_probe()
    level_zero = _level_zero_probe()
    vulkan = _portable_probe("vulkaninfo", ["--summary"])
    opencl = _portable_probe("clinfo", ["-l"])
    zluda = _zluda_probe(env)

    intel_xpu = _pytorch_xpu_probe() if include_framework_probes else {"usable": False}
    openvino_gpu = _openvino_gpu_probe() if include_framework_probes else {"usable": False}

    amd_devices = [device for device in rows if device.vendor == "AMD"]
    intel_devices = [device for device in rows if device.vendor == "INTEL" and device.kind == "gpu"]
    gpu_devices = [device for device in rows if device.kind == "gpu"]

    enriched: list[AcceleratorDeviceDescriptor] = []
    for device in rows:
        backends = list(device.backends)
        stable_id = device.stable_device_id
        device_uuid = device.device_uuid

        bdf = _normalize_bdf(device.pci_bdf)
        if device.vendor == "NVIDIA" and bdf in nvidia:
            observed = nvidia[bdf]
            stable_id = observed.get("uuid") or stable_id
            device_uuid = observed.get("uuid") or device_uuid
            backends.append(
                AcceleratorBackendDescriptor(
                    name="cuda",
                    backend_class="native",
                    detected=True,
                    available=True,
                    binding_scope="DEVICE",
                    runtime_version=observed.get("runtime_version"),
                    driver_version=observed.get("driver_version"),
                    framework_backends=(),
                    evidence_sources=("nvidia-smi:exact-pci-bdf-binding",),
                )
            )

        if device.vendor == "AMD" and rocm.get("detected"):
            bound = len(amd_devices) == 1
            descriptor = _host_backend(
                name="rocm",
                backend_class="native",
                probe=rocm,
                bind_to_device=bound,
                framework_backends=("hip",),
            )
            if descriptor is not None:
                backends.append(descriptor)

        if device.vendor == "INTEL" and device.kind == "gpu" and level_zero.get("detected"):
            bound = len(intel_devices) == 1
            frameworks: list[str] = []
            if include_framework_probes and intel_xpu.get("usable"):
                frameworks.append("pytorch-xpu")
            if include_framework_probes and openvino_gpu.get("usable"):
                frameworks.append("openvino")
            descriptor = _host_backend(
                name="level-zero",
                backend_class="native",
                probe=level_zero,
                bind_to_device=bound,
                framework_backends=tuple(frameworks),
            )
            if descriptor is not None:
                backends.append(descriptor)

        if device.kind == "gpu" and vulkan.get("detected"):
            descriptor = _host_backend(
                name="vulkan",
                backend_class="portable",
                probe=vulkan,
                bind_to_device=len(gpu_devices) == 1,
            )
            if descriptor is not None:
                backends.append(descriptor)

        if device.kind == "gpu" and opencl.get("detected"):
            descriptor = _host_backend(
                name="opencl",
                backend_class="portable",
                probe=opencl,
                bind_to_device=len(gpu_devices) == 1,
            )
            if descriptor is not None:
                backends.append(descriptor)

        rocm_bound_here = any(
            backend.name == "rocm" and backend.available
            for backend in backends
        )
        if device.vendor == "AMD" and zluda.get("detected"):
            zluda_probe = {
                **zluda,
                "usable": bool(zluda.get("usable") and rocm_bound_here),
                "evidence": tuple(zluda.get("evidence", ())) + ("requires-device-bound-rocm",),
            }
            descriptor = _host_backend(
                name="zluda",
                backend_class="translation",
                probe=zluda_probe,
                bind_to_device=len(amd_devices) == 1 and rocm_bound_here,
                framework_backends=("cuda-compat",),
                experimental=True,
            )
            if descriptor is not None:
                backends.append(descriptor)

        enriched.append(
            replace(
                device,
                stable_device_id=stable_id,
                device_uuid=device_uuid,
                backends=tuple(backends),
            )
        )
    return enriched


def discover_backend_probe_summary(
    devices: Iterable[AcceleratorDeviceDescriptor],
    *,
    include_framework_probes: bool = False,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    enriched = enrich_accelerator_backends(
        devices,
        include_framework_probes=include_framework_probes,
        environ=environ,
    )
    return {
        "schema": "fa3.accelerator-backend-discovery.v1",
        "devices": [device.as_dict() for device in enriched],
        "admission_semantics": {
            "detected_is_available": False,
            "host_unbound_backend_may_authorize_device": False,
            "available_requires_device_binding": True,
            "translation_requires_explicit_policy": True,
        },
    }
