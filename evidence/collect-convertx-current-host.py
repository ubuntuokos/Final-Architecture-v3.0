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
    digest_pinned_image,
    validate_request,
    validate_runtime_contract,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect ConvertX current-host candidate evidence without enabling production routing. "
            "Execution remains blocked until an authoritative CPU/memory resource-admission verifier is materialized."
        )
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--candidate-validation", action="store_true")
    parser.add_argument("--image")
    parser.add_argument("--base-url")
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--input-media-type")
    parser.add_argument("--output-media-type")
    parser.add_argument("--resource-admission")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    provider = json.loads(
        (root / "canonical/FA3-PROVIDER-CONVERTX-001.json").read_text(encoding="utf-8")
    )
    allowlist = json.loads(
        (root / "canonical/FA3-CONVERTX-CONVERSION-ALLOWLIST-001.json").read_text(encoding="utf-8")
    )
    conformance = json.loads(
        (root / "canonical/FA3-CONVERTX-RUNTIME-CONFORMANCE-001.json").read_text(encoding="utf-8")
    )
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    machine = provider.get("machine_interface", {})
    sandbox = provider.get("sandbox", {})
    governance = provider.get("resource_governance", {})
    resource_contract = conformance.get("resource_admission", {})
    blockers: list[str] = []

    if provider.get("id") != PROVIDER_ID:
        blockers.append("PROVIDER_ID_MISMATCH")
    if provider.get("status") not in {"QUARANTINED", "APPROVED"}:
        blockers.append("PROVIDER_STATE_NOT_ELIGIBLE_FOR_CANDIDATE_VALIDATION")
    if not args.candidate_validation:
        blockers.append("EXPLICIT_CANDIDATE_VALIDATION_REQUIRED")
    if not args.image or not digest_pinned_image(args.image):
        blockers.append("DIGEST_PINNED_IMAGE_REQUIRED")
    if not args.base_url:
        blockers.append("LOOPBACK_CONVERTX_BASE_URL_REQUIRED")
    if not args.input or not Path(args.input).is_file():
        blockers.append("REAL_INPUT_FILE_REQUIRED")
    if not args.output:
        blockers.append("REAL_OUTPUT_PATH_REQUIRED")
    if not args.input_media_type or not args.output_media_type:
        blockers.append("EXPLICIT_MEDIA_PAIR_REQUIRED")
    if not args.resource_admission or not Path(args.resource_admission).is_file():
        blockers.append("AUTHORITATIVE_RESOURCE_ADMISSION_EVIDENCE_REQUIRED")

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
    try:
        validate_runtime_contract(runtime)
    except AdmissionDenied as exc:
        blockers.append(f"RUNTIME_CONTRACT_DENIED:{exc}")

    planned_pair: dict[str, object] | None = None
    if args.input and args.input_media_type and args.output_media_type:
        request = ConversionRequest(
            input_path=str(args.input),
            input_media_type=str(args.input_media_type),
            output_media_type=str(args.output_media_type),
            resource_admission_path=(str(args.resource_admission) if args.resource_admission else None),
        )
        try:
            pair = validate_request(request, allowlist, allowed_states=("CANDIDATE", "ACTIVE"))
            planned_pair = {
                "pair": [request.input_media_type, request.output_media_type],
                "state": pair.get("state"),
                "provider_converter": pair.get("provider_converter"),
                "provider_target": pair.get("provider_target"),
            }
        except AdmissionDenied as exc:
            blockers.append(f"PAIR_POLICY_DENIED:{exc}")

    # The current executable resource-admission proof in FA3 is accelerator-specific.
    # ConvertX is CPU/memory governed, so pretending AcceleratorExecutionLease@1 is a
    # valid substitute would create a false current-host PASS. Fail closed instead.
    if resource_contract.get("current_authoritative_cpu_memory_verifier") != "MATERIALIZED":
        blockers.append("AUTHORITATIVE_CPU_MEMORY_RESOURCE_ADMISSION_VERIFIER_NOT_MATERIALIZED")
    if resource_contract.get("accelerator_contract_is_valid_cpu_memory_substitute") is not False:
        blockers.append("RESOURCE_ADMISSION_TYPE_SAFETY_NOT_ENFORCED")

    if machine.get("fa3_adapter_execution_contract_materialized") is not True:
        blockers.append("FA3_ADAPTER_EXECUTION_CONTRACT_NOT_MATERIALIZED")
    if machine.get("fa3_candidate_executor_materialized") is not True:
        blockers.append("FA3_CANDIDATE_EXECUTOR_NOT_MATERIALIZED")

    blockers.append("REAL_CANDIDATE_EXECUTION_NOT_RUN_BECAUSE_RESOURCE_ADMISSION_IS_BLOCKED")
    blockers.append("CONTAINER_EGRESS_DENIAL_NOT_CURRENT_HOST_VERIFIED")

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
        "planned_pair": planned_pair,
        "blockers": sorted(set(blockers)),
        "synthetic_input": False,
        "real_output_hash_observed": False,
        "egress_denial_verified": False,
        "resource_admission_verified": False,
        "provider_image": args.image or "",
        "base_url": args.base_url or "",
        "input_media_type": args.input_media_type or "",
        "output_media_type": args.output_media_type or "",
        "upstream_official_public_api_available": machine.get("official_public_api_available", False),
        "fa3_adapter_execution_contract_materialized": machine.get(
            "fa3_adapter_execution_contract_materialized", False
        ),
        "fa3_candidate_executor_materialized": machine.get(
            "fa3_candidate_executor_materialized", False
        ),
        "resource_admission_contract_observed": resource_contract,
        "note": (
            "The v0.18.0 candidate executor is materialized, but this collector deliberately does not execute it until "
            "an authoritative CPU/memory resource-admission verifier exists in FA3. AcceleratorExecutionLease@1 is not "
            "accepted as a substitute. No runtime PASS is claimed."
        ),
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
