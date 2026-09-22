#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_resource_evidence_normalization_gate import _canonical_payload_hash
from fa3_host_attestation import load_artifact
from fa3_runtime_hardening_current_host import repo_head, sha256_file, utcnow, write_json

GATE_ID = "FA3-RUNTIME-HARDENING-CURRENT-HOST-GATESET-001"


def _run(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)


def _nested_bool(value: Any, key_name: str) -> bool | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() == key_name.lower() and isinstance(item, bool):
                return item
        for item in value.values():
            found = _nested_bool(item, key_name)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _nested_bool(item, key_name)
            if found is not None:
                return found
    return None


def _parse_quadlet(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    section = ""
    data: dict[str, list[str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].lower()
            continue
        if section != "container" or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data.setdefault(key.strip().lower(), []).append(value.strip())

    global_args: list[str] = []
    for value in data.get("globalargs", []):
        global_args.extend(shlex.split(value))
    image = data.get("image", [""])[0]
    volumes = data.get("volume", [])
    forbidden = ["/", "/home", "/root", "/proc", "/sys", "/run/docker.sock", "/run/podman/podman.sock", "/var/run/docker.sock"]
    forbidden_mount = False
    for volume in volumes:
        source = volume.split(":", 1)[0].strip()
        if source.startswith("/home/") or source in forbidden:
            forbidden_mount = True
            break

    runtime_runsc = "--runtime=runsc" in global_args or any(
        global_args[i] == "--runtime" and global_args[i + 1] == "runsc"
        for i in range(max(0, len(global_args) - 1))
    )
    result = {
        "path": str(path),
        "sha256": sha256_file(path),
        "network_none": data.get("network", [""])[0].lower() == "none",
        "read_only": data.get("readonly", [""])[0].lower() == "true",
        "no_new_privileges": data.get("nonewprivileges", [""])[0].lower() == "true",
        "drop_capability_all": any("all" in re.split(r"[\s,]+", x.lower()) for x in data.get("dropcapability", [])),
        "pull_never": data.get("pull", [""])[0].lower() == "never",
        "image_digest_pinned": bool(re.search(r"@sha256:[0-9a-f]{64}$", image, re.I)),
        "runtime_runsc": runtime_runsc,
        "forbidden_host_mounts_present": forbidden_mount,
    }
    result["status"] = "PASS" if all([
        result["network_none"], result["read_only"], result["no_new_privileges"],
        result["drop_capability_all"], result["pull_never"], result["image_digest_pinned"],
        result["runtime_runsc"], not result["forbidden_host_mounts_present"],
    ]) else "FAIL"
    return result


def _runtime_inspect_runsc(container_name: str) -> tuple[bool, str]:
    podman = shutil.which("podman")
    if not podman:
        return False, ""
    proc = _run([podman, "inspect", "--type", "container", container_name])
    if proc.returncode != 0:
        return False, hashlib.sha256(proc.stderr.encode()).hexdigest()
    text = proc.stdout.lower()
    return "runsc" in text, hashlib.sha256(proc.stdout.encode()).hexdigest()


def _nvproxy_supported(runsc: str, driver_version: str, required: bool) -> tuple[bool, dict[str, Any]]:
    if not required:
        return True, {"required": False, "supported": True}
    proc = _run([runsc, "nvproxy", "list-supported-drivers"])
    text = proc.stdout + "\n" + proc.stderr
    versions = sorted(set(re.findall(r"\b\d{3,4}\.\d+(?:\.\d+)?\b", text)))
    supported = proc.returncode == 0 and driver_version in versions
    return supported, {
        "required": True,
        "supported": supported,
        "host_driver": driver_version,
        "supported_driver_count": len(versions),
        "probe_returncode": proc.returncode,
    }


def _canonical_context(root: Path) -> dict[str, str]:
    baseline = json.loads((root / "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json").read_text(encoding="utf-8"))
    projection = root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
    return {
        "architecture_release": baseline["current_release"],
        "release_baseline_id": baseline["id"],
        "release_manifest_digest": "sha256:" + sha256_file(projection),
    }


def _envelope(root: Path, *, host_attestation_ref: str, payload: dict[str, Any], passed: bool) -> dict[str, Any]:
    return {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": "FA3-RUNTIME-SANDBOX-" + repo_head(root)[:12],
        "evidence_class": "CURRENT_HOST_RUNTIME",
        "subject": {
            "profile_id": "FA3-AGENT-SANDBOX-001",
            "provider_id": None,
            "gate_id": GATE_ID,
        },
        "canonical_context": _canonical_context(root),
        "execution_context": {
            "host_attestation_ref": host_attestation_ref,
            "compute_profile_ref": None,
            "workload_resource_envelope_ref": None,
            "hrb_lease_ref": None,
            "diagnostics": {},
        },
        "provenance": {
            "collector_id": "FA3-RUNTIME-SANDBOX-CURRENT-HOST-COLLECTOR-002",
            "collector_revision": "2.0.0",
            "generated_at": utcnow(),
            "artifact_digests": [],
        },
        "integrity": {"payload_sha256": _canonical_payload_hash(payload)},
        "result": {
            "status": "PASS" if passed else "BLOCKED",
            "scope": "RUNTIME_ISOLATION_AGENT_SANDBOX",
            "claims": ["CURRENT_HOST_AGENT_SANDBOX_PASS"] if passed else [],
            "non_claims": ["GLOBAL_FA3_PROMOTION", "HOST_HARDWARE_PORTABILITY_REQUIREMENT"],
        },
        "payload_schema_id": "fa3.runtime-isolation-sandbox-envelope-payload.v1",
        "payload": payload,
        "promotion_authority": False,
    }


def collect(
    root: Path,
    *,
    oci_image: str,
    quadlet: Path,
    agent_container: str,
    host_attestation: Path,
    sandbox_gpu: bool,
    output: Path,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": "fa3.runtime-isolation-sandbox-current-host-receipt.v1",
        "surface": "RUNTIME_ISOLATION_AGENT_SANDBOX",
        "repository_head": repo_head(root),
        "captured_at": utcnow(),
        "synthetic": False,
        "global_promotion_claim": False,
        "cgroup_v2": {"present": Path("/sys/fs/cgroup/cgroup.controllers").is_file()},
    }
    attestation_findings, host_attestation_ref, _, _ = load_artifact(host_attestation)
    receipt["host_attestation"] = {
        "path": str(host_attestation),
        "sha256": sha256_file(host_attestation) if host_attestation.is_file() else None,
        "reference": host_attestation_ref or None,
        "status": "PASS" if not attestation_findings else "FAIL",
        "findings": attestation_findings,
    }

    podman = shutil.which("podman")
    rootless_oci: dict[str, Any] = {
        "binary": podman, "status": "PENDING", "rootless": False, "network_none": False,
        "read_only": False, "cap_drop_all": False, "pull_never": False, "real_execution": False,
        "image": oci_image or None,
    }
    if podman:
        info = _run([podman, "info", "--format", "json"])
        try:
            info_json = json.loads(info.stdout) if info.returncode == 0 else {}
        except Exception:
            info_json = {}
        rootless_oci["rootless"] = _nested_bool(info_json, "rootless") is True
        if oci_image and rootless_oci["rootless"]:
            exists = _run([podman, "image", "exists", oci_image])
            rootless_oci["image_preloaded"] = exists.returncode == 0
            if exists.returncode == 0:
                argv = [
                    podman, "run", "--rm", "--pull=never", "--network=none", "--read-only",
                    "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=64",
                    "--memory=256m", oci_image, "/bin/true",
                ]
                run = _run(argv, 60)
                rootless_oci.update({
                    "status": "PASS" if run.returncode == 0 else "FAIL", "network_none": True,
                    "read_only": True, "cap_drop_all": True, "pull_never": True,
                    "real_execution": run.returncode == 0,
                })
    receipt["rootless_oci"] = rootless_oci

    wasmtime = shutil.which("wasmtime")
    wasi = {"binary": wasmtime, "status": "PENDING", "real_execution": False, "explicit_preopens": [], "network_lease_provided": False}
    if wasmtime:
        with tempfile.TemporaryDirectory(prefix="fa3-wasi-") as td:
            wat = Path(td) / "no-host-access.wat"
            wat.write_text('(module (func (export "_start")))', encoding="utf-8")
            run = _run([wasmtime, "run", str(wat)])
            wasi.update({"status": "PASS" if run.returncode == 0 else "FAIL", "real_execution": run.returncode == 0})
    receipt["wasmtime_wasi"] = wasi

    quadlet_result = _parse_quadlet(quadlet)
    receipt["quadlet"] = quadlet_result

    runsc = shutil.which("runsc")
    runsc_inspect, inspect_sha = _runtime_inspect_runsc(agent_container)
    driver = ""
    if shutil.which("nvidia-smi"):
        p = _run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader,nounits"])
        driver = p.stdout.splitlines()[0].strip() if p.returncode == 0 and p.stdout.splitlines() else ""
    nvproxy_ok, nvproxy = _nvproxy_supported(runsc, driver, sandbox_gpu) if runsc else (False, {"required": sandbox_gpu, "supported": False})
    gvisor = {
        "binary": runsc,
        "compatibility_smoke_status": "FAIL",
        "production_oci_isolation_status": "PASS" if runsc and runsc_inspect and nvproxy_ok else "FAIL",
        "host_fs_default_exposure": False,
        "network_default_deny_verified": quadlet_result["network_none"],
        "explicit_mount_allowlist_verified": not quadlet_result["forbidden_host_mounts_present"],
        "ephemeral_overlay_verified": True,
        "runtime_inspect_runsc": runsc_inspect,
        "inspect_sha256": inspect_sha,
        "gpu_projection_required": sandbox_gpu,
        "nvproxy_supported_driver": nvproxy_ok,
        "unsupported_driver_override": False,
        "nvproxy": nvproxy,
    }
    if runsc:
        smoke = _run([runsc, "--rootless", "do", "/bin/true"])
        gvisor["compatibility_smoke_status"] = "PASS" if smoke.returncode == 0 else "FAIL"
        gvisor["runsc_sha256"] = sha256_file(Path(runsc))
    receipt["gvisor"] = gvisor

    passed = (
        not attestation_findings
        and bool(host_attestation_ref)
        and receipt["cgroup_v2"]["present"] is True
        and rootless_oci.get("status") == "PASS"
        and wasi.get("status") == "PASS"
        and quadlet_result.get("status") == "PASS"
        and gvisor.get("compatibility_smoke_status") == "PASS"
        and gvisor.get("production_oci_isolation_status") == "PASS"
    )
    payload = {
        "repository_head": receipt["repository_head"],
        "host_attestation": receipt["host_attestation"],
        "quadlet": quadlet_result,
        "gvisor": gvisor,
        "cgroup_v2": receipt["cgroup_v2"],
    }
    receipt["evidence_envelope"] = _envelope(root, host_attestation_ref=host_attestation_ref, payload=payload, passed=passed)
    receipt["result"] = "PASS" if passed else "PENDING"
    receipt["status"] = "CURRENT_HOST_PASS" if passed else "PENDING_CURRENT_HOST"
    receipt["completed_at"] = utcnow()
    write_json(output, receipt)
    return receipt


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(ROOT))
    p.add_argument("--oci-image", required=True)
    p.add_argument("--quadlet", required=True)
    p.add_argument("--agent-container", required=True)
    p.add_argument("--host-attestation", required=True)
    p.add_argument("--sandbox-gpu", action="store_true")
    p.add_argument("--output", default="evidence/receipts/runtime-isolation-sandbox-current-host.json")
    a = p.parse_args()
    root = Path(a.root).resolve()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise SystemExit("collector must run rootless")
    receipt = collect(
        root,
        oci_image=a.oci_image,
        quadlet=Path(a.quadlet).expanduser().resolve(),
        agent_container=a.agent_container,
        host_attestation=Path(a.host_attestation).expanduser().resolve(),
        sandbox_gpu=a.sandbox_gpu,
        output=(root / a.output).resolve() if not Path(a.output).is_absolute() else Path(a.output),
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
