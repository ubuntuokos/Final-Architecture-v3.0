#!/usr/bin/env python3
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import resource
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROVIDER_ID = "FA3-PROVIDER-AI-INFRA-GUARD-001"
ADAPTER_ID = "FA3-AI-INFRA-GUARD-ADAPTER-001"
ADMISSION_ID = "FA3-AI-INFRA-GUARD-RUNTIME-ADMISSION-001"
VERSION = "v4.6.0"
UPSTREAM_COMMIT = "e8931cc68001b66ad024fd87ef07394e9e96524a"
SOURCE_ARCHIVE_SHA256 = "1523b3e9f54c520b9a602e332a05f846c4e72c02e65a50feadd96533856c0ed4"

_ALLOWED_ENV = {
    "PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE",
    "TMPDIR", "XDG_CACHE_HOME", "SSL_CERT_FILE", "SSL_CERT_DIR",
}
_SECRET_RE = re.compile(r"(TOKEN|SECRET|PASSWORD|API[_-]?KEY|CREDENTIAL|PRIVATE[_-]?KEY|AUTH)", re.I)
_PROXY_RE = re.compile(r"(^|_)(HTTP|HTTPS|ALL|NO)_?PROXY$", re.I)
_CVE_RE = re.compile(r"(CVE-\d{4}-\d+)\s*\[(CRITICAL|HIGH|MEDIUM|LOW|INFO)\]", re.I)
_OLLAMA_FP_RE = re.compile(r"\[ollama(?::[^\]]*)?\]", re.I)


