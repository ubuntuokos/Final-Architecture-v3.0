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
    receipt_handler: Callable[[dict[str, Any], dict[str, Any]], None] | None = None


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

    def __init__(
        self,
        registry: dict[str, Any],
        policy_resolver: Callable[[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
    ):
        self.registry = registry
        self.policy_resolver = policy_resolver
        self.adapters: dict[str, Adapter] = {}
        self._capabilities = {
            item["capability_id"]: item
            for item in registry.get("capabilities", [])
            if isinstance(item, dict) and _nonempty(item.get("capability_id"))
        }

    @classmethod
    def from_path(
        cls,
        path: Path,
        policy_resolver: Callable[[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
    ) -> "McpGateway":
        return cls(json.loads(path.read_text(encoding="utf-8")), policy_resolver=policy_resolver)

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

    def _resolve_policy(
        self,
        request: dict[str, Any],
        capability: dict[str, Any],
        binding: dict[str, Any],
        peer_context: dict[str, Any],
    ) -> dict[str, Any]:
        mode = str(binding.get("policy_mode", "client_asserted"))
        if mode == "client_asserted":
            return request
        if mode != "external_resolver":
            raise GatewayDenied("INVALID_POLICY_MODE", "Unsupported provider policy mode")
        if self.policy_resolver is None:
            raise GatewayDenied("POLICY_RESOLVER_UNAVAILABLE", "External policy resolver is unavailable")
        decision = self.policy_resolver(request, capability, binding, peer_context)
        if not isinstance(decision, dict):
            raise GatewayDenied("INVALID_POLICY_DECISION", "External policy resolver returned invalid decision")
        effective = dict(request)
        effective["policy_decision"] = decision
        return effective

    def _validate_policy_scope(
        self,
        request: dict[str, Any],
        binding: dict[str, Any],
    ) -> None:
        decision = request.get("policy_decision")
        arguments = request.get("arguments")
        if not isinstance(decision, dict) or not isinstance(arguments, dict):
            raise GatewayDenied("POLICY_SCOPE_MISMATCH", "Policy scope cannot be validated")
        if binding.get("require_policy_purpose") is True and not _nonempty(decision.get("purpose")):
            raise GatewayDenied("POLICY_SCOPE_MISMATCH", "Policy purpose is required")
        scope = decision.get("scope")
        if not isinstance(scope, dict):
            scope = {}
        scoped_keys = tuple(str(x) for x in binding.get("policy_scope_arguments", []))
        present = 0
        for key in scoped_keys:
            value = str(arguments.get(key, "")).strip()
            if not value:
                continue
            present += 1
            allowed = scope.get(key + "s", [])
            if not isinstance(allowed, list) or value not in {str(x) for x in allowed}:
                raise GatewayDenied("POLICY_SCOPE_MISMATCH", f"Policy decision does not authorize {key}")
        if binding.get("require_scoped_arguments") is True and present == 0:
            raise GatewayDenied("POLICY_SCOPE_MISMATCH", "At least one scoped retrieval argument is required")

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

    def _apply_asset_egress(self, request: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
        if binding.get("asset_egress_mode") != "LOCAL_FILE_UPLOAD":
            return request
        arguments = request.get("arguments")
        if not isinstance(arguments, dict):
            raise GatewayDenied("ASSET_EGRESS_SCHEMA", "Asset egress requires object arguments")
        source = arguments.get("source")
        if not isinstance(source, str) or not source.strip():
            raise GatewayDenied("ASSET_EGRESS_SOURCE_INVALID", "Local asset source is required")
        if "://" in source:
            return request
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise GatewayDenied("ASSET_EGRESS_SOURCE_INVALID", "Local asset source must exist")
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        try:
            from fa3_asset_egress_policy import evaluate
            decision = evaluate({
                "request_id": "FA3-EGRESS-REQ-" + canonical_sha256({"source": str(path), "provider": binding.get("provider_id")})[:24].upper(),
                "source_ref": str(path),
                "source_sha256": digest.hexdigest(),
                "data_class": binding.get("asset_egress_data_class", "USER_DOCUMENT"),
                "destination_provider": binding.get("provider_id"),
                "destination_uri": binding.get("asset_egress_destination_uri"),
                "purpose": binding.get("asset_egress_purpose", "provider upload"),
                "approval": request.get("approval"),
            })
        except Exception as exc:
            raise GatewayDenied("ASSET_EGRESS_POLICY_ERROR", type(exc).__name__) from exc
        if decision.get("status") != "ALLOW":
            raise GatewayDenied("ASSET_EGRESS_DENIED", str(decision.get("reason_code", "DENY")))
        effective = dict(request)
        effective_arguments = dict(arguments)
        effective_arguments["_fa3_asset_egress_decision"] = decision
        effective["arguments"] = effective_arguments
        effective["asset_egress_decision"] = decision
        return effective

    def _validate_secret_refs(self, request: dict[str, Any]) -> None:
        if "secrets" in request or "credential" in request or "token" in request:
            raise GatewayDenied("INLINE_SECRET_FORBIDDEN", "Durable/inline credential material is forbidden")
        refs = request.get("secret_refs", [])
        if refs is None:
            refs = []
        if not isinstance(refs, list) or any(not _nonempty(ref) for ref in refs):
            raise GatewayDenied("INVALID_SECRET_REFERENCE", "Secret references must be opaque non-empty ids")

    def invoke(self, request: dict[str, Any], peer_context: dict[str, Any] | None = None) -> dict[str, Any]:
        started = time.time()
        peer_context = peer_context or {}
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
            self._validate_secret_refs(request)
            binding = self._select_binding(capability, request.get("provider_id"))
            effective_request = self._resolve_policy(request, capability, binding, peer_context)
            self._validate_policy(effective_request, capability)
            self._validate_policy_scope(effective_request, binding)
            self._validate_hrb(effective_request, capability)
            self._validate_approval(effective_request, capability, binding)
            effective_request = self._apply_asset_egress(effective_request, binding)
            adapter = self.adapters[binding["adapter_id"]]
            if adapter.provider_id != binding.get("provider_id"):
                raise GatewayDenied("PROVIDER_BINDING_MISMATCH", "Adapter/provider binding mismatch")
            result = adapter.handler(effective_request["arguments"])
            if not isinstance(result, dict):
                raise GatewayDenied("INVALID_RESULT_SCHEMA", "Adapter result must be an object")
            receipt = self._receipt(
                request=effective_request,
                status="success",
                reason_code="DISPATCH_PASS",
                started=started,
                provider_id=adapter.provider_id,
                adapter_id=adapter.adapter_id,
                result=result,
            )
            if binding.get("receipt_audit_required") is True:
                if adapter.receipt_handler is None:
                    raise GatewayDenied("AUDIT_HANDLER_UNAVAILABLE", "Required retrieval audit handler is unavailable")
                try:
                    adapter.receipt_handler(effective_request, receipt)
                except GatewayDenied:
                    raise
                except Exception as exc:
                    raise GatewayDenied("AUDIT_WRITE_FAILED", f"Required retrieval audit failed: {type(exc).__name__}") from exc
            return receipt
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
        egress = request.get("asset_egress_decision") if isinstance(request.get("asset_egress_decision"), dict) else {}
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
            "asset_egress_decision_id": egress.get("decision_id"),
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
