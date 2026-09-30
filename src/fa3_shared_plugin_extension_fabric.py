#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

COMPONENT_KINDS = {"PLUGIN", "EXTENSION"}
TRI_STATE = {"ENABLED", "DISABLED", "INHERIT"}
MODEL_ROUTER = "FA3-AUTH-MODEL-ROUTER-001"
HRB = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
SECURITY = "FA3-AUTH-SECURITY-GOV-001"


class SharedComponentError(ValueError):
    pass


@dataclass(frozen=True)
class BindingDecision:
    application_id: str
    component_id: str
    eligible: bool
    added_capabilities: tuple[str, ...]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "component_id": self.component_id,
            "eligible": self.eligible,
            "added_capabilities": list(self.added_capabilities),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class AIAccessDecision:
    allowed: bool
    reason: str
    route_authority: str | None
    local_allowed: bool
    remote_allowed: bool
    silent_fallback_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "route_authority": self.route_authority,
            "local_allowed": self.local_allowed,
            "remote_allowed": self.remote_allowed,
            "silent_fallback_allowed": self.silent_fallback_allowed,
        }


def _strings(value: Any, field: str, *, nonempty: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise SharedComponentError(f"{field} must be a list")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or (nonempty and not item.strip()):
            raise SharedComponentError(f"{field} contains invalid value")
        out.append(item.strip())
    return out


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise SharedComponentError("manifest must be an object")
    if manifest.get("schema") != "fa3.shared-plugin-extension-manifest.v1":
        raise SharedComponentError("unsupported manifest schema")
    component_id = manifest.get("component_id")
    if not isinstance(component_id, str) or not component_id.startswith("FA3-"):
        raise SharedComponentError("component_id must be an FA3 id")
    kind = manifest.get("kind")
    if kind not in COMPONENT_KINDS:
        raise SharedComponentError("kind must be PLUGIN or EXTENSION")
    if manifest.get("scope") != "SHARED":
        raise SharedComponentError("plugin/extension scope must be SHARED")
    if manifest.get("authority") is not False:
        raise SharedComponentError("shared component cannot be an authority")
    if manifest.get("automatic_activation") is not False:
        raise SharedComponentError("automatic activation is forbidden")

    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict):
        raise SharedComponentError("capabilities object required")
    provides = _strings(capabilities.get("provides"), "capabilities.provides")
    requires = _strings(capabilities.get("requires_host"), "capabilities.requires_host")
    if not provides:
        raise SharedComponentError("at least one provided capability is required")
    if set(provides) & set(requires):
        raise SharedComponentError("provided and required host capabilities overlap")

    contracts = _strings(manifest.get("host_contracts"), "host_contracts")
    if not contracts:
        raise SharedComponentError("at least one host contract is required")

    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict):
        raise SharedComponentError("provenance required")
    for key in ("source", "immutable_revision", "content_sha256", "license"):
        if not isinstance(provenance.get(key), str) or not provenance[key].strip():
            raise SharedComponentError(f"provenance.{key} required")
    digest = provenance["content_sha256"]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
        raise SharedComponentError("provenance.content_sha256 must be sha256 hex")

    ai = manifest.get("ai")
    if not isinstance(ai, dict):
        raise SharedComponentError("ai declaration required")
    uses_ai = ai.get("uses_ai")
    if not isinstance(uses_ai, bool):
        raise SharedComponentError("ai.uses_ai must be boolean")
    ai_caps = _strings(ai.get("capabilities", []), "ai.capabilities")
    if uses_ai and not ai_caps:
        raise SharedComponentError("AI-using component must declare AI capabilities")
    if not uses_ai and ai_caps:
        raise SharedComponentError("non-AI component cannot declare AI capabilities")
    if ai.get("direct_provider_access") is not False:
        raise SharedComponentError("direct AI provider access is forbidden")
    if ai.get("silent_fallback") is not False:
        raise SharedComponentError("silent AI fallback is forbidden")
    if ai.get("route_authority") != MODEL_ROUTER:
        raise SharedComponentError("AI route authority must be the FA3 Model Router")
    if ai.get("default_access") not in {"ENABLED", "DISABLED"}:
        raise SharedComponentError("ai.default_access must be ENABLED or DISABLED")
    if manifest.get("runtime", {}).get("hardware_authority") != HRB:
        raise SharedComponentError("hardware authority must remain HRB")
    if manifest.get("security", {}).get("admission_authority") != SECURITY:
        raise SharedComponentError("security admission authority mismatch")

    return manifest


