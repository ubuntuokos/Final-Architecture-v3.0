#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

INTEL_PCI_VENDOR = "0x8086"
BDF_RE = re.compile(r"(?:^|/)([0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7])(?:/|$)")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""


def _canonical(path: Path) -> str:
    try:
        return str(path.resolve(strict=True))
    except OSError:
        return str(path)


def _bdf(path: Path) -> str | None:
    match = BDF_RE.search(_canonical(path))
    return match.group(1).lower() if match else None


def _cpu_vendor(proc_cpuinfo: Path) -> tuple[bool, str]:
    text = _read(proc_cpuinfo)
    vendor = ""
    for line in text.splitlines():
        if line.lower().startswith("vendor_id") and ":" in line:
            vendor = line.split(":", 1)[1].strip()
            break
    return vendor == "GenuineIntel", vendor


def _drm_devices(sys_root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    drm = sys_root / "class" / "drm"
    if not drm.exists():
        return result
    for entry in sorted(drm.glob("renderD*")):
        device = entry / "device"
        if not device.exists():
            continue
        vendor = _read(device / "vendor").lower()
        if vendor != INTEL_PCI_VENDOR:
            continue
        result.append({
            "kind": "GPU",
            "physical_key": _bdf(device) or _canonical(device),
            "pci_bdf": _bdf(device),
            "vendor": vendor,
            "device_id": _read(device / "device").lower() or None,
            "drm_render_node": f"/dev/dri/{entry.name}",
            "sysfs_device": _canonical(device),
            "driver": Path(_canonical(device / "driver")).name if (device / "driver").exists() else None,
        })
    return result


def _npu_devices(sys_root: Path, dev_root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    accel = sys_root / "class" / "accel"
    if not accel.exists():
        return result
    for entry in sorted(accel.glob("accel*")):
        device = entry / "device"
        if not device.exists():
            continue
        vendor = _read(device / "vendor").lower()
        driver_name = Path(_canonical(device / "driver")).name if (device / "driver").exists() else ""
        # Current Intel NPU devices are accepted either by Intel PCI vendor or Intel NPU driver identity.
        if vendor and vendor != INTEL_PCI_VENDOR and "ivpu" not in driver_name.lower():
            continue
        if not vendor and "ivpu" not in driver_name.lower():
            continue
        result.append({
            "kind": "NPU",
            "physical_key": _bdf(device) or f"/dev/accel/{entry.name}",
            "pci_bdf": _bdf(device),
            "vendor": vendor or INTEL_PCI_VENDOR,
            "device_id": _read(device / "device").lower() or None,
            "accel_node": str(dev_root / "accel" / entry.name),
            "sysfs_device": _canonical(device),
            "driver": driver_name or None,
        })
    return result


def _probe_openvino() -> dict[str, Any]:
    try:
        import openvino as ov  # type: ignore
        core = ov.Core()
        devices = [str(x) for x in core.available_devices]
        return {"installed": True, "version": getattr(ov, "__version__", "UNKNOWN"), "devices": devices, "error": None}
    except Exception as exc:  # optional provider; absence is not a host failure
        return {"installed": False, "version": None, "devices": [], "error": type(exc).__name__}


def _probe_torch_xpu() -> dict[str, Any]:
    try:
        import torch  # type: ignore
        xpu = getattr(torch, "xpu", None)
        available = bool(xpu is not None and xpu.is_available())
        count = int(xpu.device_count()) if available else 0
        return {"installed": True, "torch_version": getattr(torch, "__version__", "UNKNOWN"), "namespace_present": xpu is not None, "available": available, "device_count": count, "error": None}
    except Exception as exc:
        return {"installed": False, "torch_version": None, "namespace_present": False, "available": False, "device_count": 0, "error": type(exc).__name__}


def discover(
    *,
    sys_root: Path = Path("/sys"),
    dev_root: Path = Path("/dev"),
    proc_cpuinfo: Path = Path("/proc/cpuinfo"),
    openvino_probe: Callable[[], dict[str, Any]] = _probe_openvino,
    torch_xpu_probe: Callable[[], dict[str, Any]] = _probe_torch_xpu,
) -> dict[str, Any]:
    intel_cpu, cpu_vendor = _cpu_vendor(proc_cpuinfo)
    gpu = _drm_devices(sys_root)
    npu = _npu_devices(sys_root, dev_root)
    openvino = openvino_probe()
    torch_xpu = torch_xpu_probe()

    aliases: list[dict[str, str]] = []
    if len(gpu) == 1:
        key = str(gpu[0]["physical_key"])
        if any(str(d).upper().startswith("GPU") for d in openvino.get("devices", [])):
            aliases.append({"physical_key": key, "alias": "OPENVINO:GPU"})
        if torch_xpu.get("available") and int(torch_xpu.get("device_count", 0)) == 1:
            aliases.append({"physical_key": key, "alias": "TORCH_XPU:0"})
    if len(npu) == 1 and any(str(d).upper().startswith("NPU") for d in openvino.get("devices", [])):
        aliases.append({"physical_key": str(npu[0]["physical_key"]), "alias": "OPENVINO:NPU"})

    return {
        "schema": "fa3.intel-capability-snapshot.v1",
        "profile_id": "FA3-INTEL-ACCEL-001",
        "read_only": True,
        "intel_cpu": {"detected": intel_cpu, "vendor_id": cpu_vendor or None},
        "intel_gpu": gpu,
        "intel_npu": npu,
        "providers": {"openvino": openvino, "torch_xpu": torch_xpu},
        "runtime_aliases": aliases,
        "alias_binding_semantics": "AUTO_BIND_ONLY_WHEN_UNAMBIGUOUS_SINGLE_PHYSICAL_DEVICE_OTHERWISE_PROVIDER_ADAPTER_MUST_SUPPLY_MAPPING",
        "current_host_promotion_claim": False,
    }


def main() -> int:
    print(json.dumps(discover(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
