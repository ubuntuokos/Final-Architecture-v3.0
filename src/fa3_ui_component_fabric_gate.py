#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from fa3_release_baseline import module_active_capability_count

ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_COUNT = module_active_capability_count(__file__)

REQUIRED = {
    "desktop_profile": ROOT / "canonical/profiles/FA3-DESKTOP-001.json",
    "profile": ROOT / "canonical/profiles/FA3-UI-COMPONENT-FABRIC-001.json",
    "contract": ROOT / "canonical/contracts/FA3-UI-COMPONENT-FABRIC-CONTRACTS-001.json",
    "reference": ROOT / "canonical/FA3-REFERENCE-UIVERSE-GALAXY-001.json",
    "gate": ROOT / "canonical/FA3-GATE-UI-COMPONENT-FABRIC-001.json",
    "acceptance": ROOT / "canonical/FA3-UI-COMPONENT-FABRIC-EVIDENCE-ACCEPTANCE-001.json",
    "decision": ROOT / "canonical/decisions/FA3-DEC-UI-COMPONENT-FABRIC-UIVERSE-GALAXY-2026-09-19.json",
    "handoff_decision": ROOT / "canonical/decisions/FA3-DEC-ONE-CLICK-NEW-CONVERSATION-HANDOFF-2026-10-04.json",
    "reference_evidence": ROOT / "evidence/reference/fa3-ui-component-fabric-reference-pass.json",
}

