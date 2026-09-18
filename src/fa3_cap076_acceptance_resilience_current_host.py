#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from fa3_enforce import BLOCKED, OK, acceptance_check, promote, receipt_ok

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITY_ID = "CAP-076"
MODES = ("positive", "negative", "rollback")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_acceptance_promotion(
    acceptance: dict[str, Any],
    state: dict[str, Any],
    rc: int,
) -> list[str]:
    findings: list[str] = []
    status = acceptance.get("status")
    decision = acceptance.get("decision")
    if acceptance.get("schema") != "fa3.acceptance-report.v1":
        findings.append("acceptance schema mismatch")
    if acceptance.get("fail_closed") is not True:
        findings.append("acceptance fail_closed must be true")
    if acceptance.get("criteria_total") != 19:
        findings.append("acceptance criteria_total must be 19")
    if status not in {"PASS", "DENIED"}:
        findings.append("acceptance status invalid")
    if (status == "PASS") != (decision == "ACCEPT"):
        findings.append("acceptance status/decision mismatch")

    allowed = status == "PASS"
    expected_state = "PROMOTED" if allowed else "PROMOTION_BLOCKED"
    expected_rc = OK if allowed else BLOCKED
    if state.get("schema") != "fa3.runtime-status.v1":
        findings.append("promotion state schema mismatch")
    if state.get("target_state") != "PROMOTED":
        findings.append("promotion target_state mismatch")
    if state.get("promotion_allowed") is not allowed:
        findings.append("promotion_allowed inconsistent with acceptance")
    if state.get("actual_state") != expected_state:
        findings.append("actual_state inconsistent with acceptance")
    if state.get("acceptance") != status:
        findings.append("promotion acceptance field mismatch")
    if rc != expected_rc:
        findings.append("promotion return code inconsistent with acceptance")
    if not allowed and not state.get("reason"):
        findings.append("blocked promotion must carry reason")
    return findings


def _run_positive(root: Path, scope: Path) -> dict[str, Any]:
    acceptance = acceptance_check(root)
    state, rc = promote(root)
    findings = validate_acceptance_promotion(acceptance, state, rc)
    if findings:
        raise RuntimeError("acceptance/promotion consistency failed: " + "; ".join(findings))
    result = {
        "mode": "positive",
        "status": "PASS",
        "acceptance_status": acceptance["status"],
        "acceptance_decision": acceptance["decision"],
        "criteria_passed": acceptance.get("criteria_passed"),
        "criteria_total": acceptance.get("criteria_total"),
        "static_gate": acceptance.get("static_gate"),
        "runtime_gate": acceptance.get("runtime_gate"),
        "terax_gate": acceptance.get("terax_gate"),
        "promotion_allowed": state.get("promotion_allowed"),
        "promotion_actual_state": state.get("actual_state"),
        "promotion_rc": rc,
        "decision_consistent": True,
    }
    return result


def _run_negative(root: Path, scope: Path) -> dict[str, Any]:
    invalid_status = scope / "invalid-status-receipt.json"
    _write_json(invalid_status, {"status": "FAIL", "signed": True})
    status_ok, status_reason = receipt_ok(invalid_status, signed=True)
    if status_ok:
        raise RuntimeError("FAIL receipt was accepted")

    unsigned = scope / "unsigned-receipt.json"
    _write_json(unsigned, {"status": "PASS", "signed": False})
    signed_ok, signed_reason = receipt_ok(unsigned, signed=True)
    if signed_ok:
        raise RuntimeError("unsigned receipt was accepted where signature is required")

    unreadable = scope / "unreadable-receipt.json"
    unreadable.write_text("{not-json", encoding="utf-8")
    readable_ok, readable_reason = receipt_ok(unreadable)
    if readable_ok:
        raise RuntimeError("unreadable receipt was accepted")

    return {
        "mode": "negative",
        "status": "PASS",
        "fail_status_rejected": True,
        "fail_status_reason": status_reason,
        "unsigned_rejected": True,
        "unsigned_reason": signed_reason,
        "unreadable_rejected": True,
        "unreadable_reason": readable_reason,
    }


def _run_rollback(root: Path, scope: Path) -> dict[str, Any]:
    receipt = scope / "rollback-drill-receipt.json"
    original = (
        json.dumps(
            {
                "status": "PASS",
                "signed": True,
                "drill": "CAP-076",
                "state": "BASELINE",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    receipt.write_bytes(original)
    pre_hash = _sha256_bytes(original)
    pre_ok, pre_reason = receipt_ok(receipt, signed=True)
    if not pre_ok:
        raise RuntimeError(f"rollback baseline receipt invalid: {pre_reason}")

    mutated = (
        json.dumps(
            {
                "status": "FAIL",
                "signed": False,
                "drill": "CAP-076",
                "state": "FAULT_INJECTED",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    receipt.write_bytes(mutated)
    mutated_hash = _sha256(receipt)
    fault_ok, fault_reason = receipt_ok(receipt, signed=True)
    if fault_ok:
        raise RuntimeError("fault-injected receipt remained accepted")

    receipt.write_bytes(original)
    post_hash = _sha256(receipt)
    post_ok, post_reason = receipt_ok(receipt, signed=True)
    if not post_ok:
        raise RuntimeError(f"restored rollback receipt invalid: {post_reason}")
    if post_hash != pre_hash:
        raise RuntimeError("rollback did not restore exact baseline bytes")
    if mutated_hash == pre_hash:
        raise RuntimeError("failure injection did not change receipt digest")

    return {
        "mode": "rollback",
        "status": "PASS",
        "pre_sha256": pre_hash,
        "mutated_sha256": mutated_hash,
        "post_sha256": post_hash,
        "fault_rejected": True,
        "fault_reason": fault_reason,
        "rollback_hash_equal": post_hash == pre_hash,
        "restored_receipt_valid": post_ok,
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
    parser = argparse.ArgumentParser(
        description="CAP-076 current-host acceptance, resilience and rollback qualification producer"
    )
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if _required_env("FA3_CURRENT_HOST") != "1":
            raise RuntimeError("real current-host execution marker required")
        if _required_env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("CURRENT_HOST execution scope required")
        if _required_env("FA3_CAPABILITY_ID") != CAPABILITY_ID:
            raise RuntimeError("producer is bound only to CAP-076")
        root = Path(_required_env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(_required_env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        result = run_mode(root, scope, args.mode)
        artifact = scope / "cap076-acceptance-resilience-evidence.json"
        payload = {
            "schema": "fa3.cap076-acceptance-resilience-current-host-evidence.v1",
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
            "covers_source_decision_ids": json.loads(
                _required_env("FA3_COVERS_SOURCE_DECISION_IDS_JSON")
            ),
            "source_artifact_path": artifact.relative_to(root).as_posix(),
            "source_artifact_sha256": _sha256(artifact),
        }
        print(json.dumps(verdict, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(
            json.dumps({"status": "REJECTED", "findings": [str(exc)]}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
