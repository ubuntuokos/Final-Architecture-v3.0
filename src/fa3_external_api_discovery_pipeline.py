#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

from fa3_api_mega_list_adapter import (
    OPENCLAW_SOURCE_ID,
    OPENCLAW_SOURCE_REPOSITORY,
    SOURCE_ID,
    SOURCE_REPOSITORY,
    SUPPORTED_CATALOG_SOURCES,
    parse_external_catalog_markdown,
)
from fa3_external_discovery_store import build_candidate_store, validate_candidate_store, volume_action

SNAPSHOT_SCHEMA = "fa3.external-api-discovery.snapshot.v1"
INGEST_RECEIPT_SCHEMA = "fa3.external-api-discovery.ingest-receipt.v1"
DRIFT_SCHEMA = "fa3.external-api-discovery.drift-report.v1"
ADMISSION_REVIEW_PLAN_SCHEMA = "fa3.external-discovery.admission-review-plan.v1"
ADMISSION_TARGET_KINDS = ("PROVIDER", "MCP", "SKILL", "WEBHOOK", "APIFY_ACTOR")
ADMISSION_REVIEW_STAGES = (
    "DISCOVER",
    "NORMALIZE",
    "DEDUPLICATE",
    "PROVENANCE",
    "LICENSE_TERMS",
    "ENDPOINT_VERIFY",
    "PROTOCOL_SCHEMA",
    "SECURITY",
    "SECRETS",
    "EGRESS",
    "CAPABILITY_MAP",
    "POLICY",
    "SANDBOX",
    "CONFORMANCE",
    "REGISTRY_ADMISSION",
)
_DISCOVERY_COMPLETE_STAGES = {"DISCOVER", "NORMALIZE", "DEDUPLICATE"}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

SOURCE_SURFACES = {
    SOURCE_ID: {"recursive_names": {"README.md"}, "root_names": set()},
    OPENCLAW_SOURCE_ID: {
        "recursive_names": {"README.md"},
        "root_names": {"OPENCLAW_RECOMMENDED.md"},
    },
}


def _source_repository(source_id: str, source_repository: str | None = None) -> str:
    expected = SUPPORTED_CATALOG_SOURCES.get(source_id)
    if expected is None:
        raise ValueError(f"unsupported external discovery source: {source_id}")
    if source_repository is not None and source_repository != expected:
        raise ValueError("external discovery source id/repository mismatch")
    return expected


def _snapshot_files(snapshot_dir: Path, source_id: str) -> list[Path]:
    config = SOURCE_SURFACES.get(source_id)
    if config is None:
        raise ValueError(f"unsupported external discovery source: {source_id}")
    paths: set[Path] = set()
    for name in config["recursive_names"]:
        paths.update(path for path in snapshot_dir.rglob(name) if path.is_file())
    for name in config["root_names"]:
        path = snapshot_dir / name
        if path.is_file():
            paths.add(path)
    return sorted(paths)


