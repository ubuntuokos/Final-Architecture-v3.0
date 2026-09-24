#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROVIDER_ID = "FA3-PROVIDER-CONVERTX-001"
PROFILE_ID = "FA3-FILE-CONVERSION-001"
ALLOWLIST_ID = "FA3-CONVERTX-CONVERSION-ALLOWLIST-001"


class ConvertXError(RuntimeError):
    pass


class AdmissionDenied(ConvertXError):
    pass


class ProviderQuarantined(AdmissionDenied):
    pass


@dataclass(frozen=True)
class ConversionRequest:
    input_path: str
    input_media_type: str
    output_media_type: str
    profile_id: str = PROFILE_ID
    converter_name: str | None = None
    provider_arguments: tuple[str, ...] = ()
    resource_admission_path: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversionRequest":
        resource_path = data.get("resource_admission_path")
        return cls(
            input_path=str(data["input_path"]),
            input_media_type=str(data["input_media_type"]),
            output_media_type=str(data["output_media_type"]),
            profile_id=str(data.get("profile_id", PROFILE_ID)),
            converter_name=(None if data.get("converter_name") in (None, "") else str(data["converter_name"])),
            provider_arguments=tuple(str(x) for x in data.get("provider_arguments", [])),
            resource_admission_path=(None if resource_path in (None, "") else str(resource_path)),
        )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    profile = load_json(root / "canonical/FA3-FILE-CONVERSION-001.json")
    provider = load_json(root / "canonical/FA3-PROVIDER-CONVERTX-001.json")
    allowlist = load_json(root / "canonical/FA3-CONVERTX-CONVERSION-ALLOWLIST-001.json")
    if profile.get("id") != PROFILE_ID:
        raise AdmissionDenied("conversion profile identity mismatch")
    if provider.get("id") != PROVIDER_ID:
        raise AdmissionDenied("provider identity mismatch")
    if allowlist.get("id") != ALLOWLIST_ID:
        raise AdmissionDenied("allowlist identity mismatch")
    return profile, provider, allowlist


