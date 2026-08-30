#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_PROVIDER_ID = "FA3-PROVIDER-MAX-001"
MOJO_PROVIDER_ID = "FA3-PROVIDER-MOJO-001"
RUNTIME_ID = "FA3-MODULAR-RUNTIME-CONFORMANCE-001"
HRB_PROFILE_ID = "FA3-HOST-RESOURCE-BROKER-001"
HRB_LEASE_SCHEMA = "AcceleratorExecutionLease@1"
DEFAULT_MODEL = "LiquidAI/LFM2.5-350M"
DEFAULT_MODEL_REVISION = "9e6c6ccf47cd318696e137d381a7ded8fe4df09f"
MODEL_ALLOWLIST_ID = "FA3-MODULAR-MODEL-ALLOWLIST-001"
DEFAULT_HRB_VERIFY_COMMAND = ("/usr/local/bin/fa3-host-resource-broker", "validate-lease", "{lease}")

class ProviderError(RuntimeError):
    pass

class PolicyDenied(ProviderError):
    pass

@dataclass(frozen=True)
class MaxServeRequest:
    model: str = DEFAULT_MODEL
    model_revision: str = ""
    devices: str = "cpu"
    host: str = "127.0.0.1"
    port: int = 18080
    max_length: int = 512
    max_new_tokens: int = 16
    hrb_lease_path: str | None = None
    evidence_channel: str = "stable"
    device_memory_utilization: float | None = None

def load_allowlist(root: Path) -> dict[str, Any]:
    return json.loads((root / "canonical/FA3-MODULAR-MODEL-ALLOWLIST-001.json").read_text(encoding="utf-8"))

def allowed_model(allowlist: dict[str, Any], model_id: str) -> dict[str, Any]:
    for model in allowlist.get("models", []):
        if model.get("model_id") == model_id:
            return model
    raise PolicyDenied("model is not in FA3 Modular production allowlist")

def validate_request(req: MaxServeRequest, allowlist: dict[str, Any]) -> None:
    model = allowed_model(allowlist, req.model)
    if model.get("immutable_revision_required") is not True:
        raise PolicyDenied("allowlisted model must require immutable revision")
    if model.get("trust_remote_code") is not False:
        raise PolicyDenied("production allowlist cannot require remote code")
    if not req.model_revision or not re.fullmatch(r"[0-9a-f]{40}", req.model_revision):
        raise PolicyDenied("production MAX execution requires an immutable Hugging Face revision pin")
    if req.model_revision != model.get("reference_revision"):
        raise PolicyDenied("MAX production smoke model revision is not the canonical allowlisted revision")
    if req.evidence_channel not in {"stable", "nightly"}:
        raise PolicyDenied("evidence_channel must be stable or nightly")
    if req.host not in {"127.0.0.1", "localhost"}:
        raise PolicyDenied("current-host MAX evidence must bind loopback only")
    if not (1024 <= req.port <= 65535):
        raise PolicyDenied("invalid server port")
    if not (64 <= req.max_length <= 4096):
        raise PolicyDenied("max_length outside bounded evidence envelope")
    if not (1 <= req.max_new_tokens <= 64):
        raise PolicyDenied("max_new_tokens outside bounded evidence envelope")
    if req.devices in {"gpu", "gpu:all"}:
        raise PolicyDenied("ambiguous/broad GPU placement forbidden; use explicit gpu:N from HRB lease")
    if req.devices != "cpu" and not re.fullmatch(r"gpu:\d+", req.devices):
        raise PolicyDenied("devices must be cpu or explicit gpu:N")
    if req.devices.startswith("gpu:"):
        if not req.hrb_lease_path:
            raise PolicyDenied("GPU MAX execution requires a canonical HRB lease")
        if req.device_memory_utilization is None or not (0.0 < req.device_memory_utilization <= 0.95):
            raise PolicyDenied("GPU MAX execution requires a bounded lease-derived memory utilization guard")
    elif req.device_memory_utilization is not None:
        raise PolicyDenied("CPU MAX execution cannot claim a GPU memory guard")

def build_max_serve_command(req: MaxServeRequest) -> list[str]:
    cmd = [
        "max", "serve", "--model", req.model,
        "--huggingface-model-revision", req.model_revision,
        "--devices", req.devices,
        "--host", req.host,
        "--port", str(req.port),
        "--max-length", str(req.max_length),
        "--no-trust-remote-code",
    ]
    if req.device_memory_utilization is not None:
        cmd += ["--device-memory-utilization", f"{req.device_memory_utilization:.6f}"]
    return cmd

def validate_hrb_lease(lease: dict[str, Any], req: MaxServeRequest) -> None:
    if req.devices == "cpu":
        return
    if lease.get("schema") != HRB_LEASE_SCHEMA or lease.get("issuer") != HRB_PROFILE_ID:
        raise PolicyDenied("HRB lease schema/issuer mismatch")
    if lease.get("status") != "ACTIVE" or not str(lease.get("accelerator_uuid", "")).startswith("GPU-"):
        raise PolicyDenied("HRB accelerator lease is not ACTIVE/typed")
    ordinal = int(req.devices.split(":", 1)[1])
    if int((lease.get("placement") or {}).get("ordinal_at_issue", -1)) != ordinal:
        raise PolicyDenied("MAX explicit GPU ordinal does not match HRB lease placement")
    if int(lease.get("memory_max_bytes", 0)) <= 0:
        raise PolicyDenied("HRB lease has no positive accelerator memory budget")
    gpu_mem_enforcement = str((lease.get("enforcement") or {}).get("gpu_memory", ""))
    if "broker_reservation" not in gpu_mem_enforcement:
        raise PolicyDenied("HRB lease does not prove broker-side GPU memory reservation")

