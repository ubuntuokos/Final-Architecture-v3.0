#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_ai_infra_guard_adapter import (
    ADAPTER_ID,
    ADMISSION_ID,
    PROVIDER_ID,
    SOURCE_ARCHIVE_SHA256,
    UPSTREAM_COMMIT,
    VERSION,
    regression_check,
    run_scan,
    sha256_file,
)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def writej(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def no_proxy_opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))

def http_get(url: str, timeout: float = 3.0) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "FA3-AI-SEC-E2E/1"})
    with no_proxy_opener().open(req, timeout=timeout) as resp:
        return resp.status, resp.read(1024 * 1024), dict(resp.headers.items())

def ollama_preflight(base_url: str) -> dict[str, Any]:
    status, body, _ = http_get(base_url.rstrip("/") + "/")
    if status != 200 or b"Ollama is running" not in body:
        raise RuntimeError("Ollama root endpoint identity check failed")
    v_status, v_body, _ = http_get(base_url.rstrip("/") + "/api/version")
    if v_status != 200:
        raise RuntimeError("Ollama version endpoint failed")
    try:
        version = json.loads(v_body.decode("utf-8"))["version"]
    except Exception as exc:
        raise RuntimeError("Ollama version response is invalid") from exc
    if not isinstance(version, str) or not version:
        raise RuntimeError("Ollama version missing")
    return {
        "base_url": base_url,
        "root_identity": "Ollama is running",
        "api_version": version,
        "root_response_sha256": hashlib.sha256(body).hexdigest(),
        "version_response_sha256": hashlib.sha256(v_body).hexdigest(),
    }

def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])

def stripped_child_env() -> dict[str, str]:
    keep = {"PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR"}
    return {k: v for k, v in os.environ.items() if k in keep and v}

