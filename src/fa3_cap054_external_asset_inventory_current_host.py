#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITY_ID = "CAP-054"
LOCK_REGISTRY = "canonical/FA3-UPSTREAM-LOCK-REGISTRY-001.json"
MODES = ("positive", "negative", "rollback")
FLOATING = {"main", "master", "head", "latest", "tip"}
HEX_REV = re.compile(r"^[0-9a-f]{40,64}$")


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


def validate_inventory(registry: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if registry.get("id") != "FA3-UPSTREAM-LOCK-REGISTRY-001":
        findings.append("registry id mismatch")
    if registry.get("schema") != "fa3.upstream-lock-registry.v1":
        findings.append("registry schema mismatch")
    if registry.get("status") != "CANONICAL":
        findings.append("registry status must be CANONICAL")

    policy = registry.get("policy")
    if not isinstance(policy, dict):
        findings.append("policy missing")
        policy = {}
    if policy.get("immutable_identity_required") is not True:
        findings.append("immutable identity policy disabled")
    if policy.get("floating_main_allowed_for_runtime") is not False:
        findings.append("floating runtime refs must be forbidden")
    if policy.get("floating_main_allowed_for_promotion_evidence") is not False:
        findings.append("floating promotion refs must be forbidden")
    for key in (
        "updates_require_candidate_validation",
        "updates_require_security_scan",
        "updates_require_conformance",
        "updates_require_evidence_binding",
        "lock_change_requires_review",
    ):
        if policy.get(key) is not True:
            findings.append(f"required policy disabled: {key}")

    locks = registry.get("locks")
    if not isinstance(locks, dict) or not locks:
        findings.append("lock inventory is empty")
        locks = {}

    provider_ids: set[str] = set()
    for lock_id, row in sorted(locks.items()):
        if not isinstance(lock_id, str) or not lock_id:
            findings.append("lock id invalid")
            continue
        if not isinstance(row, dict):
            findings.append(f"{lock_id}: lock row must be object")
            continue
        provider_id = row.get("provider_id")
        if not isinstance(provider_id, str) or not provider_id.startswith("FA3-PROVIDER-"):
            findings.append(f"{lock_id}: provider_id invalid")
        elif provider_id in provider_ids:
            findings.append(f"{lock_id}: duplicate provider_id {provider_id}")
        else:
            provider_ids.add(provider_id)

        kind = row.get("kind")
        if not isinstance(kind, str) or not kind:
            findings.append(f"{lock_id}: kind missing")
        revision = row.get("revision")
        if not isinstance(revision, str) or not revision:
            findings.append(f"{lock_id}: immutable revision missing")
        else:
            if revision.strip().lower() in FLOATING:
                findings.append(f"{lock_id}: floating revision forbidden")
            if kind in {"git_commit", "release_plus_commit", "model_revision"} and not HEX_REV.fullmatch(revision):
                findings.append(f"{lock_id}: immutable revision is not pinned hexadecimal identity")
        if row.get("update_policy") != "CONTROLLED":
            findings.append(f"{lock_id}: update_policy must be CONTROLLED")

    pipeline = registry.get("promotion_pipeline")
    required_pipeline = [
        "DISCOVER_CANDIDATE",
        "RESOLVE_IMMUTABLE_IDENTITY",
        "SECURITY_SCAN",
        "SANDBOX_CONFORMANCE",
        "CURRENT_HOST_WHEN_REQUIRED",
        "WRITE_EVIDENCE",
        "REVIEW_LOCK_DIFF",
        "PROMOTE_LOCK",
    ]
    if pipeline != required_pipeline:
        findings.append("promotion pipeline drift")
    return findings


def _run_positive(root: Path, scope: Path) -> dict[str, Any]:
    registry_path = root / LOCK_REGISTRY
    registry = _load(registry_path)
    findings = validate_inventory(registry)
    if findings:
        raise RuntimeError("external asset inventory validation failed: " + "; ".join(findings))
    locks = registry["locks"]
    return {
        "mode": "positive",
        "status": "PASS",
        "lock_count": len(locks),
        "provider_count": len({row["provider_id"] for row in locks.values()}),
        "registry_sha256": _sha256(registry_path),
        "immutable_identity_required": True,
        "floating_runtime_refs_allowed": False,
    }


def _run_negative(root: Path, scope: Path) -> dict[str, Any]:
    baseline = _load(root / LOCK_REGISTRY)

    duplicate = json.loads(json.dumps(baseline))
    keys = sorted(duplicate["locks"])
    if len(keys) < 2:
        raise RuntimeError("negative duplicate-provider injection requires at least two locks")
    duplicate["locks"][keys[1]]["provider_id"] = duplicate["locks"][keys[0]]["provider_id"]
    duplicate_findings = validate_inventory(duplicate)
    if not any("duplicate provider_id" in item for item in duplicate_findings):
        raise RuntimeError("duplicate provider identity was not rejected")

    floating = json.loads(json.dumps(baseline))
    first = sorted(floating["locks"])[0]
    floating["locks"][first]["revision"] = "main"
    floating_findings = validate_inventory(floating)
    if not any("floating revision forbidden" in item for item in floating_findings):
        raise RuntimeError("floating revision was not rejected")

    return {
        "mode": "negative",
        "status": "PASS",
        "duplicate_provider_rejected": True,
        "floating_revision_rejected": True,
        "duplicate_findings": duplicate_findings,
        "floating_findings": floating_findings,
    }


def _run_rollback(root: Path, scope: Path) -> dict[str, Any]:
    original = (root / LOCK_REGISTRY).read_bytes()
    pre_hash = _sha256_bytes(original)
    scratch = scope / "upstream-lock-registry.rollback.json"
    scratch.write_bytes(original)
    before = _load(scratch)
    before_findings = validate_inventory(before)
    if before_findings:
        raise RuntimeError("rollback baseline inventory invalid: " + "; ".join(before_findings))

    mutated = json.loads(json.dumps(before))
    first = sorted(mutated["locks"])[0]
    mutated["locks"][first]["revision"] = "latest"
    _write_json(scratch, mutated)
    mutated_hash = _sha256(scratch)
    mutated_findings = validate_inventory(_load(scratch))
    if not mutated_findings:
        raise RuntimeError("rollback failure injection was not detected")

    scratch.write_bytes(original)
    post_hash = _sha256(scratch)
    restored_findings = validate_inventory(_load(scratch))
    if restored_findings:
        raise RuntimeError("restored lock inventory invalid: " + "; ".join(restored_findings))
    if post_hash != pre_hash:
        raise RuntimeError("rollback did not restore exact lock registry bytes")
    if mutated_hash == pre_hash:
        raise RuntimeError("failure injection did not change lock registry digest")

    return {
        "mode": "rollback",
        "status": "PASS",
        "pre_sha256": pre_hash,
        "mutated_sha256": mutated_hash,
        "post_sha256": post_hash,
        "fault_detected": True,
        "rollback_hash_equal": post_hash == pre_hash,
        "restored_inventory_valid": True,
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
    parser = argparse.ArgumentParser(description="CAP-054 current-host external asset inventory qualification producer")
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if _required_env("FA3_CURRENT_HOST") != "1":
            raise RuntimeError("real current-host execution marker required")
        if _required_env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("CURRENT_HOST execution scope required")
        if _required_env("FA3_CAPABILITY_ID") != CAPABILITY_ID:
            raise RuntimeError("producer is bound only to CAP-054")
        root = Path(_required_env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(_required_env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        result = run_mode(root, scope, args.mode)
        artifact = scope / "cap054-external-asset-inventory-evidence.json"
        payload = {
            "schema": "fa3.cap054-external-asset-inventory-current-host-evidence.v1",
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
