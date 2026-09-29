#!/usr/bin/env python3
"""Static prerequisite boundary check. Never produces current-host or production PASS."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "intent": "canonical/intents/FA3-CAPTURE-INBOX-APPLICATION-INTENT-001.json",
    "assessment": "canonical/assessments/FA3-CAPTURE-INBOX-REUSE-ASSESSMENT-001.json",
    "contract": "canonical/contracts/FA3-CAPTURE-INBOX-DEPENDENCY-CONTRACTS-001.json",
    "decision": "canonical/decisions/FA3-DEC-CAPTURE-INBOX-DEPENDENCIES-2026-09-29.json",
    "donors": "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
    "model": "canonical/FA3-CAPABILITY-MODEL-175-001.json",
    "privacy": "canonical/profiles/FA3-OS-POLICY-001.json",
    "journal": "canonical/contracts/FA3-JOURNAL-CONTRACTS-001.json",
    "evidence": "evidence/evidence-registry.json",
    "recipes": "canonical/current-host-capability-proof-recipes.json",
}
DONOR_KEYS = {
    "github:contentauth/c2pa-rs", "github:automerge/automerge",
    "github:syncthing/syncthing", "github:laurent22/joplin",
    "github:gsantner/markor",
}
CAPABILITIES = {"CAP-146", "CAP-147", "CAP-150", "CAP-152", "CAP-175"}
PROHIBITED_DONOR_FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

def load_snapshot(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    result = {}
    for key, relative_path in FILES.items():
        value = json.loads((root / relative_path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{relative_path} must be a JSON object")
        result[key] = value
    return result

def validate(snapshot: dict[str, dict[str, Any]]) -> list[str]:
    """Return violations. PASS is only a static dependency boundary result."""
    errors: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    x = snapshot
    model = x["model"]
    check(model.get("canonical_capability_count") == 175, "fixed 175 baseline changed")
    ids = {c.get("id") for c in model.get("added_capabilities", [])}
    check(CAPABILITIES <= ids, "required existing capabilities missing")
    check(model.get("authority_delta") == 0, "model authority delta changed")
    for key in ("intent", "assessment", "contract", "decision"):
        obj = x[key]
        if key == "intent":
            check(obj.get("declared_new_capabilities") == [], "Capture claims new capabilities")
            check(obj.get("proposed_authority_roles") == [], "Capture claims new authorities")
            ns = obj.get("namespace_claims", {})
            check(ns.get("package_prefix") == "fa3-capture-inbox" and
                  all(str(ns.get(k, "")).startswith("$XDG_")
                      for k in ("config_root", "cache_root", "data_root", "runtime_root")),
                  "Capture must own only its XDG namespaces")
            check(ns.get("claims_default_port") is False and
                  ns.get("global_environment_mutation") is False and
                  ns.get("requires_upstream_uninstall") is False,
                  "unsafe Capture host namespace or upstream takeover")
            hw = obj.get("hardware_audit", {})
            check(hw.get("cpu_only_viable") is True and
                  hw.get("accelerator_cardinality") == "0..N" and
                  hw.get("display_gpu_auto_enlistment") is False and
                  hw.get("hardware_safety_envelope_non_bypassable") is True,
                  "hardware safety / display GPU invariant changed")
        elif key == "assessment":
            check(obj.get("new_capabilities") == 0 and
                  obj.get("new_architectural_authorities") == 0 and
                  obj.get("capability_count_after") == 175, "reuse assessment changed authority/count")
            check(obj.get("current_host_runtime_promotion_claim") is False and
                  obj.get("global_promotion_claim") is False,
                  "reuse assessment improperly promotes runtime")
            check(obj.get("project_status") == "DEPENDENCY_RECONCILIATION_PENDING_RUNTIME_AND_GLOBAL_COEXISTENCE",
                  "reuse assessment omits pending infrastructure")
            matched = {row.get("id") for row in obj.get("external_donor_sources", [])}
            check({"FA3-DONOR-C2PA-RS-001", "FA3-DONOR-AUTOMERGE-001",
                   "FA3-DONOR-SYNCTHING-001", "FA3-DONOR-JOPLIN-001",
                   "FA3-DONOR-MARKOR-001"} <= matched, "mandatory donor review missing")
        else:
            count = obj.get("capability_count" if key == "contract" else "capability_count_after")
            check(count == 175, f"{key}: fixed count changed")
            delta = obj.get("new_architectural_authority" if key == "contract" else "authority_delta")
            check(delta is False if key == "contract" else delta == 0,
                  f"{key}: new authority")
            check(obj.get("current_host_runtime_promotion_claim") is False if key == "decision" else
                  obj.get("admission", {}).get("current_host_runtime_promotion_claim") is False,
                  f"{key}: invalid runtime promotion")
    policy = x["privacy"]
    defaults = policy.get("default_capture", {})
    check(policy.get("id") == "FA3-OS-POLICY-001" and
          all(defaults.get(k) == "DENY" for k in
              ("keylogging", "generic_clipboard", "continuous_screenshots", "generic_screen_capture")),
          "privacy policy no longer denies passive collection")
    check(policy.get("policy_gate_position") == "BEFORE_DURABLE_PERSISTENCE" and
          policy.get("sensitive_data_rules", {}).get("redaction_before_persistence") is True,
          "privacy gate or pre-persistence redaction missing")
    check("erase_derived_embeddings" in policy.get("selective_erasure", {}).get("permitted_actions", []),
          "selective-erasure derivative cleanup missing")
    journal = x["journal"]
    check(journal.get("id") == "FA3-JOURNAL-CONTRACTS-001" and
          journal.get("contracts", {}).get("event", {}).get("integrity_default") == "APPEND_ONLY",
          "canonical Journal append-only authority changed")
    contract = x["contract"]
    check(contract.get("authority_bindings", {}).get("event_history") == "FA3-JOURNAL-001" and
          contract.get("authority_bindings", {}).get("privacy_capture") == "FA3-OS-POLICY-001",
          "Capture introduced parallel privacy/event authority")
    cap = contract.get("capture", {})
    check(cap.get("offline_first") is True and cap.get("cloud_dependency") is False and
          cap.get("cloud_egress_default") == "DENY" and
          cap.get("capture_initiation") == "EXPLICIT_USER_ACTION_ONLY" and
          cap.get("privacy_gate") == "FA3-OS-POLICY-001_BEFORE_DURABLE_PERSISTENCE" and
          cap.get("no_automatic_ai_content_upload") is True,
          "Capture privacy/cloud/default capture contract drift")
    custody = contract.get("data_custody", {})
    check(custody.get("secret_values_in_events_or_artifacts") is False and
          custody.get("journal") == "APPEND_ONLY_MINIMIZED_METADATA_AND_EVENT_REFERENCES" and
          "ERASE_PAYLOAD" in custody.get("selective_erasure", ""),
          "sensitive data, derived payload or Journal custody drift")
    handoff = contract.get("handoff", {})
    check("CAP-152" in handoff.get("local_route", "") and
          handoff.get("action_dispatch") == "EXISTING_FA3_UNIFIED_ACTION_FABRIC_ONLY" and
          handoff.get("inaccessible_or_unconnected_recipient") == "PENDING_OR_REJECTED_NO_FAKE_ACK" and
          handoff.get("permission") == "PER_RECIPIENT_PER_PROJECT_EXPLICIT_RELEASE_AND_SECURITY_GOVERNANCE",
          "typed handoff must remain authorized, addressed and fail-closed")
    sync = contract.get("lan_sync", {})
    check(sync.get("implementation") == "CAP150_ADAPTER_ONLY_NO_SEPARATE_CAPTURE_SYNC" and
          sync.get("cloud_relay") is False and
          sync.get("content_addressed") is True and
          sync.get("current_status") == "BLOCKED_PENDING_CAP150_PHYSICAL_TWO_HOST_E2E" and
          sync.get("semantic_or_approved_conflicts") == "HUMAN_REVIEW_OR_EXISTING_PROJECT_APPROVAL",
          "CAP-150 sync replaced, silently promoted or conflicts auto-decided")
    coex = contract.get("coexistence", {})
    check(coex.get("global_policy_pr") == 410 and
          coex.get("footprint_admission") == "PENDING_AFTER_PR410_SCHEMA_LANDS_ON_MAIN" and
          coex.get("default_ports") == [] and
          coex.get("global_env_mutations") == [] and
          coex.get("upstream_app_uninstall") is False,
          "CAP-175 host non-interference precondition removed")
    check(contract.get("admission", {}).get("global_promotion_claim") is False and
          contract.get("admission", {}).get("baseline") == 175 and
          contract.get("admission", {}).get("authority_delta") == 0,
          "false production promotion or new authority")
    donor_records = x["donors"].get("entries", [])
    normalized = [d.get("source", {}).get("normalized_key") for d in donor_records]
    donor_ids = [d.get("donor_id") for d in donor_records]
    check(len(set(normalized)) == len(normalized), "duplicate normalized donor source")
    check(len(set(donor_ids)) == len(donor_ids), "duplicate donor id")
    check(x["donors"].get("backfill", {}).get("entry_count") == len(donor_records),
          "donor count metadata not reconciled")
    by_key = {d.get("source", {}).get("normalized_key"): d for d in donor_records}
    check(DONOR_KEYS <= by_key.keys(), "Capture donor registry incomplete")
    for source in DONOR_KEYS & by_key.keys():
        donor = by_key[source]
        check(donor.get("status") in ("CANDIDATE", "ANALYZED", "ACCEPTED_REFERENCE"),
              f"{source}: donor incorrectly rejected/missing review")
        check(all(donor.get(flag) is False for flag in PROHIBITED_DONOR_FLAGS),
              f"{source}: donor has authority/auto-admission")
        check(donor.get("code_reuse_policy") == "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW",
              f"{source}: unreviewed source copy allowed")
    records = {r.get("subject_id"): r for r in x["evidence"].get("records", [])}
    for capability in ("CAP-150", "CAP-152", "CAP-175"):
        evidence = records.get(capability, {})
        check(evidence.get("obligation") == "MANDATORY", f"{capability}: evidence obligation missing")
        check(evidence.get("status") == "PENDING_CURRENT_HOST" and
              evidence.get("runtime_conformance") == "EVIDENCE-PENDING" and
              evidence.get("evidence_artifacts") == [],
              f"{capability}: dependency unexpectedly claimed closed; requalify this prerequisite gate")
    recipes = {r.get("capability_id"): r for r in x["recipes"].get("recipes", [])}
    cap150 = recipes.get("CAP-150", {})
    check(cap150.get("network_policy") == "LOOPBACK_ONLY" and
          cap150.get("local_protocol_pass_is_cross_host_production") is False and
          cap150.get("cross_host_production_e2e_required") is True and
          cap150.get("minimum_distinct_host_identities_for_cross_host_promotion", 0) >= 2,
          "CAP-150 loopback proof falsely accepted as two-host E2E")
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate(load_snapshot(args.root))
    print(json.dumps({
        "gate": "FA3-CAPTURE-INBOX-DEPENDENCY-BOUNDARY-001",
        "static_boundary": "FAIL" if errors else "PASS",
        "capture_implementation_admission": "PENDING",
        "cap150_cap152_cap175_current_host": "PENDING",
        "capability_baseline": 175,
        "authority_delta": 0,
        "errors": errors,
    }, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
