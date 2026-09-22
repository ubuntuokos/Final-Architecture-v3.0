#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

PROFILE_ID = "FA3-AI-COMMS-001"
MODEL_ROUTER_AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
POLICY_SCHEMA = "fa3.ai-comms-topology-policy.v1"

REPLACEMENT_TRIGGERS = {
    "MISSING_REQUIRED_CAPABILITY",
    "TASK_EXECUTION_INVALID",
    "UNAUTHORIZED_OPERATION_ATTEMPT",
    "AUTONOMOUS_SCOPE_EXPANSION_ATTEMPT",
    "UNAUTHORIZED_MODEL_APP_OR_RESOURCE_ATTEMPT",
}

SECURITY_EMERGENCY_TRIGGERS = {
    "ACTIVE_MALWARE",
    "RANSOMWARE_BEHAVIOR",
    "DESTRUCTIVE_FILE_ENCRYPTION",
    "ACTIVE_INTRUSION",
    "LATERAL_PROPAGATION",
    "CRITICAL_CREDENTIAL_COMPROMISE",
}


class CommunicationTopologyDenied(RuntimeError):
    pass


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CommunicationTopologyDenied(f"{name} must be a non-empty string")
    return value.strip()


def _role_set(app: dict[str, Any], app_id: str) -> set[str]:
    roles = app.get("model_roles")
    if not isinstance(roles, list) or not roles:
        raise CommunicationTopologyDenied(f"{app_id}: model_roles must be a non-empty list")
    result: set[str] = set()
    for item in roles:
        if not isinstance(item, dict):
            raise CommunicationTopologyDenied(f"{app_id}: each model role must be an object")
        role_id = _nonempty_string(item.get("role_id"), f"{app_id}.model_roles.role_id")
        if item.get("required_for_app") is not True:
            raise CommunicationTopologyDenied(f"{app_id}:{role_id}: every declared model role must be required_for_app=true")
        if role_id in result:
            raise CommunicationTopologyDenied(f"{app_id}: duplicate model role {role_id}")
        result.add(role_id)
    return result


