#!/usr/bin/env python3
"""Current-host telemetry collector for FA3-ACCEL-GUARD-001.

Read-only: collects NVIDIA process/device data when nvidia-smi exists, Linux
accelerator device nodes, and process fd ownership for /dev/accel devices.
No process or device state is changed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from typing import Any

from fa3_hardware_discovery import discover_accelerator_devices


def _run(argv: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(argv, text=True, capture_output=True, check=False)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _csv_rows(text: str, fields: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != len(fields):
            continue
        rows.append(dict(zip(fields, parts)))
    return rows


def _nvidia() -> dict[str, Any]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"available": False, "devices": [], "compute_processes": []}
    dev_fields = ["uuid", "name", "memory.total", "memory.used", "utilization.gpu"]
    rc, out, err = _run([exe, f"--query-gpu={','.join(dev_fields)}", "--format=csv,noheader,nounits"])
    devices = _csv_rows(out, dev_fields) if rc == 0 else []
    proc_fields = ["gpu_uuid", "pid", "process_name", "used_gpu_memory"]
    prc, pout, perr = _run([exe, f"--query-compute-apps={','.join(proc_fields)}", "--format=csv,noheader,nounits"])
    procs = _csv_rows(pout, proc_fields) if prc == 0 else []
    return {
        "available": True,
        "device_query_rc": rc,
        "device_query_error": err,
        "devices": devices,
        "process_query_rc": prc,
        "process_query_error": perr,
        "compute_processes": procs,
    }


def _fd_holders(device_paths: list[str]) -> list[dict[str, Any]]:
    targets = {str(Path(p).resolve()) for p in device_paths}
    holders: list[dict[str, Any]] = []
    if not targets:
        return holders
    for proc_dir in glob.glob("/proc/[0-9]*"):
        pid_text = proc_dir.rsplit("/", 1)[-1]
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        fd_dir = Path(proc_dir) / "fd"
        try:
            entries = list(fd_dir.iterdir())
        except (PermissionError, FileNotFoundError):
            continue
        matched: set[str] = set()
        for fd in entries:
            try:
                target = str(fd.resolve())
            except (PermissionError, FileNotFoundError, OSError):
                continue
            if target in targets:
                matched.add(target)
        if not matched:
            continue
        try:
            name = (Path(proc_dir) / "comm").read_text().strip()
        except (PermissionError, FileNotFoundError):
            name = "unknown"
        try:
            cgroup = (Path(proc_dir) / "cgroup").read_text().strip()
        except (PermissionError, FileNotFoundError):
            cgroup = ""
        holders.append({"pid": pid, "name": name, "devices": sorted(matched), "cgroup": cgroup})
    return sorted(holders, key=lambda x: x["pid"])


def collect() -> dict[str, Any]:
    accel = sorted(glob.glob("/dev/accel/accel*"))
    dri = sorted(glob.glob("/dev/dri/renderD*"))
    inventory = [device.as_dict() for device in discover_accelerator_devices()]
    return {
        "schema": "fa3.accelerator-guard-current-host-receipt.v1",
        "profile_id": "FA3-ACCEL-GUARD-001",
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": socket.gethostname(),
        "uid": os.getuid(),
        "read_only": True,
        "accelerator_inventory": inventory,
        "inventory_source": "FA3-HARDWARE-DISCOVERY-CONTRACTS-001",
        "nvidia": _nvidia(),
        "linux_accel_devices": accel,
        "linux_accel_fd_holders": _fd_holders(accel),
        "drm_render_nodes": dri,
        "limitations": [
            "DRM render-node fd presence alone does not identify per-engine conflict.",
            "NPU usage attribution is provider/kernel dependent; /dev/accel fd ownership is best-effort.",
            "Physical device discovery does not prove compute backend or framework compatibility.",
            "Vendor-specific telemetry enriches the generic inventory but does not replace it.",
            "This collector does not authorize, stop, pause, migrate, or kill workloads."
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = collect()
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
