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


def _loopback_base(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "http" and (parsed.hostname or "").lower() in {"127.0.0.1", "localhost", "::1"}


def _same_origin(left: str, right: str) -> bool:
    a, b = urlparse(left), urlparse(right)
    return (
        a.scheme == b.scheme
        and (a.hostname or "").lower() == (b.hostname or "").lower()
        and a.port == b.port
    )


def runtime_handoff_endpoints(item: Any, provider_id: str) -> tuple[str, str] | None:
    if not isinstance(item, dict):
        return None
    handoff = item.get("runtime_handoff")
    if not isinstance(handoff, dict):
        return None

    openai_base = str(handoff.get("openai_api_base") or handoff.get("api_base") or "").strip().rstrip("/")
    native_base = str(handoff.get("native_api_base") or "").strip().rstrip("/")
    if not native_base and provider_id == OLLAMA_PROVIDER_ID and openai_base.endswith("/v1"):
        native_base = openai_base[:-3].rstrip("/")
    if not native_base:
        native_base = openai_base

    pid = handoff.get("process_id")
    ticks = handoff.get("process_start_ticks")
    if not (
        handoff.get("preserved") is True
        and handoff.get("server_cpu_only") is True
        and handoff.get("accelerator_visibility") == "BLOCKED_FOR_SERVER_LIFETIME"
        and openai_base
        and native_base
        and _loopback_base(openai_base)
        and _loopback_base(native_base)
        and _same_origin(openai_base, native_base)
        and isinstance(pid, int) and pid > 0
        and isinstance(ticks, int) and ticks > 0
        and process_start_ticks(pid) == ticks
    ):
        return None
    return openai_base, native_base


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
    runtime_api_base: str,
    catalog_api_base: str,
    receipt: Path,
    *,
    litellm_provider: str,
    litellm_options: dict[str, Any],
    preferred_model: str | None = None,
) -> dict[str, Any]:
    row = {
        "provider_id": provider_id,
        "runtime_id": runtime_id,
        "api_base": runtime_api_base.rstrip("/"),
        "catalog_api_base": catalog_api_base.rstrip("/"),
        "enabled": True,
        "priority": 50,
        "routes": ["*"],
        "litellm_provider": litellm_provider,
        "litellm_options": dict(litellm_options),
        "admission_receipt": str(receipt),
        "selection_origin": "CURRENT_HOST_ADMISSION_HANDOFF_DISCOVERY",
        "runtime_instance_bound": True,
    }
    if preferred_model:
        row["preferred_models"] = [preferred_model]
        row["model_preference_origin"] = "CURRENT_HOST_ADMISSION_EVIDENCE"
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

    # Provider-specific protocol knowledge stays in this adapter. A provider can
    # be auto-emitted only when the exact still-running process proven by the
    # current-host admission receipt supplies its endpoints.
    endpoint_candidates = [
        {
            "provider_id": LM_STUDIO_PROVIDER_ID,
            "runtime_id": "lm-studio-live",
            "observed_catalog_default": os.environ.get("FA3_LM_STUDIO_API_BASE", "http://127.0.0.1:1234/v1"),
            "observed_runtime_default": os.environ.get("FA3_LM_STUDIO_API_BASE", "http://127.0.0.1:1234/v1"),
            "litellm_provider": "openai",
            "litellm_options": {},
        },
        {
            "provider_id": OLLAMA_PROVIDER_ID,
            "runtime_id": "ollama-live",
            "observed_catalog_default": os.environ.get("FA3_OLLAMA_OPENAI_API_BASE", "http://127.0.0.1:11434/v1"),
            "observed_runtime_default": os.environ.get("FA3_OLLAMA_API_BASE", "http://127.0.0.1:11434"),
            "litellm_provider": "ollama_chat",
            "litellm_options": {"num_gpu": 0, "num_ctx": 512},
        },
    ]

    rows: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    for descriptor in endpoint_candidates:
        provider_id = str(descriptor["provider_id"])
        runtime_id = str(descriptor["runtime_id"])
        item = providers.get(provider_id)
        admitted = isinstance(item, dict) and item.get("status") == "PASS"
        endpoints = runtime_handoff_endpoints(item, provider_id) if admitted else None
        instance_bound = endpoints is not None
        if endpoints is not None:
            catalog_api_base, runtime_api_base = endpoints
        else:
            catalog_api_base = str(descriptor["observed_catalog_default"]).rstrip("/")
            runtime_api_base = str(descriptor["observed_runtime_default"]).rstrip("/")
        live = bool(admitted and instance_bound and models_live(catalog_api_base, timeout))
        observed.append({
            "provider_id": provider_id,
            "runtime_id": runtime_id,
            "catalog_api_base": catalog_api_base,
            "api_base": runtime_api_base,
            "admitted": admitted,
            "runtime_instance_bound": instance_bound,
            "live_openai_models_endpoint": live,
        })
        if not live:
            continue

        preferred_model = ""
        if provider_id == OLLAMA_PROVIDER_ID:
            preferred_model = str(item.get("selected_model") or "").strip()
        elif provider_id == LM_STUDIO_PROVIDER_ID:
            preferred_model = str(item.get("selected_model_key") or "").strip()
        rows.append(candidate(
            provider_id,
            runtime_id,
            runtime_api_base,
            catalog_api_base,
            receipt,
            litellm_provider=str(descriptor["litellm_provider"]),
            litellm_options=dict(descriptor["litellm_options"]),
            preferred_model=preferred_model or None,
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
