#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from fa3_convertx_adapter import (
    AdmissionDenied,
    ConversionRequest,
    PROVIDER_ID,
    candidate_validation_admission,
    digest_pinned_image,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect real ConvertX current-host candidate evidence without enabling production routing. "
            "The provider may remain QUARANTINED while this evidence is collected."
        )
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--candidate-validation", action="store_true")
    parser.add_argument("--image")
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--input-media-type")
    parser.add_argument("--output-media-type")
    parser.add_argument("--hrb-lease")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    provider = json.loads(
        (root / "canonical/FA3-PROVIDER-CONVERTX-001.json").read_text(encoding="utf-8")
    )
    allowlist = json.loads(
        (root / "canonical/FA3-CONVERTX-CONVERSION-ALLOWLIST-001.json").read_text(encoding="utf-8")
    )
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    machine = provider.get("machine_interface", {})
    sandbox = provider.get("sandbox", {})
    governance = provider.get("resource_governance", {})
    blockers: list[str] = []

    if provider.get("id") != PROVIDER_ID:
        blockers.append("PROVIDER_ID_MISMATCH")
    if provider.get("status") not in {"QUARANTINED", "APPROVED"}:
        blockers.append("PROVIDER_STATE_NOT_ELIGIBLE_FOR_CANDIDATE_VALIDATION")
    if not args.candidate_validation:
        blockers.append("EXPLICIT_CANDIDATE_VALIDATION_REQUIRED")
    if not args.image or not digest_pinned_image(args.image):
        blockers.append("DIGEST_PINNED_IMAGE_REQUIRED")
    if not args.input or not Path(args.input).is_file():
        blockers.append("REAL_INPUT_FILE_REQUIRED")
    if not args.output:
        blockers.append("REAL_OUTPUT_PATH_REQUIRED")
    if not args.input_media_type or not args.output_media_type:
        blockers.append("EXPLICIT_MEDIA_PAIR_REQUIRED")
    if not args.hrb_lease or not Path(args.hrb_lease).is_file():
        blockers.append("REAL_HRB_LEASE_REQUIRED")

    runtime = {
        "non_root": sandbox.get("non_root") is True,
        "read_only_root": sandbox.get("read_only_root") is True,
        "cap_drop_all": sandbox.get("cap_drop_all") is True,
        "no_new_privileges": sandbox.get("no_new_privileges") is True,
        "seccomp": sandbox.get("seccomp_required") is True,
        "resource_limits": all(
            governance.get(key) is True
            for key in (
                "timeout_required",
                "cpu_limit_required",
                "memory_limit_required",
                "pids_limit_required",
                "output_quota_required",
            )
        ),
        "ephemeral_workspace": sandbox.get("workspace") == "PER_JOB_EPHEMERAL_ONLY",
        "host_mounts": sandbox.get("host_mounts"),
        "outbound_network": "DENY" if sandbox.get("outbound_network") == "DENY_BY_DEFAULT" else sandbox.get("outbound_network"),
        "image": args.image or "",
    }

    admission: dict[str, object] | None = None
    if not blockers:
        request = ConversionRequest(
            input_path=str(args.input),
            input_media_type=str(args.input_media_type),
            output_media_type=str(args.output_media_type),
            hrb_lease_path=str(args.hrb_lease),
        )
        try:
            admission = candidate_validation_admission(
                request,
                provider,
                allowlist,
                runtime,
                explicit=True,
            )
        except AdmissionDenied as exc:
            blockers.append(f"CANDIDATE_ADMISSION_DENIED:{exc}")

    # These remain real implementation/evidence blockers. They deliberately do
    # not depend on provider promotion or production machine_execution_enabled.
    if machine.get("fa3_adapter_execution_contract_materialized") is not True:
        blockers.append("FA3_ADAPTER_EXECUTION_CONTRACT_NOT_MATERIALIZED")
    if machine.get("fa3_candidate_executor_materialized") is not True:
        blockers.append("FA3_CANDIDATE_EXECUTOR_NOT_MATERIALIZED")
    blockers.append("HRB_LEASE_CRYPTOGRAPHIC_OR_AUTHORITATIVE_VERIFIER_NOT_MATERIALIZED")
    blockers.append("REAL_CONVERTX_EXECUTION_AND_EGRESS_PROBE_NOT_MATERIALIZED")

    receipt = {
        "schema": "fa3.convertx-current-host-receipt.v1",
        "provider_id": PROVIDER_ID,
        "status": "BLOCKED",
        "evidence_level": "NO_CURRENT_HOST_CLAIM",
        "collected_at": now,
        "candidate_validation": bool(args.candidate_validation),
        "production_routing_enabled": False,
        "provider_status_observed": provider.get("status"),
        "machine_execution_enabled_observed": machine.get("machine_execution_enabled", False),
        "admission": admission,
        "blockers": sorted(set(blockers)),
        "synthetic_input": False,
        "real_output_hash_observed": False,
        "egress_denial_verified": False,
        "hrb_lease_verified": False,
        "provider_image": args.image or "",
        "input_media_type": args.input_media_type or "",
        "output_media_type": args.output_media_type or "",
        "upstream_official_public_api_available": machine.get("official_public_api_available", False),
        "fa3_adapter_execution_contract_materialized": machine.get(
            "fa3_adapter_execution_contract_materialized", False
        ),
        "fa3_candidate_executor_materialized": machine.get(
            "fa3_candidate_executor_materialized", False
        ),
        "note": (
            "Candidate evidence is intentionally collectible before provider promotion, but this collector cannot emit PASS "
            "until the FA3 executor, authoritative HRB verification, isolation/egress proof, and real output hashing are implemented."
        ),
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
