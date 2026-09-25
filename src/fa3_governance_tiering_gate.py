#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from fa3_release_baseline import load_active_release_baseline

PROJECTION_ID = "FA3-GOVERNANCE-TIERING-001"
GATESET_ID = "FA3-GOVERNANCE-TIERING-GATESET-001"
EXPECTED_RINGS = ["LAB", "CANDIDATE", "STAGING"]

PATHS = {
    "baseline": "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json",
    "projection": "canonical/FA3-GOVERNANCE-TIERING-001.json",
    "policy": "canonical/enforcement-policy.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    "registry": "evidence/evidence-registry.json",
    "current_host_workflow": ".github/workflows/fa3-global-current-host-closure.yml",
    "enforce": "src/fa3_enforce.py",
}


def load_json(root: Path, key: str) -> dict[str, Any]:
    return json.loads((root / PATHS[key]).read_text(encoding="utf-8"))


def finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root)
    missing = [path for path in PATHS.values() if not (root / path).is_file()]
    if missing:
        return {
            "schema": "fa3.governance-tiering-gate-report.v1",
            "gate_set_id": GATESET_ID,
            "projection_id": PROJECTION_ID,
            "result": "FAIL",
            "blocking_findings": len(missing),
            "checks_passed": 0,
            "checks_total": 16,
            "findings": [finding("GOVT-000", f"missing {path}") for path in missing],
        }

    expected_count = load_active_release_baseline(root).capability_count
    projection = load_json(root, "projection")
    policy = load_json(root, "policy")
    registry = load_json(root, "registry")
    workflow_text = (root / PATHS["current_host_workflow"]).read_text(encoding="utf-8")
    enforce_text = (root / PATHS["enforce"]).read_text(encoding="utf-8")

    sources = projection.get("authoritative_sources", {})
    axes = projection.get("orthogonal_axes", {})
    assurance = axes.get("assurance", {})
    canonical = axes.get("canonical", {})
    runtime = axes.get("runtime", {})
    derivation = projection.get("derivation_rules", {})
    non_authority = projection.get("non_authority", {})
    forbidden = set(projection.get("forbidden_inferences", []))
    ring_records = assurance.get("rings", [])
    ring_ids = [item.get("id") for item in ring_records]
    ordinals = [item.get("ordinal") for item in ring_records]
    registry_records = registry.get("records", [])
    before_count = projection.get("canonical_capability_count_before")
    after_count = projection.get("canonical_capability_count_after")
    capability_delta = projection.get("capability_delta")
    semantic_effect = projection.get("semantic_effect")
    declared_migration = (
        isinstance(before_count, int)
        and isinstance(after_count, int)
        and after_count == expected_count
        and isinstance(capability_delta, int)
        and capability_delta == after_count - before_count
        and (
            (capability_delta == 0 and semantic_effect == "NO_BASELINE_SEMANTIC_CHANGE")
            or (
                capability_delta > 0
                and semantic_effect == "CAPABILITY_MODEL_EXPANSION_143_TO_175"
                and projection.get("capability_model_migration_decision")
                == "FA3-DEC-CAPABILITY-MODEL-175-2026-09-26"
            )
        )
    )

    expected_forbidden = {
        "STAGING_IMPLIES_PRODUCTION",
        "CANONICAL_CLOSED_IMPLIES_PROMOTED",
        "REFERENCE_CI_PASS_IMPLIES_CURRENT_HOST_PASS",
        "DOCUMENTATION_IMPLIES_RUNTIME_PASS",
        "ASSURANCE_RING_MAY_BYPASS_ACCEPTANCE",
        "ASSURANCE_RING_MAY_BYPASS_PROMOTION_GUARD",
    }

    checks: list[tuple[str, bool, str]] = [
        (
            "GOVT-001",
            projection.get("schema") == "fa3.governance-tiering.projection.v1"
            and projection.get("id") == PROJECTION_ID
            and projection.get("type") == "DERIVED_GOVERNANCE_PROJECTION",
            "projection identity/schema/type drift",
        ),
        (
            "GOVT-002",
            projection.get("authority_delta") == 0
            and declared_migration,
            "projection capability baseline change is undeclared, inconsistent, or gained authority",
        ),
        (
            "GOVT-003",
            policy.get("canonical_capability_count") == expected_count
            and policy.get("fail_closed") is True,
            "global canonical capability baseline or fail-closed policy drift",
        ),
        (
            "GOVT-004",
            policy.get("runtime_promotion_requires_current_host_evidence") is True
            and policy.get("document_only_promotion_forbidden") is True,
            "existing runtime promotion evidence boundary was weakened",
        ),
        (
            "GOVT-005",
            sources.get("canonical", {}).get("path") == PATHS["policy"]
            and sources.get("canonical", {}).get("release_projection_path") == PATHS["release"]
            and sources.get("evidence", {}).get("path") == PATHS["registry"],
            "projection no longer reads the canonical/evidence authorities",
        ),
        (
            "GOVT-006",
            sources.get("acceptance", {}).get("mode") == "READ_ONLY_GENERATED_OUTPUT"
            and sources.get("promotion", {}).get("mode") == "READ_ONLY_GENERATED_OUTPUT"
            and sources.get("acceptance", {}).get("producer") == "src/fa3_enforce.py::acceptance_check"
            and sources.get("promotion", {}).get("producer") == "src/fa3_enforce.py::promote",
            "Acceptance or Promotion ownership was duplicated by the projection",
        ),
        (
            "GOVT-007",
            sources.get("current_host", {}).get("projection_does_not_create_receipts") is True
            and set(sources.get("current_host", {}).get("required_runner_labels", []))
            == {"self-hosted", "linux", "x64", "fa3-current-host"}
            and "runs-on: [self-hosted, linux, x64, fa3-current-host]" in workflow_text,
            "current-host evidence or runner authority drift",
        ),
        (
            "GOVT-008",
            ring_ids == EXPECTED_RINGS and ordinals == [10, 20, 30]
            and derivation.get("assurance_ring_order") == EXPECTED_RINGS,
            "assurance ring definition/order drift",
        ),
        (
            "GOVT-009",
            assurance.get("owned_by_projection") is True
            and assurance.get("authoritative_for_production") is False
            and assurance.get("demotion_on_invalidation") is True
            and assurance.get("unknown_when_derivation_inputs_are_insufficient") is True,
            "assurance projection acquired production authority or lost fail-closed semantics",
        ),
        (
            "GOVT-010",
            canonical.get("owned_by_projection") is False
            and canonical.get("state_model") == "SOURCE_DEFINED_PASSTHROUGH"
            and runtime.get("owned_by_projection") is False
            and runtime.get("state_model") == "SOURCE_DEFINED_PASSTHROUGH",
            "canonical/runtime states became projection-owned",
        ),
        (
            "GOVT-011",
            derivation.get("ring_is_not_promotion_state") is True
            and derivation.get("ring_is_not_canonical_state") is True
            and derivation.get("canonical_and_runtime_are_independent") is True
            and derivation.get("canonical_closed_with_pending_current_host_is_valid") is True
            and derivation.get("staging_with_not_promoted_is_valid") is True,
            "orthogonal lifecycle axes collapsed into a linear promotion chain",
        ),
        (
            "GOVT-012",
            derivation.get("promotion_must_be_read_from_existing_promotion_authority") is True
            and derivation.get("missing_or_ambiguous_authoritative_state") == "UNKNOWN_OR_PENDING"
            and derivation.get("fail_closed") is True,
            "projection may infer promotion or fail open on missing authority state",
        ),
        (
            "GOVT-013",
            all(value is False for value in non_authority.values())
            and len(non_authority) >= 8,
            "projection gained mutation, promotion, canonicalization, provider-enable, or evidence authority",
        ),
        (
            "GOVT-014",
            expected_forbidden.issubset(forbidden),
            "required anti-inference invariants are missing",
        ),
        (
            "GOVT-015",
            len(registry_records) == expected_count
            and not any(record.get("subject_id") == PROJECTION_ID for record in registry_records),
            "projection changed the active capability Evidence Registry cardinality or registered itself as a capability",
        ),
        (
            "GOVT-016",
            "def acceptance_check(" in enforce_text
            and "def promote(" in enforce_text
            and '"PROMOTION_BLOCKED"' in enforce_text
            and '"PROMOTED"' in enforce_text,
            "existing Acceptance/Promotion authority implementation is unavailable",
        ),
    ]

    findings = [finding(code, message) for code, ok, message in checks if not ok]
    return {
        "schema": "fa3.governance-tiering-gate-report.v1",
        "gate_set_id": GATESET_ID,
        "projection_id": PROJECTION_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "checks_passed": sum(1 for _, ok, _ in checks if ok),
        "checks_total": len(checks),
        "authority_delta": projection.get("authority_delta"),
        "capability_delta": projection.get("capability_delta"),
        "canonical_capability_count": policy.get("canonical_capability_count"),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the zero-authority FA3 governance tiering projection")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default="reports/governance-tiering-gate-report.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    result = gate(root)
    report_path = root / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