def digest_pinned_image(image_ref: str) -> bool:
    return bool(re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", image_ref.strip()))


def resolve_pair(
    allowlist: dict[str, Any],
    source: str,
    target: str,
    allowed_states: Iterable[str],
) -> dict[str, Any] | None:
    states = set(allowed_states)
    matches = [
        row
        for row in allowlist.get("candidate_pairs", [])
        if row.get("from") == source and row.get("to") == target and row.get("state") in states
    ]
    if len(matches) != 1:
        return None
    row = matches[0]
    if not row.get("provider_converter") or not row.get("provider_target"):
        return None
    return row


def latex_denied(request: ConversionRequest) -> bool:
    suffix = Path(request.input_path).suffix.lower().lstrip(".")
    if suffix in {"tex", "ltx", "latex"}:
        return True
    name = (request.converter_name or "").lower()
    return "xelatex" in name or name in {"latex", "pdflatex", "lualatex"}


def validate_request(
    request: ConversionRequest,
    allowlist: dict[str, Any],
    *,
    allowed_states: Iterable[str] = ("CANDIDATE", "ACTIVE"),
) -> dict[str, Any]:
    findings: list[str] = []
    if request.profile_id != PROFILE_ID:
        findings.append("PROFILE_ID_MISMATCH")
    if not request.input_path:
        findings.append("INPUT_PATH_REQUIRED")
    if not request.input_media_type or not request.output_media_type:
        findings.append("MEDIA_TYPE_REQUIRED")
    if request.provider_arguments:
        findings.append("ARBITRARY_PROVIDER_ARGUMENTS_FORBIDDEN")
    if request.converter_name:
        findings.append("ARBITRARY_CONVERTER_SELECTION_FORBIDDEN")
    if latex_denied(request):
        findings.append("LATEX_FAMILY_DENIED")
    if allowlist.get("default_policy") != "DENY":
        findings.append("ALLOWLIST_NOT_FAIL_CLOSED")
    pair = resolve_pair(
        allowlist,
        request.input_media_type,
        request.output_media_type,
        allowed_states,
    )
    if pair is None:
        findings.append("CONVERSION_PAIR_NOT_ALLOWLISTED_FOR_REQUEST_STATE")
    if findings:
        raise AdmissionDenied(";".join(findings))
    return pair


def validate_runtime_contract(runtime: dict[str, Any]) -> None:
    required_true = [
        "non_root",
        "read_only_root",
        "cap_drop_all",
        "no_new_privileges",
        "seccomp",
        "resource_limits",
        "ephemeral_workspace",
    ]
    missing = [key for key in required_true if runtime.get(key) is not True]
    if missing:
        raise AdmissionDenied("runtime hardening missing: " + ",".join(missing))
    if runtime.get("host_mounts") not in (None, [], "DENY"):
        raise AdmissionDenied("host filesystem mounts forbidden")
    if runtime.get("outbound_network") != "DENY":
        raise AdmissionDenied("unrestricted outbound network forbidden")
    image = str(runtime.get("image", ""))
    if not digest_pinned_image(image):
        raise AdmissionDenied("provider image must be digest pinned")


def validate_current_host_receipt(receipt: dict[str, Any]) -> None:
    if receipt.get("schema") != "fa3.convertx-current-host-receipt.v1":
        raise AdmissionDenied("current-host receipt schema mismatch")
    if receipt.get("provider_id") != PROVIDER_ID:
        raise AdmissionDenied("current-host receipt provider mismatch")
    if receipt.get("status") != "PASS":
        raise AdmissionDenied("current-host receipt is not PASS")
    if receipt.get("evidence_level") != "CURRENT_HOST_PRODUCTION_E2E_PASS":
        raise AdmissionDenied("current-host evidence level insufficient")
    if receipt.get("candidate_validation") is not True:
        raise AdmissionDenied("receipt must originate from explicit candidate validation")
    if receipt.get("production_routing_enabled") is not False:
        raise AdmissionDenied("candidate evidence cannot claim production routing")
    if receipt.get("synthetic_input") is not False:
        raise AdmissionDenied("synthetic current-host input forbidden")
    if receipt.get("real_output_hash_observed") is not True:
        raise AdmissionDenied("real output hash missing")
    if receipt.get("egress_denial_verified") is not True:
        raise AdmissionDenied("egress denial not verified")
    if receipt.get("resource_admission_verified") is not True:
        raise AdmissionDenied("authoritative resource admission not verified")
    if not digest_pinned_image(str(receipt.get("provider_image", ""))):
        raise AdmissionDenied("receipt provider image is not digest pinned")


def _require_resource_admission(request: ConversionRequest, verified: bool) -> None:
    if not request.resource_admission_path:
        raise AdmissionDenied("execution requires authoritative resource-admission evidence")
    if verified is not True:
        raise AdmissionDenied("resource-admission evidence has not been authoritatively verified")


def candidate_validation_admission(
    request: ConversionRequest,
    provider: dict[str, Any],
    allowlist: dict[str, Any],
    runtime: dict[str, Any],
    *,
    explicit: bool,
    resource_admission_verified: bool,
) -> dict[str, Any]:
    pair = validate_request(request, allowlist, allowed_states=("CANDIDATE", "ACTIVE"))
    validate_runtime_contract(runtime)
    if explicit is not True:
        raise AdmissionDenied("candidate validation must be explicitly requested")
    if provider.get("status") not in {"QUARANTINED", "APPROVED"}:
        raise AdmissionDenied("provider state does not permit candidate validation")
    machine = provider.get("machine_interface", {})
    if machine.get("candidate_validation_allowed_while_quarantined") is not True:
        raise AdmissionDenied("candidate validation is not enabled by provider policy")
    if machine.get("candidate_validation_is_production_routing") is not False:
        raise AdmissionDenied("candidate validation must remain outside production routing")
    if machine.get("fa3_adapter_execution_contract_materialized") is not True:
        raise AdmissionDenied("FA3 adapter execution contract is not materialized")
    if machine.get("fa3_candidate_executor_materialized") is not True:
        raise AdmissionDenied("FA3 candidate executor is not materialized")
    _require_resource_admission(request, resource_admission_verified)
    return {
        "result": "ALLOW_CANDIDATE_VALIDATION",
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "pair": [request.input_media_type, request.output_media_type],
        "provider_converter": pair["provider_converter"],
        "provider_target": pair["provider_target"],
        "resource_admission_verified": True,
        "production_routing_enabled": False,
        "direct_provider_bypass": False,
    }


def machine_execution_admission(
    request: ConversionRequest,
    provider: dict[str, Any],
    allowlist: dict[str, Any],
    runtime: dict[str, Any],
    receipt: dict[str, Any] | None,
    *,
    resource_admission_verified: bool,
) -> dict[str, Any]:
    pair = validate_request(request, allowlist, allowed_states=("ACTIVE",))
    validate_runtime_contract(runtime)
    machine = provider.get("machine_interface", {})
    if provider.get("status") != "APPROVED" or not machine.get("machine_execution_enabled"):
        raise ProviderQuarantined("ConvertX machine execution remains quarantined")
    if machine.get("fa3_adapter_execution_contract_materialized") is not True:
        raise AdmissionDenied("production execution requires a materialized FA3 adapter contract")
    if machine.get("fa3_candidate_executor_materialized") is not True:
        raise AdmissionDenied("production execution requires the validated FA3 executor")
    _require_resource_admission(request, resource_admission_verified)
    if receipt is None:
        raise AdmissionDenied("machine execution requires current-host production E2E evidence")
    validate_current_host_receipt(receipt)
    return {
        "result": "ALLOW",
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "pair": [request.input_media_type, request.output_media_type],
        "provider_converter": pair["provider_converter"],
        "provider_target": pair["provider_target"],
        "resource_admission_verified": True,
        "direct_provider_bypass": False,
    }


def planning_admission(root: Path, request: ConversionRequest) -> dict[str, Any]:
    _profile, provider, allowlist = load_policy(root)
    pair = validate_request(request, allowlist, allowed_states=("CANDIDATE", "ACTIVE"))
    return {
        "result": "PLAN_ONLY",
        "provider_id": PROVIDER_ID,
        "provider_status": provider.get("status"),
        "machine_execution_enabled": provider.get("machine_interface", {}).get("machine_execution_enabled", False),
        "pair": [request.input_media_type, request.output_media_type],
        "pair_state": pair.get("state"),
        "reason": "Provider remains fail-closed until promotion gates, authoritative resource admission, and real current-host evidence pass; candidate pairs are never production-active implicitly.",
    }
