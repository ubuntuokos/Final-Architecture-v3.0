#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITY_ID = "CAP-075"
CONTRACT_ROOT = "canonical/contracts"
ROLLBACK_TARGET = "canonical/contracts/FA3-OS-EVENT-001.schema.json"
MODES = ("positive", "negative", "rollback")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _identity(obj: dict[str, Any]) -> str | None:
    for key in ("id", "x-fa3-contract-id", "$id"):
        value = obj.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def validate_contract_files(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    identities: dict[str, str] = {}
    if not paths:
        return ["contract registry is empty"]
    for path in sorted(paths):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            findings.append(f"{path.name}: invalid JSON: {exc}")
            continue
        if not isinstance(obj, dict):
            findings.append(f"{path.name}: top-level object required")
            continue
        identity = _identity(obj)
        if identity is None:
            findings.append(f"{path.name}: contract identity missing")
        elif identity in identities:
            findings.append(f"{path.name}: duplicate contract identity {identity} also in {identities[identity]}")
        else:
            identities[identity] = path.name
        if path.name.endswith(".schema.json"):
            if not isinstance(obj.get("$schema"), str) or not obj.get("$schema"):
                findings.append(f"{path.name}: JSON Schema dialect missing")
            if not isinstance(obj.get("$id"), str) or not obj.get("$id"):
                findings.append(f"{path.name}: JSON Schema $id missing")
    return findings


def _canonical_contracts(root: Path) -> list[Path]:
    contract_root = (root / CONTRACT_ROOT).resolve()
    if root not in contract_root.parents or not contract_root.is_dir():
        raise RuntimeError("canonical contract registry missing")
    return sorted(path for path in contract_root.glob("*.json") if path.is_file())


def _run_positive(root: Path, scope: Path) -> dict[str, Any]:
    paths = _canonical_contracts(root)
    findings = validate_contract_files(paths)
    required = root / ROLLBACK_TARGET
    if required not in paths:
        findings.append("FA3 OS event schema missing from contract registry")
    if findings:
        raise RuntimeError("positive registry validation failed: " + "; ".join(findings[:20]))
    identities = []
    for path in paths:
        obj = json.loads(path.read_text(encoding="utf-8"))
        identities.append(_identity(obj))
    return {
        "mode": "positive",
        "status": "PASS",
        "contract_file_count": len(paths),
        "unique_identity_count": len(set(identities)),
        "event_schema_present": required.is_file(),
        "registry_digest": hashlib.sha256(
            "\n".join(f"{p.name}:{_sha256(p)}" for p in paths).encode("utf-8")
        ).hexdigest(),
    }


def _run_negative(root: Path, scope: Path) -> dict[str, Any]:
    target = root / ROLLBACK_TARGET
    source = json.loads(target.read_text(encoding="utf-8"))
    fixture = scope / "negative-fixture"
    fixture.mkdir(parents=True, exist_ok=True)
    first = fixture / "duplicate-a.schema.json"
    second = fixture / "duplicate-b.schema.json"
    first.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    second.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    findings = validate_contract_files([first, second])
    if not any("duplicate contract identity" in item for item in findings):
        raise RuntimeError("negative duplicate-contract injection was not rejected")
    return {
        "mode": "negative",
        "status": "PASS",
        "injected_fault": "DUPLICATE_CONTRACT_IDENTITY",
        "rejection_observed": True,
        "rejection_findings": findings,
    }


def _run_rollback(root: Path, scope: Path) -> dict[str, Any]:
    target = root / ROLLBACK_TARGET
    original = target.read_bytes()
    pre_hash = _sha256_bytes(original)
    scratch = scope / "rollback-fixture.schema.json"
    scratch.write_bytes(original)
    scratch.write_bytes(b'{"corrupted":')
    mutated_hash = _sha256(scratch)
    mutation_findings = validate_contract_files([scratch])
    if not mutation_findings:
        raise RuntimeError("rollback failure injection did not make registry entry invalid")
    scratch.write_bytes(original)
    post_hash = _sha256(scratch)
    restored_findings = validate_contract_files([scratch])
    if post_hash != pre_hash or restored_findings:
        raise RuntimeError("rollback did not restore exact valid contract bytes")
    return {
        "mode": "rollback",
        "status": "PASS",
        "target": ROLLBACK_TARGET,
        "pre_sha256": pre_hash,
        "mutated_sha256": mutated_hash,
        "post_sha256": post_hash,
        "mutation_rejected": True,
        "rollback_hash_equal": post_hash == pre_hash,
        "restored_contract_valid": True,
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
    parser = argparse.ArgumentParser(description="CAP-075 current-host contract registry qualification producer")
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if _required_env("FA3_CURRENT_HOST") != "1":
            raise RuntimeError("real current-host execution marker required")
        if _required_env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("CURRENT_HOST execution scope required")
        if _required_env("FA3_CAPABILITY_ID") != CAPABILITY_ID:
            raise RuntimeError("producer is bound only to CAP-075")
        root = Path(_required_env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(_required_env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        result = run_mode(root, scope, args.mode)
        artifact = scope / "cap075-contract-registry-evidence.json"
        payload = {
            "schema": "fa3.cap075-contract-registry-current-host-evidence.v1",
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
        artifact.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
