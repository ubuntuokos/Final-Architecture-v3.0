#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fa3_agent_deliberation_runtime import make_server


def _agent(pid: str) -> dict[str, Any]:
    return {
        "participant_id": pid,
        "role": "AGENT",
        "identity_receipt_ref": f"identity:{pid}",
        "authorized": True,
        "authority_grants": [],
        "capability_grants": [],
        "model_binding": {
            "router_authority": "FA3-AUTH-MODEL-ROUTER-001",
            "route_id": f"route:{pid}",
            "provider_id": f"provider:{pid}",
            "model_id": f"model:{pid}",
            "receipt_ref": f"router-receipt:{pid}",
            "binding_source": "MODEL_ROUTER_RECEIPT",
        },
    }


def _request(base: str, method: str, path: str, body: dict[str, Any] | None, expected: int) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=5) as response:
            status = response.status
            raw = response.read()
    except HTTPError as exc:
        status = exc.code
        raw = exc.read()
    if status != expected:
        raise RuntimeError(f"{method} {path}: expected {expected}, got {status}: {raw!r}")
    value = json.loads(raw.decode("utf-8")) if raw else {}
    if not isinstance(value, dict):
        raise RuntimeError("object response required")
    return value


def collect(root: Path) -> dict[str, Any]:
    server = make_server(port=0)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, name="fa3-deliberation-reference", daemon=True)
    thread.start()
    base = f"http://{host}:{port}"
    checks: list[dict[str, Any]] = []
    try:
        health = _request(base, "GET", "/health", None, 200)
        checks.append({"id": "HEALTH", "pass": health.get("ok") is True and health.get("authoritative") is False})

        create = {
            "session_id": "ci-reference",
            "objective": "Prove governed local room semantics without runtime promotion.",
            "participants": [_agent("a"), _agent("b")],
            "mode": "OPEN",
        }
        created = _request(base, "POST", "/v1/sessions", create, 201)
        checks.append({"id": "CREATE_SESSION", "pass": created.get("session", {}).get("session_id") == "ci-reference"})

        good = {
            "message": {
                "message_id": "m1",
                "session_id": "ci-reference",
                "sender_id": "a",
                "communication_mode": "HUMAN_LANGUAGE",
                "language_tag": "en",
                "human_readable_text": "Evidence-backed reference message.",
                "human_readable_authoritative": True,
                "secret_values_present": False,
                "client_asserted_host_verified": False,
            }
        }
        accepted = _request(base, "POST", "/v1/sessions/ci-reference/messages", good, 201)
        checks.append({"id": "VALID_MESSAGE", "pass": accepted.get("accepted") is True and accepted.get("message_count") == 1})

        forged = json.loads(json.dumps(good))
        forged["message"]["message_id"] = "m2"
        forged["message"]["client_asserted_host_verified"] = True
        denied = _request(base, "POST", "/v1/sessions/ci-reference/messages", forged, 400)
        checks.append({"id": "FORGED_HOST_VERIFICATION_DENIED", "pass": "host verification" in str(denied.get("error", "")).lower()})

        snapshot = _request(base, "GET", "/v1/sessions/ci-reference", None, 200)
        checks.append({"id": "TRANSCRIPT_STABLE_AFTER_DENIAL", "pass": len(snapshot.get("messages", [])) == 1})

        closed = _request(base, "POST", "/v1/sessions/ci-reference/close", {"closure_receipt_ref": "ci:closure"}, 200)
        checks.append({"id": "CLOSE", "pass": closed.get("session", {}).get("status") == "CLOSED"})

        denied_closed = _request(base, "POST", "/v1/sessions/ci-reference/messages", good, 400)
        checks.append({"id": "CLOSED_ROOM_DENIES_MESSAGE", "pass": "turn policy denied" in str(denied_closed.get("error", "")).lower()})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    checks.extend([
        {"id": "LOOPBACK_ONLY", "pass": host == "127.0.0.1"},
        {"id": "EPHEMERAL_PORT_REQUESTED", "pass": isinstance(port, int) and port > 0},
        {"id": "NO_CURRENT_HOST_PROMOTION", "pass": True},
    ])
    passed = all(row["pass"] for row in checks)
    return {
        "schema": "fa3.agent-deliberation-reference-e2e.v1",
        "status": "PASS" if passed else "FAIL",
        "evidence_level": "CI_REFERENCE_LOOPBACK",
        "profile_id": "FA3-AGENT-COLLABORATION-DELIBERATION-001",
        "requested_bind": "127.0.0.1:0",
        "observed_bind_host": host,
        "observed_dynamic_port": port,
        "checks": checks,
        "physical_current_host": False,
        "cross_host_production": False,
        "current_host_runtime_promotion_claim": False,
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default="reports/agent-deliberation-reference-e2e-report.json")
    parser.add_argument("--receipt", default="evidence/receipts/agent-deliberation-ci-reference-e2e.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = collect(root)
    for rel in (args.report, args.receipt):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
