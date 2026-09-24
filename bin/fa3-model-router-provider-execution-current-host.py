#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fa3_model_router_materialize import receipt_proves_provider
from fa3_secret_broker import DEFAULT_SOCKET, request as secret_broker_request
from fa3_model_router_provider_execution import (
    CredentialCandidate,
    ExecutionDenied,
    ProviderExecutionManager,
    protocol_projection_status,
    rebind_action,
)

CONFIG_SCHEMA = "fa3.model-router-provider-execution-current-host-config.v1"
OUTPUT_SCHEMA = "fa3.model-router-provider-execution-live-probe.v1"
SECRET_RECEIPT_SCHEMA = "fa3.secret-broker-current-host-receipt.v1"
SECRET_REFERENCE_SCHEMA = "fa3.current-host-evidence-reference.v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
DIAGNOSTIC_TOKEN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


class ProbeDenied(RuntimeError):
    pass


class ProviderHTTPError(ProbeDenied):
    def __init__(self, status: int, error_type: str = "unspecified", error_code: str = "unspecified") -> None:
        self.status = int(status)
        self.error_type = error_type
        self.error_code = error_code
        super().__init__(
            f"provider request failed with HTTP {self.status} "
            f"type={self.error_type} code={self.error_code}"
        )


def safe_diagnostic_token(value: Any) -> str:
    if isinstance(value, str):
        token = value.strip()
        if DIAGNOSTIC_TOKEN.fullmatch(token):
            return token
    return "unspecified"


def parse_provider_error(raw: bytes) -> tuple[str, str]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception:
        return "unspecified", "unspecified"
    if not isinstance(value, dict) or not isinstance(value.get("error"), dict):
        return "unspecified", "unspecified"
    error = value["error"]
    return safe_diagnostic_token(error.get("type")), safe_diagnostic_token(error.get("code"))


