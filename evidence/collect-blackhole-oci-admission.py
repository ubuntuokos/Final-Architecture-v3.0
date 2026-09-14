#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

REFERENCE_IMAGE = "localhost/fa3-blackhole-api:reference"
TEST_AUDIT_KEY = "a5" * 32


def _run(command: list[str], cwd: Path, timeout: float = 300.0, check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed rc={proc.returncode}: {' '.join(command)}\n{proc.stderr[-2000:]}")
    return proc


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _rootless(root: Path) -> bool:
    proc = _run(["podman", "info", "--format", "{{.Host.Security.Rootless}}"], root, timeout=30)
    return proc.returncode == 0 and proc.stdout.strip().lower() == "true"


def _inspect_label(root: Path, image: str, label: str) -> str:
    proc = _run(["podman", "image", "inspect", image, "--format", f"{{{{ index .Labels \"{label}\" }}}}"], root, timeout=30)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _runtime_uid(root: Path, image: str) -> int | None:
    proc = _run(["podman", "run", "--rm", image, "id", "-u"], root, timeout=60)
    try:
        return int(proc.stdout.strip()) if proc.returncode == 0 else None
    except ValueError:
        return None


def _container_ffmpeg_sha(root: Path, image: str) -> str | None:
    proc = _run(["podman", "run", "--rm", image, "sh", "-lc", "sha256sum \"$(command -v ffmpeg)\" | awk '{print $1}'"], root, timeout=60)
    value = proc.stdout.strip().splitlines()[-1] if proc.returncode == 0 and proc.stdout.strip() else ""
    return value if len(value) == 64 else None


def _audit_self_test(root: Path, image: str) -> str:
    code = (
        "from pathlib import Path; "
        "from fa3_audit_chain import append_event,read_jsonl,verify_records; "
        "p=Path('/tmp/fa3-audit-test.jsonl'); "
        f"k='{TEST_AUDIT_KEY}'; "
        "append_event(p,{'event':'one'},k); append_event(p,{'event':'two'},k); "
        "r=verify_records(read_jsonl(p),k); "
        "assert r['result']=='PASS' and r['records']==2; print('PASS')"
    )
    proc = _run(
        [
            "podman", "run", "--rm", "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
            "--cap-drop=all", "--security-opt=no-new-privileges", "--entrypoint", "python", image, "-c", code,
        ],
        root,
        timeout=60,
    )
    return "PASS" if proc.returncode == 0 and proc.stdout.strip().endswith("PASS") else "FAIL"


def _api_health(root: Path, image: str) -> str:
    port = _free_port()
    run = _run(
        [
            "podman", "run", "-d", "--read-only", "--cap-drop=all", "--security-opt=no-new-privileges",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--tmpfs", "/var/lib/fa3/audit:rw,noexec,nosuid,size=16m",
            "-e", f"FA3_AUDIT_HMAC_KEY_HEX={TEST_AUDIT_KEY}",
            "-p", f"127.0.0.1:{port}:8080", image,
        ],
        root,
        timeout=60,
    )
    if run.returncode != 0 or not run.stdout.strip():
        return "FAIL"
    container_id = run.stdout.strip().splitlines()[-1]
    try:
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1.0) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    if response.status == 200 and payload.get("status") == "PASS" and payload.get("zero_copy_claimed") is False:
                        return "PASS"
            except Exception:
                time.sleep(0.5)
        return "FAIL"
    finally:
        _run(["podman", "rm", "-f", container_id], root, timeout=30)


def _pip_freeze(root: Path, image: str) -> list[str]:
    proc = _run(["podman", "run", "--rm", "--entrypoint", "python", image, "-m", "pip", "freeze"], root, timeout=60)
    if proc.returncode != 0:
        return []
    return sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())


def _image_id(root: Path, image: str) -> str | None:
    proc = _run(["podman", "image", "inspect", image, "--format", "{{.Id}}"], root, timeout=30)
    value = proc.stdout.strip()
    return value or None