def binding_decision(manifest: dict[str, Any], application: dict[str, Any]) -> BindingDecision:
    validate_manifest(manifest)
    app_id = application.get("application_id")
    if not isinstance(app_id, str) or not app_id:
        raise SharedComponentError("application_id required")

    reasons: list[str] = []
    if application.get("component_binding_enabled", True) is not True:
        reasons.append("APPLICATION_COMPONENT_BINDING_DISABLED")
    accepted_kinds = set(_strings(application.get("accepted_component_kinds", ["PLUGIN", "EXTENSION"]), "accepted_component_kinds"))
    if manifest["kind"] not in accepted_kinds:
        reasons.append("COMPONENT_KIND_NOT_ACCEPTED")

    host_caps = set(_strings(application.get("host_capabilities", []), "host_capabilities"))
    required = set(manifest["capabilities"]["requires_host"])
    missing = sorted(required - host_caps)
    if missing:
        reasons.append("MISSING_HOST_CAPABILITIES:" + ",".join(missing))

    host_contracts = set(_strings(application.get("host_contracts", []), "application.host_contracts"))
    missing_contracts = sorted(set(manifest["host_contracts"]) - host_contracts)
    if missing_contracts:
        reasons.append("MISSING_HOST_CONTRACTS:" + ",".join(missing_contracts))

    deny = set(_strings(application.get("denied_components", []), "denied_components"))
    if manifest["component_id"] in deny:
        reasons.append("COMPONENT_EXPLICITLY_DENIED")

    existing = set(_strings(application.get("capabilities", []), "application.capabilities"))
    provides = set(manifest["capabilities"]["provides"])
    added = tuple(sorted(provides - existing))
    if not added:
        reasons.append("NO_CAPABILITY_GAIN")

    return BindingDecision(
        application_id=app_id,
        component_id=manifest["component_id"],
        eligible=not reasons,
        added_capabilities=added,
        reasons=tuple(reasons),
    )


def derive_bindings(manifest: dict[str, Any], applications: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [binding_decision(manifest, app).as_dict() for app in applications]


def _state(scope: dict[str, Any] | None, key: str = "state") -> str:
    if scope is None:
        return "INHERIT"
    value = scope.get(key, "INHERIT")
    if value not in TRI_STATE:
        raise SharedComponentError(f"invalid AI access state: {value}")
    return value


def ai_access_decision(
    manifest: dict[str, Any],
    *,
    capability: str,
    global_policy: dict[str, Any],
    application_policy: dict[str, Any] | None = None,
    module_policy: dict[str, Any] | None = None,
    component_policy: dict[str, Any] | None = None,
    capability_policy: dict[str, Any] | None = None,
    requested_route: str = "LOCAL",
) -> AIAccessDecision:
    validate_manifest(manifest)
    ai = manifest["ai"]
    if capability not in set(ai["capabilities"]):
        return AIAccessDecision(False, "AI_CAPABILITY_NOT_DECLARED", None, False, False, False)
    if not ai["uses_ai"]:
        return AIAccessDecision(False, "COMPONENT_DOES_NOT_USE_AI", None, False, False, False)

    if requested_route not in {"LOCAL", "REMOTE"}:
        raise SharedComponentError("requested_route must be LOCAL or REMOTE")

    scopes = (
        ("GLOBAL", _state(global_policy)),
        ("APPLICATION", _state(application_policy)),
        ("MODULE", _state(module_policy)),
        ("COMPONENT", _state(component_policy)),
        ("CAPABILITY", _state(capability_policy)),
    )
    for label, state in scopes:
        if state == "DISABLED":
            return AIAccessDecision(False, f"{label}_AI_DISABLED", None, False, False, False)

    explicit_enabled = any(state == "ENABLED" for _, state in scopes)
    default_enabled = ai["default_access"] == "ENABLED"
    if not (explicit_enabled or default_enabled):
        return AIAccessDecision(False, "AI_NOT_EXPLICITLY_ENABLED", None, False, False, False)

    local_allowed = bool(global_policy.get("local_allowed", True))
    remote_allowed = bool(global_policy.get("remote_allowed", False))
    for policy in (application_policy, module_policy, component_policy, capability_policy):
        if policy is None:
            continue
        if policy.get("local_allowed") is False:
            local_allowed = False
        if policy.get("remote_allowed") is False:
            remote_allowed = False
        if policy.get("remote_allowed") is True and not global_policy.get("remote_allowed", False):
            remote_allowed = False

    if requested_route == "LOCAL" and not local_allowed:
        return AIAccessDecision(False, "LOCAL_AI_ROUTE_DISABLED", None, local_allowed, remote_allowed, False)
    if requested_route == "REMOTE" and not remote_allowed:
        return AIAccessDecision(False, "REMOTE_AI_ROUTE_DISABLED", None, local_allowed, remote_allowed, False)

    return AIAccessDecision(True, "AI_ACCESS_ALLOWED", MODEL_ROUTER, local_allowed, remote_allowed, False)


def runtime_request(
    manifest: dict[str, Any],
    *,
    capability: str,
    ai_decision: AIAccessDecision,
    application_id: str,
    module_id: str | None = None,
) -> dict[str, Any]:
    validate_manifest(manifest)
    if not ai_decision.allowed:
        raise SharedComponentError(f"AI access denied: {ai_decision.reason}")
    return {
        "schema": "fa3.shared-component-ai-request.v1",
        "component_id": manifest["component_id"],
        "application_id": application_id,
        "module_id": module_id,
        "capability": capability,
        "model_route_authority": MODEL_ROUTER,
        "provider_id": None,
        "model_id": None,
        "direct_provider_access": False,
        "silent_fallback": False,
        "hardware_authority": HRB,
    }