PINNED_GALAXY_REVISION = "adbd2adde0a299a3956ea288fb444ec01891ca41"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    failures: list[str] = []
    for name, path in REQUIRED.items():
        if not path.exists():
            failures.append(f"missing:{name}:{path.relative_to(ROOT)}")
    if failures:
        return failures

    desktop = load_json(REQUIRED["desktop_profile"])
    profile = load_json(REQUIRED["profile"])
    contract = load_json(REQUIRED["contract"])
    reference = load_json(REQUIRED["reference"])
    gate = load_json(REQUIRED["gate"])
    acceptance = load_json(REQUIRED["acceptance"])
    decision = load_json(REQUIRED["decision"])
    handoff_decision = load_json(REQUIRED["handoff_decision"])
    evidence = load_json(REQUIRED["reference_evidence"])

    checks = [
        (desktop.get("id") == "FA3-DESKTOP-001", "desktop-parent-id"),
        (profile.get("id") == "FA3-UI-COMPONENT-FABRIC-001", "profile-id"),
        (profile.get("parent_profile") == "FA3-DESKTOP-001", "profile-parent"),
        (profile.get("provider_neutral") is True, "profile-provider-neutral"),
        (profile.get("new_capability") is False, "profile-no-new-capability"),
        (profile.get("new_architectural_authority") is False, "profile-no-new-authority"),
        (profile.get("capability_count") == CAPABILITY_COUNT, "profile-capability-count"),
        (contract.get("profile") == profile.get("id"), "contract-profile-link"),
        (contract.get("provider_neutral") is True, "contract-provider-neutral"),
        (contract.get("capability_count") == CAPABILITY_COUNT, "contract-capability-count"),
        (contract.get("promotion", {}).get("fail_closed") is True, "contract-fail-closed"),
        (reference.get("class") == "EXTERNAL_REFERENCE", "reference-class"),
        (reference.get("source", {}).get("pinned_revision") == PINNED_GALAXY_REVISION, "reference-pin"),
        (reference.get("dependency", {}).get("build") is False, "reference-no-build-dependency"),
        (reference.get("dependency", {}).get("runtime") is False, "reference-no-runtime-dependency"),
        (reference.get("dependency", {}).get("git_submodule") is False, "reference-no-submodule"),
        (reference.get("dependency", {}).get("network_runtime") is False, "reference-no-network-runtime"),
        (reference.get("import_policy", {}).get("automatic_import") == "FORBIDDEN", "reference-no-auto-import"),
        (reference.get("import_policy", {}).get("raw_copy_paste_adoption") == "FORBIDDEN", "reference-no-raw-production-copy"),
        (gate.get("fail_closed") is True, "gate-fail-closed"),
        (gate.get("rule_count") == 18, "gate-rule-count"),
        (gate.get("capability_count_after") == CAPABILITY_COUNT, "gate-capability-count"),
        (gate.get("handoff_rule_id") == "FA3-RULE-ONE-CLICK-NEW-CONVERSATION-HANDOFF-001", "gate-handoff-rule-link"),
        (gate.get("handoff_decision_id") == "FA3-DEC-ONE-CLICK-NEW-CONVERSATION-HANDOFF-2026-10-04", "gate-handoff-decision-link"),
        (gate.get("handoff_priority") == "P0", "gate-handoff-priority"),
        (acceptance.get("fail_closed") is True, "acceptance-fail-closed"),
        (decision.get("capability_count_before") == decision.get("capability_count_after") and isinstance(decision.get("capability_count_after"), int) and decision.get("capability_count_after") <= CAPABILITY_COUNT, "decision-capability-count"),
        (decision.get("new_architectural_authority") == 0, "decision-no-new-authority"),
        (handoff_decision.get("status") == "CANONICAL_CLOSED", "handoff-decision-closed"),
        (handoff_decision.get("decision") == "ACCEPT_AND_MANDATE", "handoff-decision-mandated"),
        (handoff_decision.get("rule_id") == "FA3-RULE-ONE-CLICK-NEW-CONVERSATION-HANDOFF-001", "handoff-decision-rule"),
        (handoff_decision.get("contract_family_id") == "FA3-UI-COMPONENT-FABRIC-CONTRACTS-001", "handoff-decision-contract"),
        (handoff_decision.get("capability_count_after") == CAPABILITY_COUNT, "handoff-decision-capability-count"),
        (handoff_decision.get("new_capabilities") == 0, "handoff-decision-no-new-capability"),
        (handoff_decision.get("new_architectural_authorities") == 0, "handoff-decision-no-new-authority"),
        (handoff_decision.get("applies_to", {}).get("fa3_cfa3_development_process") is True, "handoff-decision-development-scope"),
        (handoff_decision.get("applies_to", {}).get("cfa3_fa3_product") is True, "handoff-decision-product-scope"),
        (evidence.get("status") == "PASS", "reference-evidence-pass"),
        (evidence.get("current_host_runtime_claim") is False, "reference-evidence-no-current-host-claim"),
        (evidence.get("individual_component_production_admitted") is False, "reference-evidence-no-component-admission"),
    ]
    failures.extend(name for ok, name in checks if not ok)

    required_component_rules = set(profile.get("canonical_component_requirements", []))
    for rule in {
        "FA3_TOKENIZED_STYLING",
        "KEYBOARD_NAVIGATION",
        "VISIBLE_FOCUS_STATE",
        "PREFERS_REDUCED_MOTION_SUPPORT_FOR_ANIMATION",
        "SOURCE_PROVENANCE",
        "LICENSE_METADATA",
        "VISUAL_REGRESSION_COVERAGE",
        "SINGLE_COPY_TARGET_FOR_NEW_CONVERSATION_HANDOFF",
        "ONE_ACTION_COMPLETE_HANDOFF_COPY",
        "NO_SCROLL_OR_SELECTION_REQUIRED_FOR_HANDOFF_COPY",
        "ONE_WORD_OR_SINGLE_CHARACTER_HANDOFF_STILL_USES_COPY_SURFACE",
    }:
        if rule not in required_component_rules:
            failures.append(f"profile-component-rule-missing:{rule}")

    source_intake = contract.get("source_intake", {})
    for key in [
        "script_elements",
        "inline_event_handlers",
        "javascript_urls",
        "iframes",
        "remote_executable_resources",
        "tracking_or_analytics_resources",
        "remote_fonts_in_production_component",
    ]:
        if source_intake.get(key) != "FORBIDDEN":
            failures.append(f"contract-intake-not-forbidden:{key}")


    handoff = contract.get("new_conversation_handoff", {})
    payload = handoff.get("payload_integrity", {})
    interaction = handoff.get("interaction", {})
    clipboard = handoff.get("clipboard", {})
    companion = handoff.get("companion_text", {})
    handoff_checks = [
        (handoff.get("rule_id") == "FA3-RULE-ONE-CLICK-NEW-CONVERSATION-HANDOFF-001", "handoff-contract-rule"),
        (handoff.get("priority") == "P0" and handoff.get("requirement") == "MUST", "handoff-contract-mandatory"),
        (payload.get("complete_payload_in_exactly_one_copy_target") is True, "handoff-single-copy-target"),
        (payload.get("split_payload_across_copy_targets") == "FORBIDDEN", "handoff-no-split-payload"),
        (payload.get("payload_fragment_outside_single_copy_target") == "FORBIDDEN", "handoff-no-outside-fragment"),
        (payload.get("one_word_or_single_character_exempt") is False, "handoff-no-short-payload-exception"),
        (payload.get("payload_length_exempt") is False, "handoff-no-length-exception"),
        (interaction.get("visible_direct_copy_control_required") is True, "handoff-visible-copy-control"),
        (interaction.get("required_copy_activation_count") == 1, "handoff-one-activation"),
        (interaction.get("manual_text_selection_required") is False, "handoff-no-manual-selection"),
        (interaction.get("scrolling_required_to_copy_complete_payload") is False, "handoff-no-scroll-to-copy"),
        (interaction.get("visual_scrolling_may_not_change_copy_scope") is True, "handoff-scroll-does-not-limit-copy"),
        (clipboard.get("mode") == "EXPLICIT_USER_INITIATED_WRITE_ONLY", "handoff-clipboard-write-only"),
        (clipboard.get("read_before_copy") is False, "handoff-no-clipboard-read"),
        (clipboard.get("background_capture") is False and clipboard.get("generic_clipboard_capture") is False, "handoff-no-background-clipboard-capture"),
        (clipboard.get("unavailable_or_copy_failure") == "FAIL_CLOSED_NOT_READY", "handoff-copy-failure-fail-closed"),
        (companion.get("may_be_required_for_handoff") is False and companion.get("may_contain_payload_fragment") is False, "handoff-companion-not-payload"),
    ]
    failures.extend(name for ok, name in handoff_checks if not ok)

    required_claims = set(acceptance.get("required_reference_claims", []))
    evidence_claims = set(evidence.get("claims", []))
    if not required_claims <= evidence_claims:
        failures.append("reference-evidence-required-claims-missing")

    required_non_claims = set(acceptance.get("required_non_claims", []))
    evidence_non_claims = set(evidence.get("non_claims", []))
    if not required_non_claims <= evidence_non_claims:
        failures.append("reference-evidence-required-non-claims-missing")

    if reference.get("promotion_rule", {}).get("reference_admission_does_not_admit_any_individual_component") is not True:
        failures.append("reference-component-admission-boundary-missing")

    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("FA3 UI Component Fabric gate: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("FA3 UI Component Fabric gate: PASS")
    print(f"profile=FA3-UI-COMPONENT-FABRIC-001 reference=FA3-REFERENCE-UIVERSE-GALAXY-001 capabilities={CAPABILITY_COUNT} new_authorities=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
