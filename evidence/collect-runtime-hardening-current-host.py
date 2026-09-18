#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_runtime_hardening_current_host import (
    CAPABILITY_COUNT,
    CURRENT_HOST_CONFORMANCE_ID,
    CURRENT_HOST_GATE_RECORD_ID,
    RUNTIME_HARDENING_CLAIM,
    frame_trace_findings,
    normalize_bdf,
    payload_sha256,
    pcie_copy_budget_findings,
    quadlet_security_findings,
    resource_admission_binding,
    runtime_inspect_has_runsc,
    sha256_file,
)

COLLECTOR_ID = "FA3-RUNTIME-HARDENING-CURRENT-HOST-COLLECTOR-001"
COLLECTOR_VERSION = "1.0.0"
DEFAULT_RESOURCE_RECEIPT = ROOT / "evidence/receipts/resource-admission-current-host.json"
DEFAULT_RECEIPT = ROOT / "evidence/receipts/runtime-hardening-current-host.json"
DEFAULT_QUADLET = Path("~/.config/containers/systemd/fa3-agent-sandbox.container").expanduser()

# Approximate one-direction effective payload throughput per lane, KB/s.
# This is derived from PCIe generation encoding/link rates, never from a GPU SKU.
PCIE_PAYLOAD_KB_S_PER_LANE = {
    1: 250_000.0,
    2: 500_000.0,
    3: 984_615.0,
    4: 1_969_230.0,
    5: 3_938_460.0,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def command_version(argv: list[str]) -> dict[str, Any]:
    proc = run(argv)
    return {
        "argv": argv,
        "returncode": proc.returncode,
        "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(proc.stderr.encode()).hexdigest(),
        "first_line": (proc.stdout or proc.stderr).splitlines()[0] if (proc.stdout or proc.stderr).splitlines() else "",
    }


def release_context(root: Path) -> dict[str, str]:
    baseline = loadj(root / "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json")
    release_projection = root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
    return {
        "architecture_release": str(baseline["current_release"]),
        "release_baseline_id": str(baseline["id"]),
        "release_manifest_digest": "sha256:" + sha256_file(release_projection),
    }


def live_nvidia_gpu(gpu_uuid: str, pci_bdf: str) -> dict[str, Any]:
    if shutil.which("nvidia-smi") is None:
        raise RuntimeError("nvidia-smi unavailable")
    proc = run([
        "nvidia-smi",
        "--query-gpu=index,uuid,pci.bus_id,name,driver_version",
        "--format=csv,noheader,nounits",
    ])
    if proc.returncode != 0:
        raise RuntimeError("nvidia-smi query failed: " + proc.stderr[-1000:])
    matches: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        parts = [part.strip() for part in line.split(",", 4)]
        if len(parts) != 5:
            continue
        row = {
            "index_observed": int(parts[0]),
            "uuid": parts[1],
            "pci_bdf": normalize_bdf(parts[2]),
            "name": parts[3],
            "driver_version": parts[4],
        }
        if row["uuid"] == gpu_uuid and row["pci_bdf"] == normalize_bdf(pci_bdf):
            matches.append(row)
    if len(matches) != 1:
        raise RuntimeError("HRB-assigned GPU UUID/BDF does not resolve to exactly one live NVIDIA GPU")
    return matches[0]


def inspect_agent_container(name: str) -> tuple[dict[str, Any], str]:
    if shutil.which("podman") is None:
        raise RuntimeError("podman unavailable")
    proc = run(["podman", "inspect", "--type", "container", name])
    if proc.returncode != 0:
        raise RuntimeError("podman inspect failed: " + proc.stderr[-1500:])
    parsed = json.loads(proc.stdout)
    if not isinstance(parsed, list) or len(parsed) != 1:
        raise RuntimeError("podman inspect did not return exactly one container")
    digest = hashlib.sha256(proc.stdout.encode()).hexdigest()
    return parsed[0], digest


def runsc_state(driver_version: str, *, gpu_projection_required: bool) -> dict[str, Any]:
    runsc = shutil.which("runsc")
    if not runsc:
        return {
            "status": "FAIL",
            "runsc_available": False,
            "runtime_inspect_runsc": False,
            "gpu_projection_required": gpu_projection_required,
            "nvproxy_supported_driver": False,
            "unsupported_driver_override": False,
            "error": "runsc unavailable",
        }
    version = command_version([runsc, "--version"])
    supported = run([runsc, "nvproxy", "list-supported-drivers"])
    supported_text = supported.stdout + "\n" + supported.stderr
    versions = sorted(set(re.findall(r"\b\d{3,4}\.\d+(?:\.\d+)?\b", supported_text)))
    supported_driver = driver_version in versions if gpu_projection_required else True
    return {
        "status": "PASS" if version["returncode"] == 0 and (not gpu_projection_required or (supported.returncode == 0 and supported_driver)) else "FAIL",
        "runsc_available": True,
        "runsc_version": version["first_line"],
        "runsc_version_stdout_sha256": version["stdout_sha256"],
        "gpu_projection_required": gpu_projection_required,
        "nvproxy_probe_returncode": supported.returncode,
        "nvproxy_supported_driver": supported_driver,
        "nvproxy_supported_driver_count": len(versions),
        "host_nvidia_driver": driver_version,
        "unsupported_driver_override": False,
    }


def _nvml_counter_constant(pynvml: Any, primary: str, legacy: str) -> Any:
    if hasattr(pynvml, primary):
        return getattr(pynvml, primary)
    if hasattr(pynvml, legacy):
        return getattr(pynvml, legacy)
    raise RuntimeError(f"pynvml lacks {primary}/{legacy}")


def collect_pcie_while_running(
    command: list[str],
    *,
    gpu_uuid: str,
    pci_bdf: str,
    interval: float,
    budget_ratio: float,
    cwd: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        import pynvml
    except Exception as exc:
        raise RuntimeError(f"pynvml unavailable: {exc!r}") from exc

    pynvml.nvmlInit()
    process: subprocess.Popen[str] | None = None
    try:
        handle = None
        for idx in range(pynvml.nvmlDeviceGetCount()):
            candidate = pynvml.nvmlDeviceGetHandleByIndex(idx)
            if str(pynvml.nvmlDeviceGetUUID(candidate)) == gpu_uuid:
                handle = candidate
                break
        if handle is None:
            raise RuntimeError("NVML could not resolve HRB-assigned GPU UUID")

        tx_kind = _nvml_counter_constant(pynvml, "NVML_PCIE_UTIL_TX_BYTES", "NVML_PCIE_UTIL_TX_THROUGHPUT")
        rx_kind = _nvml_counter_constant(pynvml, "NVML_PCIE_UTIL_RX_BYTES", "NVML_PCIE_UTIL_RX_THROUGHPUT")

        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        samples: list[dict[str, Any]] = []
        started = time.monotonic()
        while process.poll() is None:
            tx = int(pynvml.nvmlDeviceGetPcieThroughput(handle, tx_kind))
            rx = int(pynvml.nvmlDeviceGetPcieThroughput(handle, rx_kind))
            generation = int(pynvml.nvmlDeviceGetCurrPcieLinkGeneration(handle))
            width = int(pynvml.nvmlDeviceGetCurrPcieLinkWidth(handle))
            samples.append({
                "t_seconds": round(time.monotonic() - started, 6),
                "tx_kb_s": tx,
                "rx_kb_s": rx,
                "generation": generation,
                "width": width,
            })
            time.sleep(interval)

        stdout, stderr = process.communicate()
        elapsed = time.monotonic() - started
        workload = {
            "argv_sha256": hashlib.sha256("\0".join(command).encode()).hexdigest(),
            "returncode": process.returncode,
            "duration_seconds": round(elapsed, 6),
            "stdout_sha256": hashlib.sha256((stdout or "").encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256((stderr or "").encode()).hexdigest(),
        }
        if not samples:
            return {
                "status": "FAIL",
                "semantics": "SUPPORTING_COPY_BUDGET_NOT_ZERO_COPY_PROOF",
                "gpu_uuid": gpu_uuid,
                "pci_bdf": pci_bdf,
                "sampling_interval_seconds": interval,
                "sample_count": 0,
                "budget_ratio": budget_ratio,
                "capacity_source": "LIVE_NEGOTIATED_PCIE_LINK_GEN_WIDTH",
                "error": "workload completed before first NVML sample",
            }, workload

        best_capacity = 0.0
        observed_gen_width: set[tuple[int, int]] = set()
        for sample in samples:
            gen = sample["generation"]
            width = sample["width"]
            observed_gen_width.add((gen, width))
            per_lane = PCIE_PAYLOAD_KB_S_PER_LANE.get(gen)
            if per_lane:
                best_capacity = max(best_capacity, per_lane * width)

        if best_capacity <= 0:
            budget = 0.0
            status = "FAIL"
            capacity_error = "unsupported live PCIe generation"
        else:
            budget = best_capacity * budget_ratio
            status = "PASS"
            capacity_error = None

        max_tx = max(s["tx_kb_s"] for s in samples)
        max_rx = max(s["rx_kb_s"] for s in samples)
        if max_tx >= budget or max_rx >= budget or len(samples) < 10 or interval > 0.025:
            status = "FAIL"

        telemetry = {
            "status": status,
            "semantics": "SUPPORTING_COPY_BUDGET_NOT_ZERO_COPY_PROOF",
            "gpu_uuid": gpu_uuid,
            "pci_bdf": normalize_bdf(pci_bdf),
            "sampling_interval_seconds": interval,
            "sample_count": len(samples),
            "max_tx_kb_s": max_tx,
            "max_rx_kb_s": max_rx,
            "budget_kb_s": round(budget, 3),
            "budget_ratio": budget_ratio,
            "capacity_source": "LIVE_NEGOTIATED_PCIE_LINK_GEN_WIDTH",
            "capacity_model": "PCIE_STANDARD_EFFECTIVE_PAYLOAD_APPROXIMATION_V1",
            "observed_link_gen_width": [{"generation": g, "width": w} for g, w in sorted(observed_gen_width)],
            "raw_samples_sha256": hashlib.sha256(json.dumps(samples, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        }
        if capacity_error:
            telemetry["error"] = capacity_error
        return telemetry, workload
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        pynvml.nvmlShutdown()


def collect(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    resource_path = Path(args.resource_admission_receipt).expanduser().resolve()
    receipt_path = Path(args.receipt).expanduser().resolve()
    quadlet_path = Path(args.quadlet).expanduser().resolve()
    frame_trace_path = Path(args.frame_trace).expanduser().resolve()

    errors: list[str] = []
    resource = loadj(resource_path)
    binding, binding_errors = resource_admission_binding(resource)
    errors.extend(binding_errors)
    if binding is None:
        binding = {
            "gpu_uuid": "",
            "pci_bdf": "",
            "host_attestation_ref": "",
            "compute_profile_ref": "",
            "workload_resource_envelope_ref": "",
            "hrb_lease_ref": "",
        }

    quadlet_text = quadlet_path.read_text(encoding="utf-8")
    quadlet_findings = quadlet_security_findings(quadlet_text)
    if quadlet_findings:
        errors.extend(quadlet_findings)

    live_gpu = live_nvidia_gpu(binding["gpu_uuid"], binding["pci_bdf"]) if not binding_errors else {}
    inspect, inspect_sha = inspect_agent_container(args.agent_container)
    inspect_runsc = runtime_inspect_has_runsc(inspect)
    if not inspect_runsc:
        errors.append("RUNNING_CONTAINER_NOT_USING_RUNSC")

    gpu_projection_required = bool(args.sandbox_gpu)
    gvisor = runsc_state(str(live_gpu.get("driver_version", "")), gpu_projection_required=gpu_projection_required)
    gvisor["runtime_inspect_runsc"] = inspect_runsc
    if gvisor.get("status") != "PASS":
        errors.append("GVISOR_RUNTIME_OR_NVPROXY_CONFORMANCE_FAILED")

    command = list(args.workload)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise RuntimeError("workload command is required after --")
    pcie, workload = collect_pcie_while_running(
        command,
        gpu_uuid=binding["gpu_uuid"],
        pci_bdf=binding["pci_bdf"],
        interval=args.sampling_interval,
        budget_ratio=args.pcie_budget_ratio,
        cwd=root,
    )
    if workload["returncode"] != 0:
        errors.append("WORKLOAD_COMMAND_FAILED")

    if not frame_trace_path.is_file():
        errors.append("FRAME_COPY_TRACE_MISSING")
        frame_trace: dict[str, Any] = {}
    else:
        frame_trace = loadj(frame_trace_path)
        errors.extend(frame_trace_findings(frame_trace, gpu_uuid=binding["gpu_uuid"], pci_bdf=binding["pci_bdf"]))

    errors.extend(pcie_copy_budget_findings(pcie, gpu_uuid=binding["gpu_uuid"], pci_bdf=binding["pci_bdf"]))

    checks = {
        "CRIT-020-QUADLET-GVISOR-SANDBOX": "PASS" if not quadlet_findings and inspect_runsc and gvisor.get("status") == "PASS" else "FAIL",
        "CRIT-021-AGENT-BOUNDARY": "PASS" if not quadlet_findings and inspect_runsc else "FAIL",
        "CRIT-022A-PCIE-COPY-BUDGET": "PASS" if not pcie_copy_budget_findings(pcie, gpu_uuid=binding["gpu_uuid"], pci_bdf=binding["pci_bdf"]) else "FAIL",
        "CRIT-022B-GPU-FRAME-ZERO-HOST-ROUND-TRIP": "PASS" if frame_trace and not frame_trace_findings(frame_trace, gpu_uuid=binding["gpu_uuid"], pci_bdf=binding["pci_bdf"]) else "FAIL",
    }
    passed = not errors and all(value == "PASS" for value in checks.values())

    payload = {
        "schema": "fa3.runtime-hardening-current-host.payload.v1",
        "real_current_host_execution": True,
        "conformance_id": CURRENT_HOST_CONFORMANCE_ID,
        "resource_binding": {
            "gpu_uuid": binding["gpu_uuid"],
            "pci_bdf": binding["pci_bdf"],
            "resource_admission_receipt_sha256": sha256_file(resource_path),
            "resource_admission_evidence_id": resource.get("evidence_id"),
        },
        "quadlet_sandbox": {
            "status": "PASS" if not quadlet_findings else "FAIL",
            "path": str(quadlet_path),
            "sha256": sha256_file(quadlet_path),
            "findings": quadlet_findings,
            "network_default": "DENY",
            "rootfs": "READ_ONLY",
            "pull_policy": "NEVER",
            "capability_policy": "DROP_ALL",
            "image_digest_pin_required": True,
        },
        "gvisor_runtime": gvisor,
        "agent_container": {
            "name": args.agent_container,
            "inspect_sha256": inspect_sha,
            "runtime_inspect_runsc": inspect_runsc,
            "sandbox_gpu_projection_required": gpu_projection_required,
        },
        "workload": workload,
        "pcie_copy_budget": pcie,
        "frame_copy_trace": frame_trace,
        "checks": checks,
        "errors": sorted(set(errors)),
        "invariants": {
            "capability_count": CAPABILITY_COUNT,
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "global_promotion_claim": False,
            "pcie_copy_budget_is_zero_copy_proof": False,
            "zero_host_round_trip_requires_frame_copy_trace": True,
        },
    }

    artifact_digests = [
        {"kind": "resource_admission_receipt", "sha256": sha256_file(resource_path)},
        {"kind": "installed_quadlet", "sha256": sha256_file(quadlet_path)},
        {"kind": "agent_container_inspect", "sha256": inspect_sha},
    ]
    if frame_trace_path.is_file():
        artifact_digests.append({"kind": "frame_copy_trace", "sha256": sha256_file(frame_trace_path)})

    claims = []
    if passed:
        claims = [
            RUNTIME_HARDENING_CLAIM,
            "CURRENT_HOST_AGENT_SANDBOX_PASS",
            "CURRENT_HOST_PCIE_COPY_BUDGET_PASS",
            "CURRENT_HOST_GPU_ZERO_HOST_ROUND_TRIP_PASS",
        ]

    envelope = {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": f"FA3-RUNTIME-HARDENING-CURRENT-HOST-{int(time.time())}",
        "evidence_class": "CURRENT_HOST_RUNTIME",
        "subject": {
            "profile_id": "FA3-MEDIA-GPU-ZEROCOPY-001",
            "provider_id": "FA3-PROVIDER-PYNVVIDEOCODEC-001",
            "gate_id": CURRENT_HOST_GATE_RECORD_ID,
        },
        "canonical_context": release_context(root),
        "execution_context": {
            "host_attestation_ref": binding["host_attestation_ref"],
            "compute_profile_ref": binding["compute_profile_ref"],
            "workload_resource_envelope_ref": binding["workload_resource_envelope_ref"],
            "hrb_lease_ref": binding["hrb_lease_ref"],
            "diagnostics": {"agent_container": args.agent_container},
        },
        "provenance": {
            "collector_id": COLLECTOR_ID,
            "collector_revision": COLLECTOR_VERSION,
            "generated_at": now(),
            "artifact_digests": artifact_digests,
        },
        "integrity": {"payload_sha256": payload_sha256(payload)},
        "result": {
            "status": "PASS" if passed else "BLOCKED",
            "scope": "COMPONENT_CURRENT_HOST_RUNTIME_HARDENING",
            "claims": claims,
            "non_claims": [
                "GLOBAL_FA3_PROMOTION",
                "FULL_PIPELINE_TRUE_ZERO_COPY",
                "HOST_HARDWARE_PORTABILITY_REQUIREMENT",
            ],
        },
        "payload_schema_id": "fa3.runtime-hardening-current-host.payload.v1",
        "payload": payload,
        "promotion_authority": False,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return envelope


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect FA3 runtime-hardening current-host evidence")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--resource-admission-receipt", default=str(DEFAULT_RESOURCE_RECEIPT))
    parser.add_argument("--quadlet", default=str(DEFAULT_QUADLET))
    parser.add_argument("--agent-container", required=True)
    parser.add_argument("--sandbox-gpu", action="store_true", help="Require nvproxy support for the running gVisor sandbox")
    parser.add_argument("--frame-trace", required=True, help="Normalized fa3.cuda-copy-trace.v1 generated by CUPTI/Nsight/CUDA activity tracing")
    parser.add_argument("--receipt", default=str(DEFAULT_RECEIPT))
    parser.add_argument("--sampling-interval", type=float, default=0.02)
    parser.add_argument("--pcie-budget-ratio", type=float, default=0.05)
    parser.add_argument("workload", nargs=argparse.REMAINDER, help="Workload command after --")
    args = parser.parse_args()

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise SystemExit("FA3 current-host runtime-hardening collection must run rootless")
    if not (0 < args.sampling_interval <= 0.025):
        raise SystemExit("--sampling-interval must be >0 and <=0.025 seconds")
    if not (0 < args.pcie_budget_ratio <= 0.05):
        raise SystemExit("--pcie-budget-ratio must be >0 and <=0.05")

    try:
        envelope = collect(args)
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)}, indent=2), file=sys.stderr)
        return 3

    print(json.dumps({
        "evidence_id": envelope["evidence_id"],
        "status": envelope["result"]["status"],
        "claims": envelope["result"]["claims"],
        "non_claims": envelope["result"]["non_claims"],
        "receipt": str(Path(args.receipt).expanduser().resolve()),
    }, indent=2))
    return 0 if envelope["result"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