def version_channel(version_text: str) -> str:
    low = version_text.lower()
    return "nightly" if any(x in low for x in ("dev", "nightly", "alpha", "beta", "rc")) else "stable"

def compiled_artifact_identity(source_sha256: str, mojo_version: str, target: str, binary_sha256: str) -> str:
    raw = json.dumps({
        "source_sha256": source_sha256,
        "mojo_version": mojo_version,
        "target": target,
        "binary_sha256": binary_sha256,
    }, sort_keys=True).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()

def evidence_complete(e: dict[str, Any]) -> bool:
    return bool(
        e.get("status") == "PASS"
        and e.get("max", {}).get("status") == "PASS"
        and e.get("mojo", {}).get("status") == "PASS"
        and e.get("max", {}).get("provider_id") == MAX_PROVIDER_ID
        and e.get("mojo", {}).get("provider_id") == MOJO_PROVIDER_ID
        and e.get("max", {}).get("model_revision")
        and e.get("max", {}).get("model_artifact_sha256")
        and e.get("max", {}).get("response_sha256")
        and e.get("mojo", {}).get("source_sha256")
        and e.get("mojo", {}).get("binary_sha256")
        and e.get("mojo", {}).get("compiled_artifact_id")
    )

def run_executable_conformance(root: Path) -> dict[str, Any]:
    allow = load_allowlist(root)
    rev = DEFAULT_MODEL_REVISION
    good = MaxServeRequest(model_revision=rev, devices="cpu")
    cases: list[dict[str, Any]] = []

    def case(name: str, fn) -> None:
        try:
            fn()
            cases.append({"name": name, "status": "PASS"})
        except Exception as exc:
            cases.append({"name": name, "status": "FAIL", "detail": repr(exc)})

    def expect_denied(req: MaxServeRequest) -> None:
        try:
            validate_request(req, allow)
        except PolicyDenied:
            return
        raise AssertionError("request unexpectedly accepted")

    case("cpu_pinned_request_valid", lambda: validate_request(good, allow))
    case("floating_model_revision_rejected", lambda: expect_denied(MaxServeRequest(model_revision="", devices="cpu")))
    case("unknown_model_rejected", lambda: expect_denied(MaxServeRequest(model="attacker/model", model_revision=rev)))
    case("non_loopback_bind_rejected", lambda: expect_denied(MaxServeRequest(model_revision=rev, host="0.0.0.0")))
    case("gpu_without_hrb_rejected", lambda: expect_denied(MaxServeRequest(model_revision=rev, devices="gpu:0")))
    case("bare_gpu_rejected", lambda: expect_denied(MaxServeRequest(model_revision=rev, devices="gpu")))
    case("all_gpu_rejected", lambda: expect_denied(MaxServeRequest(model_revision=rev, devices="gpu:all")))
    case("bounded_tokens_required", lambda: expect_denied(MaxServeRequest(model_revision=rev, max_new_tokens=0)))
    case("stable_nightly_channel_separate", lambda: (_ for _ in ()).throw(AssertionError()) if version_channel("26.6.0.dev1") == version_channel("26.5.0") else None)
    cmd = build_max_serve_command(good)
    case("remote_code_disabled", lambda: (_ for _ in ()).throw(AssertionError()) if "--no-trust-remote-code" not in cmd else None)

    gpu_req = MaxServeRequest(
        model_revision=rev, devices="gpu:0", hrb_lease_path="/tmp/lease.json",
        device_memory_utilization=0.5,
    )
    lease = {
        "schema": HRB_LEASE_SCHEMA,
        "issuer": HRB_PROFILE_ID,
        "status": "ACTIVE",
        "accelerator_uuid": "GPU-test",
        "memory_max_bytes": 4096,
        "placement": {"ordinal_at_issue": 0},
        "enforcement": {"gpu_memory": "provider_guard+broker_reservation"},
    }
    case("typed_hrb_gpu_lease_valid", lambda: (validate_request(gpu_req, allow), validate_hrb_lease(lease, gpu_req)))
    bad = {**lease, "issuer": "OTHER"}

    def bad_lease() -> None:
        try:
            validate_hrb_lease(bad, gpu_req)
        except PolicyDenied:
            return
        raise AssertionError("bad lease accepted")

    case("bad_hrb_issuer_rejected", bad_lease)
    case("gpu_memory_guard_emitted", lambda: (_ for _ in ()).throw(AssertionError()) if "--device-memory-utilization" not in build_max_serve_command(gpu_req) else None)
    sample = {
        "status": "PASS",
        "max": {
            "status": "PASS", "provider_id": MAX_PROVIDER_ID, "model_revision": rev,
            "model_artifact_sha256": "a", "response_sha256": "b",
        },
        "mojo": {
            "status": "PASS", "provider_id": MOJO_PROVIDER_ID, "source_sha256": "c",
            "binary_sha256": "d", "compiled_artifact_id": "sha256:e",
        },
    }
    case("combined_evidence_contract_complete", lambda: (_ for _ in ()).throw(AssertionError()) if not evidence_complete(sample) else None)

    passed = sum(x["status"] == "PASS" for x in cases)
    return {
        "schema": "fa3.modular-runtime-conformance-report.v1",
        "runtime_id": RUNTIME_ID,
        "result": "PASS" if passed == len(cases) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "cases": cases,
    }
