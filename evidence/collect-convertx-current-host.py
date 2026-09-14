#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from fa3_convertx_adapter import PROVIDER_ID, digest_pinned_image


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

    machine = provider.get("machine_interface", {})
    blockers: list[str] = []
    if provider.get("id") != PROVIDER_ID:
        blockers.append("PROVIDER_ID_MISMATCH")
    if provider.get("status") != "APPROVED":
        blockers.append("PROVIDER_NOT_PROMOTED")
    if not machine.get("machine_execution_enabled", False):
        blockers.append("MACHINE_EXECUTION_DISABLED")
    if not machine.get("fa3_adapter_execution_contract_materialized", False):
        blockers.append("FA3_ADAPTER_EXECUTION_CONTRACT_NOT_MATERIALIZED")
    if not args.image or not digest_pinned_image(args.image):
        blockers.append("DIGEST_PINNED_IMAGE_REQUIRED")
    if not args.input:
        blockers.append("REAL_INPUT_REQUIRED")
    if not args.output:
        blockers.append("REAL_OUTPUT_REQUIRED")

    # Upstream may continue to expose no official public API. That alone does not
    # prevent future promotion: the required machine boundary is an FA3-owned,
    # versioned adapter/executor contract. Until that executor exists, this
    # collector cannot manufacture a production PASS from repository state.
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
            "upstream_official_public_api_available": machine.get("official_public_api_available", False),
            "fa3_adapter_execution_contract_materialized": machine.get(
                "fa3_adapter_execution_contract_materialized", False
            ),
            "note": "Promotion requires a real FA3 adapter/executor plus real HRB, isolation, egress and output-hash evidence. Repository state alone cannot produce PASS.",
        }
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 2

    # Deliberately fail closed even after policy fields are flipped until the real
    # executor path is implemented here. This prevents policy-only promotion.
    raise SystemExit("FAIL-CLOSED: real ConvertX production executor is not materialized")


if __name__ == "__main__":
    raise SystemExit(main())
