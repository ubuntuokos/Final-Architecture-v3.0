#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_accelerator_guard import (  # noqa: E402
    OBSERVABILITY_INSUFFICIENT,
    classify,
    decide,
    observe_host,
    owned_pids_from_environment,
)


def writej(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect(output: Path, sample_interval: float) -> dict:
    baseline = observe_host()
    time.sleep(max(0.0, sample_interval))
    current = observe_host()
    owned = owned_pids_from_environment()
    state = classify(baseline, current, owned)
    resolution = decide(state)

    observable = baseline.observable and current.observable
    semantics_ok = (
        resolution.get("destructive_action_authorized") is False
        and resolution.get("automatic_resolution") is False
        and resolution.get("mode") == "RECOMMEND"
    )
    result = "PASS" if observable and semantics_ok and state != OBSERVABILITY_INSUFFICIENT else "FAIL"

    receipt = {
        "schema": "fa3.hardware-fabric-current-host-receipt.v1",
        "id": "FA3-HARDWARE-FABRIC-CURRENT-HOST-RECEIPT-001",
        "executed": True,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "hardware_root": "FA3-HW-001",
        "compute_profile": "FA3-COMPUTE-PROFILE-001",
        "guard": "FA3-ACCEL-GUARD-001",
        "guard_default_mode": "RECOMMEND",
        "contention_state": state,
        "decision": resolution,
        "destructive_action_performed": False,
        "automatic_external_process_preemption_performed": False,
        "baseline": baseline.to_dict(),
        "current": current.to_dict(),
        "fa3_owned_pids": sorted(owned),
        "promotion_claim": result == "PASS",
        "notes": "PASS means the Accelerator Guard executed with sufficient typed accelerator observability and preserved RECOMMEND/user-arbitration semantics. It does not assert that accelerators were contention-free."
    }
    writej(output, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / ".fa3-current-host/hardware-fabric-receipt.json"))
    parser.add_argument("--sample-interval", type=float, default=1.0)
    args = parser.parse_args()
    receipt = collect(Path(args.output), args.sample_interval)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
