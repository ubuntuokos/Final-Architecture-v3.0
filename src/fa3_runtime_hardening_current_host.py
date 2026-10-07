#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from fa3_release_baseline import module_active_capability_count
from fa3_resource_evidence_normalization_gate import validate_evidence_envelope

CAPABILITY_COUNT = module_active_capability_count(__file__)
CONFORMANCE_ID = "FA3-RUNTIME-HARDENING-CURRENT-HOST-CONFORMANCE-001"
GATE_ID = "FA3-RUNTIME-HARDENING-CURRENT-HOST-GATESET-001"

RECEIPT_PATHS = {
    "runtime_isolation_agent_sandbox": "evidence/receipts/runtime-isolation-sandbox-current-host.json",
    "media_accelerator_memory_residency": "evidence/receipts/media-gpu-zerocopy-current-host.json",
    "hu_aqc": "evidence/receipts/hu-aqc-current-host.json",
    "promotion_shadow": "evidence/receipts/promotion-shadow-current-host.json",
}


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def repo_head(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "UNKNOWN"


def fresh_timestamp(value: Any, max_age_hours: int = 24) -> bool:
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        age = dt.datetime.now(dt.timezone.utc) - parsed.astimezone(dt.timezone.utc)
        return dt.timedelta(0) <= age <= dt.timedelta(hours=max_age_hours)
    except Exception:
        return False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_bdf(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    if raw.count(":") == 2 and len(raw.split(":")[0]) == 8:
        raw = raw[4:]
    if raw.count(":") == 1:
        raw = "0000:" + raw
    return raw


def find_key(value: Any, names: set[str]) -> Any:
    wanted = {x.lower() for x in names}
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in wanted:
                return item
        for item in value.values():
            found = find_key(item, names)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_key(item, names)
            if found is not None:
                return found
    return None


def _nested_evidence_envelope_reasons(receipt: Any, *, surface: str) -> list[str]:
    if not isinstance(receipt, dict):
        return ["receipt is not an object"]
    envelope = receipt.get("evidence_envelope")
    if not isinstance(envelope, dict):
        return ["FA3 Evidence Envelope missing"]
    errors = list(validate_evidence_envelope(envelope))
    if envelope.get("evidence_class") != "CURRENT_HOST_RUNTIME":
        errors.append("evidence class is not CURRENT_HOST_RUNTIME")
    subject = envelope.get("subject", {})
    if subject.get("gate_id") != GATE_ID:
        errors.append("evidence envelope gate binding mismatch")
    result = envelope.get("result", {})
    if result.get("scope") != surface:
        errors.append("evidence envelope surface scope mismatch")
    if "GLOBAL_FA3_PROMOTION" not in result.get("non_claims", []):
        errors.append("evidence envelope missing GLOBAL_FA3_PROMOTION non-claim")
    execution = envelope.get("execution_context", {})
    if not execution.get("host_attestation_ref"):
        errors.append("evidence envelope host attestation binding missing")
    return errors


def _base_reasons(
    receipt: Any,
    *,
    root: Path,
    schema: str,
    surface: str,
) -> list[str]:
    reasons: list[str] = []
    if not isinstance(receipt, dict):
        return ["receipt is not an object"]
    if receipt.get("schema") != schema:
        reasons.append("schema mismatch")
    if receipt.get("surface") != surface:
        reasons.append("surface mismatch")
    if receipt.get("repository_head") != repo_head(root):
        reasons.append("repository HEAD binding mismatch")
    if not fresh_timestamp(receipt.get("captured_at")):
        reasons.append("receipt timestamp is stale or invalid")
    if receipt.get("synthetic") is not False:
        reasons.append("synthetic evidence cannot qualify current-host PASS")
    if receipt.get("global_promotion_claim") is not False:
        reasons.append("component receipt attempted global promotion")
    return reasons


def validate_runtime_sandbox_receipt(receipt: Any, *, root: Path) -> tuple[bool, list[str]]:
    reasons = _base_reasons(
        receipt,
        root=root,
        schema="fa3.runtime-isolation-sandbox-current-host-receipt.v1",
        surface="RUNTIME_ISOLATION_AGENT_SANDBOX",
    )
    if not isinstance(receipt, dict):
        return False, reasons
    if receipt.get("result") != "PASS" or receipt.get("status") != "CURRENT_HOST_PASS":
        reasons.append("runtime/sandbox collector is not CURRENT_HOST_PASS")
    cgroup = receipt.get("cgroup_v2", {})
    rootless = receipt.get("rootless_oci", {})
    wasi = receipt.get("wasmtime_wasi", {})
    gvisor = receipt.get("gvisor", {})
    if cgroup.get("present") is not True:
        reasons.append("cgroup v2 is not proven")
    if not (
        rootless.get("status") == "PASS"
        and rootless.get("rootless") is True
        and rootless.get("network_none") is True
        and rootless.get("read_only") is True
        and rootless.get("cap_drop_all") is True
        and rootless.get("pull_never") is True
        and rootless.get("real_execution") is True
    ):
        reasons.append("rootless OCI isolation real execution is incomplete")
    if not (
        wasi.get("status") == "PASS"
        and wasi.get("real_execution") is True
        and wasi.get("explicit_preopens") == []
        and wasi.get("network_lease_provided") is False
    ):
        reasons.append("Wasmtime/WASI restricted execution proof is incomplete")
    if not (
        gvisor.get("compatibility_smoke_status") == "PASS"
        and gvisor.get("production_oci_isolation_status") == "PASS"
        and gvisor.get("host_fs_default_exposure") is False
        and gvisor.get("network_default_deny_verified") is True
        and gvisor.get("explicit_mount_allowlist_verified") is True
        and gvisor.get("ephemeral_overlay_verified") is True
        and gvisor.get("runtime_inspect_runsc") is True
        and (gvisor.get("gpu_projection_required") is not True or gvisor.get("nvproxy_supported_driver") is True)
        and gvisor.get("unsupported_driver_override") is False
    ):
        reasons.append("gVisor production OCI isolation/runsc/nvproxy proof is incomplete")
    quadlet = receipt.get("quadlet", {})
    if not (
        quadlet.get("status") == "PASS"
        and quadlet.get("network_none") is True
        and quadlet.get("read_only") is True
        and quadlet.get("no_new_privileges") is True
        and quadlet.get("drop_capability_all") is True
        and quadlet.get("pull_never") is True
        and quadlet.get("image_digest_pinned") is True
        and quadlet.get("runtime_runsc") is True
        and quadlet.get("forbidden_host_mounts_present") is False
    ):
        reasons.append("installed Quadlet fail-closed policy is incomplete")
    reasons.extend(_nested_evidence_envelope_reasons(receipt, surface="RUNTIME_ISOLATION_AGENT_SANDBOX"))
    return not reasons, reasons


def _version_tuple(raw: Any) -> tuple[int, ...]:
    parts = []
    for token in str(raw or "").split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def validate_media_residency_receipt(receipt: Any, *, root: Path) -> tuple[bool, list[str]]:
    reasons = _base_reasons(
        receipt,
        root=root,
        schema="fa3.media-accelerator-residency-current-host-receipt.v1",
        surface="MEDIA_ACCELERATOR_MEMORY_RESIDENCY",
    )
    if not isinstance(receipt, dict):
        return False, reasons
    if receipt.get("result") != "PASS" or receipt.get("status") != "CURRENT_HOST_PASS":
        reasons.append("media collector is not CURRENT_HOST_PASS")
    hrb = receipt.get("hrb_binding", {})
    provider_id = receipt.get("provider_id")
    residency = receipt.get("memory_residency", {})
    telemetry = receipt.get("copy_telemetry", {})
    if not (
        hrb.get("status") == "PASS"
        and hrb.get("stable_accelerator_id")
        and hrb.get("provider_binding")
    ):
        reasons.append("fresh provider-compatible HRB accelerator binding is not proven")
    if not isinstance(provider_id, str) or not provider_id.startswith("FA3-PROVIDER-"):
        reasons.append("provider adapter identity missing")
    if not (
        residency.get("status") == "PASS"
        and residency.get("provider_memory_domain")
        and residency.get("shared_buffer_identity") is True
        and residency.get("host_frame_round_trips") == 0
    ):
        reasons.append("provider memory-residency proof is incomplete")
    if telemetry and telemetry.get("semantics") != "ADVISORY_TRANSFER_TELEMETRY_NOT_ZERO_COPY_PROOF":
        reasons.append("transfer telemetry improperly claims zero-copy authority")
    trace = receipt.get("frame_copy_trace", {})
    segment = trace.get("neural_segment", {}) if isinstance(trace, dict) else {}
    if not (
        trace.get("schema") == "fa3.accelerator-copy-trace.v1"
        and trace.get("status") == "PASS"
        and bool(trace.get("collector", {}).get("kind"))
        and int(segment.get("frame_count", 0)) > 0
        and int(segment.get("host_to_device_frame_copy_count", -1)) == 0
        and int(segment.get("device_to_host_frame_copy_count", -1)) == 0
        and int(segment.get("host_frame_round_trips", -1)) == 0
        and segment.get("shared_accelerator_memory") is True
    ):
        reasons.append("provider frame-copy trace does not prove zero host frame round-trips")
    if receipt.get("classification") != "ZERO_COPY_PROVEN":
        reasons.append("receipt classification is not ZERO_COPY_PROVEN")
    if receipt.get("full_pipeline_zero_copy_claim") is not False:
        reasons.append("unsupported full-pipeline zero-copy claim")
    reasons.extend(_nested_evidence_envelope_reasons(receipt, surface="MEDIA_ACCELERATOR_MEMORY_RESIDENCY"))
    return not reasons, reasons


def validate_hu_aqc_receipt(receipt: Any, *, root: Path) -> tuple[bool, list[str]]:
    reasons = _base_reasons(
        receipt,
        root=root,
        schema="fa3.hu-aqc-current-host-receipt.v1",
        surface="HU_AQC",
    )
    if not isinstance(receipt, dict):
        return False, reasons
    if receipt.get("result") != "PASS" or receipt.get("status") != "CURRENT_HOST_PASS":
        reasons.append("HU-AQC collector is not CURRENT_HOST_PASS")
    if receipt.get("locale") != "hu-HU":
        reasons.append("locale is not hu-HU")
    if receipt.get("audio_sha256") in (None, ""):
        reasons.append("audio digest missing")
    if receipt.get("signal_metrics_recomputed_locally") is not True:
        reasons.append("signal metrics were not recomputed locally")
    if receipt.get("asr_error_rates_recomputed_locally") is not True:
        reasons.append("ASR CER/WER were not recomputed locally")
    if receipt.get("scorer_provenance_admitted") is not True:
        reasons.append("required scorer provenance/license admission missing")
    aqc = receipt.get("aqc", {})
    if aqc.get("passed") is not True or aqc.get("single_metric_authority") is not False:
        reasons.append("multi-signal HU-AQC verdict is not PASS")
    dimensions = aqc.get("dimensions", {})
    required = {
        "text_language",
        "grammar_style",
        "toxicity_policy",
        "intelligibility",
        "naturalness",
        "signal_integrity",
        "speaker_identity",
    }
    if set(dimensions) != required or not all(dimensions.values()):
        reasons.append("required HU-AQC dimensions are incomplete or failed")
    return not reasons, reasons


def validate_shadow_receipt(receipt: Any, *, root: Path) -> tuple[bool, list[str]]:
    reasons = _base_reasons(
        receipt,
        root=root,
        schema="fa3.promotion-shadow-current-host-receipt.v1",
        surface="PROMOTION_SHADOW",
    )
    if not isinstance(receipt, dict):
        return False, reasons
    if receipt.get("result") != "PASS" or receipt.get("status") != "CURRENT_HOST_PASS":
        reasons.append("Shadow collector is not CURRENT_HOST_PASS")
    if receipt.get("sandbox_dependency_status") != "PASS":
        reasons.append("Shadow current-host run is not bound to a passed sandbox receipt")
    if receipt.get("execution_allowed") is not True:
        reasons.append("Shadow execution plan was not admitted")
    if receipt.get("authoritative_output") is not False:
        reasons.append("Shadow output became authoritative")
    if receipt.get("external_side_effects") is not False:
        reasons.append("Shadow execution produced external side effects")
    if receipt.get("output_quarantined") is not True:
        reasons.append("Shadow output was not quarantined")
    if receipt.get("workspace_destroyed") is not True:
        reasons.append("Shadow ephemeral workspace was not destroyed")
    if receipt.get("promotion_authority") is not False or receipt.get("may_assign_promoted") is not False:
        reasons.append("Shadow execution attempted promotion authority")
    return not reasons, reasons


VALIDATORS: dict[str, Callable[..., tuple[bool, list[str]]]] = {
    "runtime_isolation_agent_sandbox": validate_runtime_sandbox_receipt,
    "media_accelerator_memory_residency": validate_media_residency_receipt,
    "hu_aqc": validate_hu_aqc_receipt,
    "promotion_shadow": validate_shadow_receipt,
}
