#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shlex
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count
from fa3_resource_evidence_normalization_gate import validate_evidence_envelope

CAPABILITY_COUNT = module_active_capability_count(__file__)
PROFILE_ID = "FA3-MEDIA-GPU-ZEROCOPY-001"
SANDBOX_PROFILE_ID = "FA3-AGENT-SANDBOX-001"
CURRENT_HOST_CONFORMANCE_ID = "FA3-RUNTIME-HARDENING-CURRENT-HOST-001"
CURRENT_HOST_GATESET_ID = "FA3-RUNTIME-HARDENING-CURRENT-HOST-GATESET-001"
CURRENT_HOST_GATE_RECORD_ID = "FA3-GATE-RUNTIME-HARDENING-CURRENT-HOST-001"
EVIDENCE_LEVEL = "CURRENT_HOST_RUNTIME_HARDENING_E2E_PASS"
RESOURCE_ADMISSION_CLAIM = "CURRENT_HOST_RESOURCE_ADMISSION_PASS"
RUNTIME_HARDENING_CLAIM = "CURRENT_HOST_RUNTIME_HARDENING_PASS"

FRAME_TRACE_COLLECTORS = {"CUPTI", "NSIGHT_SYSTEMS", "CUDA_ACTIVITY_TRACE"}
DIGEST_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
BDF_RE = re.compile(r"^(?:[0-9a-f]{4}:)?[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]$", re.I)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def payload_sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def normalize_bdf(value: Any) -> str:
    text = str(value or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{8}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", text):
        text = text[-12:]
    if re.fullmatch(r"[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", text):
        text = "0000:" + text
    return text


def valid_digest(value: Any) -> bool:
    return isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None


def parse_quadlet(text: str) -> dict[str, list[str]]:
    section = ""
    out: dict[str, list[str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip().lower()
            continue
        if section != "container" or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out.setdefault(key.strip().lower(), []).append(value.strip())
    return out


def _bool_all(values: list[str], expected: bool) -> bool:
    if not values:
        return False
    want = "true" if expected else "false"
    return all(v.strip().lower() == want for v in values)


def quadlet_security_findings(text: str, *, allow_image_placeholder: bool = False) -> list[str]:
    data = parse_quadlet(text)
    errors: list[str] = []

    networks = [v.strip().lower() for v in data.get("network", [])]
    if not networks or any(v != "none" for v in networks):
        errors.append("QUADLET_NETWORK_NOT_DENY_DEFAULT")
    if not _bool_all(data.get("readonly", []), True):
        errors.append("QUADLET_ROOTFS_NOT_READ_ONLY")
    if not _bool_all(data.get("nonewprivileges", []), True):
        errors.append("QUADLET_NO_NEW_PRIVILEGES_MISSING")
    pulls = [v.strip().lower() for v in data.get("pull", [])]
    if not pulls or any(v != "never" for v in pulls):
        errors.append("QUADLET_PULL_NOT_NEVER")

    drops = {token.strip().lower() for value in data.get("dropcapability", []) for token in re.split(r"[\s,]+", value) if token.strip()}
    if "all" not in drops:
        errors.append("QUADLET_DROP_CAPABILITY_ALL_MISSING")

    images = data.get("image", [])
    if len(images) != 1:
        errors.append("QUADLET_IMAGE_IDENTITY_AMBIGUOUS")
    elif allow_image_placeholder and images[0] == "@FA3_IMAGE_DIGEST@":
        pass
    elif not re.search(r"@sha256:[0-9a-f]{64}(?:$|\s)", images[0], flags=re.I):
        errors.append("QUADLET_IMAGE_NOT_DIGEST_PINNED")

    global_args: list[str] = []
    for value in data.get("globalargs", []):
        try:
            global_args.extend(shlex.split(value))
        except ValueError:
            errors.append("QUADLET_GLOBAL_ARGS_UNPARSEABLE")
    runtime_ok = "--runtime=runsc" in global_args
    if not runtime_ok:
        for idx, token in enumerate(global_args[:-1]):
            if token == "--runtime" and global_args[idx + 1] == "runsc":
                runtime_ok = True
                break
    if not runtime_ok:
        errors.append("QUADLET_GVISOR_RUNSC_NOT_ENFORCED")

    forbidden_tokens = {"--privileged", "--pid=host", "--ipc=host", "--network=host"}
    if any(token in forbidden_tokens for token in global_args):
        errors.append("QUADLET_FORBIDDEN_HOST_PRIVILEGE_ARGUMENT")

    if any(v.strip().lower() == "true" for v in data.get("environmenthost", [])):
        errors.append("QUADLET_ENVIRONMENT_HOST_EXPOSURE_FORBIDDEN")

    forbidden_mount_markers = (
        "/var/run/docker.sock",
        "/run/docker.sock",
        "/run/podman/podman.sock",
        "/root",
        "/proc",
        "/sys",
    )
    for volume in data.get("volume", []):
        source = volume.split(":", 1)[0].strip()
        if source.startswith("/home/") or source in {"/", "/home"} or any(marker in source for marker in forbidden_mount_markers):
            errors.append("QUADLET_FORBIDDEN_HOST_MOUNT")
            break

    return sorted(set(errors))


def runtime_inspect_has_runsc(value: Any) -> bool:
    def walk(node: Any) -> bool:
        if isinstance(node, dict):
            for key, item in node.items():
                key_l = str(key).lower()
                if key_l in {"runtime", "runtimepath", "ociruntime", "runtime_name"} and "runsc" in str(item).lower():
                    return True
                if walk(item):
                    return True
        elif isinstance(node, list):
            return any(walk(item) for item in node)
        return False

    return walk(value)


def resource_admission_binding(envelope: dict[str, Any]) -> tuple[dict[str, str] | None, list[str]]:
    errors = list(validate_evidence_envelope(envelope))
    if envelope.get("evidence_class") != "CURRENT_HOST_ADMISSION":
        errors.append("RESOURCE_ADMISSION_EVIDENCE_CLASS")
    result = envelope.get("result", {})
    if result.get("status") != "PASS" or RESOURCE_ADMISSION_CLAIM not in result.get("claims", []):
        errors.append("RESOURCE_ADMISSION_NOT_PASS")

    payload = envelope.get("payload", {})
    if payload.get("accelerator_required") is not True:
        errors.append("RESOURCE_ADMISSION_ACCELERATOR_NOT_REQUIRED")
    authorization = payload.get("hrb_authorization", {})
    if authorization.get("authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001" or authorization.get("status") != "VALID":
        errors.append("RESOURCE_ADMISSION_HRB_AUTHORIZATION_INVALID")

    lease = payload.get("hrb_lease_identity", {})
    uuid = str(lease.get("accelerator_uuid") or "").strip()
    bdf = normalize_bdf(lease.get("pci_bus_id"))
    if not uuid or not BDF_RE.fullmatch(bdf):
        errors.append("RESOURCE_ADMISSION_STABLE_GPU_IDENTITY_MISSING")
    if lease.get("broker_validation") is not True:
        errors.append("RESOURCE_ADMISSION_BROKER_VALIDATION_MISSING")

    selected = payload.get("compute_profile", {}).get("selected_accelerator_set", [])
    if len(selected) != 1:
        errors.append("RESOURCE_ADMISSION_SELECTED_ACCELERATOR_SET_NOT_EXACT")
    elif selected[0].get("uuid") != uuid or normalize_bdf(selected[0].get("pci_bdf")) != bdf:
        errors.append("RESOURCE_ADMISSION_GPU_BINDING_MISMATCH")

    execution = envelope.get("execution_context", {})
    if not execution.get("host_attestation_ref"):
        errors.append("RESOURCE_ADMISSION_HOST_ATTESTATION_REF_MISSING")
    if not execution.get("hrb_lease_ref"):
        errors.append("RESOURCE_ADMISSION_HRB_LEASE_REF_MISSING")

    if errors:
        return None, sorted(set(errors))
    return {
        "gpu_uuid": uuid,
        "pci_bdf": bdf,
        "host_attestation_ref": str(execution["host_attestation_ref"]),
        "compute_profile_ref": str(execution.get("compute_profile_ref") or ""),
        "workload_resource_envelope_ref": str(execution.get("workload_resource_envelope_ref") or ""),
        "hrb_lease_ref": str(execution["hrb_lease_ref"]),
    }, []


def pcie_copy_budget_findings(value: dict[str, Any], *, gpu_uuid: str, pci_bdf: str) -> list[str]:
    errors: list[str] = []
    if value.get("status") != "PASS":
        errors.append("PCIE_COPY_BUDGET_NOT_PASS")
    if value.get("semantics") != "SUPPORTING_COPY_BUDGET_NOT_ZERO_COPY_PROOF":
        errors.append("PCIE_COPY_BUDGET_SEMANTICS_INVALID")
    if value.get("gpu_uuid") != gpu_uuid or normalize_bdf(value.get("pci_bdf")) != normalize_bdf(pci_bdf):
        errors.append("PCIE_COPY_BUDGET_GPU_BINDING_MISMATCH")
    try:
        interval = float(value.get("sampling_interval_seconds"))
        samples = int(value.get("sample_count"))
        max_tx = float(value.get("max_tx_kb_s"))
        max_rx = float(value.get("max_rx_kb_s"))
        budget = float(value.get("budget_kb_s"))
        ratio = float(value.get("budget_ratio"))
    except (TypeError, ValueError):
        return errors + ["PCIE_COPY_BUDGET_NUMERIC_FIELDS_INVALID"]
    if not (0 < interval <= 0.025):
        errors.append("PCIE_COPY_BUDGET_SAMPLING_TOO_SLOW")
    if samples < 10:
        errors.append("PCIE_COPY_BUDGET_TOO_FEW_SAMPLES")
    if not (0 < ratio <= 0.05):
        errors.append("PCIE_COPY_BUDGET_RATIO_INVALID")
    if budget <= 0 or max_tx < 0 or max_rx < 0:
        errors.append("PCIE_COPY_BUDGET_VALUES_INVALID")
    elif max_tx >= budget or max_rx >= budget:
        errors.append("PCIE_COPY_BUDGET_EXCEEDED")
    if value.get("capacity_source") != "LIVE_NEGOTIATED_PCIE_LINK_GEN_WIDTH":
        errors.append("PCIE_COPY_BUDGET_CAPACITY_NOT_LIVE")
    return sorted(set(errors))


def frame_trace_findings(value: dict[str, Any], *, gpu_uuid: str, pci_bdf: str) -> list[str]:
    errors: list[str] = []
    if value.get("schema") != "fa3.cuda-copy-trace.v1":
        errors.append("FRAME_TRACE_SCHEMA_MISMATCH")
    if value.get("status") != "PASS":
        errors.append("FRAME_TRACE_NOT_PASS")
    collector = value.get("collector", {})
    if collector.get("kind") not in FRAME_TRACE_COLLECTORS or not collector.get("version"):
        errors.append("FRAME_TRACE_COLLECTOR_UNSUPPORTED")
    if value.get("gpu_uuid") != gpu_uuid or normalize_bdf(value.get("pci_bdf")) != normalize_bdf(pci_bdf):
        errors.append("FRAME_TRACE_GPU_BINDING_MISMATCH")

    segment = value.get("neural_segment", {})
    try:
        frame_count = int(segment.get("frame_count"))
        h2d = int(segment.get("host_to_device_frame_copy_count"))
        d2h = int(segment.get("device_to_host_frame_copy_count"))
        round_trips = int(segment.get("host_frame_round_trips"))
    except (TypeError, ValueError):
        return errors + ["FRAME_TRACE_COUNTERS_INVALID"]
    if frame_count <= 0:
        errors.append("FRAME_TRACE_NO_FRAMES")
    if h2d != 0 or d2h != 0 or round_trips != 0:
        errors.append("FRAME_TRACE_HOST_FRAME_COPY_OBSERVED")
    if segment.get("dlpack_shared_gpu_memory") is not True:
        errors.append("FRAME_TRACE_DLPACK_SHARED_GPU_MEMORY_NOT_PROVEN")

    full_claim = value.get("full_pipeline_zero_copy_claim") is True
    full_proven = value.get("full_pipeline_zero_copy_proven") is True
    if full_claim and not full_proven:
        errors.append("FRAME_TRACE_UNPROVEN_FULL_PIPELINE_ZERO_COPY_CLAIM")
    return sorted(set(errors))


def validate_current_host_envelope(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str) -> None:
        findings.append({"code": code, "severity": "P0", "message": message})

    for err in validate_evidence_envelope(envelope):
        fail("RUNTIME-HARDENING-HOST-ENVELOPE", err)

    if envelope.get("evidence_class") != "CURRENT_HOST_RUNTIME":
        fail("RUNTIME-HARDENING-HOST-001", "Evidence class must be CURRENT_HOST_RUNTIME")

    subject = envelope.get("subject", {})
    if subject.get("profile_id") != PROFILE_ID or subject.get("gate_id") != CURRENT_HOST_GATE_RECORD_ID:
        fail("RUNTIME-HARDENING-HOST-002", "Current-host subject profile/gate binding mismatch")

    result = envelope.get("result", {})
    claims = set(result.get("claims", []))
    non_claims = set(result.get("non_claims", []))
    if result.get("status") != "PASS" or RUNTIME_HARDENING_CLAIM not in claims:
        fail("RUNTIME-HARDENING-HOST-003", "Current-host runtime-hardening PASS claim missing")
    required_non_claims = {
        "GLOBAL_FA3_PROMOTION",
        "FULL_PIPELINE_TRUE_ZERO_COPY",
        "HOST_HARDWARE_PORTABILITY_REQUIREMENT",
    }
    if not required_non_claims.issubset(non_claims):
        fail("RUNTIME-HARDENING-HOST-004", "Required non-claims missing")

    payload = envelope.get("payload", {})
    if payload.get("schema") != "fa3.runtime-hardening-current-host.payload.v1":
        fail("RUNTIME-HARDENING-HOST-005", "Runtime-hardening payload schema mismatch")
    if payload.get("fixture_semantics") == "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST":
        fail("RUNTIME-HARDENING-HOST-006", "Synthetic fixture cannot be current-host evidence")
    if payload.get("real_current_host_execution") is not True:
        fail("RUNTIME-HARDENING-HOST-007", "Real current-host execution flag missing")

    invariants = payload.get("invariants", {})
    if not (
        invariants.get("capability_count") == CAPABILITY_COUNT
        and invariants.get("new_capabilities") == 0
        and invariants.get("new_architectural_authorities") == 0
        and invariants.get("global_promotion_claim") is False
    ):
        fail("RUNTIME-HARDENING-HOST-008", "Capability/authority/promotion invariant drift")

    binding = payload.get("resource_binding", {})
    gpu_uuid = str(binding.get("gpu_uuid") or "")
    pci_bdf = normalize_bdf(binding.get("pci_bdf"))
    if not gpu_uuid or not BDF_RE.fullmatch(pci_bdf):
        fail("RUNTIME-HARDENING-HOST-009", "Stable GPU UUID/BDF binding missing")

    quadlet = payload.get("quadlet_sandbox", {})
    if quadlet.get("status") != "PASS" or quadlet.get("findings"):
        fail("RUNTIME-HARDENING-HOST-010", "Installed Quadlet sandbox conformance failed")

    runtime = payload.get("gvisor_runtime", {})
    if not (
        runtime.get("status") == "PASS"
        and runtime.get("runsc_available") is True
        and runtime.get("runtime_inspect_runsc") is True
        and runtime.get("nvproxy_supported_driver") is True
        and runtime.get("unsupported_driver_override") is False
    ):
        fail("RUNTIME-HARDENING-HOST-011", "gVisor/runsc/nvproxy runtime proof incomplete")

    for err in pcie_copy_budget_findings(payload.get("pcie_copy_budget", {}), gpu_uuid=gpu_uuid, pci_bdf=pci_bdf):
        fail("RUNTIME-HARDENING-HOST-012", err)
    for err in frame_trace_findings(payload.get("frame_copy_trace", {}), gpu_uuid=gpu_uuid, pci_bdf=pci_bdf):
        fail("RUNTIME-HARDENING-HOST-013", err)

    checks = payload.get("checks", {})
    expected = {
        "CRIT-020-QUADLET-GVISOR-SANDBOX": "PASS",
        "CRIT-021-AGENT-BOUNDARY": "PASS",
        "CRIT-022A-PCIE-COPY-BUDGET": "PASS",
        "CRIT-022B-GPU-FRAME-ZERO-HOST-ROUND-TRIP": "PASS",
    }
    if checks != expected:
        fail("RUNTIME-HARDENING-HOST-014", "Required CRIT check set is incomplete or non-PASS")

    return findings