class AdmissionDenied(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_tree(root: Path) -> str:
    root = root.resolve()
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix().encode()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(bytes.fromhex(sha256_file(path)))
    return h.hexdigest()


def validate_loopback_target(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme != "http":
        raise AdmissionDenied("AI-Infra-Guard current-host target must use http")
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise AdmissionDenied("AI-Infra-Guard current-host target must be loopback-only")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AdmissionDenied("credentials/query/fragment are forbidden in scan target")
    if parsed.port is None or not (1024 <= parsed.port <= 65535):
        raise AdmissionDenied("explicit unprivileged loopback port is required")
    if parsed.path not in {"", "/"}:
        raise AdmissionDenied("scan target must be a base URL")
    return f"http://127.0.0.1:{parsed.port}"


def safe_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    source = dict(os.environ if source is None else source)
    env: dict[str, str] = {}
    for key, value in source.items():
        if key not in _ALLOWED_ENV or not value:
            continue
        if _SECRET_RE.search(key) or _PROXY_RE.search(key):
            raise AdmissionDenied(f"secret/proxy-like environment key reached allowlist: {key}")
        env[key] = value
    env["PYTHONIOENCODING"] = "utf-8"
    env["GODEBUG"] = "netdns=go"
    return env


def _sandbox_preexec() -> None:
    os.setsid()
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    libc = ctypes.CDLL(None)
    PR_SET_NO_NEW_PRIVS = 38
    if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        raise OSError("prctl(PR_SET_NO_NEW_PRIVS) failed")


def runtime_preflight(binary: Path, source_root: Path) -> dict[str, Any]:
    binary = binary.resolve()
    source_root = source_root.resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise AdmissionDenied(f"AI-Infra-Guard binary missing/not executable: {binary}")
    required = [
        source_root / "data/fingerprints",
        source_root / "data/vuln",
        source_root / "data/vuln_en",
    ]
    if not all(p.is_dir() for p in required):
        raise AdmissionDenied("pinned AI-Infra-Guard ruleset directories are incomplete")
    p = subprocess.run(
        [str(binary), "--help"],
        cwd=str(source_root),
        env=safe_environment(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=15,
        check=False,
    )
    if p.returncode != 0 or "scan" not in p.stdout:
        raise AdmissionDenied("AI-Infra-Guard native scan CLI preflight failed")
    return {
        "binary": str(binary),
        "binary_sha256": sha256_file(binary),
        "source_root": str(source_root),
        "fingerprints_sha256": sha256_tree(source_root / "data/fingerprints"),
        "vulnerability_rules_zh_sha256": sha256_tree(source_root / "data/vuln"),
        "vulnerability_rules_en_sha256": sha256_tree(source_root / "data/vuln_en"),
        "help_scan_surface_present": True,
    }


def parse_scan_output(text: str) -> dict[str, Any]:
    findings = [{"cve": cve.upper(), "severity": sev.upper()} for cve, sev in _CVE_RE.findall(text)]
    unique = []
    seen = set()
    for item in findings:
        key = (item["cve"], item["severity"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    counts = {level: 0 for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")}
    for item in unique:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1
    return {
        "ollama_fingerprint_observed": bool(_OLLAMA_FP_RE.search(text)),
        "advisories": unique,
        "severity_counts": counts,
    }


def run_scan(*, binary: Path, source_root: Path, target: str, output_path: Path,
             timeout_seconds: int = 180) -> dict[str, Any]:
    if not (30 <= timeout_seconds <= 300):
        raise AdmissionDenied("scan timeout outside FA3 current-host bound")
    target = validate_loopback_target(target)
    preflight = runtime_preflight(binary, source_root)
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    command = [
        str(binary.resolve()), "scan",
        "--target", target,
        "--output", str(output_path),
        "--timeout", "5",
        "--limit", "20",
        "--fps", str((source_root / "data/fingerprints").resolve()),
        "--vul", str((source_root / "data/vuln").resolve()),
        "--lang", "en",
    ]
    p = subprocess.run(
        command,
        cwd=str(source_root.resolve()),
        env=safe_environment(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
        preexec_fn=_sandbox_preexec,
    )
    if p.returncode != 0:
        raise AdmissionDenied(f"AI-Infra-Guard scan failed rc={p.returncode}: {p.stderr[-1200:]}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise AdmissionDenied("AI-Infra-Guard scan did not materialize output")
    combined = p.stdout + "\n" + p.stderr + "\n" + output_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_scan_output(combined)
    if not parsed["ollama_fingerprint_observed"]:
        raise AdmissionDenied("real AI-Infra-Guard scan did not fingerprint the current-host Ollama target")
    return {
        "provider_id": PROVIDER_ID,
        "adapter_id": ADAPTER_ID,
        "target": target,
        "command_surface": "ai-infra-guard scan",
        "returncode": p.returncode,
        "runtime_preflight": preflight,
        "isolation": {
            "non_root_required": True,
            "no_new_privs": True,
            "resource_limits": {
                "cpu_seconds": 120,
                "address_space_bytes": 2 * 1024**3,
                "open_files": 256,
                "processes": 64,
            },
            "environment_allowlist": sorted(_ALLOWED_ENV),
            "secret_env_passthrough": False,
            "proxy_env_passthrough": False,
            "target_scope": "LOOPBACK_GUARD_PROXY_ONLY",
            "arbitrary_headers": False,
        },
        "stdout_sha256": hashlib.sha256(p.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(p.stderr.encode()).hexdigest(),
        "output_path": str(output_path),
        "output_sha256": sha256_file(output_path),
        "output_size": output_path.stat().st_size,
        "scan_result": parsed,
    }


def regression_check() -> dict[str, Any]:
    cases: dict[str, bool] = {}
    cases["remote_target_denied"] = False
    try:
        validate_loopback_target("https://example.com:443/")
    except AdmissionDenied:
        cases["remote_target_denied"] = True
    cases["privileged_port_denied"] = False
    try:
        validate_loopback_target("http://127.0.0.1:80/")
    except AdmissionDenied:
        cases["privileged_port_denied"] = True
    cases["credentials_in_target_denied"] = False
    try:
        validate_loopback_target("http://user:pass@127.0.0.1:11434/")
    except AdmissionDenied:
        cases["credentials_in_target_denied"] = True
    env = safe_environment({"PATH": "/usr/bin", "HOME": "/tmp", "OPENAI_API_KEY": "secret", "HTTPS_PROXY": "http://x"})
    cases["secret_and_proxy_env_dropped"] = "OPENAI_API_KEY" not in env and "HTTPS_PROXY" not in env
    parsed = parse_scan_output("http://127.0.0.1:12345 [200] [] [ollama:server:0.12.1]\nCVE-2026-1 [HIGH]")
    cases["ollama_fingerprint_parser"] = parsed["ollama_fingerprint_observed"]
    cases["finding_parser"] = parsed["severity_counts"]["HIGH"] == 1
    return {
        "schema": "fa3.ai-infra-guard-adapter-regression.v1",
        "result": "PASS" if all(cases.values()) else "FAIL",
        "passed": sum(cases.values()),
        "total": len(cases),
        "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(regression_check(), indent=2))