def validate_topology_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise CommunicationTopologyDenied("topology policy must be an object")
    if policy.get("schema") != POLICY_SCHEMA:
        raise CommunicationTopologyDenied("unknown topology policy schema")
    applications = policy.get("applications")
    if not isinstance(applications, dict) or not applications:
        raise CommunicationTopologyDenied("applications must be a non-empty object")

    app_roles: dict[str, set[str]] = {}
    for raw_app_id, app in applications.items():
        app_id = _nonempty_string(raw_app_id, "application id")
        if not isinstance(app, dict):
            raise CommunicationTopologyDenied(f"{app_id}: application policy must be an object")
        roles = _role_set(app, app_id)
        primary = _nonempty_string(app.get("primary_model_role"), f"{app_id}.primary_model_role")
        if primary not in roles:
            raise CommunicationTopologyDenied(f"{app_id}: primary model role must be in the declared role set")
        if app.get("state") not in {"ACTIVE", "SLEEPING"}:
            raise CommunicationTopologyDenied(f"{app_id}: state must be ACTIVE or SLEEPING")
        if not isinstance(app.get("security_app"), bool):
            raise CommunicationTopologyDenied(f"{app_id}: security_app must be boolean")
        app_roles[app_id] = roles

    gateways = policy.get("cross_app_gateways")
    if not isinstance(gateways, list):
        raise CommunicationTopologyDenied("cross_app_gateways must be a list")
    seen_gateways: set[tuple[str, str, str]] = set()
    for gateway in gateways:
        if not isinstance(gateway, dict):
            raise CommunicationTopologyDenied("cross-app gateway entry must be an object")
        source = _nonempty_string(gateway.get("source_app"), "gateway.source_app")
        target = _nonempty_string(gateway.get("target_app"), "gateway.target_app")
        gateway_id = _nonempty_string(gateway.get("gateway_id"), "gateway.gateway_id")
        if source == target or source not in applications or target not in applications:
            raise CommunicationTopologyDenied("gateway endpoints must reference two distinct declared applications")
        if gateway.get("protected") is not True or gateway.get("bypass_forbidden") is not True:
            raise CommunicationTopologyDenied("cross-app gateway must be protected and bypass-forbidden")
        src_roles = set(gateway.get("allowed_source_roles") or [])
        dst_roles = set(gateway.get("allowed_target_roles") or [])
        if not src_roles or not dst_roles:
            raise CommunicationTopologyDenied("cross-app gateway must constrain source and target roles")
        if not src_roles.issubset(app_roles[source]) or not dst_roles.issubset(app_roles[target]):
            raise CommunicationTopologyDenied("gateway role allowlist references an undeclared model role")
        key = (source, target, gateway_id)
        if key in seen_gateways:
            raise CommunicationTopologyDenied("duplicate cross-app gateway binding")
        seen_gateways.add(key)

    emergency = policy.get("security_emergency_wake")
    if not isinstance(emergency, dict) or emergency.get("enabled") is not True:
        raise CommunicationTopologyDenied("security emergency wake policy is required and must be enabled")
    detectors = emergency.get("authorized_detectors")
    targets = emergency.get("target_security_apps")
    triggers = emergency.get("allowed_triggers")
    if not isinstance(detectors, list) or not detectors or not all(isinstance(x, str) and x.strip() for x in detectors):
        raise CommunicationTopologyDenied("authorized security detectors are required")
    if not isinstance(targets, list) or not targets:
        raise CommunicationTopologyDenied("security emergency target applications are required")
    for target in targets:
        if target not in applications or applications[target].get("security_app") is not True:
            raise CommunicationTopologyDenied("security emergency target must be a declared security application")
    if not isinstance(triggers, list) or not triggers or not set(triggers).issubset(SECURITY_EMERGENCY_TRIGGERS):
        raise CommunicationTopologyDenied("security emergency trigger set is invalid")
    if emergency.get("minimum_severity") != "CRITICAL":
        raise CommunicationTopologyDenied("security emergency wake requires CRITICAL severity")
    confidence = emergency.get("minimum_confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0.9 <= float(confidence) <= 1.0:
        raise CommunicationTopologyDenied("security emergency minimum confidence must be >= 0.90")
    if emergency.get("least_privilege_required") is not True:
        raise CommunicationTopologyDenied("security emergency wake must require least privilege")
    if emergency.get("immediate_user_notification_required") is not True:
        raise CommunicationTopologyDenied("security emergency wake must require immediate user notification")
    if emergency.get("gateway_still_required_for_cross_app") is not True:
        raise CommunicationTopologyDenied("security emergency wake cannot bypass cross-app gateway policy")
    return {"profile_id": PROFILE_ID, "schema": POLICY_SCHEMA, "application_count": len(applications), "gateway_count": len(gateways), "result": "ALLOW"}


def authorize_message(policy: dict[str, Any], *, sender_app: str, sender_role: str, recipient_app: str, recipient_role: str, gateway_id: str | None = None) -> dict[str, Any]:
    validate_topology_policy(policy)
    applications = policy["applications"]
    if sender_app not in applications or recipient_app not in applications:
        raise CommunicationTopologyDenied("communication endpoint application is not declared")
    if sender_role not in _role_set(applications[sender_app], sender_app):
        raise CommunicationTopologyDenied("sender model role is not authorized for the application")
    if recipient_role not in _role_set(applications[recipient_app], recipient_app):
        raise CommunicationTopologyDenied("recipient model role is not authorized for the application")
    if sender_app == recipient_app:
        if gateway_id is not None:
            raise CommunicationTopologyDenied("same-application communication must not fabricate a cross-app gateway")
        return {"result": "ALLOW", "scope": "INTRA_APP", "gateway_id": None}
    if not gateway_id:
        raise CommunicationTopologyDenied("cross-application communication requires the protected FA3 gateway")
    for gateway in policy["cross_app_gateways"]:
        if (
            gateway["source_app"] == sender_app
            and gateway["target_app"] == recipient_app
            and gateway["gateway_id"] == gateway_id
            and gateway.get("protected") is True
            and gateway.get("bypass_forbidden") is True
            and sender_role in gateway.get("allowed_source_roles", [])
            and recipient_role in gateway.get("allowed_target_roles", [])
        ):
            return {"result": "ALLOW", "scope": "CROSS_APP", "gateway_id": gateway_id}
    raise CommunicationTopologyDenied("cross-application gateway binding is not authorized")


def partner_replacement_required(*, capability_sufficient: bool, task_execution_valid: bool, unauthorized_operation_attempted: bool, autonomous_scope_expansion_attempted: bool, unauthorized_model_app_or_resource_attempted: bool) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if not capability_sufficient:
        reasons.append("MISSING_REQUIRED_CAPABILITY")
    if not task_execution_valid:
        reasons.append("TASK_EXECUTION_INVALID")
    if unauthorized_operation_attempted:
        reasons.append("UNAUTHORIZED_OPERATION_ATTEMPT")
    if autonomous_scope_expansion_attempted:
        reasons.append("AUTONOMOUS_SCOPE_EXPANSION_ATTEMPT")
    if unauthorized_model_app_or_resource_attempted:
        reasons.append("UNAUTHORIZED_MODEL_APP_OR_RESOURCE_ATTEMPT")
    return bool(reasons), tuple(reasons)


def authorize_partner_replacement(policy: dict[str, Any], *, app_id: str, logical_role: str, replacement_reasons: list[str] | tuple[str, ...], via_central_model_router: bool, candidate_pre_admitted: bool, participant_count_delta: int) -> dict[str, Any]:
    validate_topology_policy(policy)
    app = policy["applications"].get(app_id)
    if not isinstance(app, dict):
        raise CommunicationTopologyDenied("replacement application is not declared")
    if logical_role not in _role_set(app, app_id):
        raise CommunicationTopologyDenied("replacement may only target an already declared logical model role")
    if not replacement_reasons or not set(replacement_reasons).issubset(REPLACEMENT_TRIGGERS):
        raise CommunicationTopologyDenied("partner replacement requires a canonical replacement trigger")
    if via_central_model_router is not True:
        raise CommunicationTopologyDenied("partner replacement must use the central FA3 Model Router")
    if candidate_pre_admitted is not True:
        raise CommunicationTopologyDenied("replacement candidate must already be admitted")
    if participant_count_delta != 0:
        raise CommunicationTopologyDenied("partner replacement must not expand the application participant set")
    return {"result": "REPLACE_ALLOWED", "app_id": app_id, "logical_role": logical_role, "router_authority": MODEL_ROUTER_AUTHORITY, "participant_count_delta": 0}


def authorize_wake(policy: dict[str, Any], *, target_app: str, target_role: str, user_directive: bool = False, security_emergency: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_topology_policy(policy)
    applications = policy["applications"]
    app = applications.get(target_app)
    if not isinstance(app, dict):
        raise CommunicationTopologyDenied("wake target application is not declared")
    if target_role not in _role_set(app, target_app):
        raise CommunicationTopologyDenied("wake target model role is not declared")
    if app["state"] == "ACTIVE":
        return {"result": "ALLOW", "wake_required": False, "notification_required": False}
    if user_directive is True:
        return {"result": "ALLOW", "wake_required": True, "basis": "EXPLICIT_USER_DIRECTIVE", "notification_required": False}
    if not isinstance(security_emergency, dict):
        raise CommunicationTopologyDenied("sleeping application wake requires explicit user directive")
    emergency = policy["security_emergency_wake"]
    if app.get("security_app") is not True or target_app not in emergency["target_security_apps"]:
        raise CommunicationTopologyDenied("security emergency wake may target only a preauthorized security application")
    if security_emergency.get("detector_id") not in emergency["authorized_detectors"]:
        raise CommunicationTopologyDenied("security emergency detector is not authorized")
    if security_emergency.get("trigger") not in emergency["allowed_triggers"]:
        raise CommunicationTopologyDenied("security emergency trigger is not authorized")
    if security_emergency.get("severity") != "CRITICAL":
        raise CommunicationTopologyDenied("security emergency wake requires CRITICAL severity")
    confidence = security_emergency.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or float(confidence) < float(emergency["minimum_confidence"]):
        raise CommunicationTopologyDenied("security emergency confidence is below policy threshold")
    if security_emergency.get("least_privilege") is not True:
        raise CommunicationTopologyDenied("security emergency wake requires least-privilege execution")
    return {
        "result": "ALLOW",
        "wake_required": True,
        "basis": "SECURITY_EMERGENCY_WAKE",
        "notification_required": True,
        "notification_timing": "IMMEDIATE",
        "gateway_bypass_allowed": False,
        "audit_required": True,
    }


def reference_topology_policy() -> dict[str, Any]:
    return {
        "schema": POLICY_SCHEMA,
        "applications": {
            "editor": {
                "primary_model_role": "main",
                "model_roles": [
                    {"role_id": "main", "required_for_app": True},
                    {"role_id": "review", "required_for_app": True},
                ],
                "state": "ACTIVE",
                "security_app": False,
            },
            "security-response": {
                "primary_model_role": "security-main",
                "model_roles": [{"role_id": "security-main", "required_for_app": True}],
                "state": "SLEEPING",
                "security_app": True,
            },
        },
        "cross_app_gateways": [{
            "source_app": "editor",
            "target_app": "security-response",
            "gateway_id": "FA3-GW-EDITOR-SECURITY",
            "protected": True,
            "bypass_forbidden": True,
            "allowed_source_roles": ["main"],
            "allowed_target_roles": ["security-main"],
        }],
        "security_emergency_wake": {
            "enabled": True,
            "authorized_detectors": ["fa3-security-sensor"],
            "target_security_apps": ["security-response"],
            "allowed_triggers": sorted(SECURITY_EMERGENCY_TRIGGERS),
            "minimum_severity": "CRITICAL",
            "minimum_confidence": 0.9,
            "least_privilege_required": True,
            "immediate_user_notification_required": True,
            "gateway_still_required_for_cross_app": True,
        },
    }


def reference_cases() -> dict[str, bool]:
    p = reference_topology_policy()
    replacement, reasons = partner_replacement_required(
        capability_sufficient=False,
        task_execution_valid=True,
        unauthorized_operation_attempted=False,
        autonomous_scope_expansion_attempted=False,
        unauthorized_model_app_or_resource_attempted=False,
    )

    def denied(fn) -> bool:
        try:
            fn()
        except CommunicationTopologyDenied:
            return True
        return False

    return {
        "policy_valid": validate_topology_policy(p)["result"] == "ALLOW",
        "intra_app_declared_roles_allowed": authorize_message(p, sender_app="editor", sender_role="main", recipient_app="editor", recipient_role="review")["result"] == "ALLOW",
        "cross_app_protected_gateway_allowed": authorize_message(p, sender_app="editor", sender_role="main", recipient_app="security-response", recipient_role="security-main", gateway_id="FA3-GW-EDITOR-SECURITY")["result"] == "ALLOW",
        "undeclared_model_role_denied": denied(lambda: authorize_message(p, sender_app="editor", sender_role="main", recipient_app="editor", recipient_role="intruder")),
        "cross_app_without_gateway_denied": denied(lambda: authorize_message(p, sender_app="editor", sender_role="main", recipient_app="security-response", recipient_role="security-main")),
        "unfit_partner_requires_replacement": replacement and reasons == ("MISSING_REQUIRED_CAPABILITY",),
        "replacement_preserves_closed_participant_set": authorize_partner_replacement(p, app_id="editor", logical_role="review", replacement_reasons=list(reasons), via_central_model_router=True, candidate_pre_admitted=True, participant_count_delta=0)["result"] == "REPLACE_ALLOWED",
        "replacement_participant_expansion_denied": denied(lambda: authorize_partner_replacement(p, app_id="editor", logical_role="review", replacement_reasons=["TASK_EXECUTION_INVALID"], via_central_model_router=True, candidate_pre_admitted=True, participant_count_delta=1)),
        "replacement_router_bypass_denied": denied(lambda: authorize_partner_replacement(p, app_id="editor", logical_role="review", replacement_reasons=["TASK_EXECUTION_INVALID"], via_central_model_router=False, candidate_pre_admitted=True, participant_count_delta=0)),
        "sleeping_app_without_user_or_emergency_denied": denied(lambda: authorize_wake(p, target_app="security-response", target_role="security-main")),
        "explicit_user_wake_allowed": authorize_wake(p, target_app="security-response", target_role="security-main", user_directive=True)["result"] == "ALLOW",
        "security_emergency_wake_allowed_and_notified": authorize_wake(p, target_app="security-response", target_role="security-main", security_emergency={"detector_id":"fa3-security-sensor","trigger":"RANSOMWARE_BEHAVIOR","severity":"CRITICAL","confidence":0.99,"least_privilege":True})["notification_required"] is True,
        "security_emergency_low_confidence_denied": denied(lambda: authorize_wake(p, target_app="security-response", target_role="security-main", security_emergency={"detector_id":"fa3-security-sensor","trigger":"ACTIVE_MALWARE","severity":"CRITICAL","confidence":0.5,"least_privilege":True})),
        "security_emergency_nonsecurity_target_denied": denied(lambda: authorize_wake({**p, "applications": {**p["applications"], "editor": {**p["applications"]["editor"], "state": "SLEEPING"}}}, target_app="editor", target_role="main", security_emergency={"detector_id":"fa3-security-sensor","trigger":"ACTIVE_MALWARE","severity":"CRITICAL","confidence":0.99,"least_privilege":True})),
    }
