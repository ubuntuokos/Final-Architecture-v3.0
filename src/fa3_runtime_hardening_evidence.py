#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shlex
from typing import Any

from fa3_resource_evidence_normalization_gate import validate_evidence_envelope

FRAME_TRACE_COLLECTORS = {"CUPTI", "NSIGHT_SYSTEMS", "CUDA_ACTIVITY_TRACE"}
PCIE_PAYLOAD_KB_S_PER_LANE = {
    1: 250_000.0,
    2: 500_000.0,
    3: 984_615.0,
    4: 1_969_230.0,
    5: 3_938_460.0,
}


def canonical_payload_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def normalize_bdf(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    if re.fullmatch(r"[0-9a-f]{8}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", raw):
        raw = raw[-12:]
    if re.fullmatch(r"[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", raw):
        raw = "0000:" + raw
    return raw


def parse_quadlet(text: str) -> dict[str, list[str]]:
    section = ""
    values: dict[str, list[str]] = {}
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
        values.setdefault(key.strip().lower(), []).append(value.strip())
    return values


def quadlet_security_reasons(text: str, *, allow_image_placeholder: bool = False) -> list[str]:
    data = parse_quadlet(text)
    reasons: list[str] = []

    networks = [v.lower() for v in data.get("network", [])]
    if not networks or any(v != "none" for v in networks):
        reasons.append("quadlet network is not deny-default")
    if [v.lower() for v in data.get("readonly", [])] != ["true"]:
        reasons.append("quadlet root filesystem is not read-only")
    if [v.lower() for v in data.get("nonewprivileges", [])] != ["true"]:
        reasons.append("quadlet NoNewPrivileges=true is missing")
    pulls = [v.lower() for v in data.get("pull", [])]
    if not pulls or any(v != "never" for v in pulls):
        reasons.append("quadlet Pull=never is missing")
    drops = {
        token.lower()
        for value in data.get("dropcapability", [])
        for token in re.split(r"[\s,]+", value)
        if token
    }
    if "all" not in drops:
        reasons.append("quadlet DropCapability=all is missing")

    images = data.get("image", [])
    if len(images) != 1:
        reasons.append("quadlet image identity is ambiguous")
    elif allow_image_placeholder and images[0] == "@FA3_IMAGE_DIGEST@":
        pass
    elif re.search(r"@sha256:[0-9a-f]{64}$", images[0], re.I) is None:
        reasons.append("quadlet image is not digest pinned")

    args: list[str] = []
    for value in data.get("globalargs", []):
        try:
            args.extend(shlex.split(value))
        except ValueError:
            reasons.append("quadlet GlobalArgs cannot be parsed")
    runtime_ok = "--runtime=runsc" in args
    runtime_ok = runtime_ok or any(
        args[i] == "--runtime" and args[i + 1] == "runsc" for i in range(max(0, len(args) - 1))
    )
    if not runtime_ok:
        reasons.append("quadlet does not enforce runsc")

    forbidden = {"--privileged", "--pid=host", "--ipc=host", "--network=host"}
    if any(token in forbidden for token in args):
        reasons.append("quadlet contains forbidden host privilege argument")

    for volume in data.get("volume", []):
        source = volume.split(":", 1)[0].strip()
        if (
            source in {"/", "/home", "/root", "/proc", "/sys"}
            or source.startswith("/home/")
            or source in {"/var/run/docker.sock", "/run/docker.sock", "/run/podman/podman.sock"}
        ):
            reasons.append("quadlet exposes forbidden host mount")
            break
    return sorted(set(reasons))


def inspect_uses_runsc(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in {"runtime", "runtimepath", "ociruntime", "runtime_name"}:
                if "runsc" in str(item).lower():
                    return True
            if inspect_uses_runsc(item):
                return True
    elif isinstance(value, list):
        return any(inspect_uses_runsc(item) for item in value)
    return False


def resource_admission_binding(envelope: dict[str, Any]) -> tuple[dict[str, str] | None, list[str]]:
    reasons = list(validate_evidence_envelope(envelope))
    if envelope.get("evidence_class") != "CURRENT_HOST_ADMISSION":
        reasons.append("resource admission evidence class mismatch")
    result = envelope.get("result", {})
    if result.get("status") != "PASS" or "CURRENT_HOST_RESOURCE_ADMISSION_PASS" not in result.get("claims", []):
        reasons.append("resource admission is not a scoped current-host PASS")

    payload = envelope.get("payload", {})
    if payload.get("accelerator_required") is not True:
        reasons.append("resource admission does not require an accelerator")
    auth = payload.get("hrb_authorization", {})
    if auth.get("authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001" or auth.get("status") != "VALID":
        reasons.append("HRB authorization is not valid")

    lease = payload.get("hrb_lease_identity", {})
    gpu_uuid = str(lease.get("accelerator_uuid") or "").strip()
    pci_bdf = normalize_bdf(lease.get("pci_bus_id"))
    if not gpu_uuid or not re.fullmatch(r"[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", pci_bdf):
        reasons.append("stable HRB GPU UUID/BDF identity is missing")
    if lease.get("broker_validation") is not True:
        reasons.append("HRB broker validation is missing")

    selected = payload.get("compute_profile", {}).get("selected_accelerator_set", [])
    if len(selected) != 1:
        reasons.append("selected accelerator set is not exactly one device")
    elif selected[0].get("uuid") != gpu_uuid or normalize_bdf(selected[0].get("pci_bdf")) != pci_bdf:
        reasons.append("selected accelerator does not match HRB lease identity")

    execution = envelope.get("execution_context", {})
    if not execution.get("host_attestation_ref"):
        reasons.append("host attestation reference is missing")
    if not execution.get("hrb_lease_ref"):
        reasons.append("HRB lease reference is missing")

    if reasons:
        return None, sorted(set(reasons))
    return {
        "gpu_uuid": gpu_uuid,
        "pci_bdf": pci_bdf,
        "host_attestation_ref": str(execution["host_attestation_ref"]),
        "compute_profile_ref": str(execution.get("compute_profile_ref") or ""),
        "workload_resource_envelope_ref": str(execution.get("workload_resource_envelope_ref") or ""),
        "hrb_lease_ref": str(execution["hrb_lease_ref"]),
        "resource_admission_evidence_id": str(envelope.get("evidence_id") or ""),
    }, []


def frame_copy_trace_reasons(trace: dict[str, Any], *, gpu_uuid: str, pci_bdf: str) -> list[str]:
    reasons: list[str] = []
    if trace.get("schema") != "fa3.cuda-copy-trace.v1":
        reasons.append("frame-copy trace schema mismatch")
    if trace.get("status") != "PASS":
        reasons.append("frame-copy trace is not PASS")
    collector = trace.get("collector", {})
    if collector.get("kind") not in FRAME_TRACE_COLLECTORS or not collector.get("version"):
        reasons.append("frame-copy trace collector is not admitted")
    if trace.get("gpu_uuid") != gpu_uuid or normalize_bdf(trace.get("pci_bdf")) != normalize_bdf(pci_bdf):
        reasons.append("frame-copy trace GPU identity mismatch")

    segment = trace.get("neural_segment", {})
    try:
        frame_count = int(segment.get("frame_count"))
        h2d = int(segment.get("host_to_device_frame_copy_count"))
        d2h = int(segment.get("device_to_host_frame_copy_count"))
        round_trips = int(segment.get("host_frame_round_trips"))
    except (TypeError, ValueError):
        return reasons + ["frame-copy trace counters are invalid"]
    if frame_count <= 0:
        reasons.append("frame-copy trace contains no frames")
    if h2d != 0 or d2h != 0 or round_trips != 0:
        reasons.append("host frame copy observed inside neural segment")
    if segment.get("dlpack_shared_gpu_memory") is not True:
        reasons.append("DLPack shared GPU memory is not proven by trace")
    if trace.get("full_pipeline_zero_copy_claim") is True and trace.get("full_pipeline_zero_copy_proven") is not True:
        reasons.append("full-pipeline zero-copy claim is not separately proven")
    return sorted(set(reasons))


def pcie_copy_budget_reasons(telemetry: dict[str, Any], *, gpu_uuid: str, pci_bdf: str) -> list[str]:
    reasons: list[str] = []
    if telemetry.get("status") != "PASS":
        reasons.append("PCIe copy budget is not PASS")
    if telemetry.get("semantics") != "SUPPORTING_COPY_BUDGET_NOT_ZERO_COPY_PROOF":
        reasons.append("PCIe telemetry incorrectly claims zero-copy semantics")
    if telemetry.get("gpu_uuid") != gpu_uuid or normalize_bdf(telemetry.get("pci_bdf")) != normalize_bdf(pci_bdf):
        reasons.append("PCIe telemetry GPU identity mismatch")
    try:
        interval = float(telemetry.get("sampling_interval_seconds"))
        sample_count = int(telemetry.get("sample_count"))
        max_tx = float(telemetry.get("max_tx_kb_s"))
        max_rx = float(telemetry.get("max_rx_kb_s"))
        budget = float(telemetry.get("budget_kb_s"))
        ratio = float(telemetry.get("budget_ratio"))
    except (TypeError, ValueError):
        return reasons + ["PCIe telemetry numeric fields are invalid"]
    if not (0 < interval <= 0.025):
        reasons.append("PCIe sampling interval exceeds 25 ms")
    if sample_count < 10:
        reasons.append("PCIe telemetry has fewer than 10 samples")
    if not (0 < ratio <= 0.05):
        reasons.append("PCIe copy-budget ratio exceeds 5 percent")
    if budget <= 0 or max_tx < 0 or max_rx < 0 or max_tx >= budget or max_rx >= budget:
        reasons.append("PCIe copy budget exceeded or invalid")
    if telemetry.get("capacity_source") != "LIVE_NEGOTIATED_PCIE_LINK_GEN_WIDTH":
        reasons.append("PCIe capacity was not derived from live link generation/width")
    return sorted(set(reasons))


def build_embedded_evidence_envelope(
    *,
    resource_admission: dict[str, Any],
    payload_schema_id: str,
    payload: dict[str, Any],
    subject: dict[str, Any],
    collector_id: str,
    collector_revision: str,
    generated_at: str,
    claims: list[str],
    non_claims: list[str],
    artifact_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    binding, reasons = resource_admission_binding(resource_admission)
    if reasons or binding is None:
        raise ValueError("invalid resource admission evidence: " + "; ".join(reasons))
    return {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": f"{collector_id}-{generated_at}",
        "evidence_class": "CURRENT_HOST_RUNTIME",
        "subject": subject,
        "canonical_context": dict(resource_admission.get("canonical_context", {})),
        "execution_context": {
            "host_attestation_ref": binding["host_attestation_ref"],
            "compute_profile_ref": binding["compute_profile_ref"],
            "workload_resource_envelope_ref": binding["workload_resource_envelope_ref"],
            "hrb_lease_ref": binding["hrb_lease_ref"],
            "diagnostics": {},
        },
        "provenance": {
            "collector_id": collector_id,
            "collector_revision": collector_revision,
            "generated_at": generated_at,
            "artifact_digests": artifact_digests,
        },
        "integrity": {"payload_sha256": canonical_payload_hash(payload)},
        "result": {
            "status": "PASS",
            "scope": "COMPONENT_CURRENT_HOST_RUNTIME",
            "claims": claims,
            "non_claims": non_claims,
        },
        "payload_schema_id": payload_schema_id,
        "payload": payload,
        "promotion_authority": False,
    }


def embedded_evidence_reasons(envelope: Any, *, expected_payload: dict[str, Any]) -> list[str]:
    if not isinstance(envelope, dict):
        return ["embedded FA3 evidence envelope missing"]
    reasons = list(validate_evidence_envelope(envelope))
    if envelope.get("payload") != expected_payload:
        reasons.append("embedded evidence payload does not match typed receipt payload")
    if envelope.get("promotion_authority") is not False:
        reasons.append("embedded evidence envelope attempted promotion authority")
    return sorted(set(reasons))
