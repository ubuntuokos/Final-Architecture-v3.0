#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
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


def _load_gvisor_proof(path: Path | None, root: Path, runsc_sha: str | None) -> dict[str, Any]:
    base = {
        "production_oci_isolation_status": "PENDING",
        "host_fs_default_exposure": None,
        "network_default_deny_verified": False,
        "explicit_mount_allowlist_verified": False,
        "ephemeral_overlay_verified": False,
        "proof_path": str(path) if path else None,
    }
    if not path or not path.is_file():
        return base
    try:
        proof = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {**base, "proof_error": repr(exc)}
    ok = (
        proof.get("schema") == "fa3.gvisor-oci-current-host-proof.v1"
        and proof.get("result") == "PASS"
        and proof.get("repository_head") == repo_head(root)
        and proof.get("synthetic") is False
        and proof.get("runsc_sha256") == runsc_sha
        and proof.get("host_fs_default_exposure") is False
        and proof.get("network_default_deny_verified") is True
        and proof.get("explicit_mount_allowlist_verified") is True
        and proof.get("ephemeral_overlay_verified") is True
        and proof.get("global_promotion_claim") is False
    )
    return {
        **base,
        "production_oci_isolation_status": "PASS" if ok else "FAIL",
        "host_fs_default_exposure": proof.get("host_fs_default_exposure"),
        "network_default_deny_verified": proof.get("network_default_deny_verified") is True,
        "explicit_mount_allowlist_verified": proof.get("explicit_mount_allowlist_verified") is True,
        "ephemeral_overlay_verified": proof.get("ephemeral_overlay_verified") is True,
        "proof_sha256": sha256_file(path),
    }


def collect(root: Path, *, oci_image: str, gvisor_proof: Path | None, output: Path) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": "fa3.runtime-isolation-sandbox-current-host-receipt.v1",
        "surface": "RUNTIME_ISOLATION_AGENT_SANDBOX",
        "repository_head": repo_head(root),
        "captured_at": utcnow(),
        "synthetic": False,
        "global_promotion_claim": False,
        "cgroup_v2": {"present": (Path("/sys/fs/cgroup/cgroup.controllers").is_file())},
    }

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
        "image": oci_image or None,
    }
    if podman:
        version = _run([podman, "--version"])
        rootless_oci["version_output"] = version.stdout.strip() or version.stderr.strip()
        info = _run([podman, "info", "--format", "json"])
        try:
            info_json = json.loads(info.stdout) if info.returncode == 0 else {}
        except Exception:
            info_json = {}
        rootless = _nested_bool(info_json, "rootless")
        rootless_oci["rootless"] = rootless is True
        if oci_image:
            exists = _run([podman, "image", "exists", oci_image])
            rootless_oci["image_preloaded"] = exists.returncode == 0
            if exists.returncode == 0 and rootless is True:
                argv = [
                    podman, "run", "--rm", "--pull=never", "--network=none", "--read-only",
                    "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=64",
                    "--memory=256m", oci_image, "/bin/true",
                ]
                run = _run(argv, timeout=60)
                rootless_oci.update({
                    "status": "PASS" if run.returncode == 0 else "FAIL",
                    "network_none": True,
                    "read_only": True,
                    "cap_drop_all": True,
                    "pull_never": True,
                    "real_execution": run.returncode == 0,
                    "command": argv,
                    "stderr": run.stderr[-2000:],
                })
        else:
            rootless_oci["pending_reason"] = "preloaded OCI image not supplied; network pull is forbidden"
    else:
        rootless_oci["pending_reason"] = "podman not installed"
    receipt["rootless_oci"] = rootless_oci

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

    runsc = shutil.which("runsc")
    gvisor: dict[str, Any] = {
        "binary": runsc,
        "compatibility_smoke_status": "PENDING",
        "production_oci_isolation_status": "PENDING",
        "host_fs_default_exposure": None,
        "network_default_deny_verified": False,
        "explicit_mount_allowlist_verified": False,
        "ephemeral_overlay_verified": False,
    }
    runsc_sha = None
    if runsc:
        runsc_path = Path(runsc)
        runsc_sha = sha256_file(runsc_path)
        ver = _run([runsc, "--version"])
        smoke = _run([runsc, "--rootless", "do", "/bin/true"], timeout=30)
        gvisor.update({
            "version_output": ver.stdout.strip() or ver.stderr.strip(),
            "runsc_sha256": runsc_sha,
            "compatibility_smoke_status": "PASS" if smoke.returncode == 0 else "FAIL",
            "compatibility_smoke_only": True,
            "compatibility_smoke_stderr": smoke.stderr[-2000:],
        })
    else:
        gvisor["pending_reason"] = "runsc not installed"
    gvisor.update(_load_gvisor_proof(gvisor_proof, root, runsc_sha))
    receipt["gvisor"] = gvisor

    passed = (
        receipt["cgroup_v2"]["present"] is True
        and rootless_oci.get("status") == "PASS"
        and wasi.get("status") == "PASS"
        and gvisor.get("compatibility_smoke_status") == "PASS"
        and gvisor.get("production_oci_isolation_status") == "PASS"
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
    p.add_argument("--gvisor-proof")
    p.add_argument("--output", default="evidence/receipts/runtime-isolation-sandbox-current-host.json")
    a = p.parse_args()
    root = Path(a.root).resolve()
    receipt = collect(
        root,
        oci_image=a.oci_image,
        gvisor_proof=Path(a.gvisor_proof).resolve() if a.gvisor_proof else None,
        output=(root / a.output).resolve() if not Path(a.output).is_absolute() else Path(a.output),
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
