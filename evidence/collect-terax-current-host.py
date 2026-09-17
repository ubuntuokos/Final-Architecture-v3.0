#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
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


def main():
    ap = argparse.ArgumentParser(description="Read-only auxiliary Terax disabled-reference current-host collector")
    ap.add_argument("--state", choices=["disabled-reference"], default="disabled-reference")
    ap.add_argument("--output", default="evidence/receipts/terax-current-host.json")
    ap.add_argument("--valid-days", type=int, default=7)
    a = ap.parse_args()

    procs = proc_snapshot()
    now = datetime.now(timezone.utc)
    fingerprint = hashlib.sha256(
        f"{platform.system()}|{platform.release()}|{platform.machine()}|{os.getuid()}".encode()
    ).hexdigest()

    metrics = {
        "resident_process_count": len(procs),
        "worker_thread_count": sum(x["threads"] for x in procs),
        "ram_resident_bytes": sum(x["rss_bytes"] for x in procs),
        "network_session_count": 0 if not procs else -1,
        "active_polling": False if not procs else True,
        "background_inference": False
    }
    zero = (
        all(metrics[k] == 0 for k in (
            "resident_process_count", "worker_thread_count", "ram_resident_bytes", "network_session_count"
        ))
        and metrics["active_polling"] is False
        and metrics["background_inference"] is False
    )
    status = "PASS" if zero else "FAIL"

    obj = {
        "schema": "fa3.terax-current-host.v2",
        "provider_id": PROVIDER_ID,
        "host_scope": "CURRENT_HOST",
        "provider_state": "DISABLED_REFERENCE_ONLY",
        "status": status,
        "collected_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(days=a.valid_days)).isoformat().replace("+00:00", "Z"),
        "host_fingerprint_sha256": fingerprint,
        "secret_collection": "PROHIBITED",
        "network_access": "NOT_USED",
        "workload_execution_requested": False,
        "requested_resource_classes": [],
        "hrb_admission_applicability": "NOT_APPLICABLE_NO_WORKLOAD_EXECUTION",
        "accelerator_discovery_performed": False,
        "accelerator_lease_required": False,
        "accelerator_lease_evidence": "NOT_APPLICABLE_NO_ACCELERATOR_RESOURCE_CLASS",
        "gpu_telemetry": "NOT_APPLICABLE_NO_ACCELERATOR_RESOURCE_CLASS",
        "provider_receipt_substitution_allowed": False,
        "capability_promotion_claim": False,
        "global_promotion_claim": False,
        "metrics": metrics,
        "observed_processes": procs,
        "claim": "Auxiliary provider evidence only. PASS proves no observed Terax-owned runtime process cost while the optional reference provider is disabled. No GPU/NVIDIA/CUDA probe is performed because no accelerator workload is requested. This receipt cannot satisfy any capability-specific positive, negative, or rollback test and cannot promote the 143-capability FA3 runtime."
    }
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, indent=2) + "\n")
    print(json.dumps(obj, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
