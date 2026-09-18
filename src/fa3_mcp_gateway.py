#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

AUTHORITY_ID = "FA3-AUTH-MCP-GATEWAY-001"
PROFILE_ID = "FA3-MCP-CURRENT-HOST-001"
RECEIPT_SCHEMA = "fa3.mcp.gateway.receipt.v1"


class GatewayDenied(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Adapter:
    adapter_id: str
    provider_id: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


class McpGateway:
    """Provider-neutral FA3 tool/capability mediation boundary.

    This core intentionally owns no policy, secret, resource, model-routing or
    durable-workflow authority.  External decisions/leases are verified and
    enforced before an admitted CONNECTED adapter may be invoked.
    """

    def __init__(self, registry: dict[str, Any]):
        self.registry = registry
        self.adapters: dict[str, Adapter] = {}
        self._capabilities = {
            item["capability_id"]: item
            for item in registry.get("capabilities", [])
            if isinstance(item, dict) and _nonempty(item.get("capability_id"))
        }

    @classmethod
    def from_path(cls, path: Path) -> "McpGateway":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def register_adapter(self, adapter: Adapter) -> None:
        self.adapters[adapter.adapter_id] = adapter

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "profile": PROFILE_ID,
            "authority": AUTHORITY_ID,
            "capability_count": len(self._capabilities),
            "connected_adapter_count": len(self.adapters),
        }

    def readiness(self) -> dict[str, Any]:
        connected_bindings = 0
        for capability in self._capabilities.values():
            for binding in capability.get("providers", []):
                if (
                    isinstance(binding, dict)
                    and binding.get("state") == "CONNECTED"
                    and binding.get("adapter_id") in self.adapters
                ):
                    connected_bindings += 1
        return {
            "ready": connected_bindings > 0,
            "connected_bindings": connected_bindings,
            "reason": "CONNECTED_ADAPTER_AVAILABLE" if connected_bindings else "NO_CONNECTED_ADAPTER",
        }

    def list_capabilities(self) -> list[dict[str, Any]]:
        return [
            {
                "capability_id": item["capability_id"],
                "risk_class": item.get("risk_class"),
                "side_effects": item.get("side_effects", []),
                "available": any(
                    isinstance(binding, dict)
                    and binding.get("state") == "CONNECTED"
                    and binding.get("adapter_id") in self.adapters
                    for binding in item.get("providers", [])
                ),
            }
            for item in self._capabilities.values()
        ]

    def _select_binding(self, capability: dict[str, Any], requested_provider: str | None) -> dict[str, Any]:
        bindings = [binding for binding in capability.get("providers", []) if isinstance(binding, dict)]
        if requested_provider:
            bindings = [binding for binding in bindings if binding.get("provider_id") == requested_provider]
        bindings = [
            binding
            for binding in bindings
            if binding.get("state") == "CONNECTED" and binding.get("adapter_id") in self.adapters
        ]
        if not bindings:
            raise GatewayDenied("UNADMITTED_ADAPTER", "No CONNECTED admitted adapter is available")
        bindings.sort(key=lambda binding: (int(binding.get("priority", 1000)), str(binding.get("provider_id", ""))))
        return bindings[0]

    def _validate_policy(self, request: dict[str, Any], capability: dict[str, Any]) -> None:
        decision = request.get("policy_decision")
        if not isinstance(decision, dict):
            raise GatewayDenied("MISSING_POLICY_DECISION", "Policy decision is required")
        expected_authority = self.registry.get("policy_authority")
        if not _nonempty(expected_authority) or decision.get("authority") != expected_authority:
            raise GatewayDenied("INVALID_POLICY_AUTHORITY", "Policy decision authority mismatch")
        if decision.get("status") != "ALLOW":
            raise GatewayDenied("POLICY_DENY", "Policy did not allow invocation")
        if decision.get("capability_id") != capability["capability_id"]:
            raise GatewayDenied("POLICY_SCOPE_MISMATCH", "Policy decision is not bound to capability")
        if not _nonempty(decision.get("decision_id")):
            raise GatewayDenied("INVALID_POLICY_DECISION", "Policy decision id is required")

    def _validate_approval(
        self,
        request: dict[str, Any],
        capability: dict[str, Any],
        binding: dict[str, Any] | None = None,
    ) -> None:
        override = binding.get("approval_override") if isinstance(binding, dict) else None
        mode = str(override if override in {"policy", "session", "explicit", "strong"} else capability.get("approval", "policy"))
        if mode not in {"session", "explicit", "strong"}:
            return
        approval = request.get("approval")
        if not isinstance(approval, dict) or approval.get("status") != "APPROVED":
            raise GatewayDenied("MISSING_REQUIRED_APPROVAL", "Required approval is missing")
        if approval.get("capability_id") != capability["capability_id"]:
            raise GatewayDenied("APPROVAL_SCOPE_MISMATCH", "Approval is not bound to capability")
        if not _nonempty(approval.get("approval_id")):
            raise GatewayDenied("INVALID_APPROVAL", "Approval id is required")

    def _validate_hrb(self, request: dict[str, Any], capability: dict[str, Any]) -> None:
        if capability.get("hrb_required") is not True:
            return
        lease = request.get("hrb_lease")
        if not isinstance(lease, dict):
            raise GatewayDenied("MISSING_OR_INVALID_HRB_LEASE", "HRB lease is required")
        if lease.get("issuer") != "FA3-HOST-RESOURCE-BROKER-001" or lease.get("status") != "ACTIVE":
            raise GatewayDenied("MISSING_OR_INVALID_HRB_LEASE", "HRB lease authority/status mismatch")
        try:
            if int(lease.get("expires_epoch", 0)) <= int(time.time()):
                raise GatewayDenied("MISSING_OR_INVALID_HRB_LEASE", "HRB lease is expired")
        except (TypeError, ValueError):
            raise GatewayDenied("MISSING_OR_INVALID_HRB_LEASE", "HRB lease expiry is invalid")
        if not _nonempty(lease.get("lease_id")):
            raise GatewayDenied("MISSING_OR_INVALID_HRB_LEASE", "HRB lease id is required")

    def _validate_secret_refs(self, request: dict[str, Any]) -> None:
        if "secrets" in request or "credential" in request or "token" in request:
            raise GatewayDenied("INLINE_SECRET_FORBIDDEN", "Durable/inline credential material is forbidden")
        refs = request.get("secret_refs", [])
        if refs is None:
            refs = []
        if not isinstance(refs, list) or any(not _nonempty(ref) for ref in refs):
            raise GatewayDenied("INVALID_SECRET_REFERENCE", "Secret references must be opaque non-empty ids")

    def invoke(self, request: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        actor = request.get("actor_id")
        client = request.get("client_id")
        session = request.get("session_id")
        capability_id = request.get("capability_id")
        if not all(_nonempty(value) for value in (actor, client, session)):
            return self._deny(request, "UNKNOWN_IDENTITY", "Actor/client/session identity is required", started)
        capability = self._capabilities.get(str(capability_id))
        if capability is None:
            return self._deny(request, "UNKNOWN_CAPABILITY", "Capability is not registered", started)
        arguments = request.get("arguments")
        if not isinstance(arguments, dict):
            return self._deny(request, "INVALID_SCHEMA", "Arguments must be an object", started)

        try:
            self._validate_policy(request, capability)
            self._validate_hrb(request, capability)
            self._validate_secret_refs(request)
            binding = self._select_binding(capability, request.get("provider_id"))
            self._validate_approval(request, capability, binding)
            adapter = self.adapters[binding["adapter_id"]]
            if adapter.provider_id != binding.get("provider_id"):
                raise GatewayDenied("PROVIDER_BINDING_MISMATCH", "Adapter/provider binding mismatch")
            result = adapter.handler(arguments)
            if not isinstance(result, dict):
                raise GatewayDenied("INVALID_RESULT_SCHEMA", "Adapter result must be an object")
            return self._receipt(
                request=request,
                status="success",
                reason_code="DISPATCH_PASS",
                started=started,
                provider_id=adapter.provider_id,
                adapter_id=adapter.adapter_id,
                result=result,
            )
        except GatewayDenied as exc:
            return self._deny(request, exc.code, exc.message, started)

    def _deny(self, request: dict[str, Any], code: str, message: str, started: float) -> dict[str, Any]:
        return self._receipt(request=request, status="denied", reason_code=code, started=started, message=message)

    def _receipt(
        self,
        request: dict[str, Any],
        status: str,
        reason_code: str,
        started: float,
        provider_id: str | None = None,
        adapter_id: str | None = None,
        result: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        safe_request = {
            key: value
            for key, value in request.items()
            if key not in {"secrets", "credential", "token", "secret_refs"}
        }
        policy = request.get("policy_decision") if isinstance(request.get("policy_decision"), dict) else {}
        approval = request.get("approval") if isinstance(request.get("approval"), dict) else {}
        lease = request.get("hrb_lease") if isinstance(request.get("hrb_lease"), dict) else {}
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "profile_id": PROFILE_ID,
            "authority": AUTHORITY_ID,
            "timestamp_epoch": int(time.time()),
            "actor_id": request.get("actor_id"),
            "client_id": request.get("client_id"),
            "session_id": request.get("session_id"),
            "capability_id": request.get("capability_id"),
            "provider_id": provider_id,
            "adapter_id": adapter_id,
            "policy_decision_id": policy.get("decision_id"),
            "approval_id": approval.get("approval_id"),
            "resource_lease_id": lease.get("lease_id"),
            "request_sha256": canonical_sha256(safe_request),
            "result_status": status,
            "reason_code": reason_code,
            "duration_ms": max(0, int((time.time() - started) * 1000)),
            "global_promotion_claim": False,
        }
        if message:
            receipt["message"] = message
        if result is not None:
            receipt["result"] = result
        return receipt
