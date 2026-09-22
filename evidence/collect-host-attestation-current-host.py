#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_host_attestation import build_artifact, collect_live_attestation, validate_artifact
from fa3_runtime_hardening_current_host import write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect a digest-bound FA3 current-host attestation artifact")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=".fa3-current-host/input/host-attestation.json")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise SystemExit("host attestation collector must run rootless")
    root = Path(args.root).resolve()
    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = root / output
    artifact = build_artifact(collect_live_attestation())
    findings, _, _ = validate_artifact(artifact)
    if findings:
        raise SystemExit("; ".join(findings))
    write_json(output, artifact)
    print(json.dumps({
        "status": "PASS",
        "host_attestation_ref": artifact["host_attestation_ref"],
        "output": str(output),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
