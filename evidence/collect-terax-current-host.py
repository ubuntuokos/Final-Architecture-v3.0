#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROVIDER_ID = "FA3-PROVIDER-TERAX-001"


def proc_snapshot():
    rows = []
    proc = Path("/proc")
    if not proc.exists():
        return rows
    for p in proc.iterdir():
        if not p.name.isdigit():
            continue
        try:
            comm = (p / "comm").read_text(errors="replace").strip()
        except Exception:
            continue
        if "terax" not in comm.lower():
            continue
        threads = 0
        rss_kb = 0
        try:
            for line in (p / "status").read_text(errors="replace").splitlines():
                if line.startswith("Threads:"):
                    threads = int(line.split()[1])
                elif line.startswith("VmRSS:"):
                    rss_kb = int(line.split()[1])
        except Exception:
            pass
        rows.append({"pid": int(p.name), "comm": comm, "threads": threads, "rss_bytes": rss_kb * 1024})
    return rows


def gpu_snapshot(pids):
    if not shutil.which("nvidia-smi"):
        return "UNAVAILABLE", []
    cp = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=10
    )
    if cp.returncode != 0:
        return "UNAVAILABLE", []
    rows = []
    for line in cp.stdout.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            mem = int(parts[-1])
        except ValueError:
            continue
        name = ",".join(parts[1:-1]).strip()
        if pid in pids or "terax" in name.lower():
            rows.append({"pid": pid, "process_name": name, "used_memory_mib": mem})
    return "AVAILABLE", rows


def main():
    ap = argparse.ArgumentParser(description="Read-only Terax disabled-provider current-host evidence collector")
    ap.add_argument("--state", choices=["disabled-reference"], default="disabled-reference")
    ap.add_argument("--output", default="evidence/receipts/terax-current-host.json")
    ap.add_argument("--valid-days", type=int, default=7)
    a = ap.parse_args()

    procs = proc_snapshot()
    pids = {x["pid"] for x in procs}
    gpu_status, gpu = gpu_snapshot(pids)
    now = datetime.now(timezone.utc)
    fingerprint = hashlib.sha256(
        f"{platform.system()}|{platform.release()}|{platform.machine()}|{os.getuid()}".encode()
    ).hexdigest()

    metrics = {
        "resident_process_count": len(procs),
        "worker_thread_count": sum(x["threads"] for x in procs),
        "ram_resident_bytes": sum(x["rss_bytes"] for x in procs),
        "gpu_memory_bytes": sum(x["used_memory_mib"] for x in gpu) * 1024 * 1024,
        "network_session_count": 0 if not procs else -1,
        "accelerator_reservation_count": 0 if not procs and not gpu else -1,
        "active_polling": False if not procs else True,
        "background_inference": False if not gpu else True
    }
    zero = (
        all(metrics[k] == 0 for k in (
            "resident_process_count", "worker_thread_count", "ram_resident_bytes",
            "gpu_memory_bytes", "network_session_count", "accelerator_reservation_count"
        ))
        and metrics["active_polling"] is False
        and metrics["background_inference"] is False
    )
    status = "PASS" if zero and gpu_status == "AVAILABLE" else "FAIL"

    obj = {
        "schema": "fa3.terax-current-host.v1",
        "provider_id": PROVIDER_ID,
        "host_scope": "CURRENT_HOST",
        "provider_state": "DISABLED_REFERENCE_ONLY",
        "status": status,
        "collected_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(days=a.valid_days)).isoformat().replace("+00:00", "Z"),
        "host_fingerprint_sha256": fingerprint,
        "secret_collection": "PROHIBITED",
        "network_access": "NOT_USED",
        "gpu_telemetry": gpu_status,
        "metrics": metrics,
        "observed_processes": procs,
        "observed_gpu_processes": gpu,
        "claim": "PASS proves disabled Terax provider has effectively zero observed runtime cost on the collecting host; it does not promote the full 143-capability FA3 runtime."
    }
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, indent=2) + "\n")
    print(json.dumps(obj, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
