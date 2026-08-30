#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-AUTOGPT-001"
CAPABILITY_ID = "CAP-028"
CONTRACT_ID = "FA3-AUTOGPT-CONTRACTS-001"
REQUEST_SCHEMA = "fa3.autogpt-block-execution-request.v1"
RESULT_SCHEMA = "fa3.autogpt-block-execution-result.v1"
CAPABILITY = "managed_external_agent_runtime.autogpt.block.execute"
STORE_VALUE_BLOCK_ID = "1ff065e9-88e8-4358-9d82-8dc91f622ba9"
ALLOWED_BLOCK_IDS = {STORE_VALUE_BLOCK_ID}
AUTHORITY = "FA3-AUTH-SECURITY-GOV-001"
MCP_AUTHORITY = "FA3-AUTH-MCP-GATEWAY-001"
HRB_AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"


class AdmissionError(ValueError):
    pass


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _loopback_base_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "http":
        raise AdmissionError("AutoGPT provider URL must use local HTTP behind the FA3 boundary")
    if parsed.hostname not in {"127.0.0.1", "::1"}:
        raise AdmissionError("AutoGPT provider URL must be a literal loopback address")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AdmissionError("AutoGPT provider URL contains forbidden URL components")
    if not parsed.port:
        raise AdmissionError("AutoGPT provider URL must include an explicit port")
    return value.rstrip("/")


def validate_request(request: dict[str, Any]) -> None:
    required = (
        "request_id","caller_identity","delegation_id","workflow_run_id","capability_id",
        "provider_id","block_id","authorization_decision","mcp_admission",
        "host_resource_admission","input","timeout_seconds",
    )
    missing = [key for key in required if not request.get(key) and key != "input"]
    if missing:
        raise AdmissionError(f"missing required request fields: {missing}")
    if request.get("schema") != REQUEST_SCHEMA:
        raise AdmissionError("request schema mismatch")
    if request.get("provider_id") != PROVIDER_ID or request.get("capability_id") != CAPABILITY_ID:
        raise AdmissionError("provider/capability identity mismatch")
    if request.get("block_id") not in ALLOWED_BLOCK_IDS:
        raise AdmissionError("block is not in the FA3 AutoGPT production allowlist")
    auth = request.get("authorization_decision") or {}
    if (
        auth.get("authority") != AUTHORITY
        or auth.get("decision") != "ALLOW"
        or not auth.get("decision_id")
        or CAPABILITY not in auth.get("capabilities", [])
    ):
        raise AdmissionError("external FA3 authorization was not admitted")
    mcp = request.get("mcp_admission") or {}
    if (
        mcp.get("authority") != MCP_AUTHORITY
        or mcp.get("decision") != "ALLOW"
        or mcp.get("capability") != CAPABILITY
        or not mcp.get("admission_id")
    ):
        raise AdmissionError("Central MCP/capability-gateway admission is missing")
    hrb = request.get("host_resource_admission") or {}
    if (
        hrb.get("authority") != HRB_AUTHORITY
        or hrb.get("decision") != "ALLOW"
        or hrb.get("resource_class") != "CPU_RAM_ONLY"
        or hrb.get("accelerator_lease_id") not in {None, "NONE_REQUIRED"}
        or not hrb.get("admission_id")
    ):
        raise AdmissionError("Host Resource Broker admission is missing or requests an accelerator")
    timeout = request.get("timeout_seconds")
    if not isinstance(timeout, int) or not 1 <= timeout <= 30:
        raise AdmissionError("timeout is outside the canonical bounded range")
    data = request.get("input")
    if not isinstance(data, dict) or set(data) - {"input", "data"}:
        raise AdmissionError("input shape is outside the admitted StoreValueBlock contract")
    value = data.get("input")
    if not isinstance(value, str) or not value:
        raise AdmissionError("StoreValueBlock input must be a non-empty string")
    if len(value.encode("utf-8")) > 4096:
        raise AdmissionError("StoreValueBlock input exceeds 4096 UTF-8 bytes")
    if request.get("network_egress_allowed", False) is not False:
        raise AdmissionError("external network egress is forbidden for this runtime profile")
    lowered = {str(k).lower() for k in data}
    if lowered & {"api_key","token","password","secret","credentials"}:
        raise AdmissionError("credential-bearing input fields are forbidden")


def _request_json(method: str, url: str, api_key: str | None, payload: dict[str, Any] | None, timeout: int) -> tuple[int, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Accept":"application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(4 * 1024 * 1024)
            return response.status, json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read(2 * 1024 * 1024)
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = {"detail":raw.decode("utf-8",errors="replace")[:1000]}
        return exc.code, body


@dataclass
class AutoGPTProvider:
    base_url: str
    api_key: str = field(repr=False)
    request_fn: Any = field(default=_request_json, repr=False)

    def __post_init__(self) -> None:
        self.base_url = _loopback_base_url(self.base_url)
        if not self.api_key.startswith("agpt_"):
            raise AdmissionError("AutoGPT API key format is invalid")

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        validate_request(request)
        timeout = request["timeout_seconds"]
        endpoint = f"{self.base_url}/external-api/v1/blocks/{urllib.parse.quote(request['block_id'], safe='')}/execute"
        status, body = self.request_fn("POST", endpoint, self.api_key, request["input"], timeout)
        if status != 200:
            raise RuntimeError(f"AutoGPT block execution failed with HTTP {status}: {body}")
        expected = request["input"].get("data") or request["input"]["input"]
        output = body.get("output") if isinstance(body, dict) else None
        if not isinstance(output, list) or output != [expected]:
            raise RuntimeError("AutoGPT StoreValueBlock output did not match admitted deterministic input")
        result = {
            "schema": RESULT_SCHEMA,
            "request_id": request["request_id"],
            "caller_identity": request["caller_identity"],
            "delegation_id": request["delegation_id"],
            "workflow_run_id": request["workflow_run_id"],
            "capability_id": CAPABILITY_ID,
            "provider_id": PROVIDER_ID,
            "block_id": request["block_id"],
            "authorization_decision_id": request["authorization_decision"]["decision_id"],
            "mcp_admission_id": request["mcp_admission"]["admission_id"],
            "host_resource_admission_id": request["host_resource_admission"]["admission_id"],
            "input_digest": canonical_digest(request["input"]),
            "output_digest": canonical_digest(body),
            "result_status": "PASS",
            "output": body,
            "provider_http_status": status,
            "secret_material_recorded": False,
        }
        return result

    def unauthenticated_denied(self) -> bool:
        status, _ = self.request_fn("GET", f"{self.base_url}/external-api/v1/blocks", None, None, 10)
        return status == 401

    def graph_scope_escalation_denied(self) -> bool:
        status, _ = self.request_fn(
            "POST",
            f"{self.base_url}/external-api/v1/graphs/00000000-0000-0000-0000-000000000000/execute/1",
            self.api_key,
            {"node_input": {}},
            10,
        )
        return status == 403

    def listed_block_ids(self) -> set[str]:
        status, body = self.request_fn("GET", f"{self.base_url}/external-api/v1/blocks", self.api_key, None, 20)
        if status != 200 or not isinstance(body, list):
            raise RuntimeError(f"AutoGPT block inventory failed with HTTP {status}")
        return {str(item.get("id")) for item in body if isinstance(item, dict) and item.get("id")}
