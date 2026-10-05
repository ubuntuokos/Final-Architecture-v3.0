#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol

ACTION_SCHEMA = "fa3.uaf.action-contract.v1"
RESULT_SCHEMA = "fa3.uaf.action-result.v1"
CONTEXT_SCHEMA = "fa3.uaf.execution-context.v1"
EVIDENCE_SCHEMA = "fa3.uaf.evidence-receipt.v1"


class UafError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ActionContract:
    action_id: str
    version: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    semantics: dict[str, Any]
    exposure: dict[str, Any]
    security: dict[str, Any]
    resources: dict[str, Any]
    provider: dict[str, Any]
    evidence: dict[str, Any]
    source_path: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any], source_path: str | None = None) -> "ActionContract":
        if raw.get("schema") != ACTION_SCHEMA:
            raise UafError("UAF-CONTRACT-VERSION-INVALID", "unsupported action contract schema")
        action_id = str(raw.get("id", "")).strip()
        version = str(raw.get("version", "")).strip()
        if not action_id or not version:
            raise UafError("UAF-CONTRACT-VERSION-INVALID", "action id/version required")
        return cls(
            action_id=action_id,
            version=version,
            description=str(raw.get("description", "")),
            input_schema=_object(raw.get("input_schema"), "input_schema"),
            output_schema=_object(raw.get("output_schema"), "output_schema"),
            semantics=_object(raw.get("semantics"), "semantics"),
            exposure=_object(raw.get("exposure"), "exposure"),
            security=_object(raw.get("security"), "security"),
            resources=_object(raw.get("resources"), "resources"),
            provider=_object(raw.get("provider"), "provider"),
            evidence=_object(raw.get("evidence"), "evidence"),
            source_path=source_path,
        )


@dataclass(frozen=True)
class ExecutionContext:
    context_id: str
    workspace: str | None = None
    application: str | None = None
    project: str | None = None
    selection: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": CONTEXT_SCHEMA,
            "context_id": self.context_id,
            "workspace": self.workspace,
            "application": self.application,
            "project": self.project,
            "selection": dict(self.selection),
            "session_id": self.session_id,
        }


@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    arguments: dict[str, Any]
    principal: dict[str, Any]
    context: ExecutionContext
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requested_version: str | None = None
    approval: dict[str, Any] | None = None
    secret_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    action_ids: tuple[str, ...]
    capabilities: tuple[str, ...] = ()
    priority: int = 100
    state: str = "CONNECTED"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionResult:
    request_id: str
    trace_id: str
    action_id: str
    contract_version: str
    provider_id: str
    status: str
    output: dict[str, Any]
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": RESULT_SCHEMA,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "action_id": self.action_id,
            "contract_version": self.contract_version,
            "provider_id": self.provider_id,
            "status": self.status,
            "output": self.output,
            "evidence": self.evidence,
        }


class ActionProvider(Protocol):
    descriptor: ProviderDescriptor
    def execute(
        self,
        request: ActionRequest,
        resource_lease: Any = None,
        secret_leases: tuple[Any, ...] = (),
    ) -> dict[str, Any]: ...


class CallableProvider:
    def __init__(
        self,
        descriptor: ProviderDescriptor,
        handler: Callable[[ActionRequest, Any, tuple[Any, ...]], dict[str, Any]],
    ):
        self.descriptor = descriptor
        self._handler = handler

    def execute(
        self,
        request: ActionRequest,
        resource_lease: Any = None,
        secret_leases: tuple[Any, ...] = (),
    ) -> dict[str, Any]:
        return self._handler(request, resource_lease, secret_leases)


