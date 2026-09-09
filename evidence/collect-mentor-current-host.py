#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_mentor_current_host import (
    CAPABILITY_COUNT, EVIDENCE_AUTHORITY, EVIDENCE_LEVEL, KNOWLEDGE_AUTHORITY,
    MCP_AUTHORITY, PARENT_PROFILE_ID, PROFILE_ID, bkt_update, digest_json,
    endpoint_is_loopback, fsrs_style_schedule, now, receipt_digest, sanitized_endpoint,
)

DEFAULT_CONFIG = Path.home() / ".config/fa3/mentor-current-host.json"
DEFAULT_RECEIPT = ROOT / "evidence/receipts/mentor-current-host.json"


def writej(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def token_from_config(cfg: dict[str, Any]) -> str | None:
    path = cfg.get("auth_token_file")
    if not path:
        return None
    p = Path(os.path.expandvars(os.path.expanduser(str(path)))).resolve()
    token = p.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("auth token file is empty")
    return token


def request_json(url: str, *, payload: dict[str, Any] | None = None, token: str | None = None, timeout: float = 10.0) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": "fa3-mentor-current-host/1.0"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(1024 * 1024)
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError("endpoint returned non-object JSON")
    return obj


def status_pass(obj: dict[str, Any]) -> bool:
    return str(obj.get("status", "")).upper() in {"PASS", "OK", "HEALTHY", "ACCEPTED", "ALLOW", "ALLOWED"}


def authority_id(obj: dict[str, Any]) -> str | None:
    return obj.get("authority_id") or obj.get("authority")


def safe_component_error(exc: Exception) -> dict[str, Any]:
    return {"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:1000]}


def check_endpoint_policy(cfg: dict[str, Any]) -> None:
    required = ["mentor_health_url", "mcp_dispatch_url", "knowledge_query_url", "memory_read_url", "evidence_append_url"]
    missing = [x for x in required if not cfg.get(x)]
    if missing:
        raise RuntimeError(f"missing required endpoint config: {', '.join(missing)}")
    if cfg.get("allow_non_loopback") is True:
        return
    bad = [x for x in required if not endpoint_is_loopback(str(cfg[x]))]
    if bad:
        raise RuntimeError(f"non-loopback endpoint denied without explicit override: {', '.join(bad)}")


def mcp_envelope(run_id: str, capability: str, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "fa3.mcp-typed-escalation.v1",
        "request_id": f"mentor-e2e-{uuid.uuid4()}",
        "caller": {"profile_id": PARENT_PROFILE_ID, "current_host_profile_id": PROFILE_ID, "run_id": run_id},
        "target_authority": "central_mcp_gateway",
        "target_capability": capability,
        "operation": operation,
        "requires_authorization": True,
        "execute_by_mentor": False,
        "explicit_user_consent": True,
        "payload": payload,
    }


def run_bubblewrap() -> dict[str, Any]:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return {"status": "FAIL", "backend": None, "error": "bubblewrap executable not found"}
    version = subprocess.run([bwrap, "--version"], text=True, capture_output=True, check=False, timeout=5)
    if version.returncode != 0:
        return {"status": "FAIL", "backend": "bubblewrap", "error": "bwrap --version failed"}

    with tempfile.TemporaryDirectory(prefix="fa3-mentor-host-sentinel-") as td:
        host_dir = Path(td).resolve()
        escaped = host_dir / "sandbox-escaped"
        base = [
            bwrap, "--die-with-parent", "--new-session", "--unshare-pid", "--unshare-ipc", "--unshare-uts", "--unshare-net",
            "--ro-bind", "/", "/", "--tmpfs", "/tmp", "--proc", "/proc", "--dev", "/dev", "--chdir", "/tmp",
        ]
        python = shutil.which("python3") or "/usr/bin/python3"
        positive = subprocess.run(base + [python, "-c", "from pathlib import Path; Path('/tmp/fa3-result').write_text('FA3_MENTOR_LAB_PASS'); print(Path('/tmp/fa3-result').read_text())"], text=True, capture_output=True, check=False, timeout=8)
        host_write = subprocess.run(base + [python, "-c", f"from pathlib import Path; Path({str(escaped)!r}).write_text('BAD')"], text=True, capture_output=True, check=False, timeout=8)
        net_probe = subprocess.run(base + [python, "-c", "import socket,sys; print(socket.if_nameindex()); socket.create_connection(('1.1.1.1',443),0.75)"], text=True, capture_output=True, check=False, timeout=8)
        timeout_terminated = False
        try:
            subprocess.run(base + [python, "-c", "import time; time.sleep(10)"], text=True, capture_output=True, check=False, timeout=1)
        except subprocess.TimeoutExpired:
            timeout_terminated = True

        positive_ok = positive.returncode == 0 and "FA3_MENTOR_LAB_PASS" in positive.stdout
        host_write_denied = host_write.returncode != 0 and not escaped.exists()
        network_denied = net_probe.returncode != 0
        result = {
            "status": "PASS" if all([positive_ok, host_write_denied, network_denied, timeout_terminated]) else "FAIL",
            "backend": "bubblewrap",
            "version": version.stdout.strip() or version.stderr.strip(),
            "positive_lab": positive_ok,
            "host_write_denied": host_write_denied,
            "network_denied": network_denied,
            "timeout_terminated": timeout_terminated,
            "writable_host_paths": [],
            "network_policy": "UNSHARE_NET",
            "root_mount": "READ_ONLY",
            "positive_stdout_sha256": hashlib.sha256(positive.stdout.encode()).hexdigest(),
            "negative_host_stderr_sha256": hashlib.sha256(host_write.stderr.encode()).hexdigest(),
            "negative_network_stderr_sha256": hashlib.sha256(net_probe.stderr.encode()).hexdigest(),
        }
        return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--config", default=os.environ.get("FA3_MENTOR_CURRENT_HOST_CONFIG", str(DEFAULT_CONFIG)))
    ap.add_argument("--receipt", default=str(DEFAULT_RECEIPT))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    receipt_path = Path(args.receipt)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    config_path = Path(os.path.expandvars(os.path.expanduser(args.config))).resolve()
    run_id = f"fa3-mentor-{uuid.uuid4()}"
    receipt: dict[str, Any] = {
        "schema": "fa3.mentor-current-host-receipt.v1",
        "profile_id": PROFILE_ID,
        "parent_profile_id": PARENT_PROFILE_ID,
        "status": "FAIL",
        "host_scope": "CURRENT_HOST",
        "fixture_semantics": "REAL_CURRENT_HOST_EXECUTION",
        "evidence_level": EVIDENCE_LEVEL,
        "run_id": run_id,
        "started_at": now(),
        "capability_count_after": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
        "host": {"system": platform.system(), "machine": platform.machine(), "node_sha256": hashlib.sha256(platform.node().encode()).hexdigest()},
        "config": {"path_sha256": hashlib.sha256(str(config_path).encode()).hexdigest(), "secret_values_persisted": False},
        "components": {},
        "observed_authorities": [],
        "errors": [],
    }
    components = receipt["components"]

    cfg: dict[str, Any] = {}
    token: str | None = None
    try:
        if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
            raise RuntimeError("Linux x86_64 required")
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            raise RuntimeError("current-host E2E must not run as root")
        cfg = loadj(config_path)
        if cfg.get("schema") != "fa3.mentor-current-host-config.v1":
            raise RuntimeError("config schema mismatch")
        check_endpoint_policy(cfg)
        token = token_from_config(cfg)
        receipt["config"].update({
            "schema": cfg.get("schema"),
            "allow_non_loopback": cfg.get("allow_non_loopback") is True,
            "endpoints": {k: sanitized_endpoint(str(cfg[k])) for k in ["mentor_health_url", "mcp_dispatch_url", "knowledge_query_url", "memory_read_url", "evidence_append_url"]},
            "token_file_configured": bool(cfg.get("auth_token_file")),
        })
    except Exception as exc:
        receipt["errors"].append({"phase": "config", **safe_component_error(exc)})

    if cfg:
        try:
            obj = request_json(str(cfg["mentor_health_url"]), token=token)
            ok = status_pass(obj) and obj.get("profile_id", PARENT_PROFILE_ID) == PARENT_PROFILE_ID
            components["mentor_runtime"] = {"status": "PASS" if ok else "FAIL", "profile_id": obj.get("profile_id"), "response_sha256": digest_json(obj)}
        except Exception as exc:
            components["mentor_runtime"] = safe_component_error(exc)

        try:
            env = mcp_envelope(run_id, "mentor.current_host.probe", "probe", {"nonce": run_id})
            obj = request_json(str(cfg["mcp_dispatch_url"]), payload=env, token=token)
            aid = authority_id(obj)
            ok = status_pass(obj) and aid == MCP_AUTHORITY and obj.get("execution_performed_by_mentor") is False
            components["central_mcp"] = {"status": "PASS" if ok else "FAIL", "authority_id": aid, "execution_performed_by_mentor": obj.get("execution_performed_by_mentor"), "request_sha256": digest_json(env), "response_sha256": digest_json(obj)}
            if aid:
                receipt["observed_authorities"].append(aid)
        except Exception as exc:
            components["central_mcp"] = safe_component_error(exc)

        try:
            q = {"schema": "fa3.knowledge-query.v1", "query": "FA3-MENTOR-001 current-host conformance", "limit": 5, "require_provenance": True, "run_id": run_id}
            obj = request_json(str(cfg["knowledge_query_url"]), payload=q, token=token)
            aid = authority_id(obj)
            provenance = obj.get("provenance_refs") or obj.get("provenance") or []
            ok = status_pass(obj) and aid == KNOWLEDGE_AUTHORITY and bool(provenance)
            components["knowledge_rag"] = {"status": "PASS" if ok else "FAIL", "authority_id": aid, "provenance_refs": provenance[:20] if isinstance(provenance, list) else [str(provenance)], "request_sha256": digest_json(q), "response_sha256": digest_json(obj)}
            if aid:
                receipt["observed_authorities"].append(aid)
        except Exception as exc:
            components["knowledge_rag"] = safe_component_error(exc)

        namespace = f"fa3-mentor-e2e/{run_id}"
        marker = f"marker-{uuid.uuid4()}"
        try:
            write_env = mcp_envelope(run_id, "memory.write", "put", {"namespace": namespace, "key": "marker", "value": marker, "ttl_seconds": 300})
            write_obj = request_json(str(cfg["mcp_dispatch_url"]), payload=write_env, token=token)
            write_ok = status_pass(write_obj) and authority_id(write_obj) == MCP_AUTHORITY
            read_obj: dict[str, Any] = {}
            roundtrip = False
            for _ in range(6):
                read_obj = request_json(str(cfg["memory_read_url"]), payload={"schema": "fa3.memory-read-query.v1", "namespace": namespace, "key": "marker", "run_id": run_id}, token=token)
                observed = read_obj.get("value")
                if observed == marker:
                    roundtrip = True
                    break
                time.sleep(0.5)
            memory_authority = authority_id(read_obj)
            cleanup_env = mcp_envelope(run_id, "memory.delete", "delete", {"namespace": namespace, "key": "marker"})
            cleanup_obj = request_json(str(cfg["mcp_dispatch_url"]), payload=cleanup_env, token=token)
            cleanup_ok = status_pass(cleanup_obj)
            memory_ok = write_ok and status_pass(read_obj) and roundtrip and bool(memory_authority) and memory_authority not in {PROFILE_ID, PARENT_PROFILE_ID, "FA3-PROVIDER-MENTOR-LOCAL-001"} and cleanup_ok
            components["memory"] = {"status": "PASS" if memory_ok else "FAIL", "authority_id": memory_authority, "explicit_user_consent": True, "write_via_central_mcp": True, "marker_roundtrip": roundtrip, "ttl_seconds": 300, "cleanup": "PASS" if cleanup_ok else "FAIL", "write_response_sha256": digest_json(write_obj), "read_response_sha256": digest_json(read_obj), "cleanup_response_sha256": digest_json(cleanup_obj)}
            if memory_authority:
                receipt["observed_authorities"].append(memory_authority)
        except Exception as exc:
            components["memory"] = {**safe_component_error(exc), "explicit_user_consent": True, "write_via_central_mcp": True, "marker_roundtrip": False}

        evidence_id: str | None = None
        try:
            event = {"schema": "fa3.evidence-event.v1", "event_type": "mentor.current_host.e2e", "subject_id": PROFILE_ID, "run_id": run_id, "payload_digest": digest_json({k: v.get("status") for k, v in components.items()})}
            obj = request_json(str(cfg["evidence_append_url"]), payload=event, token=token)
            aid = authority_id(obj)
            evidence_id = obj.get("evidence_id") or obj.get("receipt_id")
            ok = status_pass(obj) and aid == EVIDENCE_AUTHORITY and bool(evidence_id)
            components["evidence"] = {"status": "PASS" if ok else "FAIL", "authority_id": aid, "evidence_id": evidence_id, "event_sha256": digest_json(event), "response_sha256": digest_json(obj)}
            if aid:
                receipt["observed_authorities"].append(aid)
        except Exception as exc:
            components["evidence"] = safe_component_error(exc)

        try:
            before = 0.20
            after = bkt_update(before, True)
            schedule = fsrs_style_schedule(previous_stability_days=1.0, difficulty=5.0, correct=True, p_known=after)
            ok = bool(evidence_id) and after > before and schedule["interval_days"] > 0
            components["mastery"] = {"status": "PASS" if ok else "FAIL", "engine": "BKT_PLUS_FSRS_STYLE_PROVIDER_NEUTRAL", "p_known_before": before, "p_known_after": round(after, 8), **schedule, "evidence_refs": [evidence_id] if evidence_id else []}
        except Exception as exc:
            components["mastery"] = safe_component_error(exc)

    components["bubblewrap"] = run_bubblewrap()

    required = ["mentor_runtime", "central_mcp", "knowledge_rag", "memory", "evidence", "mastery", "bubblewrap"]
    all_pass = all(str(components.get(x, {}).get("status", "")).upper() == "PASS" for x in required)
    forbidden_authorities = {PROFILE_ID, PARENT_PROFILE_ID, "FA3-PROVIDER-MENTOR-LOCAL-001"}
    authority_ok = not any(x in forbidden_authorities for x in receipt["observed_authorities"])
    receipt["status"] = "PASS" if all_pass and authority_ok else "FAIL"
    receipt["finished_at"] = now()
    receipt["observed_authorities"] = sorted(set(receipt["observed_authorities"]))
    receipt["receipt_sha256"] = receipt_digest(receipt)
    writej(receipt_path, receipt)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
