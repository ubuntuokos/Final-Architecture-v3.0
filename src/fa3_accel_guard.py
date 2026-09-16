#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VALID_STATES = {
    "READY_FOR_HRB_ADMISSION",
    "BUSY_EXTERNAL",
    "LEASED_BY_FA3",
    "DEGRADED",
    "UNAVAILABLE",
    "UNSUPPORTED",
    "EXPERIMENTAL_REQUIRES_OPT_IN",
}


def assess(
    *,
    physical_key: str,
    provider_ready: bool,
    supported: bool = True,
    degraded: bool = False,
    external_busy: bool = False,
    fa3_leased: bool = False,
    experimental: bool = False,
    explicit_opt_in: bool = False,
    prior_user_policy: str | None = None,
) -> dict[str, Any]:
    if not physical_key:
        raise ValueError("physical accelerator identity is required")
    if not supported:
        state = "UNSUPPORTED"
    elif not provider_ready:
        state = "UNAVAILABLE"
    elif degraded:
        state = "DEGRADED"
    elif experimental and not explicit_opt_in:
        state = "EXPERIMENTAL_REQUIRES_OPT_IN"
    elif external_busy:
        state = "BUSY_EXTERNAL"
    elif fa3_leased:
        state = "LEASED_BY_FA3"
    else:
        state = "READY_FOR_HRB_ADMISSION"

    conflict = state == "BUSY_EXTERNAL"
    automatic = bool(conflict and prior_user_policy)
    return {
        "schema": "fa3.accelerator-guard-receipt.v1",
        "profile_id": "FA3-ACCEL-GUARD-001",
        "physical_key": physical_key,
        "state": state,
        "mode": "RECOMMEND",
        "user_decision_required": conflict and not automatic,
        "automatic_action_authorized_by_prior_policy": automatic,
        "prior_user_policy": prior_user_policy,
        "lease_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "guard_is_lease_authority": False,
        "direct_external_process_eviction": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a normalized FA3 accelerator contention observation")
    parser.add_argument("observation", help="JSON observation file")
    args = parser.parse_args()
    payload = json.loads(Path(args.observation).read_text(encoding="utf-8"))
    receipt = assess(**payload)
    if receipt["state"] not in VALID_STATES:
        raise SystemExit(2)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
