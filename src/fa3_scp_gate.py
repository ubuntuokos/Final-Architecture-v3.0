#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PROFILE = "canonical/profiles/FA3-SCP-FABRIC-001.json"
CONTRACTS = "canonical/contracts/FA3-SCP-CONTRACTS-001.json"
ENFORCEMENT = "canonical/scp-enforcement.json"
DECISION = "canonical/decisions/FA3-DEC-SCP-FABRIC-2026-09-30.json"
ASSESSMENT = "canonical/assessments/FA3-SCP-FABRIC-REUSE-ASSESSMENT-001.json"
PLAN = "docs/FA3-SCP-FABRIC-FINAL-PLAN-2026-09-30.md"
DONOR = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
UI = "canonical/FA3-SCP-UI-BINDINGS-001.json"

REQUIRED = (
    "authenticated_source",
    "authenticated_destination",
    "trusted_host",
    "valid_layer",
    "valid_scope",
    "valid_capability",
    "valid_security_state",
    "destination_allowed",
)


def load(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"NOT_OBJECT:{rel}")
    return value


def evaluate_request(context: dict[str, Any]) -> dict[str, Any]:
    reasons = [f"MISSING_OR_FALSE:{key}" for key in REQUIRED if context.get(key) is not True]
    traffic = context.get("traffic_class")
    if traffic in ("EXTERNAL_EGRESS", "EXTERNAL_INGRESS") and context.get("external_permission") is not True:
        reasons.append("EXTERNAL_PERMISSION_REQUIRED")
    if context.get("ai_request") is True:
        for key in ("ai_enabled", "provider_admitted", "model_route_approved"):
            if context.get(key) is not True:
                reasons.append(f"AI_POLICY_DENY:{key}")
    return {
        "allowed": not reasons,
        "decision": "ALLOW" if not reasons else "DENY",
        "reasons": reasons,
    }


def gate(root: Path) -> dict[str, Any]:
    findings: list[str] = []
    profile = load(root, PROFILE)
    contracts = load(root, CONTRACTS)
    enforcement = load(root, ENFORCEMENT)
    decision = load(root, DECISION)
    assessment = load(root, ASSESSMENT)
    ui = load(root, UI)
    donor_raw = (root / DONOR).read_bytes()
    plan_raw = (root / PLAN).read_bytes()

    if profile.get("id") != "FA3-SCP-FABRIC-001" or profile.get("authority") is not False:
        findings.append("PROFILE_AUTHORITY_BOUNDARY_INVALID")
    if profile.get("capability_count") != 175 or profile.get("new_capability") is not False:
        findings.append("CAPABILITY_BASELINE_DRIFT")
    if enforcement.get("default_action") != "DENY" or enforcement.get("fail_closed") is not True:
        findings.append("DEFAULT_DENY_FAIL_CLOSED_REQUIRED")
    if enforcement.get("failure_mode_allow") is not False:
        findings.append("FAILURE_MODE_ALLOW_FORBIDDEN")
    if contracts.get("authority") is not False:
        findings.append("CONTRACT_AUTHORITY_INVALID")
    if ui.get("shared_component") != "apps/shared/scp/qml/SecureCommunicationSettings.qml":
        findings.append("SHARED_UI_COMPONENT_INVALID")
    if ui.get("shared_backend") != "apps/shared/scp/SCPSettingsService.cpp":
        findings.append("SHARED_BACKEND_INVALID")
    if decision.get("status") != "APPROVED" or decision.get("explicit_user_approval") is not True:
        findings.append("OWNER_APPROVAL_MISSING")
    if decision.get("approved_plan_sha256") != hashlib.sha256(plan_raw).hexdigest():
        findings.append("APPROVED_PLAN_HASH_MISMATCH")
    donor_sha = hashlib.sha256(donor_raw).hexdigest()
    if assessment.get("donor_registry_sha256") != donor_sha:
        findings.append("DONOR_REGISTRY_SNAPSHOT_MISMATCH")
    if assessment.get("donor_review") not in ("REVIEWED_MATCH", "REVIEWED_NO_MATCH"):
        findings.append("DONOR_REVIEW_MISSING")
    if assessment.get("adopted_donors") != []:
        findings.append("UNEXPECTED_DONOR_ADOPTION")

    if evaluate_request({})["decision"] != "DENY":
        findings.append("EMPTY_CONTEXT_MUST_DENY")

    allow = {key: True for key in REQUIRED}
    if evaluate_request(allow)["decision"] != "ALLOW":
        findings.append("COMPLETE_INTERNAL_CONTEXT_SHOULD_ALLOW")

    external = dict(allow, traffic_class="EXTERNAL_EGRESS")
    if evaluate_request(external)["decision"] != "DENY":
        findings.append("EXTERNAL_WITHOUT_PERMISSION_MUST_DENY")
    external["external_permission"] = True
    if evaluate_request(external)["decision"] != "ALLOW":
        findings.append("AUTHORIZED_EXTERNAL_CONTEXT_SHOULD_ALLOW")

    ai = dict(external, ai_request=True, ai_enabled=False, provider_admitted=True, model_route_approved=True)
    if evaluate_request(ai)["decision"] != "DENY":
        findings.append("AI_DISABLED_MUST_DENY")

    required_files = [
        "apps/shared/scp/SCPSettingsService.h",
        "apps/shared/scp/SCPSettingsService.cpp",
        "apps/shared/scp/qml/SecureCommunicationSettings.qml",
        "apps/fa3-scp-manager/CMakeLists.txt",
        "apps/fa3-scp-manager/src/main.cpp",
        "apps/fa3-scp-manager/qml/Main.qml",
    ]
    for rel in required_files:
        if not (root / rel).is_file():
            findings.append(f"MISSING_MATERIALIZATION:{rel}")

    return {
        "schema": "fa3.scp-gate-result.v1",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "capability_baseline": profile.get("capability_count"),
        "authority": False,
        "runtime_promotion_claim": False,
        "current_host_status": "PENDING_PHYSICAL_RUNTIME_EVIDENCE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
