#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from fa3_convertx_adapter import PROVIDER_ID, digest_pinned_image


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect real ConvertX current-host evidence. The collector fails closed while the provider is quarantined."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--image")
    parser.add_argument("--input")
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    provider_path = root / "canonical/FA3-PROVIDER-CONVERTX-001.json"
    provider = json.loads(provider_path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    blockers: list[str] = []
    if provider.get("id") != PROVIDER_ID:
        blockers.append("PROVIDER_ID_MISMATCH")
    if provider.get("status") != "APPROVED":
        blockers.append("PROVIDER_NOT_PROMOTED")
    if not provider.get("machine_interface", {}).get("machine_execution_enabled", False):
        blockers.append("MACHINE_EXECUTION_DISABLED")
    if provider.get("machine_interface", {}).get("official_public_api_available") is not True:
        blockers.append("NO_STABLE_MACHINE_EXECUTION_CONTRACT")
    if not args.image or not digest_pinned_image(args.image):
        blockers.append("DIGEST_PINNED_IMAGE_REQUIRED")

    # Current FA3 policy intentionally prevents this collector from manufacturing a
    # production PASS from files alone. A future promoted adapter must execute the
    # conversion and supply HRB + isolation + egress evidence directly.
    if blockers:
        receipt = {
            "schema": "fa3.convertx-current-host-receipt.v1",
            "provider_id": PROVIDER_ID,
            "status": "BLOCKED",
            "evidence_level": "NO_CURRENT_HOST_CLAIM",
            "collected_at": now,
            "blockers": blockers,
            "synthetic_input": False,
            "real_output_hash_observed": False,
            "egress_denial_verified": False,
            "hrb_lease_verified": False,
            "provider_image": args.image or "",
            "note": "Current upstream ConvertX web flow is not treated as a stable FA3 machine API. Promotion requires a real adapter/executor and real current-host E2E evidence.",
        }
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 2

    # This branch is deliberately unreachable with the current canonical provider
    # record. It prevents a future policy edit from silently producing PASS without
    # implementing the real executor in this collector.
    raise SystemExit("FAIL-CLOSED: real ConvertX production executor is not materialized")


if __name__ == "__main__":
    raise SystemExit(main())
