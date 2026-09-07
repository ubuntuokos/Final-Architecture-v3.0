#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

PROVIDER_ID = "FA3-PROVIDER-MINIMAX-H3-001"
MODEL_ID = "MiniMax-H3"
GLOBAL_API_BASE = "https://api.minimax.io"
ALLOWED_API_BASES = {"https://api.minimax.io", "https://api.minimaxi.com"}
CREDENTIAL_CLASSES = {"PAYG_API_KEY", "TOKEN_PLAN_SUBSCRIPTION_KEY"}


class H3AdmissionError(RuntimeError):
    pass


class H3ProviderError(RuntimeError):
    pass


Transport = Callable[[str, str, dict[str, str], bytes | None, float], tuple[int, dict[str, str], bytes]]


def _http_transport(method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float):
    req = urllib.request.Request(url=url, method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return int(response.status), dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        return int(exc.code), dict(exc.headers.items()) if exc.headers else {}, payload


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load_json_bytes(payload: bytes, context: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise H3ProviderError(f"{context}: non-JSON provider response") from exc
    if not isinstance(value, dict):
        raise H3ProviderError(f"{context}: provider response must be an object")
    return value


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _safe_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted = {}
    for key, value in headers.items():
        redacted[key] = "<redacted>" if key.lower() == "authorization" else value
    return redacted


def validate_credential_class(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in CREDENTIAL_CLASSES:
        raise H3AdmissionError("Credential class must be explicitly PAYG_API_KEY or TOKEN_PLAN_SUBSCRIPTION_KEY")
    return normalized


def validate_api_base(value: str) -> str:
    base = str(value or "").rstrip("/")
    if base not in ALLOWED_API_BASES:
        raise H3AdmissionError(f"MiniMax API base is not allowlisted: {base}")
    return base


def admit_local_execution(license_evidence_path: str | Path | None) -> dict[str, Any]:
    if not license_evidence_path:
        return {"result": "DENY", "state": "LOCAL_DENIED_WITHOUT_LICENSE_EVIDENCE"}
    path = Path(license_evidence_path)
    if not path.is_file():
        return {"result": "DENY", "state": "LOCAL_DENIED_WITHOUT_LICENSE_EVIDENCE"}
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"result": "DENY", "state": "LOCAL_DENIED_INVALID_LICENSE_EVIDENCE"}
    allowed = (
        evidence.get("deployment_authorized") is True
        and evidence.get("territory_evaluation") == "ALLOW"
        and (evidence.get("decision") == "ALLOW" or evidence.get("status") == "PASS")
    )
    return {
        "result": "ALLOW" if allowed else "DENY",
        "state": "LOCAL_LICENSE_ADMISSION_PASS" if allowed else "LOCAL_DENIED_LICENSE_ADMISSION_FAILED",
        "evidence_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def project_video_generation_ir(ir: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(ir, dict):
        raise H3AdmissionError("VideoGenerationIR must be a JSON object")
    prompt = ir.get("prompt") or ir.get("creative_prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise H3AdmissionError("VideoGenerationIR requires a non-empty prompt")
    duration = int(ir.get("duration", 4))
    if duration < 4 or duration > 15:
        raise H3AdmissionError("MiniMax H3 duration must be between 4 and 15 seconds")
    resolution = str(ir.get("resolution", "768P")).upper()
    if resolution not in {"768P", "2K"}:
        raise H3AdmissionError("MiniMax H3 resolution projection supports 768P or 2K")
    ratio = str(ir.get("ratio", "16:9"))
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt.strip()}]
    for ref in ir.get("references", []):
        if not isinstance(ref, dict):
            raise H3AdmissionError("Reference entries must be objects")
        media_type = str(ref.get("media_type", ""))
        url = ref.get("url")
        role = ref.get("role")
        if not isinstance(url, str) or not url:
            raise H3AdmissionError("Reference URL is required")
        if media_type == "image":
            item: dict[str, Any] = {"type": "image_url", "image_url": {"url": url}}
        elif media_type == "video":
            item = {"type": "video_url", "video_url": {"url": url}}
        elif media_type == "audio":
            item = {"type": "audio_url", "audio_url": {"url": url}}
        else:
            raise H3AdmissionError(f"Unsupported reference media_type: {media_type}")
        if role:
            item["role"] = str(role)
        content.append(item)
    return {
        "model": MODEL_ID,
        "content": content,
        "resolution": resolution,
        "duration": duration,
        "ratio": ratio,
    }


@dataclass(frozen=True)
class H3HostedConfig:
    token: str
    credential_class: str
    service_terms_admitted: bool
    api_base: str = GLOBAL_API_BASE
    allow_subscription_for_production: bool = False
    request_timeout_seconds: float = 60.0
    poll_interval_seconds: float = 10.0
    poll_timeout_seconds: float = 900.0

    def validated(self) -> "H3HostedConfig":
        if not self.token or not self.token.strip():
            raise H3AdmissionError("MiniMax credential is missing")
        validate_credential_class(self.credential_class)
        validate_api_base(self.api_base)
        if not self.service_terms_admitted:
            raise H3AdmissionError("MiniMax hosted service terms admission is missing")
        if self.credential_class == "TOKEN_PLAN_SUBSCRIPTION_KEY" and not self.allow_subscription_for_production:
            raise H3AdmissionError("Token Plan production use requires explicit FA3 policy acknowledgement")
        return self


class MiniMaxH3Adapter:
    def __init__(self, config: H3HostedConfig, transport: Transport | None = None):
        self.config = config.validated()
        self.transport = transport or _http_transport

    def _provider_json(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, str], float]:
        url = self.config.api_base.rstrip("/") + path
        headers = {
            "Authorization": f"Bearer {self.config.token}",
            "Content-Type": "application/json",
            "User-Agent": "FA3-MiniMax-H3-Adapter/1.0",
        }
        started = time.monotonic()
        status, response_headers, payload = self.transport(
            method,
            url,
            headers,
            _json_bytes(body) if body is not None else None,
            self.config.request_timeout_seconds,
        )
        latency_ms = round((time.monotonic() - started) * 1000, 3)
        if status < 200 or status >= 300:
            try:
                provider_error = json.loads(payload.decode("utf-8"))
            except Exception:
                provider_error = {"body_sha256": _sha256_bytes(payload)}
            raise H3ProviderError(f"MiniMax API request failed HTTP {status}: {provider_error}")
        return _load_json_bytes(payload, path), response_headers, latency_ms

    def create_video(self, ir: dict[str, Any]) -> dict[str, Any]:
        projected = project_video_generation_ir(ir)
        response, headers, latency = self._provider_json("POST", "/v2/video_generation", projected)
        task_id = response.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise H3ProviderError("MiniMax create-video response has no task_id")
        return {
            "task_id": task_id,
            "request_projection": projected,
            "submit_latency_ms": latency,
            "rate_limit_headers": {k: v for k, v in headers.items() if "rate" in k.lower() or "limit" in k.lower()},
        }

    def create_context_ir(self, ir: dict[str, Any]) -> dict[str, Any]:
        projected = project_video_generation_ir(ir)
        request = {k: v for k, v in projected.items() if k != "resolution"}
        response, headers, latency = self._provider_json("POST", "/v2/h3_context_ir", request)
        task_id = response.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise H3ProviderError("MiniMax Context-IR response has no task_id")
        return {"task_id": task_id, "submit_latency_ms": latency, "response_headers": _safe_headers(headers)}

    def query_task(self, task_id: str) -> dict[str, Any]:
        if not task_id or "/" in task_id:
            raise H3AdmissionError("Invalid provider task_id")
        response, headers, latency = self._provider_json("GET", f"/v2/query/video_generation/{task_id}")
        return {"response": response, "poll_latency_ms": latency, "response_headers": _safe_headers(headers)}

    def wait_for_task(self, task_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.config.poll_timeout_seconds
        polls: list[dict[str, Any]] = []
        while True:
            observed = self.query_task(task_id)
            response = observed["response"]
            task = response.get("task") if isinstance(response.get("task"), dict) else response
            status = str(task.get("status", "")).lower()
            polls.append({"status": status, "latency_ms": observed["poll_latency_ms"]})
            if status in {"succeeded", "success"}:
                return {"task": task, "polls": polls}
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise H3ProviderError(f"MiniMax task entered terminal failure state: {status}")
            if time.monotonic() >= deadline:
                raise H3ProviderError("MiniMax task polling timed out")
            time.sleep(self.config.poll_interval_seconds)

    def download_result(self, url: str, output: Path) -> dict[str, Any]:
        if not isinstance(url, str) or not url.startswith("https://"):
            raise H3ProviderError("Provider result URL must be HTTPS")
        started = time.monotonic()
        status, headers, payload = self.transport("GET", url, {"User-Agent": "FA3-MiniMax-H3-Adapter/1.0"}, None, self.config.request_timeout_seconds)
        latency_ms = round((time.monotonic() - started) * 1000, 3)
        if status < 200 or status >= 300 or not payload:
            raise H3ProviderError(f"Failed to download MiniMax result: HTTP {status}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
        return {
            "path": str(output),
            "sha256": _sha256_bytes(payload),
            "bytes": len(payload),
            "download_latency_ms": latency_ms,
            "content_type": headers.get("Content-Type") or headers.get("content-type"),
        }

    def run_hosted_video(self, ir: dict[str, Any], output: Path) -> dict[str, Any]:
        started = time.monotonic()
        submitted = self.create_video(ir)
        completed = self.wait_for_task(submitted["task_id"])
        task = completed["task"]
        content = task.get("content") if isinstance(task.get("content"), dict) else {}
        result_url = content.get("url")
        if not isinstance(result_url, str) or not result_url:
            raise H3ProviderError("Succeeded MiniMax task has no result URL")
        artifact = self.download_result(result_url, output)
        elapsed_ms = round((time.monotonic() - started) * 1000, 3)
        usage = task.get("usage") if isinstance(task.get("usage"), dict) else {}
        return {
            "status": "PASS",
            "provider_id": PROVIDER_ID,
            "model": MODEL_ID,
            "task_id": submitted["task_id"],
            "credential_class": self.config.credential_class,
            "billing_mode": "PAYG" if self.config.credential_class == "PAYG_API_KEY" else "TOKEN_PLAN",
            "entitlement_discovery": {
                "result": "PASS",
                "method": "REAL_REQUEST_ACCEPTED_AND_COMPLETED",
                "eligible_model": MODEL_ID,
                "requested_operation": "VIDEO_GENERATION",
                "rate_limit_headers": submitted["rate_limit_headers"],
            },
            "request_projection": submitted["request_projection"],
            "provider_usage": usage,
            "cost_evidence": {
                "static_price_used": False,
                "amount": task.get("cost") or task.get("billing_amount"),
                "amount_source": "PROVIDER_TASK_RESPONSE" if (task.get("cost") is not None or task.get("billing_amount") is not None) else "NOT_EXPOSED_IN_TASK_RESPONSE",
            },
            "latency": {
                "submit_ms": submitted["submit_latency_ms"],
                "poll_count": len(completed["polls"]),
                "download_ms": artifact["download_latency_ms"],
                "end_to_end_ms": elapsed_ms,
            },
            "artifact": artifact,
            "secret_persisted": False,
            "provider_terminal_status": str(task.get("status", "")).lower(),
        }


def adapter_conformance() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    checks.append(("credential-class-rejects-implicit", False))
    try:
        validate_credential_class("")
    except H3AdmissionError:
        checks[-1] = (checks[-1][0], True)
    checks.append(("local-deny-without-license", admit_local_execution(None)["state"] == "LOCAL_DENIED_WITHOUT_LICENSE_EVIDENCE"))
    projected = project_video_generation_ir({"prompt": "FA3 conformance", "duration": 4, "ratio": "16:9", "resolution": "768P"})
    checks.append(("canonical-ir-projection", projected["model"] == MODEL_ID and projected["duration"] == 4))
    checks.append(("allowed-global-base", validate_api_base(GLOBAL_API_BASE) == GLOBAL_API_BASE))
    passed = sum(1 for _, ok in checks if ok)
    return {"result": "PASS" if passed == len(checks) else "FAIL", "passed": passed, "total": len(checks), "checks": [{"name": n, "pass": ok} for n, ok in checks]}


def config_from_env() -> H3HostedConfig:
    return H3HostedConfig(
        token=os.environ.get("MINIMAX_H3_API_KEY", ""),
        credential_class=os.environ.get("FA3_MINIMAX_H3_CREDENTIAL_CLASS", ""),
        service_terms_admitted=os.environ.get("FA3_MINIMAX_H3_SERVICE_TERMS_ADMITTED") == "1",
        api_base=os.environ.get("MINIMAX_H3_API_BASE", GLOBAL_API_BASE),
        allow_subscription_for_production=os.environ.get("FA3_ALLOW_TOKEN_PLAN_PRODUCTION") == "1",
        poll_interval_seconds=float(os.environ.get("FA3_MINIMAX_H3_POLL_INTERVAL_SECONDS", "10")),
        poll_timeout_seconds=float(os.environ.get("FA3_MINIMAX_H3_POLL_TIMEOUT_SECONDS", "900")),
    )


if __name__ == "__main__":
    print(json.dumps(adapter_conformance(), indent=2))
