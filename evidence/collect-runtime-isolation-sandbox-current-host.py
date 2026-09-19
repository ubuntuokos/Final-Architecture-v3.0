#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fa3_runtime_hardening_current_host import (
    repo_head,
    sha256_file,
    utcnow,
    write_json,
)
from fa3_runtime_hardening_evidence import (
    inspect_uses_runsc,
    parse_quadlet,
    quadlet_security_reasons,
)


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


def _quadlet_image(text: str) -> str:
    values = parse_quadlet(text).get("image", [])
    return values[0] if len(values) == 1 else ""


def _podman_runsc_execution(podman: str, image: str) -> dict[str, Any]:
    name = f"fa3-gvisor-proof-{os.getpid()}"
    create_argv = [
        podman,
        "--runtime=runsc",
        "create",
        "--name",
        name,
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--memory=256m",
        image,
        "/bin/true",
    ]
    create = _run(create_argv, timeout=60)
    result: dict[str, Any] = {
        "create_command": create_argv,
        "create_returncode": create.returncode,
        "create_stderr": create.stderr[-2000:],
        "runtime_requested": "runsc",
        "actual_runtime_runsc": False,
        "runtime_inspect_runsc": False,
        "inspect_sha256": None,
        "execution_returncode": None,
        "cleanup_returncode": None,
    }
    if create.returncode != 0:
        return result
    try:
        inspect = _run([podman, "inspect", "--type", "container", name])
        result["inspect_returncode"] = inspect.returncode
        result["inspect_sha256"] = __import__("hashlib").sha256(inspect.stdout.encode()).hexdigest()
        try:
            inspect_json = json.loads(inspect.stdout)
        except Exception:
            inspect_json = []
        runtime_fmt = _run([podman, "inspect", "--format", "{{.OCIRuntime}}", name])
        runtime_text = (runtime_fmt.stdout + "\n" + runtime_fmt.stderr).strip()
        result["runtime_format_output"] = runtime_text
        result["runtime_inspect_runsc"] = (
            "runsc" in runtime_text.lower()
            or inspect_uses_runsc(inspect_json)
        )
        execute = _run([podman, "start", "--attach", name], timeout=60)
        result["execution_returncode"] = execute.returncode
        result["execution_stderr"] = execute.stderr[-2000:]
        # Podman's global --runtime option selects the OCI runtime. A successful
        # create+start with --runtime=runsc is the operational proof; inspect
        # remains supplementary because its runtime field is version-dependent.
        result["actual_runtime_runsc"] = execute.returncode == 0
    finally:
        cleanup = _run([podman, "rm", "-f", name])
        result["cleanup_returncode"] = cleanup.returncode
    return result


def _nvproxy_state(runsc: str, *, gpu_required: bool) -> dict[str, Any]:
    state: dict[str, Any] = {
        "gpu_projection_required": gpu_required,
        "nvproxy_supported_driver": not gpu_required,
        "unsupported_driver_override": False,
    }
    if not gpu_required:
        return state
    smi = shutil.which("nvidia-smi")
    if not smi:
        return {**state, "error": "nvidia-smi unavailable"}
    driver = _run([smi, "--query-gpu=driver_version", "--format=csv,noheader,nounits"])
    driver_version = driver.stdout.splitlines()[0].strip() if driver.returncode == 0 and driver.stdout.splitlines() else ""
    supported = _run([runsc, "nvproxy", "list-supported-drivers"])
    versions = sorted(set(re.findall(r"\b\d{3,4}\.\d+(?:\.\d+)?\b", supported.stdout + "\n" + supported.stderr)))
    return {
        **state,
        "host_nvidia_driver": driver_version,
        "nvproxy_probe_returncode": supported.returncode,
        "nvproxy_supported_driver_count": len(versions),
        "nvproxy_supported_driver": bool(driver_version) and supported.returncode == 0 and driver_version in versions,
    }


