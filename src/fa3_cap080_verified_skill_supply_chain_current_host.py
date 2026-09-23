#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from fa3_skill_fabric_gate import (
    gate as skill_gate,
    good_package,
    good_use_receipt,
    package_admission_allowed,
    run_regressions,
    skill_use_allowed,
)

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITY_ID = "CAP-080"
MODES = ("positive", "negative", "rollback")
PROFILE_PATH = "canonical/profiles/FA3-SKILL-FABRIC-001.json"
CONTRACT_PATH = "canonical/contracts/FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001.json"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("top-level object required")
    return obj


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_skill_fabric(root: Path) -> list[str]:
    findings: list[str] = []
    profile = _load(root / PROFILE_PATH)
    contract = _load(root / CONTRACT_PATH)

    if not (
        profile.get("id") == "FA3-SKILL-FABRIC-001"
        and profile.get("status") == "CANONICAL"
        and profile.get("priority") == "P0"
        and profile.get("requirement") == "MUST"
        and profile.get("provider_neutral") is True
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == 143
        and profile.get("contract_id") == "FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001"
    ):
        findings.append("skill-fabric identity/governance drift")

    boundaries = profile.get("authority_boundaries", {})
    if not boundaries or any(value is not False for value in boundaries.values()):
        findings.append("skill fabric expanded architectural authority")

    selection = profile.get("selection_and_composition", {})
    if not (
        selection.get("smallest_matching_skill_set_required") is True
        and selection.get("progressive_disclosure_required") is True
        and selection.get("global_everything_context_forbidden") is True
        and selection.get("explicit_dependencies_required") is True
        and selection.get("dependency_cycles_forbidden") is True
        and selection.get("composition_cannot_expand_authority") is True
    ):
        findings.append("skill selection/composition invariant drift")

    if not (
        contract.get("id") == "FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001"
        and contract.get("status") == "CANONICAL"
        and contract.get("provider_neutral") is True
        and contract.get("new_capability") is False
        and contract.get("new_architectural_authority") is False
        and contract.get("capability_count") == 143
    ):
        findings.append("skill admission contract identity/governance drift")

    supply = contract.get("supply_chain", {})
    execution = contract.get("execution_safety", {})
    dependencies = contract.get("dependency_governance", {})
    tools = contract.get("tool_governance", {})
    evaluation = contract.get("evaluation", {})
    if not (
        supply.get("floating_ref_not_sufficient_for_admission") is True
        and supply.get("immutable_commit_required") is True
        and supply.get("content_digest_required") is True
        and supply.get("manifest_digest_required") is True
        and supply.get("auto_pull_into_admitted_context_forbidden") is True
        and supply.get("new_upstream_commit_requires_new_admission") is True
        and supply.get("remote_include_or_fetch_during_admission_forbidden") is True
    ):
        findings.append("skill supply-chain invariant drift")
    if not (
        execution.get("package_is_data_until_separately_authorized") is True
        and execution.get("executable_directives_inert_by_default") is True
        and execution.get("shell_interpolation_implicit_execution_forbidden") is True
        and execution.get("script_asset_auto_execution_forbidden") is True
        and execution.get("direct_shell_tool_or_network_authority_from_skill_forbidden") is True
        and execution.get("symlink_escape_forbidden") is True
        and execution.get("absolute_path_and_parent_traversal_forbidden") is True
    ):
        findings.append("skill execution-safety invariant drift")
    if not (
        dependencies.get("explicit_graph_required") is True
        and dependencies.get("cycles_forbidden") is True
        and dependencies.get("hidden_dependency_inheritance_forbidden") is True
        and dependencies.get("dependency_versions_or_digests_required_at_use") is True
    ):
        findings.append("skill dependency-governance invariant drift")
    if not (
        tools.get("discovery_is_not_authorization") is True
        and tools.get("central_mcp_gateway_required") is True
        and tools.get("direct_secret_access_forbidden") is True
        and tools.get("direct_external_mutation_forbidden") is True
        and tools.get("mutation_requires_authorization_receipt") is True
        and tools.get("applicable_human_approval_preserved") is True
    ):
        findings.append("skill tool/authorization boundary drift")
    if not (
        evaluation.get("behavioral_eval_required") is True
        and evaluation.get("negative_eval_required") is True
        and evaluation.get("adversarial_prompt_injection_eval_required") is True
        and evaluation.get("eval_result_must_be_pass") is True
        and evaluation.get("eval_result_bound_to_content_digest") is True
    ):
        findings.append("skill evaluation invariant drift")
    return findings