class ActionRegistry:
    def __init__(self, contracts: list[ActionContract]):
        self._contracts: dict[str, ActionContract] = {}
        for contract in contracts:
            if contract.action_id in self._contracts:
                raise UafError(
                    "UAF-CONTRACT-VERSION-INVALID",
                    f"duplicate action id: {contract.action_id}",
                )
            self._contracts[contract.action_id] = contract

    @classmethod
    def from_directory(cls, root: Path) -> "ActionRegistry":
        contracts: list[ActionContract] = []
        for path in sorted(root.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            contracts.append(ActionContract.from_dict(raw, source_path=path.as_posix()))
        if not contracts:
            raise UafError("UAF-CONTRACT-NOT-FOUND", "action registry is empty")
        return cls(contracts)

    def get(self, action_id: str) -> ActionContract:
        try:
            return self._contracts[action_id]
        except KeyError as exc:
            raise UafError(
                "UAF-CONTRACT-NOT-FOUND", f"unknown action: {action_id}"
            ) from exc

    def list(self) -> list[ActionContract]:
        return [self._contracts[key] for key in sorted(self._contracts)]


class ProviderRegistry:
    """Non-authoritative provider catalog. HRB remains resource authority."""

    def __init__(self) -> None:
        self._providers: dict[str, ActionProvider] = {}

    def register(self, provider: ActionProvider) -> None:
        pid = provider.descriptor.provider_id
        if not pid:
            raise UafError("UAF-NO-COMPATIBLE-PROVIDER", "provider id required")
        if pid in self._providers:
            raise UafError(
                "UAF-NO-COMPATIBLE-PROVIDER", f"duplicate provider id: {pid}"
            )
        self._providers[pid] = provider

    def list_descriptors(self) -> list[ProviderDescriptor]:
        return [self._providers[key].descriptor for key in sorted(self._providers)]

    def select(
        self,
        action_id: str,
        *,
        decision_fabric: Any = None,
        decision_provider_id: str = "FA3-PROVIDER-DECISION-RULES-001",
        decision_state: Any = None,
        decision_rollout: str = "SHADOW",
    ) -> ActionProvider:
        candidates = [
            provider
            for provider in self._providers.values()
            if action_id in provider.descriptor.action_ids
            and provider.descriptor.state == "CONNECTED"
        ]
        if not candidates:
            raise UafError(
                "UAF-NO-COMPATIBLE-PROVIDER",
                f"no connected provider for {action_id}",
            )
        candidates.sort(
            key=lambda provider: (
                provider.descriptor.priority,
                provider.descriptor.provider_id,
            )
        )
        deterministic = candidates[0]
        if decision_fabric is None:
            return deterministic

        trace = decision_fabric.decide(
            {
                "contract": "SELECT_ONE",
                "purpose": "Select one already-connected UAF provider for an already-authorized action",
                "candidates": [
                    {
                        "id": provider.descriptor.provider_id,
                        "description": ",".join(provider.descriptor.capabilities),
                        "metadata": {"priority": -provider.descriptor.priority},
                    }
                    for provider in candidates
                ],
                "constraints": {},
                "policy_context": {
                    "action_id": action_id,
                    "execution_authority": "FA3-UNIFIED-ACTION-FABRIC-001",
                    "authorization_already_required": True,
                },
                "evidence_refs": [],
                "state": decision_state,
                "failure_policy": "EXISTING_BEHAVIOR",
                "rollout": decision_rollout,
                "final_policy_owner": "FA3-UNIFIED-ACTION-FABRIC-001",
            },
            decision_provider_id,
        )
        if decision_rollout != "ACTIVE" or trace.get("status") != "DECIDED":
            return deterministic
        selected = (trace.get("result") or {}).get("selected")
        for provider in candidates:
            if provider.descriptor.provider_id == selected:
                return provider
        raise UafError("UAF-NO-COMPATIBLE-PROVIDER", "Decision Fabric selected a provider outside the connected candidate set")


class ActionDispatcher:
    def __init__(
        self,
        registry: ActionRegistry,
        providers: ProviderRegistry,
        *,
        authorize: Callable[[ActionRequest, ActionContract], bool] | None = None,
        verify_approval: Callable[[ActionRequest, ActionContract], bool] | None = None,
        acquire_resources: Callable[
            [ActionRequest, ActionContract, ProviderDescriptor], Any
        ] | None = None,
        release_resources: Callable[[Any], None] | None = None,
        acquire_secret_lease: Callable[
            [str, ActionRequest, ActionContract, ProviderDescriptor], Any
        ] | None = None,
        release_secret_lease: Callable[[Any], None] | None = None,
        evidence_sink: Callable[[dict[str, Any]], None] | None = None,
        decision_fabric: Any = None,
        decision_provider_id: str = "FA3-PROVIDER-DECISION-RULES-001",
        decision_rollout: str = "SHADOW",
    ) -> None:
        self.registry = registry
        self.providers = providers
        self.authorize = authorize
        self.verify_approval = verify_approval
        self.acquire_resources = acquire_resources
        self.release_resources = release_resources
        self.acquire_secret_lease = acquire_secret_lease
        self.release_secret_lease = release_secret_lease
        self.evidence_sink = evidence_sink
        self.decision_fabric = decision_fabric
        self.decision_provider_id = decision_provider_id
        self.decision_rollout = decision_rollout

    def execute(self, request: ActionRequest) -> ActionResult:
        started = int(time.time())
        contract = self.registry.get(request.action_id)
        if request.requested_version and request.requested_version != contract.version:
            raise UafError(
                "UAF-CONTRACT-VERSION-INVALID",
                "requested action version unavailable",
            )
        _reject_inline_secret_fields(request.arguments)
        _validate_schema(request.arguments, contract.input_schema, "UAF-INPUT-INVALID")
        _validate_principal(request.principal)
        if self.authorize is None or self.authorize(request, contract) is not True:
            raise UafError(
                "UAF-UNAUTHORIZED", "external authorization did not allow action"
            )
        if _approval_required(contract):
            _validate_approval_grant(request, contract)
            if self.verify_approval is None or self.verify_approval(
                request, contract
            ) is not True:
                raise UafError(
                    "UAF-APPROVAL-REQUIRED",
                    "approval authority did not confirm/consume grant",
                )
        provider = self.providers.select(
            request.action_id,
            decision_fabric=self.decision_fabric,
            decision_provider_id=self.decision_provider_id,
            decision_state={
                "request_id": request.request_id,
                "context": request.context.as_dict(),
                "principal": request.principal,
            },
            decision_rollout=self.decision_rollout,
        )
        resource_lease: Any = None
        secret_leases: list[Any] = []
        try:
            if _hrb_required(contract):
                if self.acquire_resources is None:
                    raise UafError(
                        "UAF-RESOURCE-DENIED",
                        "HRB adapter required but unavailable",
                    )
                resource_lease = self.acquire_resources(
                    request, contract, provider.descriptor
                )
                if resource_lease is None:
                    raise UafError(
                        "UAF-RESOURCE-DENIED",
                        "HRB admission did not return a lease",
                    )
            if request.secret_refs:
                if self.acquire_secret_lease is None:
                    raise UafError(
                        "UAF-SECRET-DENIED",
                        "Secret Broker adapter required but unavailable",
                    )
                for secret_ref in request.secret_refs:
                    if not _opaque_ref(secret_ref):
                        raise UafError(
                            "UAF-SECRET-DENIED",
                            "invalid opaque secret reference",
                        )
                    lease = self.acquire_secret_lease(
                        secret_ref, request, contract, provider.descriptor
                    )
                    if lease is None:
                        raise UafError(
                            "UAF-SECRET-DENIED",
                            "secret projection lease denied",
                        )
                    secret_leases.append(lease)
            output = provider.execute(
                request, resource_lease, tuple(secret_leases)
            )
            if not isinstance(output, dict):
                raise UafError(
                    "UAF-OUTPUT-INVALID", "provider output must be an object"
                )
            _validate_schema(
                output, contract.output_schema, "UAF-OUTPUT-INVALID"
            )
            receipt = _evidence_receipt(
                request,
                contract,
                provider.descriptor,
                output,
                started,
                resource_lease,
                tuple(secret_leases),
            )
            if contract.evidence.get("required") is True:
                if self.evidence_sink is None:
                    raise UafError(
                        "UAF-EVIDENCE-FAILED",
                        "required evidence sink unavailable",
                    )
                self.evidence_sink(receipt)
            return ActionResult(
                request_id=request.request_id,
                trace_id=request.trace_id,
                action_id=contract.action_id,
                contract_version=contract.version,
                provider_id=provider.descriptor.provider_id,
                status="success",
                output=output,
                evidence=receipt,
            )
        finally:
            for lease in reversed(secret_leases):
                if self.release_secret_lease is not None:
                    self.release_secret_lease(lease)
            if resource_lease is not None and self.release_resources is not None:
                self.release_resources(resource_lease)


def build_reference_runtime(
    action_dir: Path,
    *,
    authorize: Callable[[ActionRequest, ActionContract], bool],
    evidence_sink: Callable[[dict[str, Any]], None],
) -> ActionDispatcher:
    registry = ActionRegistry.from_directory(action_dir)
    providers = ProviderRegistry()

    def capabilities(
        request: ActionRequest, _resource: Any, _secrets: tuple[Any, ...]
    ) -> dict[str, Any]:
        return {"actions": [contract.action_id for contract in registry.list()]}

    def provider_list(
        request: ActionRequest, _resource: Any, _secrets: tuple[Any, ...]
    ) -> dict[str, Any]:
        return {
            "providers": [
                descriptor.provider_id
                for descriptor in providers.list_descriptors()
            ]
        }

    providers.register(
        CallableProvider(
            ProviderDescriptor(
                "FA3-UAF-REFERENCE-CAPABILITIES-001",
                ("system.capabilities.list",),
                priority=10,
            ),
            capabilities,
        )
    )
    providers.register(
        CallableProvider(
            ProviderDescriptor(
                "FA3-UAF-REFERENCE-PROVIDERS-001",
                ("system.providers.list",),
                priority=10,
            ),
            provider_list,
        )
    )
    register_hardware_discovery_provider(providers)
    return ActionDispatcher(
        registry,
        providers,
        authorize=authorize,
        evidence_sink=evidence_sink,
    )


def register_hardware_discovery_provider(providers: ProviderRegistry) -> None:
    from fa3_hardware_discovery import (
        discover_accelerator_devices,
        discover_cpu_topology,
    )

    def hardware_describe(
        request: ActionRequest, _resource: Any, _secrets: tuple[Any, ...]
    ) -> dict[str, Any]:
        return {
            "cpu": discover_cpu_topology(),
            "accelerators": [
                device.as_dict() for device in discover_accelerator_devices()
            ],
        }

    providers.register(
        CallableProvider(
            ProviderDescriptor(
                provider_id="FA3-UAF-HARDWARE-DISCOVERY-ADAPTER-001",
                action_ids=("hardware.describe",),
                capabilities=("hardware.discovery",),
                priority=10,
                metadata={
                    "authority": "NON_AUTHORITY_ADAPTER",
                    "source": "FA3-HARDWARE-DISCOVERY-CONTRACTS-001",
                },
            ),
            hardware_describe,
        )
    )


def _object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise UafError(
            "UAF-CONTRACT-VERSION-INVALID",
            f"{field_name} must be object",
        )
    return value


def _validate_principal(principal: dict[str, Any]) -> None:
    if not isinstance(principal, dict) or not str(principal.get("id", "")).strip():
        raise UafError("UAF-UNAUTHORIZED", "principal identity required")


def _approval_required(contract: ActionContract) -> bool:
    return str(contract.security.get("approval", "policy")) in {
        "session",
        "explicit",
        "strong",
        "conditional",
    }


def _hrb_required(contract: ActionContract) -> bool:
    return contract.resources.get("hrb_required") is True


def _opaque_ref(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 256
        and not any(
            marker in value.lower()
            for marker in ("password=", "token=", "api_key=")
        )
    )


def _reject_inline_secret_fields(value: Any, path: str = "arguments") -> None:
    suspicious = {
        "password",
        "passwd",
        "token",
        "api_key",
        "apikey",
        "secret",
        "credential",
        "private_key",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in suspicious:
                raise UafError(
                    "UAF-SECRET-DENIED",
                    f"inline secret field forbidden: {path}.{key}",
                )
            _reject_inline_secret_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_inline_secret_fields(child, f"{path}[{index}]")


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _parse_expiry(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        raise UafError(
            "UAF-APPROVAL-INVALID", "approval expiry required"
        )
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
        return parsed.timestamp()
    except ValueError as exc:
        raise UafError(
            "UAF-APPROVAL-INVALID",
            "approval expiry must be timezone-aware ISO-8601",
        ) from exc


def _validate_approval_grant(
    request: ActionRequest, contract: ActionContract
) -> None:
    approval = request.approval
    if not isinstance(approval, dict):
        raise UafError(
            "UAF-APPROVAL-REQUIRED", "approval grant required"
        )
    required = (
        "approval_id",
        "principal_ref",
        "action_id",
        "action_version",
        "argument_digest",
        "context_digest",
        "expires_at",
        "single_use",
    )
    if any(key not in approval for key in required):
        raise UafError(
            "UAF-APPROVAL-INVALID",
            "approval grant missing required binding",
        )
    if approval.get("principal_ref") != str(request.principal.get("id")):
        raise UafError(
            "UAF-APPROVAL-INVALID", "approval principal mismatch"
        )
    if (
        approval.get("action_id") != contract.action_id
        or approval.get("action_version") != contract.version
    ):
        raise UafError(
            "UAF-APPROVAL-INVALID",
            "approval action/version mismatch",
        )
    if approval.get("argument_digest") != _canonical_digest(
        request.arguments
    ):
        raise UafError(
            "UAF-APPROVAL-INVALID",
            "approval argument digest mismatch",
        )
    if approval.get("context_digest") != _canonical_digest(
        request.context.as_dict()
    ):
        raise UafError(
            "UAF-APPROVAL-INVALID",
            "approval context digest mismatch",
        )
    if approval.get("single_use") is not True:
        raise UafError(
            "UAF-APPROVAL-INVALID", "approval must be single-use"
        )
    if _parse_expiry(approval.get("expires_at")) <= time.time():
        raise UafError("UAF-APPROVAL-INVALID", "approval expired")


def _lease_ref(lease: Any) -> str | None:
    if lease is None:
        return None
    if isinstance(lease, dict):
        for key in ("lease_id", "grant_id", "id"):
            value = lease.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None
    for key in ("lease_id", "grant_id", "id"):
        value = getattr(lease, key, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _evidence_receipt(
    request: ActionRequest,
    contract: ActionContract,
    provider: ProviderDescriptor,
    output: dict[str, Any],
    started: int,
    resource_lease: Any = None,
    secret_leases: tuple[Any, ...] = (),
) -> dict[str, Any]:
    return {
        "schema": EVIDENCE_SCHEMA,
        "request_id": request.request_id,
        "trace_id": request.trace_id,
        "action_id": contract.action_id,
        "contract_version": contract.version,
        "principal_ref": str(request.principal.get("id")),
        "context_digest": _canonical_digest(request.context.as_dict()),
        "argument_digest": _canonical_digest(request.arguments),
        "provider_id": provider.provider_id,
        "resource_lease_ref": _lease_ref(resource_lease),
        "secret_lease_refs": [
            ref
            for ref in (_lease_ref(lease) for lease in secret_leases)
            if ref is not None
        ],
        "result_digest": _canonical_digest(output),
        "started_epoch": started,
        "completed_epoch": int(time.time()),
        "status": "PASS",
        "global_promotion_claim": False,
    }


def _validate_schema(
    value: Any, schema: dict[str, Any], code: str
) -> None:
    """Dependency-free fail-closed subset for UAF bootstrap action schemas."""
    typ = schema.get("type")
    if typ == "object":
        if not isinstance(value, dict):
            raise UafError(code, "object required")
        required = schema.get("required", [])
        if not isinstance(required, list):
            raise UafError(code, "invalid required declaration")
        missing = [key for key in required if key not in value]
        if missing:
            raise UafError(
                code,
                "missing required fields: " + ",".join(map(str, missing)),
            )
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise UafError(code, "invalid properties declaration")
        if schema.get("additionalProperties", True) is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                raise UafError(
                    code, "unknown fields: " + ",".join(unknown)
                )
        for key, subschema in properties.items():
            if key in value:
                if not isinstance(subschema, dict):
                    raise UafError(code, f"invalid schema for {key}")
                _validate_schema(value[key], subschema, code)
        return
    if typ == "array":
        if not isinstance(value, list):
            raise UafError(code, "array required")
        items = schema.get("items")
        if isinstance(items, dict):
            for item in value:
                _validate_schema(item, items, code)
        return
    if typ == "string":
        if not isinstance(value, str):
            raise UafError(code, "string required")
        enum = schema.get("enum")
        if isinstance(enum, list) and value not in enum:
            raise UafError(code, "value not in enum")
        minimum = schema.get("minLength")
        if isinstance(minimum, int) and len(value) < minimum:
            raise UafError(code, "string shorter than minimum")
        return
    if typ == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise UafError(code, "integer required")
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, int) and value < minimum:
            raise UafError(code, "integer below minimum")
        if isinstance(maximum, int) and value > maximum:
            raise UafError(code, "integer above maximum")
        return
    if typ == "boolean":
        if not isinstance(value, bool):
            raise UafError(code, "boolean required")
        return
    if typ in (None, "null"):
        if typ == "null" and value is not None:
            raise UafError(code, "null required")
        return
    raise UafError(code, f"unsupported runtime schema type: {typ}")