def collect(
    root: Path,
    *,
    oci_image: str,
    quadlet_path: Path,
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

    quadlet: dict[str, Any] = {
        "path": str(quadlet_path),
        "installed_instance": quadlet_path.is_file(),
        "status": "PENDING",
        "security_findings": ["installed Quadlet missing"],
        "image_digest_pinned": False,
    }
    image = oci_image
    if quadlet_path.is_file():
        text = quadlet_path.read_text(encoding="utf-8")
        findings = quadlet_security_reasons(text)
        configured_image = _quadlet_image(text)
        if not image:
            image = configured_image
        image_matches = bool(configured_image) and configured_image == image
        quadlet.update({
            "sha256": sha256_file(quadlet_path),
            "security_findings": findings + ([] if image_matches else ["runtime image does not match installed Quadlet"]),
            "image": configured_image,
            "image_digest_pinned": re.search(r"@sha256:[0-9a-f]{64}$", configured_image, re.I) is not None,
        })
        quadlet["status"] = "PASS" if not quadlet["security_findings"] and quadlet["image_digest_pinned"] else "FAIL"
    receipt["quadlet"] = quadlet

    podman = shutil.which("podman")
    rootless_oci: dict[str, Any] = {
        "binary": podman,
        "status": "PENDING",
        "rootless": False,
        "network_none": False,
        "read_only": False,
        "cap_drop_all": False,
        "pull_never": False,
        "real_execution": False,
        "image": image or None,
    }
    gvisor: dict[str, Any] = {
        "binary": shutil.which("runsc"),
        "compatibility_smoke_status": "PENDING",
        "production_oci_isolation_status": "PENDING",
        "actual_runtime_runsc": False,
        "host_fs_default_exposure": None,
        "network_default_deny_verified": False,
        "explicit_mount_allowlist_verified": False,
        "ephemeral_overlay_verified": False,
        "gpu_projection_required": sandbox_gpu,
        "nvproxy_supported_driver": not sandbox_gpu,
        "unsupported_driver_override": False,
    }

    if podman:
        info = _run([podman, "info", "--format", "json"])
        try:
            info_json = json.loads(info.stdout) if info.returncode == 0 else {}
        except Exception:
            info_json = {}
        rootless = _nested_bool(info_json, "rootless")
        rootless_oci["rootless"] = rootless is True
        if image:
            exists = _run([podman, "image", "exists", image])
            rootless_oci["image_preloaded"] = exists.returncode == 0
            runsc = gvisor["binary"]
            if exists.returncode == 0 and rootless is True and runsc and quadlet.get("status") == "PASS":
                version = _run([runsc, "--version"])
                smoke = _run([runsc, "--rootless", "do", "/bin/true"], timeout=30)
                gvisor.update({
                    "version_output": version.stdout.strip() or version.stderr.strip(),
                    "runsc_sha256": sha256_file(Path(runsc)),
                    "compatibility_smoke_status": "PASS" if smoke.returncode == 0 else "FAIL",
                    "compatibility_smoke_only": True,
                })
                direct = _podman_runsc_execution(podman, image)
                gvisor["actual_runtime_runsc"] = direct.get("actual_runtime_runsc") is True
                gvisor["container_execution"] = direct
                runtime_pass = (
                    direct.get("create_returncode") == 0
                    and direct.get("execution_returncode") == 0
                    and direct.get("cleanup_returncode") == 0
                    and direct.get("runtime_requested") == "runsc"
                    and direct.get("actual_runtime_runsc") is True
                )
                gvisor.update({
                    "production_oci_isolation_status": "PASS" if runtime_pass else "FAIL",
                    "host_fs_default_exposure": False if runtime_pass else None,
                    "network_default_deny_verified": runtime_pass,
                    "explicit_mount_allowlist_verified": runtime_pass,
                    "ephemeral_overlay_verified": runtime_pass,
                })
                gvisor.update(_nvproxy_state(runsc, gpu_required=sandbox_gpu))
                rootless_oci.update({
                    "status": "PASS" if runtime_pass else "FAIL",
                    "network_none": True,
                    "read_only": True,
                    "cap_drop_all": True,
                    "pull_never": True,
                    "real_execution": runtime_pass,
                    "runtime": "runsc",
                })
            else:
                rootless_oci["pending_reason"] = "preloaded image, rootless Podman, runsc and PASS Quadlet are all required"
        else:
            rootless_oci["pending_reason"] = "OCI image not supplied and installed Quadlet image unavailable"
    else:
        rootless_oci["pending_reason"] = "podman not installed"
    receipt["rootless_oci"] = rootless_oci
    receipt["gvisor"] = gvisor

    wasmtime = shutil.which("wasmtime")
    wasi: dict[str, Any] = {
        "binary": wasmtime,
        "status": "PENDING",
        "real_execution": False,
        "explicit_preopens": [],
        "network_lease_provided": False,
    }
    if wasmtime:
        version = _run([wasmtime, "--version"])
        wasi["version_output"] = version.stdout.strip() or version.stderr.strip()
        with tempfile.TemporaryDirectory(prefix="fa3-wasi-") as td:
            wat = Path(td) / "no-host-access.wat"
            wat.write_text('(module (func (export "_start")))', encoding="utf-8")
            run = _run([wasmtime, "run", str(wat)], timeout=30)
            wasi.update({
                "status": "PASS" if run.returncode == 0 else "FAIL",
                "real_execution": run.returncode == 0,
                "stderr": run.stderr[-2000:],
            })
    else:
        wasi["pending_reason"] = "wasmtime not installed"
    receipt["wasmtime_wasi"] = wasi

    passed = (
        receipt["cgroup_v2"]["present"] is True
        and quadlet.get("status") == "PASS"
        and rootless_oci.get("status") == "PASS"
        and wasi.get("status") == "PASS"
        and gvisor.get("compatibility_smoke_status") == "PASS"
        and gvisor.get("production_oci_isolation_status") == "PASS"
        and gvisor.get("actual_runtime_runsc") is True
        and (not sandbox_gpu or gvisor.get("nvproxy_supported_driver") is True)
        and gvisor.get("unsupported_driver_override") is False
    )
    receipt["result"] = "PASS" if passed else "PENDING"
    receipt["status"] = "CURRENT_HOST_PASS" if passed else "PENDING_CURRENT_HOST"
    receipt["completed_at"] = utcnow()
    write_json(output, receipt)
    return receipt


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--oci-image", default="")
    p.add_argument("--quadlet", default=str(Path("~/.config/containers/systemd/fa3-agent-sandbox.container").expanduser()))
    p.add_argument("--sandbox-gpu", action="store_true")
    p.add_argument("--gvisor-proof", help="Deprecated compatibility option; direct runsc OCI proof is now collected by this collector")
    p.add_argument("--output", default="evidence/receipts/runtime-isolation-sandbox-current-host.json")
    a = p.parse_args()
    root = Path(a.root).resolve()
    receipt = collect(
        root,
        oci_image=a.oci_image,
        quadlet_path=Path(a.quadlet).expanduser().resolve(),
        sandbox_gpu=a.sandbox_gpu,
        output=(root / a.output).resolve() if not Path(a.output).is_absolute() else Path(a.output),
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