def _run_positive(root: Path, scope: Path) -> dict[str, Any]:
    findings = validate_skill_fabric(root)
    if findings:
        raise RuntimeError("skill fabric validation failed: " + "; ".join(findings))

    report = skill_gate(root)
    regressions = run_regressions()
    package = good_package()
    use = good_use_receipt()

    if report.get("result") != "PASS":
        raise RuntimeError("canonical skill admission gate failed")
    if report.get("current_host_runtime_claim") is not False:
        raise RuntimeError("reference gate attempted current-host provider runtime claim")
    if regressions.get("result") != "PASS" or regressions.get("total", 0) < 45 or regressions.get("passed") != regressions.get("total"):
        raise RuntimeError("provider-neutral skill fabric regression matrix not PASS")
    if not package_admission_allowed(package):
        raise RuntimeError("known-valid skill package was rejected")
    if not skill_use_allowed(use):
        raise RuntimeError("known-valid skill use receipt was rejected")

    descriptor = scope / "verified-skill-package-positive.json"
    _write_json(descriptor, package)
    return {
        "mode": "positive",
        "status": "PASS",
        "canonical_gate": report["result"],
        "regression_total": regressions["total"],
        "regression_passed": regressions["passed"],
        "case_ids_exact": regressions.get("case_ids_exact"),
        "positive_package_admitted": True,
        "positive_use_receipt_admitted": True,
        "descriptor_sha256": _sha256(descriptor),
        "reference_provider_runtime_claim": False,
    }


def _run_negative(root: Path, scope: Path) -> dict[str, Any]:
    base = good_package()

    cycle = copy.deepcopy(base)
    cycle["dependencies"]["edges"].append({"from": "product-marketing", "to": "copywriting"})
    if package_admission_allowed(cycle):
        raise RuntimeError("dependency cycle was admitted")

    traversal = copy.deepcopy(base)
    traversal["files"].append("../escape")
    if package_admission_allowed(traversal):
        raise RuntimeError("path traversal was admitted")

    secret = copy.deepcopy(base)
    secret["execution"]["direct_credential_access"] = True
    if package_admission_allowed(secret):
        raise RuntimeError("direct credential access was admitted")

    active = copy.deepcopy(base)
    active["execution"]["mode"] = "ACTIVE_EXECUTION"
    if package_admission_allowed(active):
        raise RuntimeError("active execution directive was admitted")

    use = good_use_receipt()
    use["tool_intent"]["via_central_mcp"] = False
    if skill_use_allowed(use):
        raise RuntimeError("tool intent bypassing Central MCP was admitted")

    skipped = copy.deepcopy(base)
    skipped["review"]["skipped"] = True
    if package_admission_allowed(skipped):
        raise RuntimeError("skipped review was admitted")

    noncommercial = copy.deepcopy(base)
    noncommercial["license"]["commercial_use"] = "DENY"
    if package_admission_allowed(noncommercial):
        raise RuntimeError("non-commercial skill was admitted as redistributable")

    runtime_fetch = copy.deepcopy(base)
    runtime_fetch["execution"]["remote_fetch_during_activation"] = True
    if package_admission_allowed(runtime_fetch):
        raise RuntimeError("runtime remote skill fetch was admitted")

    expanded = good_use_receipt()
    expanded["candidate_expanded_after_eligibility"] = True
    if skill_use_allowed(expanded):
        raise RuntimeError("post-eligibility candidate expansion was admitted")

    evidence = {
        "dependency_cycle_rejected": True,
        "path_traversal_rejected": True,
        "direct_credential_access_rejected": True,
        "active_execution_rejected": True,
        "central_mcp_bypass_rejected": True,
        "skipped_review_rejected": True,
        "noncommercial_redistribution_rejected": True,
        "runtime_remote_fetch_rejected": True,
        "candidate_expansion_rejected": True,
    }
    _write_json(scope / "verified-skill-package-negative.json", evidence)
    return {"mode": "negative", "status": "PASS", **evidence}


