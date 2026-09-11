#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def version(command: list[str]) -> dict[str, object]:
    executable = shutil.which(command[0])
    if not executable:
        return {"available": False, "path": None, "version": None}
    process = subprocess.run([executable, *command[1:]], text=True, capture_output=True, check=False)
    first_line = (process.stdout or process.stderr).splitlines()
    return {
        "available": process.returncode == 0,
        "path": executable,
        "version": first_line[0] if first_line else None,
    }


def collect(root: Path) -> dict[str, object]:
    kdenlive = version(["kdenlive", "--version"])
    ffmpeg = version(["ffmpeg", "-version"])
    ffprobe = version(["ffprobe", "-version"])
    ready = bool(kdenlive["available"] and ffmpeg["available"] and ffprobe["available"])
    receipt = {
        "schema": "fa3.lut-color-current-host-readiness.v1",
        "gate_id": "FA3-LUT-COLOR-GATESET-001",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": "READY_FOR_REAL_COLOR_E2E" if ready else "PENDING_CURRENT_HOST_PREREQUISITES",
        "tools": {"kdenlive": kdenlive, "ffmpeg": ffmpeg, "ffprobe": ffprobe},
        "required_real_e2e": [
            "registered immutable LUT artifact hash verification",
            "technical-primary-creative-output order execution",
            "Kdenlive preview and human picture-lock approval",
            "FFmpeg headless semantic comparison",
            "color/pixel/range/HDR metadata validation",
            "gamut, clipping and representative-frame QC",
            "rollback drill and evidence receipt",
        ],
        "production_e2e_executed": False,
        "runtime_promotion_claimed": False,
    }
    out = root / "evidence/receipts/lut-color-current-host-readiness.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect FA3 LUT/color current-host readiness without claiming production E2E")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    receipt = collect(Path(args.root).resolve())
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
