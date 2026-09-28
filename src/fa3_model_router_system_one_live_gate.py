#!/usr/bin/env python3
"""Physical native System One Model Router -> LiteLLM -> admitted provider E2E gate.

This is a separate, optional post-admission proof. Repository/static/current-host
boundary tests never produce this receipt. Probe failures leave the provider disabled.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from fa3_model_router_materialize import AUTHORITY, sha256_file
from fa3_model_router_system_one_admit import http_probe
from fa3_model_router_system_one_transport import (
    NativeRouterTransport, RouterNativeDenied, _read_protected,
)

SCHEMA = "fa3.system-one-router-e2e-current-host.v1"
ROUTE = "fa3-decision-system-one"


class NativeRouterE2EDenied(RuntimeError):
    pass


def verify_live_router(
    *, root: Path, selection: Path, native_admission: Path, origin: str, master_key: str,
    http: Callable[[str, str, str, dict[str, Any] | None], tuple[int, dict[str, Any]]] = http_probe,
) -> dict[str, Any]:
    if not master_key:
        raise NativeRouterE2EDenied("broker-projected LiteLLM credential missing")
    rec = _read_protected(selection)
    native = _read_protected(native_admission)
    if not (
        native.get("schema") == "fa3.system-one-native-current-host-receipt.v1"
        and native.get("result") == "PASS"
        and native.get("real_upstream_response") is True
        and native.get("invalid_bearer_rejected") is True
        and native.get("secret_broker_admission_verified") is True
    ):
        raise NativeRouterE2EDenied("no admitted real native provider proof")
    transport = NativeRouterTransport(
        selection_receipt=selection, route_registry=root / "deployment/model-router/routes.json",
        router_origin=origin, master_key=master_key,
    )
    _, binding = transport.binding()
    if not (
        binding.get("provider_id") == native.get("provider_id")
        and binding.get("model") == native.get("selected_model")
        and str(binding.get("api_base", "")).rstrip("/") == str(native.get("api_base", "")).rstrip("/")
        and rec.get("admission_receipt_sha256", {}).get(binding["provider_id"]) == sha256_file(native_admission)
    ):
        raise NativeRouterE2EDenied("LiteLLM binding is not the exact admitted native instance")
    questions = {
        "e2e_noop_choice": {
            "type": "choice",
            "instructions": "Non-executing, low-risk router end-to-end probe.",
            "criteria": {"observe": "Observe only", "handoff": "Request human review"},
        }
    }
    payload = {"model": binding["model"], "state": {"probe": "no_action"},
               "questions": questions}
    endpoint = origin.rstrip("/") + "/fa3/system-one/decisions"
    for bad_key in ("FA3_INTENTIONALLY_WRONG_MASTER", ""):
        status, _ = http(endpoint, "POST", bad_key, payload)
        if status not in {401, 403}:
            raise NativeRouterE2EDenied("LiteLLM native pass-through did not enforce central client authentication")
    status, raw = http(endpoint, "POST", master_key, payload)
    if status != 200 or not isinstance(raw, dict):
        raise NativeRouterE2EDenied("LiteLLM native end-to-end response failed")
    if raw.get("model") != native.get("served_model"):
        raise NativeRouterE2EDenied("native E2E served model differs from exact admitted provider proof")
    answers = raw.get("answers")
    one = answers.get("e2e_noop_choice") if isinstance(answers, dict) else None
    probs = one.get("probabilities") if isinstance(one, dict) else None
    if not (
        isinstance(answers, dict) and set(answers) == set(questions)
        and isinstance(one, dict)
        and one.get("choice") in questions["e2e_noop_choice"]["criteria"]
        and isinstance(probs, dict) and set(probs) == set(questions["e2e_noop_choice"]["criteria"])
        and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(v) and 0 <= v <= 1 for v in probs.values())
        and abs(sum(probs.values()) - 1) < 0.05
    ):
        raise NativeRouterE2EDenied("LiteLLM path lost or fabricated native probability distribution")
    try:
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        raise NativeRouterE2EDenied("current checkout HEAD unavailable") from None
    return {
        "schema": SCHEMA,
        "result": "PASS",
        "status": "CURRENT_HOST_NATIVE_LITELLM_PASS",
        "authority": AUTHORITY,
        "logical_route": ROUTE,
        "data_plane": "LITELLM_AUTHENTICATED_PASS_THROUGH",
        "native_provider_id": binding["provider_id"],
        "selection_receipt_sha256": sha256_file(selection),
        "native_admission_sha256": sha256_file(native_admission),
        "router_origin": origin,
        "repository_head": head,
        "invalid_and_missing_master_key_rejected": True,
        "native_probability_distribution_preserved": True,
        "real_native_provider_request": True,
        "execution_performed": False,
        "confidence_is_authorization": False,
        "global_promotion_claim": False,
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def _atomic(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".fa3-native-router-e2e-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--native-admission", type=Path, required=True)
    ap.add_argument("--router-origin", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if os.environ.get("FA3_SYSTEM_ONE_LIVE_ROUTER_ENABLE") != "1":
        raise SystemExit("explicit native LiteLLM E2E enablement is required")
    key = os.environ.get("FA3_MODEL_ROUTER_MASTER_KEY", "")
    result = verify_live_router(
        root=args.root.resolve(), selection=args.selection,
        native_admission=args.native_admission, origin=args.router_origin,
        master_key=key,
    )
    _atomic(args.output, result)
    print(json.dumps({"result": result["result"], "schema": SCHEMA,
                      "receipt_path": str(args.output.resolve()),
                      "repository_head": result["repository_head"],
                      "global_promotion_claim": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
