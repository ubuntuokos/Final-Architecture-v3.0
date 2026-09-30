#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TRUST_ALLOWED = {"ADMITTED"}
INSTALL_ALLOWED = {"INSTALLED"}
ACTIVATION_ALLOWED = {"ENABLED", "ACTIVE"}
AI_CLASSES = {"AI_NONE", "AI_OPTIONAL", "AI_REQUIRED"}
EXECUTION_CLASSES = {
    "CONTENT_ONLY", "WASM_SANDBOXED", "PROCESS_ISOLATED", "VENV_ISOLATED",
    "IN_PROCESS_TRUSTED", "HOST_NATIVE", "MCP_PROVIDER", "EXTERNAL_BRIDGE",
}
REQUIRED_SECTIONS = {
    "identity","source","package_class","execution_class","host_bindings","abi",
    "capabilities","consumes","permissions","ai","dependencies","conflicts","resources",
    "entrypoints","ui_contributions","migrations","rollback","license","sbom",
    "signatures","evidence",
}

@dataclass(frozen=True)
class ExecutionDecision:
    allowed: bool
    reasons: tuple[str, ...]

def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != "fa3.plugin-extension.manifest.v1":
        errors.append("manifest-schema")
    missing = sorted(REQUIRED_SECTIONS - set(manifest))
    errors.extend(f"missing:{x}" for x in missing)
    if manifest.get("execution_class") not in EXECUTION_CLASSES:
        errors.append("execution-class")
    ai = manifest.get("ai", {})
    if not isinstance(ai, dict) or ai.get("class") not in AI_CLASSES:
        errors.append("ai-class")
    if manifest.get("silent_install") is True or manifest.get("silent_activation") is True:
        errors.append("silent-lifecycle-forbidden")
    return errors

def effective_execution_allowed(state: dict[str, Any]) -> ExecutionDecision:
    reasons: list[str] = []
    checks = [
        (state.get("trust") in TRUST_ALLOWED, "not-admitted"),
        (state.get("installation") in INSTALL_ALLOWED, "not-installed"),
        (state.get("activation") in ACTIVATION_ALLOWED, "not-enabled"),
        (state.get("compatible") is True, "incompatible"),
        (state.get("permission_allowed") is True, "permission-denied"),
        (state.get("layer_allowed") is True, "layer-denied"),
        (state.get("coexistence_pass") is True, "coexistence-failed"),
        (state.get("resource_admitted") is True, "resource-not-admitted"),
        (state.get("required_evidence_valid") is True, "evidence-invalid"),
        (state.get("host_binding_valid") is True, "host-binding-invalid"),
    ]
    for ok, reason in checks:
        if not ok:
            reasons.append(reason)

    ai_class = state.get("ai_class", "AI_NONE")
    if ai_class != "AI_NONE" and state.get("ai_requested") is True:
        for ok, reason in [
            (state.get("ai_policy_allowed") is True, "ai-policy-denied"),
            (state.get("model_router_allowed") is True, "model-router-denied"),
            (state.get("requested_provider_allowed") is True, "provider-denied"),
        ]:
            if not ok:
                reasons.append(reason)

    return ExecutionDecision(not reasons, tuple(reasons))

def shared_binding_state(package: dict[str, Any], application_id: str) -> dict[str, Any]:
    bindings = package.get("consumer_bindings", {})
    value = bindings.get(application_id, {})
    return {
        "package_id": package.get("id"),
        "application_id": application_id,
        "installed_once": package.get("installation") == "INSTALLED",
        "enabled": value.get("enabled") is True,
        "context_application": application_id,
    }


def plugin_visibility_state(package: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Project one package into a context-filtered application manager view."""
    if context.get("global_catalog") is True:
        return {"visible": True, "state": "GLOBAL_CATALOG", "reason": None}

    app_id = context.get("application_id")
    if not app_id:
        return {"visible": False, "state": "HIDDEN", "reason": "application-context-required"}

    required_caps = set(package.get("requires_capabilities", []))
    app_caps = set(context.get("application_capabilities", []))
    explicit_apps = set(package.get("supported_applications", []))
    excluded_apps = set(package.get("excluded_applications", []))

    if app_id in excluded_apps:
        return {"visible": False, "state": "HIDDEN", "reason": "application-excluded"}
    if explicit_apps and app_id not in explicit_apps:
        return {"visible": False, "state": "HIDDEN", "reason": "not-applicable-to-application"}
    if required_caps and not required_caps.issubset(app_caps):
        return {"visible": False, "state": "HIDDEN", "reason": "capability-mismatch"}
    if context.get("compatible") is False:
        return {"visible": False, "state": "HIDDEN", "reason": "incompatible"}
    if context.get("policy_denied") is True:
        return {
            "visible": context.get("diagnostic_view") is True,
            "state": "DENIED",
            "reason": "policy-denied",
        }
    if context.get("temporarily_available") is False:
        return {"visible": True, "state": "TEMP_UNAVAILABLE", "reason": "runtime-or-dependency-unavailable"}

    installed = package.get("installation") == "INSTALLED"
    return {
        "visible": True,
        "state": "AVAILABLE" if installed else "INSTALLABLE",
        "reason": None,
    }

def project_packages_for_application(packages: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for package in packages:
        visibility = plugin_visibility_state(package, context)
        if visibility["visible"]:
            out.append({**package, "applicability": visibility})
    return out