def collect_reference(root: Path) -> dict[str, Any]:
    findings: list[str] = []
    if shutil.which("podman") is None:
        findings.append("PODMAN_NOT_FOUND")
        return {"schema": "fa3.blackhole-oci-admission.v1", "mode": "REFERENCE_OCI", "result": "FAIL", "findings": findings, "production_claim": False, "zero_copy_claimed": False}

    rootless = _rootless(root)
    if not rootless:
        findings.append("PODMAN_NOT_ROOTLESS")
    build = _run(
        ["podman", "build", "--pull=missing", "-f", "deployment/containers/blackhole-api.Containerfile", "-t", REFERENCE_IMAGE, "."],
        root,
        timeout=1200,
    )
    if build.returncode != 0:
        findings.append("OCI_BUILD_FAILED")
        return {
            "schema": "fa3.blackhole-oci-admission.v1", "mode": "REFERENCE_OCI", "result": "FAIL",
            "rootless": rootless, "findings": findings, "build_stderr": build.stderr[-4000:],
            "production_claim": False, "zero_copy_claimed": False,
        }

    runtime_uid = _runtime_uid(root, REFERENCE_IMAGE)
    if runtime_uid != 10002:
        findings.append("RUNTIME_UID_NOT_10002")
    runtime_class = _inspect_label(root, REFERENCE_IMAGE, "io.fa3.runtime.class")
    zero_copy_label = _inspect_label(root, REFERENCE_IMAGE, "io.fa3.zero-copy-claimed")
    if runtime_class != "REFERENCE_OCI_NOT_PRODUCTION":
        findings.append("REFERENCE_RUNTIME_CLASS_INVALID")
    if zero_copy_label.lower() != "false":
        findings.append("REFERENCE_ZERO_COPY_CLAIM_INVALID")
    audit_chain = _audit_self_test(root, REFERENCE_IMAGE)
    api_health = _api_health(root, REFERENCE_IMAGE)
    if audit_chain != "PASS":
        findings.append("AUDIT_CHAIN_SELF_TEST_FAILED")
    if api_health != "PASS":
        findings.append("API_HEALTH_FAILED")

    return {
        "schema": "fa3.blackhole-oci-admission.v1",
        "mode": "REFERENCE_OCI",
        "result": "PASS" if not findings else "FAIL",
        "rootless": rootless,
        "runtime_uid": runtime_uid,
        "runtime_class": runtime_class,
        "image_id": _image_id(root, REFERENCE_IMAGE),
        "ffmpeg_binary_sha256": _container_ffmpeg_sha(root, REFERENCE_IMAGE),
        "api_health": api_health,
        "audit_chain": audit_chain,
        "resolved_python_packages": _pip_freeze(root, REFERENCE_IMAGE),
        "production_claim": False,
        "zero_copy_claimed": False,
        "findings": findings,
    }


