#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

LM_STUDIO_PROVIDER_ID = "FA3-PROVIDER-LM-STUDIO-MODEL-001"
OLLAMA_PROVIDER_ID = "FA3-PROVIDER-OLLAMA-MODEL-001"
RECEIPT_REL = "evidence/receipts/model-manager-current-host.json"


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    path.chmod(0o600)


def process_start_ticks(pid: int) -> int | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        tail = raw[raw.rfind(")") + 2:].split()
        return int(tail[19]) if len(tail) >= 20 else None
    except Exception:
        return None


def runtime_handoff_endpoint(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    handoff = item.get("runtime_handoff")
    if not isinstance(handoff, dict):
        return None
    api_base = str(handoff.get("api_base") or "").strip().rstrip("/")
    parsed = urlparse(api_base)
    pid = handoff.get("process_id")
    ticks = handoff.get("process_start_ticks")
    if not (
        handoff.get("preserved") is True
        and handoff.get("server_cpu_only") is True
        and handoff.get("accelerator_visibility") == "BLOCKED_FOR_SERVER_LIFETIME"
        and parsed.scheme == "http"
        and (parsed.hostname or "").lower() in {"127.0.0.1", "localhost", "::1"}
        and isinstance(pid, int) and pid > 0
        and isinstance(ticks, int) and ticks > 0
        and process_start_ticks(pid) == ticks
    ):
        return None
    return api_base


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


def candidate(
    provider_id: str,
    runtime_id: str,
    api_base: str,
    receipt: Path,
    *,
    catalog_api_base: str,
    admission_api_base: str,
    litellm_provider: str,
    preferred_model: str | None = None,
    litellm_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "provider_id": provider_id,
        "runtime_id": runtime_id,
        "api_base": api_base.rstrip("/"),
        "catalog_api_base": catalog_api_base.rstrip("/"),
        "admission_api_base": admission_api_base.rstrip("/"),
        "enabled": True,
        "priority": 50,
        "routes": ["*"],
        "litellm_provider": litellm_provider,
        "admission_receipt": str(receipt),
        "selection_origin": "CURRENT_HOST_ADMISSION_HANDOFF_DISCOVERY",
        "runtime_instance_bound": True,
    }
    if preferred_model:
        row["preferred_models"] = [preferred_model]
        row["model_preference_origin"] = "CURRENT_HOST_ADMISSION_EVIDENCE"
    if litellm_options:
        row["litellm_options"] = dict(litellm_options)
    return row


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
        {
            "provider_id": LM_STUDIO_PROVIDER_ID,
            "runtime_id": "lm-studio-live",
            "litellm_provider": "openai",
            "litellm_options": {},
        },
        {
            "provider_id": OLLAMA_PROVIDER_ID,
            "runtime_id": "ollama-live",
            "litellm_provider": "ollama_chat",
            "litellm_options": {"num_gpu": 0, "num_ctx": 512},
        },
    ]

    rows: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    for endpoint in endpoint_candidates:
        provider_id = str(endpoint["provider_id"])
        runtime_id = str(endpoint["runtime_id"])
        item = providers.get(provider_id)
        admitted = isinstance(item, dict) and item.get("status") == "PASS"
        handoff_api_base = runtime_handoff_endpoint(item) if admitted else None
        instance_bound = handoff_api_base is not None
        catalog_api_base = handoff_api_base or ""
        runtime_api_base = catalog_api_base
        if provider_id == OLLAMA_PROVIDER_ID and catalog_api_base.endswith("/v1"):
            runtime_api_base = catalog_api_base[:-3]
        live = bool(admitted and instance_bound and models_live(catalog_api_base, timeout))
        observed.append({
            "provider_id": provider_id,
            "runtime_id": runtime_id,
            "catalog_api_base": catalog_api_base,
            "runtime_api_base": runtime_api_base,
            "admitted": admitted,
            "runtime_instance_bound": instance_bound,
            "live_openai_models_endpoint": live,
        })
        if live:
            preferred_model = ""
            if isinstance(item, dict):
                if provider_id == OLLAMA_PROVIDER_ID:
                    preferred_model = str(item.get("selected_model") or "").strip()
                elif provider_id == LM_STUDIO_PROVIDER_ID:
                    preferred_model = str(item.get("selected_model_key") or "").strip()
            rows.append(candidate(
                provider_id,
                runtime_id,
                runtime_api_base,
                receipt,
                catalog_api_base=catalog_api_base,
                admission_api_base=catalog_api_base,
                litellm_provider=str(endpoint["litellm_provider"]),
                preferred_model=preferred_model or None,
                litellm_options=endpoint.get("litellm_options") if isinstance(endpoint.get("litellm_options"), dict) else None,
            ))

    if not rows:
        raise RuntimeError(
            "no admitted, runtime-instance-bound, live OpenAI-compatible local provider endpoint discovered; "
            "supply --providers/FA3_MODEL_ROUTER_PROVIDERS for another instance-bound admitted runtime"
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
