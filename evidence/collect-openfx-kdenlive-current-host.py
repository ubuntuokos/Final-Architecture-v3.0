#!/usr/bin/env python3
"""Read-only current-host readiness probe for Kdenlive/OpenFX interoperability."""
from __future__ import annotations
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def present(name: str) -> bool:
    return shutil.which(name) is not None

def main() -> int:
    checks = {
        "kdenlive_executable": present("kdenlive"),
        "ffmpeg_executable": present("ffmpeg"),
        "ffprobe_executable": present("ffprobe"),
        "openfx_host_candidate_natron": present("natron"),
        "openfx_gate_source": (ROOT / "src/fa3_openfx_interop_gate.py").is_file(),
    }
    ready_for_real_e2e = all(checks.values())
    report = {
        "evidence_id": "FA3-EVIDENCE-OPENFX-KDENLIVE-CURRENT-HOST-001",
        "kind": "CURRENT_HOST_READINESS_PROBE",
        "checks": checks,
        "runtime_ready_for_real_e2e": ready_for_real_e2e,
        "production_status": "READY_FOR_REAL_E2E" if ready_for_real_e2e else "PENDING_CURRENT_HOST",
        "native_kdenlive_openfx_host": False,
        "note": "Readiness is not production PASS. Real admission requires an admitted OpenFX host/plugin bundle, immutable plugin and parameter hashes, HRB lease where accelerated, deterministic frame/color/alpha/timebase validation, Kdenlive relink/picture-lock evidence and rollback receipt.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
