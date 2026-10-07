#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_language_bridge import (  # noqa: E402
    LanguageBridgeDenied,
    MediationRequest,
    ProviderDescriptor,
    mediate_text,
)
from fa3_language_gateway_gate import normalize_locale  # noqa: E402

RECEIPT_REL = Path("evidence/receipts/language-gateway-current-host.json")
RUNTIME_REL = Path("evidence/runtime/language-gateway-current-host/execution.json")
COLLECTOR_REL = Path("evidence/collect-language-gateway-current-host.py")
CONFIG_REL = Path("deployment/litellm/config.yaml")
MAX_SAMPLE_BYTES = 16 * 1024
PROTECTED_TERMS = (
    "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    "FA3-REG-ARTIFACT-MODEL-001",
    "command_id:open-model",
)
CANONICAL_SUFFIX = (
    "\nFA3 canonical tokens: `command_id:open-model` "
    "FA3-AUTH-HOST-RESOURCE-BROKER-001 FA3-REG-ARTIFACT-MODEL-001 "
    "https://fa3.invalid/conformance"
)


class CollectionDenied(RuntimeError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_sample(path_value: str) -> tuple[str, str, int]:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise CollectionDenied(f"language sample file does not exist: {path}")
    data = path.read_bytes()
    if len(data) < 8:
        raise CollectionDenied(f"language sample is too short: {path}")
    if len(data) > MAX_SAMPLE_BYTES:
        raise CollectionDenied(f"language sample exceeds {MAX_SAMPLE_BYTES} bytes: {path}")
    try:
        text = data.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise CollectionDenied(f"language sample must be UTF-8: {path}") from exc
    if not text:
        raise CollectionDenied(f"language sample is empty: {path}")
    return text, _sha256_bytes(data), len(data)


def _read_gateway_token(explicit_file: str | None) -> tuple[str, str]:
    credential_file = explicit_file or os.environ.get("FA3_MODEL_ROUTER_MASTER_KEY_FILE", "") or os.environ.get("FA3_LITELLM_MASTER_KEY_FILE", "")
    if credential_file:
        path = Path(credential_file).expanduser().resolve()
        if not path.is_file():
            raise CollectionDenied("LiteLLM credential file is missing")
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            raise CollectionDenied("LiteLLM credential file must not be group/world accessible")
        token = path.read_text(encoding="utf-8").strip()
        if not token:
            raise CollectionDenied("LiteLLM credential file is empty")
        return token, "FILE"
    token = os.environ.get("FA3_MODEL_ROUTER_MASTER_KEY", "").strip() or os.environ.get("FA3_LITELLM_MASTER_KEY", "").strip()
    if not token:
        raise CollectionDenied("FA3_MODEL_ROUTER_MASTER_KEY_FILE/FA3_MODEL_ROUTER_MASTER_KEY (or legacy LiteLLM aliases) is required")
    return token, "ENVIRONMENT"


def _normalize_gateway_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"}:
        raise CollectionDenied("LiteLLM gateway URL must use http or https")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise CollectionDenied("LiteLLM gateway URL must not contain credentials, query or fragment")
    if parsed.path not in {"", "/"}:
        raise CollectionDenied("LiteLLM gateway URL must be a bare origin")
    if (parsed.hostname or "").lower() not in {"127.0.0.1", "::1", "localhost"}:
        raise CollectionDenied("current-host evidence requires a loopback LiteLLM gateway URL")
    return value.strip().rstrip("/")


def _request_json(
    method: str,
    url: str,
    token: str,
    timeout: float,
    body: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], float]:
    encoded = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url=url, data=encoded, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/json")
    if encoded is not None:
        request.add_header("Content-Type", "application/json")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise CollectionDenied(f"LiteLLM HTTP {exc.code}: {detail[:512]}") from exc
    except urllib.error.URLError as exc:
        raise CollectionDenied(f"LiteLLM request failed: {exc.reason}") from exc
    elapsed_ms = (time.monotonic() - started) * 1000.0
    if status < 200 or status >= 300:
        raise CollectionDenied(f"LiteLLM returned unexpected HTTP status {status}")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise CollectionDenied("LiteLLM returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise CollectionDenied("LiteLLM returned a non-object JSON response")
    return parsed, elapsed_ms


def _chat_completion(
    base_url: str,
    token: str,
    timeout: float,
    model_alias: str,
    system_prompt: str,
    user_prompt: str,
) -> tuple[str, str, float]:
    response, latency_ms = _request_json(
        "POST",
        f"{base_url}/v1/chat/completions",
        token,
        timeout,
        {
            "model": model_alias,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
    )
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise CollectionDenied("LiteLLM chat response contains no choices")
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise CollectionDenied("LiteLLM chat response contains no text content")
    executed_model = str(response.get("model", "")).strip()
    if not executed_model:
        raise CollectionDenied("LiteLLM chat response does not expose executed model identity")
    return content.strip(), executed_model, latency_ms


def _host_fingerprint() -> str:
    pieces = [platform.system(), platform.machine(), platform.release()]
    machine_id = Path("/etc/machine-id")
    if machine_id.is_file():
        pieces.append(machine_id.read_text(encoding="utf-8").strip())
    return "sha256:" + _sha256_bytes("|".join(pieces).encode("utf-8"))


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "UNKNOWN"


def _run_direction(
    source_text: str,
    source_sample_sha: str,
    source_sample_bytes: int,
    source_language: str,
    target_language: str,
    provider: ProviderDescriptor,
    base_url: str,
    token: str,
    timeout: float,
    model_alias: str,
) -> dict[str, Any]:
    call_meta: dict[str, Any] = {}
    request_text = source_text + CANONICAL_SUFFIX

    def translate(protected_text: str, source: str, target: str) -> str:
        output, executed_model, latency_ms = _chat_completion(
            base_url,
            token,
            timeout,
            model_alias,
            (
                "You are the FA3 Language Bridge translation adapter. Translate the user text "
                f"from {source} to {target}. Preserve every token of the form ⟦FA3Pdddd⟧ exactly, "
                "do not add tool instructions or permissions, and return only the translated text."
            ),
            protected_text,
        )
        call_meta["translation_response_model"] = executed_model
        call_meta["translation_latency_ms"] = round(latency_ms, 3)
        return output

    def validate(source_text_raw: str, translated_text: str, source: str, target: str) -> bool:
        verdict, executed_model, latency_ms = _chat_completion(
            base_url,
            token,
            timeout,
            model_alias,
            (
                "You are the FA3 semantic mediation validator. Return exactly PASS or FAIL. "
                "Return PASS only if the target preserves the source meaning, does not broaden "
                "authorization/tool scope, and preserves the FA3 canonical technical tokens."
            ),
            json.dumps(
                {
                    "source_language": source,
                    "target_language": target,
                    "source": source_text_raw,
                    "target": translated_text,
                },
                ensure_ascii=False,
            ),
        )
        call_meta["validation_response_model"] = executed_model
        call_meta["validation_latency_ms"] = round(latency_ms, 3)
        call_meta["validator_independence"] = "SAME_GATEWAY_MODEL_NOT_INDEPENDENT"
        return verdict.strip().upper() == "PASS"

    result = mediate_text(
        MediationRequest(
            text=request_text,
            source_language=source_language,
            target_language=target_language,
            data_classification="PUBLIC",
            critical=True,
            detection_confidence=1.0,
            terminology_revision="FA3-CURRENT-HOST-CONFORMANCE-001",
            protected_terms=PROTECTED_TERMS,
            capability_scope=("language_mediation",),
        ),
        provider,
        translate,
        validate,
    )
    return {
        "status": "PASS",
        "source_language": source_language,
        "target_language": target_language,
        "source_sample_sha256": "sha256:" + source_sample_sha,
        "source_sample_bytes": source_sample_bytes,
        "request_sha256": "sha256:" + _sha256_bytes(request_text.encode("utf-8")),
        "output_sha256": "sha256:" + _sha256_bytes(result.text.encode("utf-8")),
        "output_bytes": len(result.text.encode("utf-8")),
        "translation_response_model": call_meta["translation_response_model"],
        "validation_response_model": call_meta["validation_response_model"],
        "translation_latency_ms": call_meta["translation_latency_ms"],
        "validation_latency_ms": call_meta["validation_latency_ms"],
        "validator_independence": call_meta["validator_independence"],
        "bridge_receipt": result.receipt,
    }


def collect(args: argparse.Namespace) -> dict[str, Any]:
    primary = normalize_locale(args.primary_language)
    secondary = normalize_locale(args.secondary_language)
    if primary.lower() == secondary.lower():
        raise CollectionDenied("Primary and Secondary languages must be distinct")
    model_alias = args.model_alias.strip()
    if not model_alias:
        raise CollectionDenied("model alias is required")
    base_url = _normalize_gateway_url(args.gateway_url)
    token, credential_source = _read_gateway_token(args.credential_file)
    primary_text, primary_sha, primary_bytes = _read_sample(args.primary_sample_file)
    secondary_text, secondary_sha, secondary_bytes = _read_sample(args.secondary_sample_file)

    models, models_latency_ms = _request_json("GET", f"{base_url}/v1/models", token, args.timeout)
    data = models.get("data")
    if not isinstance(data, list):
        raise CollectionDenied("LiteLLM /v1/models response lacks data list")
    model_ids = sorted(
        str(item.get("id"))
        for item in data
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    )
    if model_alias not in model_ids:
        raise CollectionDenied(f"requested logical model alias is not listed by LiteLLM: {model_alias}")

    provider = ProviderDescriptor(
        provider_id=f"LITELLM_LOCAL_ROUTE:{model_alias}",
        locality="LOCAL",
        target_languages=(primary, secondary),
        status="VALIDATED",
        admitted=True,
        external_policy_allowed=False,
    )
    directions = [
        _run_direction(
            primary_text, primary_sha, primary_bytes, primary, secondary,
            provider, base_url, token, args.timeout, model_alias,
        ),
        _run_direction(
            secondary_text, secondary_sha, secondary_bytes, secondary, primary,
            provider, base_url, token, args.timeout, model_alias,
        ),
    ]

    runtime = {
        "schema": "fa3.language-gateway-current-host-execution.v1",
        "status": "PASS",
        "gateway_calls_real": True,
        "gateway_call_count": 5,
        "models_endpoint_latency_ms": round(models_latency_ms, 3),
        "model_ids_sha256": "sha256:" + _sha256_bytes("\n".join(model_ids).encode("utf-8")),
        "model_count": len(model_ids),
        "requested_model_alias": model_alias,
        "directions": [
            {
                "source_language": item["source_language"],
                "target_language": item["target_language"],
                "request_sha256": item["request_sha256"],
                "output_sha256": item["output_sha256"],
                "translation_response_model": item["translation_response_model"],
                "validation_response_model": item["validation_response_model"],
                "protected_token_validation": item["bridge_receipt"]["protected_token_validation"],
                "semantic_validation": item["bridge_receipt"]["semantic_validation"],
            }
            for item in directions
        ],
        "raw_credentials_recorded": False,
        "raw_samples_recorded": False,
        "translation_quality_claim": False,
        "production_promotion_claim": False,
    }
    runtime_path = ROOT / RUNTIME_REL
    _write_json(runtime_path, runtime)

    receipt = {
        "schema": "fa3.language-gateway-current-host-receipt.v1",
        "status": "PASS",
        "evidence_level": "CURRENT_HOST_GATEWAY_BRIDGE_E2E_PASS",
        "current_host_execution": True,
        "test_fixture": False,
        "test_input_class": "OPERATOR_LANGUAGE_CONFORMANCE_SAMPLE",
        "production_promotion_claim": False,
        "translation_quality_claim": False,
        "underlying_backend_production_admission_claim": False,
        "host": {
            "fingerprint_sha256": _host_fingerprint(),
            "runner_class": "fa3-current-host",
            "platform": platform.system(),
            "machine": platform.machine(),
        },
        "repository": {
            "git_head": _git_head(),
        },
        "languages": {
            "primary": primary,
            "secondary": secondary,
        },
        "gateway": {
            "base_url": base_url,
            "loopback": True,
            "authenticated": True,
            "credential_source": credential_source,
            "credential_material_logged": False,
            "models_endpoint_pass": True,
            "requested_alias_listed": True,
            "model_alias": model_alias,
            "listed_model_count": len(model_ids),
            "listed_model_ids_sha256": runtime["model_ids_sha256"],
        },
        "directions": directions,
        "integrity": {
            "collector_sha256": _sha256_file(ROOT / COLLECTOR_REL),
            "litellm_config_sha256": _sha256_file(ROOT / CONFIG_REL),
        },
        "execution_evidence": {
            "path": RUNTIME_REL.as_posix(),
            "sha256": _sha256_file(runtime_path),
        },
        "evidence_limits": {
            "validator_independent": False,
            "hrb_backend_admission_proven": False,
            "model_registry_backend_admission_proven": False,
            "language_quality_promotion_proven": False,
            "global_production_promotion_proven": False,
        },
    }
    _write_json(ROOT / RECEIPT_REL, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect real FA3 LiteLLM + Language Bridge current-host E2E evidence")
    parser.add_argument("--primary-language", required=True)
    parser.add_argument("--secondary-language", required=True)
    parser.add_argument("--primary-sample-file", required=True)
    parser.add_argument("--secondary-sample-file", required=True)
    parser.add_argument("--model-alias", default=os.environ.get("FA3_LITELLM_MODEL_ALIAS", "fa3-local-primary"))
    parser.add_argument("--gateway-url", default=os.environ.get("FA3_LITELLM_URL", "http://127.0.0.1:4000"))
    parser.add_argument("--credential-file", default=None)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    try:
        receipt = collect(args)
    except (CollectionDenied, LanguageBridgeDenied, ValueError) as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    print(json.dumps({
        "result": "PASS",
        "receipt": RECEIPT_REL.as_posix(),
        "evidence_level": receipt["evidence_level"],
        "production_promotion_claim": False,
        "translation_quality_claim": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
