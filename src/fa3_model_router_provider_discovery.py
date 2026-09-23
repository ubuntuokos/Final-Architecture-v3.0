#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

LM_STUDIO_PROVIDER_ID = "FA3-PROVIDER-LM-STUDIO-MODEL-001"
OLLAMA_PROVIDER_ID = "FA3-PROVIDER-OLLAMA-MODEL-001"
RECEIPT_REL = "evidence/receipts/model-manager-current-host.json"


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    path.chmod(0o600)


def models_live(api_base: str, timeout: float) -> bool:
    url = api_base.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"User-Agent": "FA3-Model-Router-Discovery/1"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            body = json.loads(resp.read(4 * 1024 * 1024).decode("utf-8"))
        rows = body.get("data") if isinstance(body, dict) else None
        return isinstance(rows, list) and any(isinstance(x, dict) and str(x.get("id", "")).strip() for x in rows)
    except Exception:
        return False


def candidate(provider_id: str, runtime_id: str, api_base: str, receipt: Path) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "runtime_id": runtime_id,
        "api_base": api_base.rstrip("/"),
        "enabled": True,
        "priority": 50,
        "routes": ["*"],
        "litellm_provider": "openai",
        "admission_receipt": str(receipt),
        "selection_origin": "CURRENT_HOST_LIVE_ENDPOINT_DISCOVERY",
    }


def discover(root: Path, output: Path, timeout: float) -> dict[str, Any]:
    root = root.resolve()
    receipt = (root / RECEIPT_REL).resolve()
    rec = loadj(receipt)
    if rec.get("status") != "PASS":
        raise RuntimeError("Model Manager current-host receipt is not PASS")
    providers = rec.get("providers")
    if not isinstance(providers, dict):
        raise RuntimeError("Model Manager current-host provider evidence missing")

    # Provider-specific endpoint knowledge lives only in this adapter.
    # The central router consumes the generated generic registry and does not
    # encode an Ollama/LM Studio preference or model pin.
    endpoint_candidates = [
        (
            LM_STUDIO_PROVIDER_ID,
            "lm-studio-live",
            os.environ.get("FA3_LM_STUDIO_API_BASE", "http://127.0.0.1:1234/v1"),
        ),
        (
            OLLAMA_PROVIDER_ID,
            "ollama-live",
            os.environ.get("FA3_OLLAMA_API_BASE", "http://127.0.0.1:11434/v1"),
        ),
    ]

    rows: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    for provider_id, runtime_id, api_base in endpoint_candidates:
        item = providers.get(provider_id)
        admitted = isinstance(item, dict) and item.get("status") == "PASS"
        live = bool(admitted and models_live(api_base, timeout))
        observed.append({
            "provider_id": provider_id,
            "runtime_id": runtime_id,
            "api_base": api_base,
            "admitted": admitted,
            "live_openai_models_endpoint": live,
        })
        if live:
            rows.append(candidate(provider_id, runtime_id, api_base, receipt))

    if not rows:
        raise RuntimeError(
            "no admitted live OpenAI-compatible local provider endpoint discovered; "
            "supply --providers/FA3_MODEL_ROUTER_PROVIDERS for another admitted runtime"
        )

    registry = {
        "schema": "fa3.model-router-runtime-providers.v1",
        "authority": "FA3-AUTH-MODEL-ROUTER-001",
        "generated": True,
        "provider_neutral": True,
        "physical_model_pins": False,
        "providers": rows,
        "observed_candidates": observed,
    }
    writej(output, registry)
    return registry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--output", required=True)
    ap.add_argument("--timeout", type=float, default=3.0)
    args = ap.parse_args()
    result = discover(Path(args.root), Path(args.output).expanduser().resolve(), args.timeout)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