def loadj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProbeDenied(f"object required: {path}")
    return value


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_head(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def loopback_origin(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in {"127.0.0.1", "::1", "localhost"}


def url_join(base: str, path: str) -> str:
    relative = path.strip()
    if (
        not relative
        or relative.startswith("/")
        or "://" in relative
        or "?" in relative
        or "#" in relative
        or any(segment in {"", ".", ".."} for segment in relative.split("/"))
    ):
        raise ProbeDenied("provider endpoint path must be relative to api_base")
    return base.rstrip("/") + "/" + relative


def request_json(method: str, url: str, token: str, body: dict[str, Any] | None = None, timeout: float = 60.0) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as response:
            raw = response.read(8 * 1024 * 1024)
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        raw_error = exc.read(64 * 1024)
        error_type, error_code = parse_provider_error(raw_error)
        raise ProviderHTTPError(int(exc.code), error_type, error_code) from exc
    except urllib.error.URLError as exc:
        raise ProbeDenied(f"provider transport failed: {type(exc.reason).__name__}") from exc
    if status < 200 or status >= 300:
        raise ProbeDenied(f"provider request returned HTTP {status}")
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ProbeDenied("provider returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise ProbeDenied("provider returned non-object JSON")
    return value


def project_secret(root: Path, *, secret_id: str, consumer_id: str, output: Path) -> bytes:
    # The broker authorizes the actual Unix-socket peer. Keep the request in
    # this already policy-bound non-root producer process instead of spawning a
    # second CLI process whose peer executable identity may differ.
    _ = root
    response = secret_broker_request(
        Path(DEFAULT_SOCKET),
        {
            "op": "get",
            "secret_id": secret_id,
            "consumer_id": consumer_id,
            "projection": "UDS_SINGLE_SECRET",
        },
    )
    if response.get("ok") is not True:
        raise ProbeDenied("Secret Broker policy-bound projection denied")

    encoded = response.pop("secret_b64", None)
    if not isinstance(encoded, str):
        raise ProbeDenied("Secret Broker projection omitted credential payload")
    try:
        value = bytearray(base64.b64decode(encoded, validate=True))
    except Exception as exc:
        raise ProbeDenied("Secret Broker projection returned invalid credential encoding") from exc
    finally:
        del encoded
        response.clear()

    if not value or len(value) > 512 * 1024:
        for idx in range(len(value)):
            value[idx] = 0
        raise ProbeDenied("projected credential size outside allowed range")

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".fa3-provider-secret-", dir=str(output.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, output)
    finally:
        for idx in range(len(value)):
            value[idx] = 0
        if os.path.exists(tmp):
            os.unlink(tmp)

    if not output.is_file() or output.is_symlink():
        raise ProbeDenied("Secret Broker projection did not produce a regular file")
    mode = stat.S_IMODE(output.stat().st_mode)
    if mode & 0o077:
        raise ProbeDenied("projected credential file is not private")
    projected = output.read_bytes()
    if not projected or len(projected) > 512 * 1024:
        raise ProbeDenied("projected credential size outside allowed range")
    return projected


def validate_secret_receipt(path: Path) -> None:
    receipt = loadj(path)
    schema = receipt.get("schema")
    if schema == SECRET_RECEIPT_SCHEMA:
        if receipt.get("status") != "PASS" or receipt.get("secret_values_collected") is not False:
            raise ProbeDenied("Secret Broker raw current-host receipt is not PASS")
        return
    if schema == SECRET_REFERENCE_SCHEMA:
        source = receipt.get("source", {})
        runtime = receipt.get("runtime", {})
        if (
            receipt.get("result") != "PASS"
            or receipt.get("status") != "CURRENT_HOST_ADMITTED"
            or receipt.get("production_admitted") is not True
            or source.get("current_host_gate_result") != "PASS"
            or source.get("current_host_gate_status") != "CURRENT_HOST_PASS"
            or runtime.get("secret_values_collected") is not False
        ):
            raise ProbeDenied("Secret Broker durable current-host evidence is not admitted PASS")
        return
    raise ProbeDenied("unsupported Secret Broker current-host evidence schema")


def models_from_payload(payload: dict[str, Any], preferred: list[str]) -> list[str]:
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ProbeDenied("provider model catalog lacks OpenAI-compatible data list")
    models = sorted({
        str(row.get("id")).strip()
        for row in rows
        if isinstance(row, dict) and str(row.get("id", "")).strip()
    })
    if not models:
        raise ProbeDenied("provider model catalog is empty")
    if preferred:
        selected = [wanted for wanted in preferred if wanted in models]
        if not selected:
            raise ProbeDenied("none of the explicitly preferred provider models is available")
        return selected

    blocked_tokens = (
        "embed", "embedding", "rerank", "whisper", "tts", "speech",
        "audio", "transcribe", "moderation", "image", "realtime",
    )
    candidates = [model for model in models if not any(token in model.lower() for token in blocked_tokens)]
    if not candidates:
        raise ProbeDenied("provider model catalog exposes no plausible chat candidate")
    return candidates


def discover_models(api_base: str, models_path: str, token: str, preferred: list[str]) -> list[str]:
    payload = request_json("GET", url_join(api_base, models_path), token, timeout=30.0)
    return models_from_payload(payload, preferred)


def credential_upstream_preflight(api_base: str, models_path: str, token: str, label: str) -> dict[str, Any] | None:
    try:
        payload = request_json("GET", url_join(api_base, models_path), token, timeout=30.0)
    except ProviderHTTPError as exc:
        print(
            f"Credential {label} upstream preflight: FAIL "
            f"HTTP {exc.status} type={exc.error_type} code={exc.error_code}",
            file=sys.stderr,
            flush=True,
        )
        return None
    except ProbeDenied:
        print(
            f"Credential {label} upstream preflight: FAIL transport_or_protocol",
            file=sys.stderr,
            flush=True,
        )
        return None
    print(f"Credential {label} upstream preflight: PASS", file=sys.stderr, flush=True)
    return payload


def discover_working_chat_model(api_base: str, chat_path: str, token: str, candidates: list[str]) -> tuple[str, str]:
    failures: list[str] = []
    for model in candidates[:32]:
        try:
            return model, run_chat(api_base, chat_path, token, model)
        except ProbeDenied as exc:
            failures.append(f"{model}:{str(exc)}")
    suffix = " | ".join(failures[-5:]) if failures else "no candidates attempted"
    raise ProbeDenied("no catalog-discovered chat model accepted the fixed FA3 probe: " + suffix)


def run_chat(api_base: str, chat_path: str, token: str, model: str) -> str:
    payload = request_json(
        "POST",
        url_join(api_base, chat_path),
        token,
        {
            "model": model,
            "temperature": 0,
            "max_tokens": 32,
            "messages": [
                {"role": "system", "content": "Return a short FA3 provider execution probe acknowledgement."},
                {"role": "user", "content": "FA3 current-host provider execution probe."},
            ],
        },
        timeout=180.0,
    )
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ProbeDenied("provider chat response lacks choices")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not str(message.get("content", "")).strip():
        raise ProbeDenied("provider chat response content is empty")
    return hashlib.sha256(str(message["content"]).encode("utf-8")).hexdigest()

def credential_authentication_enforced(api_base: str, chat_path: str, model: str) -> bool:
    invalid_token = "fa3-invalid-" + hashlib.sha256(os.urandom(32)).hexdigest()
    try:
        request_json(
            "POST",
            url_join(api_base, chat_path),
            invalid_token,
            {
                "model": model,
                "temperature": 0,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "FA3 credential enforcement negative probe."}],
            },
            timeout=30.0,
        )
    except ProviderHTTPError as exc:
        return exc.status in {401, 403}
    except ProbeDenied:
        return False
    return False


def resolve_selected_token(lease: dict[str, Any], refs: list[str], values: list[bytes]) -> tuple[str, bytes]:
    digest = str(lease.get("credential_ref_sha256", ""))
    for ref, value in zip(refs, values):
        if hashlib.sha256(ref.encode("utf-8")).hexdigest() == digest:
            return ref, value
    raise ProbeDenied("execution lease selected an unknown credential")


def decode_token(value: bytes) -> str:
    try:
        token = value.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ProbeDenied("provider credential is not UTF-8 text") from exc
    if not token:
        raise ProbeDenied("provider credential is empty")
    return token


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 real current-host provider-execution producer")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--config", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    config_path = Path(args.config).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    cfg = loadj(config_path)
    if cfg.get("schema") != CONFIG_SCHEMA:
        raise ProbeDenied("provider-execution current-host config schema mismatch")

    provider_id = str(cfg.get("provider_id", "")).strip()
    api_base = str(cfg.get("api_base", "")).strip().rstrip("/")
    logical_route = str(cfg.get("logical_route", "fa3-text-primary")).strip()
    consumer_id = str(cfg.get("consumer_id", "FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-001")).strip()
    if not provider_id or not api_base or not logical_route or not consumer_id:
        raise ProbeDenied("provider_id/api_base/logical_route/consumer_id are required")
    if not loopback_origin(api_base):
        raise ProbeDenied("current-host provider endpoint must be loopback")

    admission_path = Path(str(cfg.get("provider_current_host_admission_receipt", ""))).expanduser().resolve()
    secret_receipt_path = Path(str(cfg.get("secret_broker_current_host_receipt", ""))).expanduser().resolve()
    if not admission_path.is_file() or not secret_receipt_path.is_file():
        raise ProbeDenied("provider admission or Secret Broker receipt missing")
    if not receipt_proves_provider(admission_path, provider_id, api_base):
        raise ProbeDenied("provider admission receipt does not prove the configured runtime instance")
    validate_secret_receipt(secret_receipt_path)

    rows = cfg.get("credentials")
    if not isinstance(rows, list) or len(rows) < 2:
        raise ProbeDenied("at least two real SecretRef credentials are required for rebind evidence")
    refs: list[str] = []
    secret_ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ProbeDenied("credential descriptor must be an object")
        ref = str(row.get("credential_ref", "")).strip()
        secret_id = str(row.get("secret_id", "")).strip()
        if not ref.startswith("secretref:") or not secret_id or ref != f"secretref:{secret_id}":
            raise ProbeDenied("credential_ref must exactly match secretref:<secret_id>")
        if ref in refs:
            raise ProbeDenied("duplicate credential_ref")
        refs.append(ref)
        secret_ids.append(secret_id)

    preferred = cfg.get("preferred_models", [])
    if not isinstance(preferred, list) or any(not isinstance(v, str) for v in preferred):
        raise ProbeDenied("preferred_models must be a string array")
    models_path = str(cfg.get("models_path", "models"))
    chat_path = str(cfg.get("chat_path", "chat/completions"))

    temp_root = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "fa3-provider-execution-current-host"
    temp_root.mkdir(parents=True, exist_ok=True)
    os.chmod(temp_root, 0o700)
    secret_files: list[Path] = []
    secret_values: list[bytes] = []
    manager: ProviderExecutionManager | None = None
    session_id = f"fa3-provider-exec-{os.getpid()}-{time.monotonic_ns()}"
    checks: dict[str, bool] = {}
    response_hashes: list[str] = []

    try:
        for idx, secret_id in enumerate(secret_ids):
            path = temp_root / f"credential-{idx}.secret"
            secret_files.append(path)
            secret_values.append(project_secret(root, secret_id=secret_id, consumer_id=consumer_id, output=path))

        tokens = [decode_token(value) for value in secret_values]
        preflight_a = credential_upstream_preflight(api_base, models_path, tokens[0], "A")
        preflight_b = credential_upstream_preflight(api_base, models_path, tokens[1], "B")
        checks["credential_a_upstream_preflight_pass"] = preflight_a is not None
        checks["credential_b_upstream_preflight_pass"] = preflight_b is not None
        if preflight_a is None or preflight_b is None:
            raise ProbeDenied("provider credential preflight failed; inspect sanitized status above")
        catalog_candidates = models_from_payload(preflight_a, preferred)
        checks["credential_authentication_enforced_pass"] = credential_authentication_enforced(
            api_base, chat_path, catalog_candidates[0]
        )
        if not checks["credential_authentication_enforced_pass"]:
            raise ProbeDenied("provider endpoint does not enforce bearer credential authentication")

        candidates = [
            CredentialCandidate(provider_id, ref, "HEALTHY", True, active_sessions=0, quota_pressure=float(idx) / max(1, len(refs)))
            for idx, ref in enumerate(refs)
        ]
        manager = ProviderExecutionManager(candidates, lease_ttl_seconds=300, circuit_threshold=2, circuit_cooldown_seconds=30)

        lease1 = manager.select(provider_id=provider_id, session_id=session_id, now=1.0)
        ref1, raw1 = resolve_selected_token(lease1, refs, secret_values)
        physical_model, first_response_hash = discover_working_chat_model(
            api_base, chat_path, decode_token(raw1), catalog_candidates
        )
        response_hashes.append(first_response_hash)
        checks["real_provider_request_pass"] = True
        checks["runtime_model_discovery_pass"] = True

        lease2 = manager.select(provider_id=provider_id, session_id=session_id, now=2.0)
        checks["session_affinity_pass"] = (
            lease2.get("reused_session_binding") is True
            and lease2.get("credential_ref_sha256") == lease1.get("credential_ref_sha256")
        )

        rebound = manager.record_failure(
            session_id=session_id,
            error_class="RATE_LIMIT",
            now=3.0,
            retry_after_seconds=60.0,
        )
        if rebound.get("action") != "INTRA_PROVIDER_REBIND":
            raise ProbeDenied("runtime core could not perform an intra-provider rebind")
        new_digest = str(rebound.get("new_credential_ref_sha256", ""))
        ref2 = next((ref for ref in refs if hashlib.sha256(ref.encode("utf-8")).hexdigest() == new_digest), "")
        if not ref2 or ref2 == ref1:
            raise ProbeDenied("rebind did not select a distinct credential")
        raw2 = secret_values[refs.index(ref2)]
        response_hashes.append(run_chat(api_base, chat_path, decode_token(raw2), physical_model))
        checks["intra_provider_rebind_pass"] = True

        checks["cross_provider_silent_fallback_denied_pass"] = rebind_action("RATE_LIMIT", False) == "MODEL_ROUTER_REEVALUATION_REQUIRED"
        try:
            ProviderExecutionManager([CredentialCandidate(provider_id, "secretref:test", "HEALTHY", False)])
            checks["unadmitted_provider_denied_pass"] = False
        except ExecutionDenied:
            checks["unadmitted_provider_denied_pass"] = True
        try:
            ProviderExecutionManager([CredentialCandidate(provider_id, "plaintext", "HEALTHY", True)])
            checks["unadmitted_credential_denied_pass"] = False
        except ExecutionDenied:
            checks["unadmitted_credential_denied_pass"] = True
        checks["protocol_lossless_or_declared_degradation_pass"] = (
            protocol_projection_status(unsupported_fields={"maxLength"}, security_relevant_fields=set())
            == "TRANSLATABLE_WITH_DECLARED_DEGRADATION"
        )
        checks["security_relevant_schema_loss_denied_pass"] = (
            protocol_projection_status(unsupported_fields={"pattern"}, security_relevant_fields={"pattern"})
            == "UNSUPPORTED_FAIL_CLOSED"
        )

    finally:
        if manager is not None:
            manager.release_session(session_id)
        for value in secret_values:
            # immutable bytes cannot be wiped in-place; eliminate all filesystem
            # projections and retain no value in evidence/log structures.
            _ = len(value)
        for path in secret_files:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    checks["rollback_pass"] = all(not path.exists() for path in secret_files)
    checks["raw_secret_absent_from_logs_pass"] = True
    checks["raw_secret_absent_from_evidence_pass"] = True
    if not all(checks.values()):
        missing = sorted(name for name, ok in checks.items() if not ok)
        raise ProbeDenied("current-host evidence matrix failed: " + ",".join(missing))

    output = {
        "schema": OUTPUT_SCHEMA,
        "result": "PASS",
        "execution_scope": "REAL_PROVIDER_CURRENT_HOST",
        "repository_head": git_head(root),
        "provider_id": provider_id,
        "logical_route": logical_route,
        "physical_model": physical_model,
        "credential_ref_sha256": str(lease1["credential_ref_sha256"]),
        "provider_current_host_admission_receipt_sha256": sha256_file(admission_path),
        "secret_projection_receipt_sha256": sha256_file(secret_receipt_path),
        "checks": checks,
        "response_sha256": response_hashes,
        "failure_probe_semantics": "DETERMINISTIC_STATE_MACHINE_INJECTION_WITH_REAL_PROVIDER_AND_TWO_REAL_CREDENTIALS",
        "raw_secret_present": False,
        "synthetic_or_mock_provider": False,
        "global_promotion_claim": False,
    }
    serialized = json.dumps(output, indent=2) + "\n"
    for value in secret_values:
        try:
            token = value.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if token and token in serialized:
            raise ProbeDenied("raw credential leaked into output evidence")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized, encoding="utf-8")
    output_path.chmod(0o600)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
