#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

TEST_KINDS = ("positive", "negative", "rollback")
REQUEST_SCHEMA = "fa3.current-host-change-request.v1"
RECEIPT_SCHEMA = "fa3.current-host-delta-receipt.v1"
BASE_SCHEMA = "fa3.current-host-base-state.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _cap_sort_key(capability_id: str) -> tuple[int, str]:
    try:
        return (int(capability_id.split("-", 1)[1]), capability_id)
    except Exception:
        return (10**9, capability_id)


def canonical_capabilities(root: Path) -> list[str]:
    registry = load_json(root / "evidence/evidence-registry.json")
    ids = [
        row.get("subject_id")
        for row in registry.get("records", [])
        if isinstance(row, dict)
        and isinstance(row.get("subject_id"), str)
        and row["subject_id"].startswith("CAP-")
    ]
    expected = registry.get("canonical_capability_count")
    if not isinstance(expected, int) or expected <= 0:
        raise ValueError("evidence registry canonical_capability_count missing")
    if len(ids) != expected or len(set(ids)) != expected:
        raise ValueError("evidence registry capability set/cardinality mismatch")
    return sorted(ids, key=_cap_sort_key)


def _list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def validate_request(root: Path, request: dict[str, Any], authority: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    caps = set(canonical_capabilities(root))

    if request.get("schema") != REQUEST_SCHEMA:
        findings.append("request schema mismatch")
    for key in ("request_id", "application_id", "rationale"):
        if not isinstance(request.get(key), str) or not request[key].strip():
            findings.append(f"{key} is required")

    for key in ("base_release_digest", "parent_effective_digest", "change_digest"):
        value = request.get(key)
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            findings.append(f"{key} must be a lowercase sha256 hex digest")

    impact = request.get("runtime_impact")
    allowed = set(authority.get("runtime_impact_classes", []))
    if impact not in allowed:
        findings.append("runtime_impact is unsupported")

    changed_paths = request.get("changed_paths")
    if not _list_of_strings(changed_paths) or not changed_paths:
        findings.append("changed_paths must be a non-empty string list")

    affected = request.get("affected_capabilities", [])
    consumers = request.get("consumer_capabilities", [])
    for label, values in (("affected_capabilities", affected), ("consumer_capabilities", consumers)):
        if not _list_of_strings(values):
            findings.append(f"{label} must be a string list")
            continue
        if len(values) != len(set(values)):
            findings.append(f"{label} contains duplicates")
        unknown = sorted(set(values) - caps, key=_cap_sort_key)
        if unknown:
            findings.append(f"{label} contains unknown capability IDs: {unknown}")

    flags = request.get("flags")
    if not isinstance(flags, dict):
        findings.append("flags must be an object")
        flags = {}
    allowed_flags = set(authority.get("full_requalification_trigger_flags", [])) | {
        "hardware_surface_changed",
        "software_coexistence_surface_changed",
    }
    unknown_flags = sorted(set(flags) - allowed_flags)
    if unknown_flags:
        findings.append(f"flags contains unsupported keys: {unknown_flags}")
    for key, value in flags.items():
        if not isinstance(value, bool):
            findings.append(f"flags.{key} must be boolean")

    if request.get("global_promotion_claim") is not False:
        findings.append("global_promotion_claim must be false")

    full_trigger = impact == "GLOBAL" or any(
        flags.get(key) is True for key in authority.get("full_requalification_trigger_flags", [])
    )
    if impact in {"LOCAL", "SHARED"} and not affected and not full_trigger:
        findings.append("runtime-changing request requires affected_capabilities")
    if impact == "SHARED" and not consumers and not full_trigger:
        findings.append("SHARED runtime impact requires consumer_capabilities")
    if impact == "NONE" and any(flags.get(key) is True for key in allowed_flags):
        findings.append("NONE runtime impact cannot declare runtime/global change flags")

    return findings


def plan_request(root: Path, request: dict[str, Any], authority: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    authority = authority or load_json(root / "canonical/FA3-CURRENT-HOST-CHANGE-DELTA-AUTHORITY-001.json")
    findings = validate_request(root, request, authority)
    if findings:
        return {
            "schema": "fa3.current-host-delta-plan.v1",
            "status": "FAIL",
            "fail_closed": True,
            "findings": findings,
            "global_promotion_claim": False,
        }

    all_caps = canonical_capabilities(root)
    flags = request["flags"]
    full_trigger = request["runtime_impact"] == "GLOBAL" or any(
        flags.get(key) is True for key in authority["full_requalification_trigger_flags"]
    )

    if request["runtime_impact"] == "NONE":
        classification = "NO_RUNTIME_IMPACT"
        selected_caps: list[str] = []
    elif full_trigger:
        classification = "FULL_REQUALIFICATION"
        selected_caps = list(all_caps)
    elif request["runtime_impact"] == "SHARED" or request.get("consumer_capabilities"):
        classification = "IMPACT_REQUALIFICATION"
        selected_caps = sorted(
            set(request["affected_capabilities"])
            | set(request.get("consumer_capabilities", []))
            | set(authority.get("mandatory_runtime_delta_capabilities", [])),
            key=_cap_sort_key,
        )
    else:
        classification = "CAPABILITY_DELTA_REQUALIFICATION"
        selected_caps = sorted(
            set(request["affected_capabilities"])
            | set(authority.get("mandatory_runtime_delta_capabilities", [])),
            key=_cap_sort_key,
        )

    obligations = [
        {"capability_id": capability_id, "test_kind": test_kind}
        for capability_id in selected_caps
        for test_kind in TEST_KINDS
    ]
    required_shared_gates = [] if classification == "NO_RUNTIME_IMPACT" else list(
        authority.get("required_shared_gates", [])
    )
    plan = {
        "schema": "fa3.current-host-delta-plan.v1",
        "status": "PASS",
        "fail_closed": True,
        "authority_id": authority["id"],
        "request_id": request["request_id"],
        "application_id": request["application_id"],
        "classification": classification,
        "base_release_digest": request["base_release_digest"],
        "parent_effective_digest": request["parent_effective_digest"],
        "change_digest": request["change_digest"],
        "changed_paths": sorted(set(request["changed_paths"])),
        "affected_capabilities": selected_caps,
        "affected_capability_count": len(selected_caps),
        "required_test_kinds": list(TEST_KINDS),
        "required_obligations": obligations,
        "required_obligation_count": len(obligations),
        "required_shared_gates": required_shared_gates,
        "hardware_surface_changed": bool(flags.get("hardware_surface_changed")),
        "software_coexistence_surface_changed": bool(flags.get("software_coexistence_surface_changed")),
        "base_full_closure_required_before_delta_activation": classification != "NO_RUNTIME_IMPACT",
        "unaffected_base_proof_semantics": "REMAINS_BOUND_TO_IMMUTABLE_BASE_ONLY_NOT_COPIED_OR_RELABELED_TO_DELTA",
        "physical_current_host_proof_required": classification != "NO_RUNTIME_IMPACT",
        "historical_evidence_reused": False,
        "synthetic_current_host_pass_allowed": False,
        "global_promotion_claim": False,
        "activation_status": (
            "NO_RUNTIME_ACTIVATION_REQUIRED"
            if classification == "NO_RUNTIME_IMPACT"
            else "PLANNED_REQUIRES_FRESH_PHYSICAL_DELTA_PROOF"
        ),
        "findings": [],
    }
    plan["plan_digest"] = _digest_json(plan)
    return plan


def verify_delta_receipt(plan: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    if plan.get("status") != "PASS":
        findings.append("delta plan is not PASS")
    if plan.get("classification") == "NO_RUNTIME_IMPACT":
        findings.append("NO_RUNTIME_IMPACT plan does not accept a runtime delta receipt")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("receipt schema mismatch")
    for key in ("plan_digest", "base_release_digest", "parent_effective_digest", "change_digest"):
        if receipt.get(key) != plan.get(key):
            findings.append(f"receipt {key} does not match plan")
    if receipt.get("physical_current_host_execution") is not True:
        findings.append("physical_current_host_execution must be true")
    if receipt.get("synthetic_current_host_pass") is not False:
        findings.append("synthetic_current_host_pass must be false")
    if receipt.get("historical_evidence_reused") is not False:
        findings.append("historical_evidence_reused must be false")
    if receipt.get("global_promotion_claim") is not False:
        findings.append("global_promotion_claim must be false")

    expected = {
        (row["capability_id"], row["test_kind"])
        for row in plan.get("required_obligations", [])
        if isinstance(row, dict)
    }
    proofs = receipt.get("proofs")
    actual: set[tuple[str, str]] = set()
    proof_projection: list[dict[str, str]] = []
    if not isinstance(proofs, list):
        findings.append("proofs must be a list")
        proofs = []
    for row in proofs:
        if not isinstance(row, dict):
            findings.append("proof row must be an object")
            continue
        key = (row.get("capability_id"), row.get("test_kind"))
        if not all(isinstance(item, str) for item in key):
            findings.append("proof capability_id/test_kind missing")
            continue
        if key in actual:
            findings.append(f"duplicate proof obligation: {key[0]}/{key[1]}")
        actual.add(key)
        if row.get("status") != "PASS":
            findings.append(f"proof is not PASS: {key[0]}/{key[1]}")
        artifact = row.get("artifact_sha256")
        if not isinstance(artifact, str) or HEX64.fullmatch(artifact) is None:
            findings.append(f"proof artifact digest invalid: {key[0]}/{key[1]}")
        else:
            proof_projection.append(
                {"capability_id": key[0], "test_kind": key[1], "artifact_sha256": artifact}
            )
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            findings.append(f"missing proof obligations: {missing}")
        if extra:
            findings.append(f"unexpected proof obligations: {extra}")

    gates = receipt.get("shared_gates")
    if not isinstance(gates, dict):
        findings.append("shared_gates must be an object")
        gates = {}
    for gate in plan.get("required_shared_gates", []):
        if gates.get(gate) != "PASS":
            findings.append(f"required shared gate is not PASS: {gate}")

    if findings:
        return {
            "schema": "fa3.current-host-delta-gate-report.v1",
            "result": "FAIL",
            "fail_closed": True,
            "plan_digest": plan.get("plan_digest"),
            "global_promotion_claim": False,
            "findings": findings,
        }

    evidence_projection = {
        "plan_digest": plan["plan_digest"],
        "base_release_digest": plan["base_release_digest"],
        "parent_effective_digest": plan["parent_effective_digest"],
        "change_digest": plan["change_digest"],
        "proofs": sorted(proof_projection, key=lambda x: (_cap_sort_key(x["capability_id"]), x["test_kind"])),
        "shared_gates": {key: gates[key] for key in sorted(plan["required_shared_gates"])},
    }
    delta_digest = _digest_json(evidence_projection)
    effective_host_digest = _digest_text(plan["parent_effective_digest"] + ":" + delta_digest)
    return {
        "schema": "fa3.current-host-delta-gate-report.v1",
        "result": "PASS",
        "fail_closed": True,
        "delta_status": "DELTA_ADMITTED",
        "request_id": plan["request_id"],
        "application_id": plan["application_id"],
        "classification": plan["classification"],
        "base_release_digest": plan["base_release_digest"],
        "parent_effective_digest": plan["parent_effective_digest"],
        "change_digest": plan["change_digest"],
        "plan_digest": plan["plan_digest"],
        "delta_digest": delta_digest,
        "effective_host_digest": effective_host_digest,
        "affected_capabilities": plan["affected_capabilities"],
        "verified_obligation_count": len(expected),
        "historical_evidence_reused": False,
        "synthetic_current_host_pass": False,
        "global_promotion_claim": False,
        "findings": [],
    }


def compose_effective_host(base: dict[str, Any], deltas: list[dict[str, Any]]) -> dict[str, Any]:
    findings: list[str] = []
    if base.get("schema") != BASE_SCHEMA:
        findings.append("base state schema mismatch")
    if base.get("status") != "CURRENT_HOST_BASE_ADMITTED":
        findings.append("base Current Host is not admitted")
    if base.get("capability_count") != 175 or base.get("obligation_count") != 525:
        findings.append("base state is not the fixed 175/525 model")
    base_digest = base.get("base_release_digest")
    effective = base.get("effective_host_digest", base_digest)
    if not isinstance(base_digest, str) or HEX64.fullmatch(base_digest) is None:
        findings.append("base_release_digest invalid")
    if not isinstance(effective, str) or HEX64.fullmatch(effective) is None:
        findings.append("base effective_host_digest invalid")

    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not findings:
        for index, delta in enumerate(deltas, start=1):
            if delta.get("result") != "PASS" or delta.get("delta_status") != "DELTA_ADMITTED":
                findings.append(f"delta {index} is not admitted")
                break
            delta_digest = delta.get("delta_digest")
            if not isinstance(delta_digest, str) or HEX64.fullmatch(delta_digest) is None:
                findings.append(f"delta {index} digest invalid")
                break
            if delta_digest in seen:
                findings.append(f"delta {index} is duplicated")
                break
            seen.add(delta_digest)
            if delta.get("base_release_digest") != base_digest:
                findings.append(f"delta {index} base_release_digest mismatch")
                break
            if delta.get("parent_effective_digest") != effective:
                findings.append(f"delta {index} parent_effective_digest breaks overlay chain")
                break
            if delta.get("effective_host_digest") != _digest_text(effective + ":" + delta_digest):
                findings.append(f"delta {index} effective_host_digest mismatch")
                break
            effective = delta["effective_host_digest"]
            chain.append(
                {
                    "delta_digest": delta_digest,
                    "request_id": delta.get("request_id"),
                    "application_id": delta.get("application_id"),
                    "classification": delta.get("classification"),
                    "effective_host_digest": effective,
                }
            )

    return {
        "schema": "fa3.effective-current-host.v1",
        "status": "PASS" if not findings else "FAIL",
        "fail_closed": True,
        "base_release_digest": base_digest,
        "effective_host_digest": effective if not findings else None,
        "delta_count": len(chain),
        "ordered_deltas": chain,
        "capability_count": 175,
        "obligation_model": "POSITIVE_NEGATIVE_ROLLBACK_PER_AFFECTED_CAPABILITY",
        "historical_evidence_relabeling": "FORBIDDEN",
        "global_promotion_claim": False,
        "findings": findings,
    }


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Current Host Change & Delta Authority")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = parser.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan")
    plan_p.add_argument("--request", required=True)
    plan_p.add_argument("--output", required=True)

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--plan", required=True)
    verify_p.add_argument("--receipt", required=True)
    verify_p.add_argument("--output", required=True)

    compose_p = sub.add_parser("compose")
    compose_p.add_argument("--base", required=True)
    compose_p.add_argument("--delta", action="append", default=[])
    compose_p.add_argument("--output", required=True)

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if args.command == "plan":
        result = plan_request(root, load_json(Path(args.request)))
    elif args.command == "verify":
        result = verify_delta_receipt(load_json(Path(args.plan)), load_json(Path(args.receipt)))
    else:
        result = compose_effective_host(
            load_json(Path(args.base)),
            [load_json(Path(path)) for path in args.delta],
        )

    _write(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status", result.get("result")) == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
