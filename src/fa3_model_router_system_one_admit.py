#!/usr/bin/env python3
"""Opt-in real current-host admission for the native System One provider bridge.

Not a CI or mock admission: requires the running FA3 native bridge, a live upstream
decision, invalid-bearer rejection, a primary-model designation and Secret Broker
credential-file projection. Emits secret-free evidence and a disabled-until-admitted
runtime descriptor; never promotes the whole FA3 system.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import stat
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from fa3_model_router_materialize import AUTHORITY, sha256_file
from fa3_model_router_provider_discovery import process_start_ticks
from fa3_model_router_system_one_native_bridge import (
    NATIVE_PROVIDER_ID, NativeBridgeDenied, read_projected_credential,
)

SCHEMA = "fa3.system-one-native-current-host-receipt.v1"


class NativeAdmissionDenied(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise NativeAdmissionDenied("native probe must not follow redirects")


def loopback_base(text: str) -> bool:
    p = urlparse(text)
    return p.scheme == "http" and (p.hostname or "") in {"127.0.0.1", "localhost", "::1"} and p.path.rstrip("/") == "/v1" and p.port is not None and not p.username and not p.password


def http_probe(url: str, method: str, token: str, payload: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
    if not url.startswith("http://127.0.0.1:") and not url.startswith("http://localhost:"):
        raise NativeAdmissionDenied("native probe may address loopback only")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"},
    )
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with op.open(req, timeout=15.0) as res:
            raw = res.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise NativeAdmissionDenied("native upstream response exceeds probe ceiling")
            obj = json.loads(raw)
            return res.status, obj if isinstance(obj, dict) else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise NativeAdmissionDenied("native provider probe transport/JSON failed") from None


def _owned_listen_socket(pid: int, port: int) -> bool:
    try:
        open_inodes = set()
        for fd in Path(f"/proc/{pid}/fd").iterdir():
            target = os.readlink(fd)
            if target.startswith("socket:[") and target.endswith("]"):
                open_inodes.add(target[8:-1])
        for proc_net in ("/proc/net/tcp", "/proc/net/tcp6"):
            with open(proc_net, encoding="ascii") as handle:
                for line in handle.read().splitlines()[1:]:
                    fields = line.split()
                    if len(fields) >= 10 and fields[3] == "0A":
                        local_ip, local_port = fields[1].split(":")
                        if int(local_port, 16) == port and fields[9] in open_inodes:
                            if local_ip.upper() in {"0100007F", "00000000000000000000000001000000"}:
                                return True
    except (OSError, ValueError):
        return False
    return False


def _native_process_proof(pid: int, port: int, designation: Path, upstream: str) -> int:
    ticks = process_start_ticks(pid)
    if not ticks:
        raise NativeAdmissionDenied("native backend process identity cannot be verified")
    try:
        argv = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        args = [a.decode("utf-8", errors="replace") for a in argv if a]
        env = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    except OSError:
        raise NativeAdmissionDenied("native backend command/environment cannot be inspected") from None
    if not (
        any(a.endswith("fa3_model_router_system_one_native_bridge.py") for a in args)
        and "--designation" in args and str(designation.resolve()) in args
        and "--upstream" in args and upstream in args
        and _owned_listen_socket(pid, port)
        and all(f"{name}=".encode() in env for name in
                ("CUDA_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES", "ZE_AFFINITY_MASK"))
    ):
        raise NativeAdmissionDenied("native bridge process, listening socket, or CPU-only boundary invalid")
    # The three accelerator masks must actually be empty.
    for name in ("CUDA_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES", "ZE_AFFINITY_MASK"):
        if f"{name}=".encode() not in env:
            raise NativeAdmissionDenied("native bridge accelerator masking is not established")
    return ticks


def _validate_broker_reference(root: Path, path: Path) -> None:
    if not path.is_file():
        raise NativeAdmissionDenied("admitted Secret Broker current-host reference missing")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not (
        obj.get("schema") == "fa3.current-host-evidence-reference.v1"
        and obj.get("result") == "PASS"
        and obj.get("status") == "CURRENT_HOST_ADMITTED"
        and obj.get("production_admitted") is True
        and (obj.get("source") or {}).get("current_host_gate_result") == "PASS"
        and (obj.get("runtime") or {}).get("real_execution") is True
        and (obj.get("runtime") or {}).get("synthetic") is False
        and (obj.get("runtime") or {}).get("secret_values_collected") is False
    ):
        raise NativeAdmissionDenied("Secret Broker current-host reference not admitted")


def _probe(bridge_base: str, token: str, model: str, aliases: list[str],
           request: Callable[[str, str, str, dict[str, Any] | None], tuple[int, dict[str, Any]]] = http_probe) -> tuple[str, str]:
    models_status, catalog = request(bridge_base + "/models", "GET", token, None)
    if models_status != 200 or model not in {
        row.get("id") for row in catalog.get("data", []) if isinstance(row, dict)
    }:
        raise NativeAdmissionDenied("designated model not confirmed in live native catalogue")
    questions = {
        "native_admission_probe": {
            "type": "choice",
            "instructions": "Select the already designated no-op observation response.",
            "criteria": {"observe": "Observe only", "handoff": "Request human review"},
        }
    }
    payload = {"model": model, "state": {"test": "non-executing native admission"},
               "questions": questions}
    invalid_status, _ = request(bridge_base + "/decisions", "POST", "FA3_INTENTIONALLY_INVALID_BEARER", payload)
    if invalid_status != 401:
        raise NativeAdmissionDenied("invalid bearer was not rejected by native bridge")
    empty_status, _ = request(bridge_base + "/decisions", "POST", "", payload)
    if empty_status != 401:
        raise NativeAdmissionDenied("missing bearer was not rejected by native bridge")
    status, result = request(bridge_base + "/decisions", "POST", token, payload)
    if status != 200 or result.get("model") not in [model, *aliases]:
        raise NativeAdmissionDenied("real native response model is not explicitly designated")
    answers = result.get("answers")
    a = answers.get("native_admission_probe") if isinstance(answers, dict) else None
    probs = a.get("probabilities") if isinstance(a, dict) else None
    if not (
        isinstance(a, dict)
        and set(answers) == set(questions)
        and a.get("choice") in questions["native_admission_probe"]["criteria"]
        and isinstance(probs, dict)
        and set(probs) == set(questions["native_admission_probe"]["criteria"])
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                and 0 <= v <= 1 for v in probs.values())
        and abs(sum(probs.values()) - 1) < 0.05
    ):
        raise NativeAdmissionDenied("upstream native response lacks real bounded probability distribution")
    return str(result["model"]), str(result.get("id") or "")


def _atomic(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".fa3-native-admission-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(obj, out, ensure_ascii=False, indent=2)
            out.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def admit(*, root: Path, designation: Path, bridge_api_base: str, bridge_pid: int,
          secret_broker_reference: Path, output: Path, runtime_registry: Path | None = None,
          runtime_output: Path | None = None) -> dict[str, Any]:
    if os.environ.get("FA3_SYSTEM_ONE_NATIVE_ENABLE") != "1":
        raise NativeAdmissionDenied("native live provider admission requires explicit enable")
    if not loopback_base(bridge_api_base):
        raise NativeAdmissionDenied("native service must listen on one explicit loopback /v1 origin")
    if designation.is_symlink() or not designation.is_file() or stat.S_IMODE(designation.stat().st_mode) not in {0o400, 0o600}:
        raise NativeAdmissionDenied("primary-model designation file must be protected")
    designated = json.loads(designation.read_text(encoding="utf-8"))
    if not (
        designated.get("schema") == "fa3.system-one-model-designation.v1"
        and designated.get("result") == "PASS"
        and designated.get("router_authority") == AUTHORITY
        and designated.get("provider_id") == NATIVE_PROVIDER_ID
        and designated.get("approved_by_primary_model") is True
        and designated.get("logical_route") == "fa3-decision-system-one"
        and designated.get("upstream") in {"openrouter", "typesafe"}
        and isinstance(designated.get("approved_models"), list)
        and bool(designated["approved_models"])
    ):
        raise NativeAdmissionDenied("primary-model designation missing or not approved")
    _validate_broker_reference(root, secret_broker_reference)
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    if not credential_dir:
        raise NativeAdmissionDenied("no transient Secret Broker credential directory projected")
    projected = Path(credential_dir)
    token = read_projected_credential(projected, "fa3-system-one-bridge-token")
    # Must prove both independent credential projections, without reading or storing the upstream value.
    upstream_credential = projected / "fa3-system-one-upstream"
    if upstream_credential.is_symlink() or not upstream_credential.is_file() or stat.S_IMODE(upstream_credential.stat().st_mode) not in {0o400, 0o600}:
        raise NativeAdmissionDenied("native upstream credential projection missing")
    port = urlparse(bridge_api_base).port
    ticks = _native_process_proof(bridge_pid, port, designation, designated["upstream"])
    model = designated["approved_models"][0]
    served, request_id = _probe(
        bridge_api_base.rstrip("/"), token, model,
        designated.get("served_model_aliases", {}).get(model, []),
    )
    record = {
        "schema": SCHEMA, "provider_id": NATIVE_PROVIDER_ID, "status": "PASS", "result": "PASS",
        "evidence_level": "CURRENT_HOST_REAL_NATIVE_PROVIDER",
        "protocol": "SYSTEM_ONE_DECISIONS_V1",
        "api_base": bridge_api_base.rstrip("/"),
        "real_upstream_response": True, "invalid_bearer_rejected": True,
        "secret_broker_admission_verified": True,
        "secret_broker_reference_sha256": sha256_file(secret_broker_reference),
        "model_designation_sha256": sha256_file(designation),
        "selected_model": model, "served_model": served,
        "upstream_request_id_sha256": hashlib.sha256(request_id.encode()).hexdigest() if request_id else None,
        "real_execution": True, "synthetic": False,
        "runtime_handoff": {
            "preserved": True, "server_cpu_only": True,
            "accelerator_visibility": "BLOCKED_FOR_SERVER_LIFETIME",
            "api_base": bridge_api_base.rstrip("/"),
            "process_id": bridge_pid, "process_start_ticks": ticks,
        },
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "global_promotion_claim": False, "provider_promotion_only": True,
    }
    _atomic(output, record)
    if runtime_output is not None:
        rows = []
        if runtime_registry is not None:
            old = json.loads(runtime_registry.read_text(encoding="utf-8"))
            if old.get("schema") != "fa3.model-router-runtime-providers.v1":
                raise NativeAdmissionDenied("runtime registry schema mismatch")
            rows = old.get("providers", [])
            if not isinstance(rows, list):
                raise NativeAdmissionDenied("runtime provider registry is invalid")
            rows = [row for row in rows if row.get("provider_id") != NATIVE_PROVIDER_ID]
        rows.append({
            "provider_id": NATIVE_PROVIDER_ID, "runtime_id": f"system-one-native-{bridge_pid}",
            "api_base": bridge_api_base.rstrip("/"), "catalog_api_base": bridge_api_base.rstrip("/"),
            "admission_api_base": bridge_api_base.rstrip("/"), "enabled": True, "priority": 50,
            "routes": ["fa3-decision-system-one"], "runtime_apis": ["SYSTEM_ONE_DECISIONS_V1"],
            "approved_models": designated["approved_models"],
            "model_designation_receipt": str(designation.resolve()),
            "native_bridge_auth_env": "FA3_SYSTEM_ONE_BRIDGE_TOKEN",
            "api_key_env": "FA3_SYSTEM_ONE_BRIDGE_TOKEN",
            "admission_receipt": str(output.resolve()),
            "selection_origin": "EXPLICIT_NATIVE_CURRENT_HOST_ADMISSION",
            "runtime_instance_bound": True,
        })
        _atomic(runtime_output, {
            "schema": "fa3.model-router-runtime-providers.v1",
            "authority": AUTHORITY, "provider_neutral": True,
            "physical_model_pins": False, "generated": True, "providers": rows,
        })
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--designation", type=Path, required=True)
    ap.add_argument("--bridge-api-base", required=True)
    ap.add_argument("--bridge-pid", type=int, required=True)
    ap.add_argument("--secret-broker-reference", type=Path,
                    default=Path("evidence/reference/secret-broker-current-host-2026-09-24.json"))
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--runtime-registry", type=Path)
    ap.add_argument("--runtime-output", type=Path)
    args = ap.parse_args()
    root = args.root.resolve()
    broker_ref = args.secret_broker_reference
    if not broker_ref.is_absolute():
        broker_ref = root / broker_ref
    result = admit(root=root, designation=args.designation.resolve(), bridge_api_base=args.bridge_api_base,
                   bridge_pid=args.bridge_pid, secret_broker_reference=broker_ref,
                   output=args.output.resolve(), runtime_registry=args.runtime_registry,
                   runtime_output=args.runtime_output)
    print(json.dumps({
        "schema": SCHEMA, "result": result["result"], "provider_id": result["provider_id"],
        "selected_model": result["selected_model"],
        "receipt_path": str(args.output.resolve()),
        "runtime_registry_path": str(args.runtime_output.resolve()) if args.runtime_output else None,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
