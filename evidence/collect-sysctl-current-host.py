#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_release_baseline import active_capability_count
from fa3_sysctl_governance import classify_key, snapshot_digest


DEFAULT_KEYS = [
    "vm.swappiness",
    "vm.overcommit_memory",
    "vm.overcommit_ratio",
    "vm.dirty_ratio",
    "vm.dirty_background_ratio",
    "vm.dirty_bytes",
    "vm.dirty_background_bytes",
    "vm.vfs_cache_pressure",
    "vm.min_free_kbytes",
    "vm.max_map_count",
    "vm.zone_reclaim_mode",
    "vm.compaction_proactiveness",
    "vm.extfrag_threshold",
    "vm.nr_hugepages",
    "vm.nr_overcommit_hugepages",
    "kernel.numa_balancing",
    "kernel.kptr_restrict",
    "kernel.dmesg_restrict",
    "kernel.unprivileged_bpf_disabled",
    "kernel.yama.ptrace_scope",
    "fs.protected_hardlinks",
    "fs.protected_symlinks",
    "fs.protected_fifos",
    "fs.protected_regular",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_key(sysctl_bin: str, key: str) -> dict[str, Any]:
    try:
        cp = subprocess.run(
            [sysctl_bin, "-n", key],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"key": key, "status": "ERROR", "error": type(exc).__name__}
    if cp.returncode != 0:
        return {"key": key, "status": "UNAVAILABLE"}
    return {
        "key": key,
        "status": "PRESENT",
        "value": cp.stdout.strip(),
        "classification": classify_key(key),
    }


def collect(keys: list[str]) -> dict[str, Any]:
    sysctl_bin = shutil.which("sysctl")
    if not sysctl_bin:
        return {
            "schema": "fa3.sysctl-current-host-snapshot.v1",
            "status": "FAIL",
            "evidence_level": "CURRENT_HOST_SYSCTL_OBSERVATION_INCOMPLETE",
            "blocking_reasons": ["SYSCTL_COMMAND_UNAVAILABLE"],
            "mutation_performed": False,
            "persistent_mutation_performed": False,
            "global_promotion_claim": False,
        }

    entries = [read_key(sysctl_bin, key) for key in keys]
    present = {x["key"]: x["value"] for x in entries if x["status"] == "PRESENT"}
    errors = [x["key"] for x in entries if x["status"] == "ERROR"]
    pass_state = bool(present) and not errors
    return {
        "schema": "fa3.sysctl-current-host-snapshot.v1",
        "status": "PASS" if pass_state else "FAIL",
        "evidence_level": "CURRENT_HOST_SYSCTL_OBSERVATION_PASS" if pass_state else "CURRENT_HOST_SYSCTL_OBSERVATION_INCOMPLETE",
        "collected_at": now(),
        "mode": "OBSERVE_ONLY",
        "sysctl_binary": sysctl_bin,
        "requested_key_count": len(keys),
        "present_key_count": len(present),
        "snapshot_sha256": snapshot_digest(present),
        "entries": entries,
        "mutation_performed": False,
        "persistent_mutation_performed": False,
        "capability_count_after": active_capability_count(ROOT),
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
        "blocking_reasons": [] if pass_state else ["SYSCTL_OBSERVATION_ERROR"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect read-only FA3 sysctl current-host snapshot")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default="evidence/receipts/sysctl-current-host.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    result = collect(DEFAULT_KEYS)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
