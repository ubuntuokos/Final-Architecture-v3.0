#!/usr/bin/env python3
"""FA3 ROCm current-host evidence collector.

Fail-closed rules:
- No eligible AMD GPU => NOT_APPLICABLE_NOT_MATERIALIZED (not a failure, never PASS).
- AMD GPU without usable ROCm => PENDING/FAIL depending on discovered state, never PASS.
- PASS requires live AMD hardware, rocminfo or amd-smi visibility, HIP/ROCm tooling,
  and a successful minimal device enumeration path.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

POLICY_ID = "FA3-ACCEL-ROCM-001"
AMD_VENDOR = "0x1002"


def run(argv: list[str], timeout: int = 15) -> dict:
    exe = shutil.which(argv[0])
    if not exe:
        return {"command": argv[0], "present": False, "returncode": None, "stdout": "", "stderr": ""}
    try:
        proc = subprocess.run([exe, *argv[1:]], text=True, capture_output=True, timeout=timeout, check=False)
        return {
            "command": argv[0],
            "present": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-4000:],
        }
    except Exception as exc:
        return {"command": argv[0], "present": True, "returncode": None, "stdout": "", "stderr": repr(exc)}


def amd_pci_devices() -> list[dict]:
    devices = []
    root = Path("/sys/bus/pci/devices")
    if root.exists():
        for dev in sorted(root.iterdir()):
            try:
                vendor = (dev / "vendor").read_text().strip().lower()
                klass = (dev / "class").read_text().strip().lower()
            except OSError:
                continue
            if vendor == AMD_VENDOR and klass.startswith(("0x03", "0x12")):
                devices.append({"pci": dev.name, "vendor": vendor, "class": klass})
    return devices


def main() -> int:
    pci = amd_pci_devices()
    amd_smi = run(["amd-smi", "list"])
    rocminfo = run(["rocminfo"])
    offload_arch = run(["offload-arch"])
    hipcc = run(["hipcc", "--version"])

    amd_present = bool(pci)
    rocm_visible = any(
        item["present"] and item["returncode"] == 0
        for item in (amd_smi, rocminfo, offload_arch)
    )
    toolchain_visible = hipcc["present"] and hipcc["returncode"] == 0

    if not amd_present:
        status = "NOT_APPLICABLE_NOT_MATERIALIZED"
        runtime_conformance = "NOT_TESTED_NO_ELIGIBLE_AMD_GPU"
        exit_code = 0
    elif not rocm_visible:
        status = "PENDING_ROCM_MATERIALIZATION_OR_REPAIR"
        runtime_conformance = "EVIDENCE_PENDING"
        exit_code = 2
    elif not toolchain_visible:
        status = "PENDING_HIP_TOOLCHAIN_CONFORMANCE"
        runtime_conformance = "EVIDENCE_PENDING"
        exit_code = 2
    else:
        status = "PASS_LIVE_AMD_ROCM_DISCOVERY"
        runtime_conformance = "DISCOVERY_PASS_REQUIRES_WORKLOAD_SPECIFIC_CORRECTNESS_FOR_PROVIDER_PROMOTION"
        exit_code = 0

    receipt = {
        "schema": "fa3.rocm.current-host-evidence.v1",
        "policy_id": POLICY_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hostname": os.uname().nodename,
        "status": status,
        "runtime_conformance": runtime_conformance,
        "amd_gpu_present": amd_present,
        "rocm_visible": rocm_visible,
        "hip_toolchain_visible": toolchain_visible,
        "pci_devices": pci,
        "probes": {
            "amd_smi": amd_smi,
            "rocminfo": rocminfo,
            "offload_arch": offload_arch,
            "hipcc": hipcc,
        },
        "invariants": {
            "absence_is_not_failure": True,
            "absence_is_never_runtime_pass": True,
            "runtime_pass_requires_live_amd_hardware": True,
            "no_forced_materialization": True,
        },
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
