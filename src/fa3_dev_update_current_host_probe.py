#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> dict[str, object]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip()[:4000],
        "stderr": proc.stderr.strip()[:4000],
    }


def main() -> int:
    report_dir = ROOT / "reports/dev-update-current-host"
    report_dir.mkdir(parents=True, exist_ok=True)
    facts: dict[str, object] = {
        "schema": "fa3.dev-update-current-host-probe.v1",
        "captured_unix": int(time.time()),
        "claims": [],
        "non_claims": ["CURRENT_HOST_E2E_PASS", "GLOBAL_FA3_PROMOTION"],
        "uid": os.getuid(),
        "euid": os.geteuid(),
        "tools": {
            "apt-get": shutil.which("apt-get"),
            "unattended-upgrade": shutil.which("unattended-upgrade"),
            "needrestart": shutil.which("needrestart"),
            "notify-send": shutil.which("notify-send"),
            "nvidia-smi": shutil.which("nvidia-smi"),
        },
        "reboot_required": Path("/var/run/reboot-required").exists(),
        "os_release": {},
        "checks": {},
    }
    os_release = Path("/etc/os-release")
    if os_release.exists():
        for line in os_release.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                facts["os_release"][key] = value.strip('"')

    facts["checks"]["canonical_gate"] = run([sys.executable, str(ROOT / "src/fa3_dev_update_gate.py")])
    facts["checks"]["static_gate"] = run([str(ROOT / "bin/fa3-enforce"), "static"])
    if shutil.which("nvidia-smi"):
        facts["checks"]["nvidia_compute_processes"] = run([
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ])

    # Exercise restart arbitration without touching host services or reboot state.
    with tempfile.TemporaryDirectory() as td:
        script = (
            "import json, pathlib, fa3_update_fabric as u; "
            f"u.STATE_DIR=pathlib.Path({td!r}); u.RESTART_STATE=u.STATE_DIR/'restart-required.json'; "
            "u.set_restart_required('host',['kernel'],['protected-probe-workload']); "
            "print(json.dumps(u.choose_restart('RESTART_NOW',['protected-probe-workload'],None)))"
        )
        facts["checks"]["protected_workload_restart_arbitration"] = run([
            sys.executable,
            "-c",
            script,
        ])

    blockers: list[str] = []
    for name in ("canonical_gate", "static_gate", "protected_workload_restart_arbitration"):
        check = facts["checks"].get(name, {})
        if check.get("returncode") != 0:
            blockers.append(name)
    facts["status"] = "REFERENCE_PROBE_PASS_CURRENT_HOST_E2E_PENDING" if not blockers else "FAIL"
    facts["blocking_findings"] = blockers
    out = report_dir / "current-host-probe.json"
    out.write_text(json.dumps(facts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(facts, indent=2, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