def collect_current_host(root: Path, production_image: str) -> dict[str, Any]:
    findings: list[str] = []
    if not production_image or "@sha256:" not in production_image:
        findings.append("IMMUTABLE_PRODUCTION_IMAGE_DIGEST_REQUIRED")
        return {
            "schema": "fa3.blackhole-oci-admission.v1", "mode": "CURRENT_HOST_PRODUCTION", "result": "FAIL",
            "production_image_immutable": False, "zero_copy_claimed": False, "findings": findings,
        }
    if shutil.which("podman") is None:
        findings.append("PODMAN_NOT_FOUND")
        return {"schema": "fa3.blackhole-oci-admission.v1", "mode": "CURRENT_HOST_PRODUCTION", "result": "FAIL", "production_image_immutable": True, "zero_copy_claimed": False, "findings": findings}

    rootless = _rootless(root)
    if not rootless:
        findings.append("PODMAN_NOT_ROOTLESS")
    inspect = _run(["podman", "image", "inspect", production_image], root, timeout=60)
    if inspect.returncode != 0:
        pull = _run(["podman", "pull", production_image], root, timeout=1200)
        if pull.returncode != 0:
            findings.append("PRODUCTION_IMAGE_UNAVAILABLE")
            return {
                "schema": "fa3.blackhole-oci-admission.v1", "mode": "CURRENT_HOST_PRODUCTION", "result": "FAIL",
                "rootless": rootless, "production_image_immutable": True, "zero_copy_claimed": False,
                "findings": findings, "pull_stderr": pull.stderr[-4000:],
            }

    runtime_uid = _runtime_uid(root, production_image)
    if runtime_uid != 10002:
        findings.append("RUNTIME_UID_NOT_10002")
    runtime_class = _inspect_label(root, production_image, "io.fa3.runtime.class")
    zero_copy_label = _inspect_label(root, production_image, "io.fa3.zero-copy-claimed")
    if runtime_class != "CURRENT_HOST_PRODUCTION":
        findings.append("PRODUCTION_RUNTIME_CLASS_INVALID")
    if zero_copy_label.lower() != "false":
        findings.append("ZERO_COPY_CLAIM_FORBIDDEN_BY_CURRENT_CANONICAL_BASELINE")

    try:
        ffmpeg_receipt = json.loads((root / "evidence/receipts/ffmpeg-ai-current-host.json").read_text(encoding="utf-8"))
        expected_ffmpeg_sha = ffmpeg_receipt["ffmpeg_feature_manifest"]["ffmpeg_binary_sha256"]
        receipt_pass = ffmpeg_receipt.get("status") == "PASS" and ffmpeg_receipt.get("fixture_semantics") != "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST"
    except Exception:
        expected_ffmpeg_sha = None
        receipt_pass = False
    if not receipt_pass:
        findings.append("FFMPEG_CURRENT_HOST_RECEIPT_NOT_PASS")
    observed_ffmpeg_sha = _container_ffmpeg_sha(root, production_image)
    digest_match = bool(expected_ffmpeg_sha and observed_ffmpeg_sha == expected_ffmpeg_sha)
    if not digest_match:
        findings.append("PRODUCTION_IMAGE_FFMPEG_DIGEST_MISMATCH")

    audit_chain = _audit_self_test(root, production_image)
    api_health = _api_health(root, production_image)
    if audit_chain != "PASS":
        findings.append("AUDIT_CHAIN_SELF_TEST_FAILED")
    if api_health != "PASS":
        findings.append("API_HEALTH_FAILED")

    return {
        "schema": "fa3.blackhole-oci-admission.v1",
        "mode": "CURRENT_HOST_PRODUCTION",
        "result": "PASS" if not findings else "FAIL",
        "rootless": rootless,
        "runtime_uid": runtime_uid,
        "runtime_class": runtime_class,
        "production_image": production_image,
        "production_image_immutable": True,
        "image_id": _image_id(root, production_image),
        "ffmpeg_binary_sha256": observed_ffmpeg_sha,
        "expected_ffmpeg_binary_sha256": expected_ffmpeg_sha,
        "ffmpeg_digest_matches_current_host_receipt": digest_match,
        "api_health": api_health,
        "audit_chain": audit_chain,
        "zero_copy_claimed": False,
        "global_fa3_promotion_claim": False,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect FA3 Blackhole reference/current-host OCI admission evidence")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--mode", choices=("reference", "current-host"), default="reference")
    parser.add_argument("--production-image", default=os.environ.get("FA3_BLACKHOLE_PRODUCTION_IMAGE", ""))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = collect_reference(root) if args.mode == "reference" else collect_current_host(root, args.production_image)
    output = root / ("reports/blackhole-runtime-reference-oci-report.json" if args.mode == "reference" else "reports/blackhole-runtime-current-host-report.json")
    _write(output, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
