#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import active_capability_count

GATE_ID = "FA3-OS-EVENT-PRIVACY-GATESET-001"
PROFILE_ID = "FA3-OS-001"
POLICY_ID = "FA3-OS-POLICY-001"
EVENT_CONTRACT_ID = "FA3-OS-EVENT-001"
JOURNAL_PROFILE_ID = "FA3-JOURNAL-001"
JOURNAL_CONTRACT_ID = "FA3-JOURNAL-CONTRACTS-001"

PROFILE_PATH = Path("canonical/profiles/FA3-OS-001.json")
POLICY_PATH = Path("canonical/profiles/FA3-OS-POLICY-001.json")
SCHEMA_PATH = Path("canonical/contracts/FA3-OS-EVENT-001.schema.json")
ENFORCEMENT_PATH = Path("canonical/fa3-os-event-privacy-enforcement.json")
JOURNAL_PROFILE_PATH = Path("canonical/profiles/FA3-JOURNAL-001.json")
JOURNAL_CONTRACT_PATH = Path("canonical/contracts/FA3-JOURNAL-CONTRACTS-001.json")


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def _require(condition: bool, findings: list[dict[str, Any]], code: str, message: str, **details: Any) -> None:
    if not condition:
        findings.append(_finding(code, message, **details))


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    required = [
        PROFILE_PATH,
        POLICY_PATH,
        SCHEMA_PATH,
        ENFORCEMENT_PATH,
        JOURNAL_PROFILE_PATH,
        JOURNAL_CONTRACT_PATH,
    ]
    missing = [str(path) for path in required if not (root / path).is_file()]
    if missing:
        for path in missing:
            findings.append(_finding("FA3-OS-REF-000", "Required canonical artifact is missing", path=path))
        return {"result": "FAIL", "findings": findings}

    try:
        profile = _load(root / PROFILE_PATH)
        policy = _load(root / POLICY_PATH)
        schema = _load(root / SCHEMA_PATH)
        enforcement = _load(root / ENFORCEMENT_PATH)
        journal = _load(root / JOURNAL_PROFILE_PATH)
        journal_contract = _load(root / JOURNAL_CONTRACT_PATH)
        capability_count = active_capability_count(root)
    except Exception as exc:
        return {
            "result": "FAIL",
            "findings": [_finding("FA3-OS-REF-001", "Canonical artifact could not be loaded", error=str(exc))],
        }

    _require(journal.get("profile_id") == JOURNAL_PROFILE_ID, findings, "FA3-OS-JRN-001", "Journal profile identity drift")
    rules = journal.get("profile_rules", {})
    _require(rules.get("event_history") == "append_only", findings, "FA3-OS-JRN-002", "Journal history is no longer append-only")
    _require(rules.get("delete_or_rewrite_historical_events") is False, findings, "FA3-OS-JRN-003", "Journal historical rewrite protection drift")
    _require(journal.get("canonical_contract") == JOURNAL_CONTRACT_ID, findings, "FA3-OS-JRN-004", "Journal canonical contract drift")

    event_contract = journal_contract.get("event_contract", {})
    _require(journal_contract.get("profile_id") == JOURNAL_CONTRACT_ID, findings, "FA3-OS-JRN-005", "Journal contract identity drift")
    _require(event_contract.get("immutability") == "event records are append-only once committed", findings, "FA3-OS-JRN-006", "Journal envelope immutability drift")
    _require(
        event_contract.get("correction_semantics") == "append superseding event; historical payload is never rewritten",
        findings,
        "FA3-OS-JRN-007",
        "Journal correction semantics drift",
    )

    _require(profile.get("profile_id") == PROFILE_ID, findings, "FA3-OS-REF-002", "FA3 OS profile identity drift")
    _require(profile.get("status") == "CANONICAL", findings, "FA3-OS-REF-003", "FA3 OS is not CANONICAL")
    _require(profile.get("canonical_root") is False, findings, "FA3-OS-AUTH-001", "FA3 OS was promoted to a canonical root")
    _require(profile.get("architectural_authority") is False, findings, "FA3-OS-AUTH-002", "FA3 OS was promoted to architectural authority")
    _require(profile.get("new_capability") is False, findings, "FA3-OS-CAP-001", "FA3 OS introduced a new capability")
    _require(profile.get("capability_count") == capability_count, findings, "FA3-OS-CAP-002", "FA3 OS capability-count invariant drift")
    _require(profile.get("ledger_authority") == JOURNAL_PROFILE_ID, findings, "FA3-OS-AUTH-003", "FA3 OS ledger authority is not FA3-JOURNAL-001")
    _require(profile.get("canonical_event_envelope") == JOURNAL_CONTRACT_ID, findings, "FA3-OS-AUTH-004", "FA3 OS defines or references a competing outer event envelope")
    _require(profile.get("event_enrichment_contract") == EVENT_CONTRACT_ID, findings, "FA3-OS-REF-004", "FA3 OS event enrichment contract drift")
    _require(profile.get("privacy_policy_profile") == POLICY_ID, findings, "FA3-OS-REF-005", "FA3 OS privacy profile binding drift")
    _require(profile.get("session_resume", {}).get("execution_authority") is False, findings, "FA3-OS-AUTH-005", "Resume Plan gained execution authority")
    projection_rule = str(profile.get("derived_projection_rule", "")).lower()
    _require("derived" in projection_rule and "rebuildable" in projection_rule and "must not rewrite" in projection_rule, findings, "FA3-OS-HIST-001", "Derived-memory non-authority rule drift")

    _require(policy.get("profile_id") == POLICY_ID, findings, "FA3-OS-PRIV-001", "Privacy profile identity drift")
    _require(policy.get("parent_profile") == PROFILE_ID, findings, "FA3-OS-PRIV-002", "Privacy profile parent drift")
    _require(policy.get("fail_closed") is True, findings, "FA3-OS-PRIV-003", "Privacy gate is not fail-closed")
    _require(policy.get("policy_gate_position") == "BEFORE_DURABLE_PERSISTENCE", findings, "FA3-OS-PRIV-004", "Privacy gate is not before persistence")
    defaults = policy.get("default_capture", {})
    expected_defaults = {
        "keylogging": "DENY",
        "generic_clipboard": "DENY",
        "continuous_screenshots": "DENY",
        "generic_screen_capture": "DENY",
        "terminal": "METADATA_ONLY",
        "password_managers": "DENY",
        "credential_and_secret_paths": "DENY",
    }
    for key, expected in expected_defaults.items():
        _require(defaults.get(key) == expected, findings, "FA3-OS-PRIV-005", "Unsafe default capture policy drift", field=key, expected=expected, actual=defaults.get(key))

    sensitive = policy.get("sensitive_data_rules", {})
    _require(sensitive.get("redaction_before_persistence") is True, findings, "FA3-OS-PRIV-006", "Secret redaction-before-persistence requirement drift")
    _require(sensitive.get("credentials_must_not_be_persisted") is True, findings, "FA3-OS-PRIV-007", "Credential persistence prohibition drift")
    _require(sensitive.get("secrets_must_not_be_persisted") is True, findings, "FA3-OS-PRIV-008", "Secret persistence prohibition drift")

    retrieval = policy.get("context_retrieval", {})
    _require(retrieval.get("policy_filter_required") is True, findings, "FA3-OS-CTX-001", "Context retrieval is not policy-filtered")
    _require(retrieval.get("audit_required") is True, findings, "FA3-OS-CTX-002", "Context retrieval auditing is disabled")

    erasure = policy.get("selective_erasure", {})
    _require(erasure.get("canonical_history_semantics") == "APPEND_ONLY_COMPATIBLE", findings, "FA3-OS-ERASE-001", "Selective erasure is not append-only compatible")
    _require(erasure.get("historical_event_rewrite") is False, findings, "FA3-OS-ERASE-002", "Selective erasure permits rewriting committed Journal history")
    forbidden = set(erasure.get("forbidden_actions", []))
    _require("silent_mutation_of_committed_journal_event" in forbidden, findings, "FA3-OS-ERASE-003", "Silent Journal mutation is not explicitly forbidden")
    permitted = set(erasure.get("permitted_actions", []))
    for expected in ("erase_referenced_sensitive_payload", "erase_derived_embeddings", "erase_derived_summaries", "erase_semantic_indexes"):
        _require(expected in permitted, findings, "FA3-OS-ERASE-004", "Required privacy-erasure action missing", action=expected)

    _require(schema.get("x-fa3-contract-id") == EVENT_CONTRACT_ID, findings, "FA3-OS-SCHEMA-001", "Event enrichment contract identity drift")
    _require(schema.get("x-fa3-canonical-envelope") == JOURNAL_CONTRACT_ID, findings, "FA3-OS-SCHEMA-002", "Event enrichment schema outer-envelope binding drift")
    _require(schema.get("x-fa3-ledger-authority") == JOURNAL_PROFILE_ID, findings, "FA3-OS-SCHEMA-003", "Event enrichment schema ledger authority drift")
    _require(schema.get("x-fa3-authoritative-history") is False, findings, "FA3-OS-SCHEMA-004", "Event enrichment schema was promoted to authoritative history")
    required_fields = set(schema.get("required", []))
    _require("capture_policy_id" in required_fields, findings, "FA3-OS-SCHEMA-005", "capture_policy_id is not required")
    properties = schema.get("properties", {})
    _require(properties.get("capture_policy_id", {}).get("const") == POLICY_ID, findings, "FA3-OS-SCHEMA-006", "capture_policy_id is not pinned to the canonical privacy policy")
    prohibited_inline_fields = {"raw_content", "clipboard_content", "keystrokes", "screenshot_bytes", "terminal_content", "secret", "credential"}
    present = prohibited_inline_fields.intersection(properties)
    _require(not present, findings, "FA3-OS-SCHEMA-007", "Event enrichment schema permits prohibited inline sensitive content", fields=sorted(present))
    _require("payload_reference" in properties, findings, "FA3-OS-SCHEMA-008", "Event enrichment schema lacks payload_reference")
    _require("provenance" in properties and "confidence" in properties, findings, "FA3-OS-SCHEMA-009", "Event enrichment schema lacks provenance/confidence")

    _require(enforcement.get("gate_id") == GATE_ID, findings, "FA3-OS-ENF-001", "Enforcement gate identity drift")
    _require(enforcement.get("fail_closed") is True, findings, "FA3-OS-ENF-002", "Enforcement is not fail-closed")
    _require(enforcement.get("ledger_authority") == JOURNAL_PROFILE_ID, findings, "FA3-OS-ENF-003", "Enforcement ledger authority drift")
    _require(enforcement.get("canonical_event_envelope") == JOURNAL_CONTRACT_ID, findings, "FA3-OS-ENF-004", "Enforcement envelope drift")
    _require(enforcement.get("new_capabilities") == 0, findings, "FA3-OS-ENF-005", "Enforcement permits new capabilities")
    _require(enforcement.get("new_architectural_authorities") == 0, findings, "FA3-OS-ENF-006", "Enforcement permits new architectural authorities")
    _require(enforcement.get("capability_count_after") == capability_count, findings, "FA3-OS-ENF-007", "Enforcement capability count drift")

    return {
        "result": "PASS" if not findings else "FAIL",
        "capability_count": capability_count,
        "findings": findings,
    }


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    reference = reference_check(root)
    return {
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "privacy_profile_id": POLICY_ID,
        "event_contract_id": EVENT_CONTRACT_ID,
        "ledger_authority": JOURNAL_PROFILE_ID,
        "result": reference["result"],
        "capability_count": reference.get("capability_count"),
        "reference": reference,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 OS Event Ledger / Privacy fail-closed regression gate")
    parser.add_argument("--repo-root", default=".", help="FA3 repository root")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    report = gate(Path(args.repo_root))
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