def _run_rollback(root: Path, scope: Path) -> dict[str, Any]:
    descriptor = scope / "skill-package.rollback.json"
    baseline = good_package()
    original = (json.dumps(baseline, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    descriptor.write_bytes(original)
    pre_hash = _sha256_bytes(original)

    restored = _load(descriptor)
    if not package_admission_allowed(restored):
        raise RuntimeError("rollback baseline package invalid")

    faulted = copy.deepcopy(restored)
    faulted["dependencies"]["edges"].append({"from": "product-marketing", "to": "copywriting"})
    _write_json(descriptor, faulted)
    mutated_hash = _sha256(descriptor)
    if package_admission_allowed(_load(descriptor)):
        raise RuntimeError("rollback fault package remained admitted")

    descriptor.write_bytes(original)
    post_hash = _sha256(descriptor)
    if post_hash != pre_hash:
        raise RuntimeError("rollback did not restore exact descriptor bytes")
    if mutated_hash == pre_hash:
        raise RuntimeError("rollback fault did not change descriptor digest")
    if not package_admission_allowed(_load(descriptor)):
        raise RuntimeError("restored package not admitted")

    return {
        "mode": "rollback",
        "status": "PASS",
        "pre_sha256": pre_hash,
        "mutated_sha256": mutated_hash,
        "post_sha256": post_hash,
        "fault_rejected": True,
        "rollback_hash_equal": True,
        "restored_package_admitted": True,
    }


def run_mode(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    root = root.resolve()
    scope = scope.resolve()
    if mode not in MODES:
        raise ValueError(f"unsupported mode: {mode}")
    if root not in scope.parents:
        raise RuntimeError("source artifact scope escapes repository")
    scope.mkdir(parents=True, exist_ok=True)
    if mode == "positive":
        return _run_positive(root, scope)
    if mode == "negative":
        return _run_negative(root, scope)
    return _run_rollback(root, scope)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable missing: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="CAP-080 current-host verified skill supply-chain qualification producer")
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if _required_env("FA3_CURRENT_HOST") != "1":
            raise RuntimeError("real current-host execution marker required")
        if _required_env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("CURRENT_HOST execution scope required")
        if _required_env("FA3_CAPABILITY_ID") != CAPABILITY_ID:
            raise RuntimeError("producer is bound only to CAP-080")
        root = Path(_required_env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(_required_env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        result = run_mode(root, scope, args.mode)
        artifact = scope / "cap080-verified-skill-supply-chain-evidence.json"
        payload = {
            "schema": "fa3.cap080-verified-skill-supply-chain-current-host-evidence.v1",
            "subject_id": CAPABILITY_ID,
            "test_kind": _required_env("FA3_TEST_KIND"),
            "test_id": _required_env("FA3_TEST_ID"),
            "qualification_id": _required_env("FA3_QUALIFICATION_ID"),
            "constituent_id": _required_env("FA3_CONSTITUENT_ID"),
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "global_promotion_claim": False,
            "result": result,
        }
        _write_json(artifact, payload)
        verdict = {
            "schema": VERDICT_SCHEMA,
            "producer_id": args.producer_id,
            "qualification_id": _required_env("FA3_QUALIFICATION_ID"),
            "constituent_id": _required_env("FA3_CONSTITUENT_ID"),
            "subject_id": CAPABILITY_ID,
            "test_kind": _required_env("FA3_TEST_KIND"),
            "test_id": _required_env("FA3_TEST_ID"),
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "source_evidence_class": _required_env("FA3_SOURCE_EVIDENCE_CLASS"),
            "covers_source_decision_ids": json.loads(_required_env("FA3_COVERS_SOURCE_DECISION_IDS_JSON")),
            "source_artifact_path": artifact.relative_to(root).as_posix(),
            "source_artifact_sha256": _sha256(artifact),
        }
        print(json.dumps(verdict, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "REJECTED", "findings": [str(exc)]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