def _surface_allowed(source_id: str, rel: str) -> bool:
    config = SOURCE_SURFACES.get(source_id)
    if config is None:
        return False
    path = PurePosixPath(rel)
    if path.name in config["recursive_names"]:
        return True
    return len(path.parts) == 1 and path.name in config["root_names"]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_relpath(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe snapshot path: {value}")
    return path.as_posix()


def create_snapshot_manifest(
    snapshot_dir: Path,
    *,
    source_commit: str,
    source_id: str = SOURCE_ID,
    source_repository: str | None = None,
) -> dict[str, Any]:
    snapshot_dir = Path(snapshot_dir).resolve()
    if not SHA40.fullmatch(source_commit):
        raise ValueError("immutable 40-character source commit required")
    source_repository = _source_repository(source_id, source_repository)
    files: list[dict[str, Any]] = []
    for path in _snapshot_files(snapshot_dir, source_id):
        rel = path.relative_to(snapshot_dir).as_posix()
        data = path.read_bytes()
        files.append(
            {
                "path": rel,
                "sha256": _sha256_bytes(data),
                "size": len(data),
                "copy_policy": "LOCAL_DISCOVERY_METADATA_SNAPSHOT",
            }
        )
    if not files:
        raise ValueError("snapshot requires at least one supported catalog surface")
    manifest = {
        "schema": SNAPSHOT_SCHEMA,
        "source_id": source_id,
        "source_repository": source_repository,
        "source_commit": source_commit,
        "immutable": True,
        "network_fetch_performed": False,
        "files": files,
    }
    manifest["manifest_digest"] = _stable_digest({k: v for k, v in manifest.items() if k != "manifest_digest"})
    return manifest


def validate_snapshot_manifest(snapshot_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if manifest.get("schema") != SNAPSHOT_SCHEMA:
        findings.append({"code": "EXTDISC-SNAPSHOT-SCHEMA", "message": "invalid snapshot schema"})
    source_id = str(manifest.get("source_id") or "")
    source_repository = str(manifest.get("source_repository") or "")
    try:
        _source_repository(source_id, source_repository)
    except ValueError:
        findings.append({"code": "EXTDISC-SNAPSHOT-SOURCE", "message": "unexpected source identity"})
    if not SHA40.fullmatch(str(manifest.get("source_commit", ""))):
        findings.append({"code": "EXTDISC-SNAPSHOT-COMMIT", "message": "immutable source commit required"})
    if manifest.get("immutable") is not True or manifest.get("network_fetch_performed") is not False:
        findings.append({"code": "EXTDISC-SNAPSHOT-BOUNDARY", "message": "snapshot must be immutable and offline"})
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        findings.append({"code": "EXTDISC-SNAPSHOT-FILES", "message": "snapshot file inventory required"})
        return findings

    seen: set[str] = set()
    for row in files:
        if not isinstance(row, dict):
            findings.append({"code": "EXTDISC-SNAPSHOT-FILE", "message": "snapshot row must be object"})
            continue
        try:
            rel = _safe_relpath(str(row.get("path", "")))
        except ValueError as exc:
            findings.append({"code": "EXTDISC-SNAPSHOT-PATH", "message": str(exc)})
            continue
        if rel in seen:
            findings.append({"code": "EXTDISC-SNAPSHOT-DUPLICATE", "message": f"duplicate snapshot path: {rel}"})
            continue
        seen.add(rel)
        if not _surface_allowed(source_id, rel):
            findings.append({"code": "EXTDISC-SNAPSHOT-SURFACE", "message": f"unsupported snapshot surface: {rel}"})
            continue
        if not SHA256.fullmatch(str(row.get("sha256", ""))):
            findings.append({"code": "EXTDISC-SNAPSHOT-HASH", "message": f"invalid sha256: {rel}"})
            continue
        path = snapshot_dir / rel
        if not path.is_file():
            findings.append({"code": "EXTDISC-SNAPSHOT-MISSING", "message": f"missing snapshot file: {rel}"})
            continue
        data = path.read_bytes()
        if len(data) != int(row.get("size", -1)):
            findings.append({"code": "EXTDISC-SNAPSHOT-SIZE", "message": f"size drift: {rel}"})
        if _sha256_bytes(data) != row["sha256"]:
            findings.append({"code": "EXTDISC-SNAPSHOT-HASH-DRIFT", "message": f"content drift: {rel}"})
    expected_manifest_digest = _stable_digest({k: v for k, v in manifest.items() if k != "manifest_digest"})
    if manifest.get("manifest_digest") != expected_manifest_digest:
        findings.append({"code": "EXTDISC-SNAPSHOT-MANIFEST-DIGEST", "message": "snapshot manifest digest drift"})
    return findings


def load_snapshot_manifest(snapshot_dir: Path) -> dict[str, Any]:
    path = Path(snapshot_dir) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot_observations(snapshot_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    snapshot_dir = Path(snapshot_dir).resolve()
    manifest = load_snapshot_manifest(snapshot_dir)
    findings = validate_snapshot_manifest(snapshot_dir, manifest)
    if findings:
        raise ValueError(json.dumps(findings, ensure_ascii=False, sort_keys=True))

    observations: list[dict[str, Any]] = []
    for row in manifest["files"]:
        rel = _safe_relpath(row["path"])
        text = (snapshot_dir / rel).read_text(encoding="utf-8")
        parsed = parse_external_catalog_markdown(
            text,
            source_path=rel,
            source_id=manifest["source_id"],
            source_repository=manifest["source_repository"],
        )
        for observation in parsed:
            observation["source_commit"] = manifest["source_commit"]
        observations.extend(parsed)

    source_snapshot = {
        "source_id": manifest["source_id"],
        "source_repository": manifest["source_repository"],
        "source_commit": manifest["source_commit"],
        "manifest_digest": manifest["manifest_digest"],
        "file_count": len(manifest["files"]),
        "immutable": True,
        "network_fetch_performed": False,
    }
    return source_snapshot, observations


def ingest_snapshot(snapshot_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    source_snapshot, observations = _snapshot_observations(snapshot_dir)
    store = build_candidate_store(source_snapshot=source_snapshot, observations=observations)
    store_findings = validate_candidate_store(store)
    if store_findings:
        raise ValueError(json.dumps(store_findings, ensure_ascii=False, sort_keys=True))

    receipt = {
        "schema": INGEST_RECEIPT_SCHEMA,
        "result": "PASS",
        "source_snapshot": source_snapshot,
        "source_snapshots": [source_snapshot],
        "source_count": 1,
        "observation_count": len(observations),
        "candidate_count": store["candidate_count"],
        "store_digest": store["store_digest"],
        "authority": False,
        "runtime_provider": False,
        "automatic_donor_creation": False,
        "automatic_provider_admission": False,
        "automatic_mcp_registration": False,
        "automatic_activation": False,
    }
    receipt["receipt_digest"] = _stable_digest({k: v for k, v in receipt.items() if k != "receipt_digest"})
    return store, receipt


def ingest_snapshots(snapshot_dirs: list[Path]) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(snapshot_dirs) < 2:
        raise ValueError("multi-source reconciliation requires at least two snapshot directories")
    source_snapshots: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for snapshot_dir in snapshot_dirs:
        source_snapshot, source_observations = _snapshot_observations(Path(snapshot_dir))
        source_id = str(source_snapshot["source_id"])
        if source_id in seen_source_ids:
            raise ValueError(f"duplicate external discovery source in reconciliation: {source_id}")
        seen_source_ids.add(source_id)
        source_snapshots.append(source_snapshot)
        observations.extend(source_observations)

    store = build_candidate_store(source_snapshots=source_snapshots, observations=observations)
    store_findings = validate_candidate_store(store)
    if store_findings:
        raise ValueError(json.dumps(store_findings, ensure_ascii=False, sort_keys=True))

    receipt = {
        "schema": INGEST_RECEIPT_SCHEMA,
        "result": "PASS",
        "source_snapshot": store["source_snapshot"],
        "source_snapshots": store["source_snapshots"],
        "source_count": len(store["source_snapshots"]),
        "observation_count": len(observations),
        "candidate_count": store["candidate_count"],
        "store_digest": store["store_digest"],
        "authority": False,
        "runtime_provider": False,
        "automatic_donor_creation": False,
        "automatic_provider_admission": False,
        "automatic_mcp_registration": False,
        "automatic_activation": False,
    }
    receipt["receipt_digest"] = _stable_digest({k: v for k, v in receipt.items() if k != "receipt_digest"})
    return store, receipt

def _normalize_target_kind(value: str) -> str:
    normalized = str(value or "").strip().upper().replace("-", "_")
    if normalized not in ADMISSION_TARGET_KINDS:
        raise ValueError(
            "explicit admission review target kind required: "
            + ", ".join(ADMISSION_TARGET_KINDS)
        )
    return normalized


def build_admission_review_plan(
    store: dict[str, Any],
    *,
    candidate_id: str,
    target_kind: str,
) -> dict[str, Any]:
    findings = validate_candidate_store(store)
    if findings:
        raise ValueError(json.dumps(findings, ensure_ascii=False, sort_keys=True))

    normalized_kind = _normalize_target_kind(target_kind)
    matches = [
        row
        for row in store.get("candidates", [])
        if isinstance(row, dict) and row.get("candidate_id") == candidate_id
    ]
    if len(matches) != 1:
        raise ValueError("exactly one validated external discovery candidate is required")
    candidate = matches[0]

    stages = []
    for stage in ADMISSION_REVIEW_STAGES:
        completed_from_discovery = stage in _DISCOVERY_COMPLETE_STAGES
        stages.append(
            {
                "stage": stage,
                "status": "PASS_FROM_DERIVED_DISCOVERY" if completed_from_discovery else "PENDING_REVIEW",
                "authorization_effect": False,
            }
        )

    plan = {
        "schema": ADMISSION_REVIEW_PLAN_SCHEMA,
        "review_status": "DRAFT_REVIEW_REQUIRED",
        "authority": False,
        "runtime_effect": False,
        "registry_mutation_permitted": False,
        "network_probe_performed": False,
        "secret_resolution_performed": False,
        "current_host_pass_claimed": False,
        "admission_ready": False,
        "automatic_donor_creation": False,
        "automatic_provider_admission": False,
        "automatic_mcp_registration": False,
        "automatic_activation": False,
        "catalog_hints_authorize_target_kind": False,
        "inherits_apify_org_donor_status": False,
        "donor_usage_edge_created": False,
        "requested_target_kind": normalized_kind,
        "store_digest": store["store_digest"],
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "candidate_summary": {
            "provider_identity": candidate.get("provider_identity"),
            "service_identity": candidate.get("service_identity"),
            "canonical_locator": candidate.get("canonical_locator"),
            "listing_names": list(candidate.get("listing_names", [])),
            "listing_descriptions": list(candidate.get("listing_descriptions", [])),
            "source_categories": list(candidate.get("source_categories", [])),
            "mcp_hint_observed": bool(candidate.get("mcp_hint_observed")),
            "skill_hint_observed": bool(candidate.get("skill_hint_observed")),
            "webhook_hint_observed": bool(candidate.get("webhook_hint_observed")),
            "apify_actor_identities": list(candidate.get("apify_actor_identities", [])),
            "observations": list(candidate.get("observations", [])),
        },
        "source_snapshots": list(store.get("source_snapshots", [])),
        "bindings": {
            "external_discovery_profile_id": "FA3-EXTERNAL-API-DISCOVERY-001",
            "candidate_store_policy_id": "FA3-EXTERNAL-DISCOVERY-CANDIDATE-STORE-001",
            "license_rights_contract_id": "FA3-LICENSE-RIGHTS-CONTRACTS-001",
            "security_authority_id": "FA3-AUTH-SECURITY-GOV-001",
            "secret_authority_id": "FA3-SECRET-BROKER-001",
            "mcp_authority_id": "FA3-AUTH-MCP-GATEWAY-001",
            "resource_authority_id": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "registry_authority_id": "FA3-REGISTRY-001",
            "evidence_authority_id": "FA3-AUTH-OBS-EVIDENCE-001",
            "network_egress_authority": "EXISTING_FA3_NETWORK_EGRESS_AUTHORITY_ONLY",
        },
        "required_review_outputs": [
            "ExternalLicenseTermsAssessment",
            "ExternalEndpointDescriptor",
            "ExternalProtocolDescriptor",
            "ExternalSecurityClassification",
            "ExternalAuthRequirement",
            "ExternalEgressAssessment",
            "ExternalCapabilityMapping",
            "ExternalSandboxProbeResult",
            "ExternalProviderAdmissionDecision",
        ],
        "stages": stages,
    }
    plan["plan_digest"] = _stable_digest({k: v for k, v in plan.items() if k != "plan_digest"})
    return plan


def validate_admission_review_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if plan.get("schema") != ADMISSION_REVIEW_PLAN_SCHEMA:
        findings.append({"code": "EXTDISC-REVIEW-SCHEMA", "message": "invalid admission review plan schema"})
    if plan.get("review_status") != "DRAFT_REVIEW_REQUIRED":
        findings.append({"code": "EXTDISC-REVIEW-STATE", "message": "review plan must remain draft"})
    for flag in (
        "authority",
        "runtime_effect",
        "registry_mutation_permitted",
        "network_probe_performed",
        "secret_resolution_performed",
        "current_host_pass_claimed",
        "admission_ready",
        "automatic_donor_creation",
        "automatic_provider_admission",
        "automatic_mcp_registration",
        "automatic_activation",
        "catalog_hints_authorize_target_kind",
        "inherits_apify_org_donor_status",
        "donor_usage_edge_created",
    ):
        if plan.get(flag) is not False:
            findings.append({"code": "EXTDISC-REVIEW-AUTHORITY", "message": f"{flag} must be false"})
    if plan.get("requested_target_kind") not in ADMISSION_TARGET_KINDS:
        findings.append({"code": "EXTDISC-REVIEW-TARGET", "message": "unsupported admission review target kind"})
    stages = plan.get("stages")
    if not isinstance(stages, list) or [row.get("stage") for row in stages if isinstance(row, dict)] != list(ADMISSION_REVIEW_STAGES):
        findings.append({"code": "EXTDISC-REVIEW-STAGES", "message": "admission review stage order drift"})
    else:
        for row in stages:
            expected = "PASS_FROM_DERIVED_DISCOVERY" if row["stage"] in _DISCOVERY_COMPLETE_STAGES else "PENDING_REVIEW"
            if row.get("status") != expected or row.get("authorization_effect") is not False:
                findings.append({"code": "EXTDISC-REVIEW-STAGE-STATE", "message": f"invalid stage state: {row.get('stage')}"})
    bindings = plan.get("bindings", {})
    if not (
        bindings.get("license_rights_contract_id") == "FA3-LICENSE-RIGHTS-CONTRACTS-001"
        and bindings.get("mcp_authority_id") == "FA3-AUTH-MCP-GATEWAY-001"
        and bindings.get("secret_authority_id") == "FA3-SECRET-BROKER-001"
        and bindings.get("resource_authority_id") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        and bindings.get("registry_authority_id") == "FA3-REGISTRY-001"
    ):
        findings.append({"code": "EXTDISC-REVIEW-BINDINGS", "message": "canonical authority/rights bindings drift"})
    if not str(plan.get("candidate_id") or "") or not str(plan.get("candidate_digest") or "") or not str(plan.get("store_digest") or ""):
        findings.append({"code": "EXTDISC-REVIEW-BINDING", "message": "candidate/store digest binding missing"})
    expected_digest = _stable_digest({k: v for k, v in plan.items() if k != "plan_digest"})
    if plan.get("plan_digest") != expected_digest:
        findings.append({"code": "EXTDISC-REVIEW-DIGEST", "message": "admission review plan digest drift"})
    return findings


def drift_report(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    prev = {row["candidate_id"]: row for row in previous.get("candidates", []) if isinstance(row, dict) and row.get("candidate_id")}
    curr = {row["candidate_id"]: row for row in current.get("candidates", []) if isinstance(row, dict) and row.get("candidate_id")}
    added = sorted(set(curr) - set(prev))
    removed = sorted(set(prev) - set(curr))
    common = sorted(set(prev) & set(curr))
    changed = sorted(
        candidate_id
        for candidate_id in common
        if prev[candidate_id].get("candidate_digest") != curr[candidate_id].get("candidate_digest")
    )
    report = {
        "schema": DRIFT_SCHEMA,
        "authority": False,
        "canonical_state_replacement_allowed": False,
        "previous_store_digest": previous.get("store_digest"),
        "current_store_digest": current.get("store_digest"),
        "added_candidate_ids": added,
        "removed_candidate_ids": removed,
        "changed_candidate_ids": changed,
        "has_drift": bool(added or removed or changed),
    }
    report["drift_digest"] = _stable_digest({k: v for k, v in report.items() if k != "drift_digest"})
    return report


def default_state_root() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base) / "fa3" / "external-discovery" / "candidates"
    return Path.home() / ".local" / "state" / "fa3" / "external-discovery" / "candidates"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 offline external API discovery ingestion")
    sub = parser.add_subparsers(dest="command", required=True)

    p_snapshot = sub.add_parser("snapshot")
    p_snapshot.add_argument("--snapshot-dir", required=True)
    p_snapshot.add_argument("--source-commit", required=True)
    p_snapshot.add_argument("--source-id", default=SOURCE_ID, choices=sorted(SUPPORTED_CATALOG_SOURCES))
    p_snapshot.add_argument("--source-repository")
    p_snapshot.add_argument("--output")

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--snapshot-dir", required=True)
    p_ingest.add_argument("--output")
    p_ingest.add_argument("--receipt")

    p_reconcile = sub.add_parser("reconcile")
    p_reconcile.add_argument("--snapshot-dir", action="append", required=True)
    p_reconcile.add_argument("--output")
    p_reconcile.add_argument("--receipt")

    p_review = sub.add_parser("review-plan")
    p_review.add_argument("--store", required=True)
    p_review.add_argument("--candidate-id", required=True)
    p_review.add_argument("--target-kind", required=True, choices=[value.lower().replace("_", "-") for value in ADMISSION_TARGET_KINDS])
    p_review.add_argument("--output")

    p_check = sub.add_parser("check")
    p_check.add_argument("--store", required=True)

    p_drift = sub.add_parser("drift")
    p_drift.add_argument("--previous", required=True)
    p_drift.add_argument("--current", required=True)
    p_drift.add_argument("--output")

    p_capacity = sub.add_parser("capacity")
    p_capacity.add_argument("--current-records", required=True, type=int)
    p_capacity.add_argument("--planned-capacity", required=True, type=int)

    args = parser.parse_args()

    if args.command == "snapshot":
        snapshot_dir = Path(args.snapshot_dir)
        manifest = create_snapshot_manifest(
            snapshot_dir,
            source_commit=args.source_commit,
            source_id=args.source_id,
            source_repository=args.source_repository,
        )
        output = Path(args.output) if args.output else snapshot_dir / "manifest.json"
        _write_json(output, manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    if args.command == "ingest":
        store, receipt = ingest_snapshot(Path(args.snapshot_dir))
        output = Path(args.output) if args.output else default_state_root() / "candidate-store.json"
        receipt_path = Path(args.receipt) if args.receipt else output.with_name("ingest-receipt.json")
        _write_json(output, store)
        _write_json(receipt_path, receipt)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0

    if args.command == "reconcile":
        store, receipt = ingest_snapshots([Path(path) for path in args.snapshot_dir])
        output = Path(args.output) if args.output else default_state_root() / "candidate-store.json"
        receipt_path = Path(args.receipt) if args.receipt else output.with_name("ingest-receipt.json")
        _write_json(output, store)
        _write_json(receipt_path, receipt)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0

    if args.command == "review-plan":
        store = _load_json(Path(args.store))
        plan = build_admission_review_plan(
            store,
            candidate_id=args.candidate_id,
            target_kind=args.target_kind,
        )
        findings = validate_admission_review_plan(plan)
        if findings:
            raise ValueError(json.dumps(findings, ensure_ascii=False, sort_keys=True))
        output = Path(args.output) if args.output else default_state_root() / "review-plans" / (
            f"{plan['candidate_id']}-{plan['requested_target_kind'].lower()}.json"
        )
        _write_json(output, plan)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if args.command == "check":
        store = _load_json(Path(args.store))
        findings = validate_candidate_store(store)
        report = {"result": "PASS" if not findings else "FAIL", "findings": findings}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if not findings else 2

    if args.command == "drift":
        report = drift_report(_load_json(Path(args.previous)), _load_json(Path(args.current)))
        if args.output:
            _write_json(Path(args.output), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.command == "capacity":
        report = volume_action(current_records=args.current_records, planned_capacity=args.planned_capacity)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    return 3


if __name__ == "__main__":
    raise SystemExit(main())