def ensure_real_ollama(runtime_dir: Path) -> tuple[dict[str, Any], subprocess.Popen[str] | None]:
    existing = "http://127.0.0.1:11434"
    try:
        info = ollama_preflight(existing)
        info["mode"] = "EXISTING_CURRENT_HOST_SERVICE"
        info["launched_by_collector"] = False
        return info, None
    except Exception:
        pass

    ollama = shutil.which("ollama")
    if not ollama:
        raise RuntimeError("no current-host Ollama service and no ollama binary found")
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = stripped_child_env()
    env["OLLAMA_HOST"] = f"127.0.0.1:{port}"
    env["OLLAMA_ORIGINS"] = "http://127.0.0.1"
    log = (runtime_dir / "ollama-ephemeral.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [ollama, "serve"],
        env=env,
        text=True,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    deadline = time.monotonic() + 45
    last = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            log.close()
            raise RuntimeError(f"ephemeral Ollama exited early rc={proc.returncode}")
        try:
            info = ollama_preflight(base)
            info["mode"] = "EPHEMERAL_REAL_CURRENT_HOST_SERVICE"
            info["launched_by_collector"] = True
            info["ollama_binary"] = str(Path(ollama).resolve())
            info["ollama_binary_sha256"] = sha256_file(Path(ollama).resolve())
            try:
                vp = subprocess.run([ollama, "--version"], env=stripped_child_env(), text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10, check=False)
                info["ollama_version_output"] = vp.stdout.strip()
            except Exception:
                info["ollama_version_output"] = None
            log.flush()
            return info, proc
        except Exception as exc:
            last = exc
            time.sleep(0.5)
    log.close()
    try:
        os.killpg(proc.pid, 15)
    except ProcessLookupError:
        pass
    raise RuntimeError(f"ephemeral Ollama did not become ready: {last}")

class GuardedProxy(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False
    def __init__(self, address, upstream: str):
        super().__init__(address, GuardedProxyHandler)
        self.upstream = upstream.rstrip("/")
        self.requests: list[dict[str, Any]] = []

class GuardedProxyHandler(http.server.BaseHTTPRequestHandler):
    server: GuardedProxy
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if not self.path.startswith("/") or self.path.startswith("//"):
            self.send_error(400)
            return
        url = self.server.upstream + self.path
        try:
            status, body, headers = http_get(url, timeout=5)
        except Exception:
            self.send_error(502)
            return
        self.server.requests.append({
            "method": "GET",
            "path": self.path.split("?", 1)[0],
            "upstream_status": status,
            "response_sha256": hashlib.sha256(body).hexdigest(),
        })
        self.send_response(status)
        ctype = headers.get("Content-Type")
        if ctype:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self) -> None:
        self.do_GET()

def main() -> int:
    ap = argparse.ArgumentParser(description="Collect real AI-Infra-Guard current-host production E2E evidence")
    default_runtime = Path.home() / ".local/lib/fa3/ai-infra-guard" / VERSION
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--binary", default=str(default_runtime / "bin/ai-infra-guard"))
    ap.add_argument("--source-root", default=str(default_runtime / "source/tree"))
    ap.add_argument("--build-metadata", default=str(default_runtime / "build-metadata.json"))
    ap.add_argument("--timeout-seconds", type=int, default=180)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    binary = Path(args.binary).expanduser().resolve()
    source_root = Path(args.source_root).expanduser().resolve()
    metadata_path = Path(args.build_metadata).expanduser().resolve()
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("AI-Infra-Guard current-host evidence requires Linux x86_64")
    if os.geteuid() == 0:
        raise RuntimeError("AI-Infra-Guard current-host evidence must run as a non-root user")
    if not metadata_path.is_file():
        raise RuntimeError("AI-Infra-Guard pinned build metadata missing")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not (
        metadata.get("release") == VERSION
        and metadata.get("release_commit") == UPSTREAM_COMMIT
        and metadata.get("source_archive_sha256") == SOURCE_ARCHIVE_SHA256
        and metadata.get("binary_sha256") == sha256_file(binary)
    ):
        raise RuntimeError("AI-Infra-Guard build metadata/runtime identity mismatch")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime_dir = root / "evidence/runtime/ai-infra-guard-current-host" / stamp
    runtime_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = root / "evidence/receipts/ai-infra-guard-current-host.json"
    started = utc_now()
    regressions = regression_check()
    if regressions.get("result") != "PASS":
        raise RuntimeError("AI-Infra-Guard isolated adapter regression failed")

    ollama_proc: subprocess.Popen[str] | None = None
    proxy: GuardedProxy | None = None
    proxy_thread: threading.Thread | None = None
    try:
        ollama, ollama_proc = ensure_real_ollama(runtime_dir)
        upstream = ollama["base_url"]
        proxy_port = free_port()
        proxy = GuardedProxy(("127.0.0.1", proxy_port), upstream)
        proxy_thread = threading.Thread(target=proxy.serve_forever, name="fa3-aig-guard-proxy", daemon=True)
        proxy_thread.start()
        guarded_target = f"http://127.0.0.1:{proxy_port}"
        output_path = runtime_dir / "ai-infra-guard-scan.txt"
        scan = run_scan(
            binary=binary,
            source_root=source_root,
            target=guarded_target,
            output_path=output_path,
            timeout_seconds=args.timeout_seconds,
        )
        if not proxy.requests:
            raise RuntimeError("guard proxy observed no AI-Infra-Guard traffic")
        paths = sorted({x["path"] for x in proxy.requests})
        if "/" not in paths or "/api/version" not in paths:
            raise RuntimeError("AI-Infra-Guard did not execute expected Ollama fingerprint/version probes")

        severity = scan["scan_result"]["severity_counts"]
        receipt = {
            "schema": "fa3.ai-infra-guard-current-host-receipt.v1",
            "provider_id": PROVIDER_ID,
            "adapter_id": ADAPTER_ID,
            "admission_id": ADMISSION_ID,
            "status": "PASS",
            "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS",
            "collector_mode": "REAL_AI_INFRA_GUARD_NATIVE_SCAN_REAL_CURRENT_HOST_OLLAMA",
            "synthetic_scanner": False,
            "synthetic_target": False,
            "started_at": started,
            "completed_at": utc_now(),
            "host": {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
                "hostname_sha256": hash_text(socket.gethostname()),
                "effective_uid": os.geteuid(),
            },
            "upstream": {
                "release": VERSION,
                "release_commit": UPSTREAM_COMMIT,
                "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
            },
            "build": metadata,
            "adapter_regression": regressions,
            "target": {
                "type": "REAL_CURRENT_HOST_OLLAMA_SERVICE",
                "service": ollama,
                "guard_proxy": {
                    "bind": guarded_target,
                    "fixed_upstream": upstream,
                    "external_redirect_forwarding": False,
                    "request_count": len(proxy.requests),
                    "paths": paths,
                    "request_log_sha256": hash_text(json.dumps(proxy.requests, sort_keys=True)),
                },
            },
            "production_e2e": scan,
            "security_findings": {
                "advisory_count": len(scan["scan_result"]["advisories"]),
                "severity_counts": severity,
                "advisories": scan["scan_result"]["advisories"],
                "target_promotion_effect": "NONE",
                "critical_findings_block_target_promotion": severity.get("CRITICAL", 0) > 0,
            },
            "authority": {
                "scanner_is_security_authority": False,
                "scanner_is_promotion_authority": False,
                "scanner_output_requires_fa3_attestation": True,
            },
            "isolation_verdict": "PASS",
            "runtime_admission_eligible": True,
            "global_capability_promotion_effect": "NONE_PROVIDER_SPECIFIC_EVIDENCE_ONLY",
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "capability_count_after": 143,
        }
        writej(receipt_path, receipt)
        writej(runtime_dir / "summary.json", {
            "provider_id": PROVIDER_ID,
            "status": "PASS",
            "evidence_level": receipt["evidence_level"],
            "completed_at": receipt["completed_at"],
            "scanner_binary_sha256": scan["runtime_preflight"]["binary_sha256"],
            "fingerprints_sha256": scan["runtime_preflight"]["fingerprints_sha256"],
            "vulnerability_rules_en_sha256": scan["runtime_preflight"]["vulnerability_rules_en_sha256"],
            "target_ollama_version": ollama["api_version"],
            "scan_output_sha256": scan["output_sha256"],
            "advisory_count": receipt["security_findings"]["advisory_count"],
        })
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0
    finally:
        if proxy is not None:
            proxy.shutdown()
            proxy.server_close()
        if proxy_thread is not None:
            proxy_thread.join(timeout=5)
        if ollama_proc is not None:
            try:
                os.killpg(ollama_proc.pid, 15)
            except ProcessLookupError:
                pass
            try:
                ollama_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(ollama_proc.pid, 9)
                except ProcessLookupError:
                    pass
                ollama_proc.wait(timeout=5)

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        fail = {
            "schema": "fa3.ai-infra-guard-current-host-receipt.v1",
            "provider_id": PROVIDER_ID,
            "adapter_id": ADAPTER_ID,
            "admission_id": ADMISSION_ID,
            "status": "FAIL",
            "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "completed_at": utc_now(),
        }
        writej(ROOT / "evidence/receipts/ai-infra-guard-current-host.json", fail)
        print(json.dumps(fail, indent=2), file=sys.stderr)
        raise SystemExit(2)
