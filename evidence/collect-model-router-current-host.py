#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_model_router_runtime import AUTHORITY_ID, materialize  # noqa: E402

RECEIPT_SCHEMA = "fa3.model-router.current-host-receipt.v1"
GATE_ID = "FA3-MODEL-ROUTER-CURRENT-HOST-GATESET-001"
DEFAULT_ROUTES = ("fa3-pageindex-index", "fa3-pageindex-reason")


class EvidenceDenied(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(method: str, url: str, token: str, body: dict[str, Any] | None = None, timeout: float = 60.0) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise EvidenceDenied(f"LiteLLM HTTP {exc.code}: {detail[:512]}") from exc
    except urllib.error.URLError as exc:
        raise EvidenceDenied(f"LiteLLM request failed: {exc.reason}") from exc
    try:
        out = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise EvidenceDenied("LiteLLM returned invalid JSON") from exc
    if not isinstance(out, dict):
        raise EvidenceDenied("LiteLLM returned non-object JSON")
    return out


def wait_ready(base: str, token: str, timeout: float = 120.0) -> list[str]:
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            obj = request_json("GET", base + "/v1/models", token, timeout=5)
            rows = obj.get("data")
            if isinstance(rows, list):
                return sorted(str(x.get("id")) for x in rows if isinstance(x, dict) and str(x.get("id", "")).strip())
        except Exception as exc:
            last = exc
        time.sleep(0.5)
    raise EvidenceDenied(f"LiteLLM readiness timeout: {last}")


def run_route(base: str, token: str, route: str, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    obj = request_json(
        "POST",
        base + "/v1/chat/completions",
        token,
        {
            "model": route,
            "temperature": 0,
            "max_tokens": 32,
            "messages": [
                {"role": "system", "content": "Return a short harmless conformance response."},
                {"role": "user", "content": "FA3 Model Router current-host transport conformance."},
            ],
        },
        timeout=timeout,
    )
    latency_ms = round((time.monotonic() - started) * 1000.0, 3)
    choices = obj.get("choices")
    if not isinstance(choices, list) or not choices:
        raise EvidenceDenied(f"route {route} returned no choices")
    first = choices[0] if isinstance(choices[0], dict) else {}
    msg = first.get("message", {}) if isinstance(first, dict) else {}
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise EvidenceDenied(f"route {route} returned empty content")
    return {
        "route": route,
        "status": "PASS",
        "response_model": str(obj.get("model", "")),
        "response_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "response_bytes": len(content.encode("utf-8")),
        "latency_ms": latency_ms,
    }


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "UNKNOWN"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=os.environ.get("FA3_MODEL_ROUTER_PROVIDER_CATALOG", ""))
    ap.add_argument("--litellm-bin", default=os.environ.get("FA3_LITELLM_BIN", "litellm"))
    ap.add_argument("--output", default="evidence/receipts/model-router-current-host.json")
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--route", action="append", dest="routes")
    args = ap.parse_args()

    if platform.system() != "Linux":
        raise SystemExit("current-host Model Router evidence requires Linux")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise SystemExit("current-host Model Router evidence must not run as root")
    if not args.catalog:
        raise SystemExit("FA3_MODEL_ROUTER_PROVIDER_CATALOG or --catalog is required; the router must not invent a provider/model")

    catalog = Path(args.catalog).expanduser().resolve()
    if not catalog.is_file():
        raise SystemExit(f"provider catalog missing: {catalog}")
    routes_file = ROOT / "deployment/model-router/routes.json"
    requested_routes = tuple(args.routes or DEFAULT_ROUTES)

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime = ROOT / "evidence/runtime/model-router-current-host" / stamp
    runtime.mkdir(parents=True, exist_ok=True)
    config = runtime / "litellm.generated.yaml"
    resolution_file = runtime / "resolution.json"
    resolution = materialize(catalog, routes_file, config, resolution_file)
    by_route = {x["route"]: x for x in resolution["routes"]}
    missing = [r for r in requested_routes if r not in by_route]
    if missing:
        raise SystemExit("requested routes missing from runtime resolution: " + ",".join(missing))

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    token = "sk-fa3-" + secrets.token_urlsafe(32)
    env = os.environ.copy()
    env["FA3_LITELLM_MASTER_KEY"] = token
    log = (runtime / "litellm.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [args.litellm_bin, "--config", str(config), "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "gate_id": GATE_ID,
        "authority": AUTHORITY_ID,
        "result": "FAIL",
        "provider_neutral": True,
        "endpoint": base,
        "logical_routes": list(requested_routes),
        "physical_backend_pinned": False,
        "physical_model_pinned": False,
        "selection_source": "CURRENT_HOST_PROVIDER_CATALOG",
        "repository_head": git_head(),
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "host": {"system": platform.system(), "machine": platform.machine(), "release": platform.release()},
        "catalog_sha256": sha256(catalog),
        "routes_sha256": sha256(routes_file),
        "generated_config_sha256": sha256(config),
        "resolution_sha256": sha256(resolution_file),
        "route_resolutions": {r: by_route[r] for r in requested_routes},
        "global_promotion_claim": False,
    }
    out = ROOT / args.output
    try:
        models = wait_ready(base, token)
        if not set(requested_routes).issubset(set(models)):
            raise EvidenceDenied("LiteLLM /v1/models does not expose all requested logical routes")
        executions = [run_route(base, token, r, args.timeout) for r in requested_routes]
        receipt["executions"] = executions
        reason_resolution = by_route[requested_routes[-1]]
        receipt["executed_backend"] = reason_resolution["provider_id"]
        receipt["executed_runtime"] = reason_resolution["runtime"]
        receipt["executed_model"] = reason_resolution["model_id"]
        receipt["result"] = "PASS"
        receipt["evidence_level"] = "CURRENT_HOST_MODEL_ROUTER_E2E_PASS"
        receipt["checks"] = {
            "authority_bound": True,
            "provider_catalog_dynamic": True,
            "logical_routes_exposed": True,
            "physical_backend_not_canonical_pinned": True,
            "physical_model_not_canonical_pinned": True,
            "authenticated_loopback_litellm": True,
            "real_route_execution": True,
        }
    except Exception as exc:
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
    finally:
        try:
            os.killpg(proc.pid, 15)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
        try:
            proc.wait(timeout=15)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        log.close()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
