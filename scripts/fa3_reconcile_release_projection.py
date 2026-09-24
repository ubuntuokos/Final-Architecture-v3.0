#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fa3_release_baseline import load_active_release_baseline

DEFAULT_PROJECTION = "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
DEFAULT_POLICY = "canonical/enforcement-policy.json"
SNAPSHOT_SEMANTICS = "PRE_MAINTENANCE_CANONICAL_MAIN_ANCHOR"
MUTABLE_TOP_LEVEL = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache"}
MUTABLE_DIR_NAMES = {"__pycache__"}


def run(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def run_z(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "surrogateescape").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return proc.stdout.decode("utf-8", "surrogateescape")


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def mutable_path(rel: str) -> bool:
    parts = Path(rel).parts
    if not parts:
        return True
    if parts[0] in MUTABLE_TOP_LEVEL:
        return True
    if any(part in MUTABLE_DIR_NAMES for part in parts):
        return True
    if rel.startswith("evidence/receipts/") and rel != "evidence/receipts/.gitkeep":
        return True
    return False


def diff_rows(root: Path, base: str, snapshot: str):
    raw = run_z(root, "diff", "--name-status", "-z", "--find-renames", base, snapshot)
    tokens = raw.split("\0")
    if tokens and tokens[-1] == "":
        tokens.pop()
    rows = []
    i = 0
    while i < len(tokens):
        status = tokens[i]
        i += 1
        if status.startswith(("R", "C")):
            if i + 1 >= len(tokens):
                raise RuntimeError(f"unparseable rename/copy record: {status}")
            _old_path = tokens[i]
            path = tokens[i + 1]
            i += 2
        else:
            if i >= len(tokens):
                raise RuntimeError(f"unparseable name-status record: {status}")
            path = tokens[i]
            i += 1
        rows.append((status, path))
    return rows


def status_label(status: str) -> str:
    if status.startswith("A"):
        return "added"
    if status.startswith("M"):
        return "modified"
    if status.startswith("D"):
        return "removed"
    if status.startswith("R"):
        return "renamed"
    if status.startswith("C"):
        return "copied"
    return "other"


def reconcile(root: Path, projection_rel: str, policy_rel: str) -> dict:
    root = Path(root).resolve()
    active_baseline = load_active_release_baseline(root)
    capability_count = active_baseline.capability_count
    projection_path = root / projection_rel
    policy_path = root / policy_rel
    projection = loadj(projection_path)
    policy = loadj(policy_path)

    gui_conformance = loadj(root / "canonical/FA3-GUI-RUNTIME-CONFORMANCE-001.json")
    gui_runtime_pass = (
        gui_conformance.get("status") == "CURRENT_HOST_PASS"
        and gui_conformance.get("production_admitted") is True
        and gui_conformance.get("current_host_receipt_present") is True
        and gui_conformance.get("promotion_blockers") == []
    )

    base = projection.get("base_release_commit")
    if not base:
        raise RuntimeError("projection base_release_commit is missing")
    snapshot = run(root, "rev-parse", "HEAD")
    root_tree = run(root, "rev-parse", f"{snapshot}^{{tree}}")
    canonical_tree = run(root, "rev-parse", f"{snapshot}:canonical")
    commit_count = int(run(root, "rev-list", "--count", f"{base}..{snapshot}"))
    rows = diff_rows(root, base, snapshot)
    paths = [path for _, path in rows]
    status_by_path = {path: status_label(status) for status, path in rows}

    added = sum(status.startswith("A") for status, _ in rows)
    modified = sum(status.startswith("M") for status, _ in rows)
    removed = sum(status.startswith("D") for status, _ in rows)
    other = len(rows) - added - modified - removed

    def prefixed(prefix: str):
        return sorted(path for path in paths if path.startswith(prefix))

    projection["last_reconciled_at"] = run(root, "show", "-s", "--format=%cs", snapshot)
    projection["source_snapshot"] = {
        "snapshot_semantics": SNAPSHOT_SEMANTICS,
        "baseline_commit_sha": base,
        "pre_projection_head_sha": snapshot,
        "pre_projection_root_tree_sha": root_tree,
        "pre_projection_canonical_tree_sha": canonical_tree,
        "commits_ahead_of_v3_0_11_conformance_commit": commit_count,
        "total_post_baseline_commits": commit_count,
        "delta_file_count": len(rows),
        "delta_added_files": added,
        "delta_modified_files": modified,
        "delta_removed_files": removed,
        "delta_other_files": other,
    }

    inventory = projection.setdefault("overlay_inventory", {})
    inventory.update({
        "canonical_files_in_post_baseline_delta": len(prefixed("canonical/")),
        "evidence_files_in_post_baseline_delta": len(prefixed("evidence/")),
        "source_files_in_post_baseline_delta": len(prefixed("src/")),
        "test_files_in_post_baseline_delta": len(prefixed("tests/")),
        "workflow_files_in_post_baseline_delta": len(prefixed(".github/workflows/")),
        "provider_records": prefixed("canonical/providers/"),
        "profile_records": prefixed("canonical/profiles/"),
        "contract_records": prefixed("canonical/contracts/"),
        "decision_records": prefixed("canonical/decisions/"),
        "upstream_reference_records": prefixed("canonical/references/"),
        "reference_evidence_records": prefixed("evidence/reference/"),
    })

    projection.setdefault("invariants", {})["canonical_capability_count"] = capability_count
    projection["mandatory_reference_gates"] = list(policy.get("mandatory_reference_gates", []))
    projection["inference_cache_hardening_reconciliation"] = {
        "parent_gate_id": "FA3-INFERENCE-PORTABILITY-GATESET-001",
        "subgate_id": "FA3-INFERENCE-PORTABILITY-CACHE-HARDENING-001",
        "profile_id": "FA3-INFERENCE-PORTABILITY-001",
        "contract_id": "FA3-INFERENCE-PORTABILITY-CONTRACTS-001",
        "provider_id": "FA3-PROVIDER-TENSORRT-RTX-001",
        "decision_id": "FA3-DEC-INFERENCE-CACHE-HARDENING-2026-09-07",
        "reference_id": "FA3-TENSORRT-RTX-RUNTIME-CACHE-REFERENCE-2026-09-07",
        "reference_evidence": "evidence/reference/inference-cache-hardening-ci-2026-09-07.json",
        "capability_bindings": ["CAP-005", "CAP-006", "CAP-137", "CAP-143"],
        "reconciliation_status": "GLOBAL_PROJECTION_RECONCILED_CI_REFERENCE_PASS_CURRENT_HOST_PENDING",
        "current_host_runtime_promotion_claim": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": capability_count,
    }
    projection["inference_portability_2026_09_23_reconciliation"] = {
        "profile_id": "FA3-INFERENCE-PORTABILITY-001",
        "contract_id": "FA3-INFERENCE-PORTABILITY-CONTRACTS-001",
        "decision_id": "FA3-DEC-INFERENCE-PORTABILITY-RECONCILIATION-2026-09-23",
        "reference_id": "FA3-INFERENCE-PORTABILITY-UPSTREAM-REFERENCE-2026-09-23",
        "parent_gate_id": "FA3-INFERENCE-PORTABILITY-GATESET-001",
        "subgate_id": "FA3-INFERENCE-PORTABILITY-RECONCILIATION-001",
        "reference_evidence": "evidence/reference/inference-portability-reconciliation-ci-2026-09-23.json",
        "capability_bindings": ["CAP-005", "CAP-006", "CAP-137", "CAP-143"],
        "hardware_discovery_contract": "FA3-HARDWARE-DISCOVERY-CONTRACTS-001",
        "hrb_contract": "FA3-HOST-RESOURCE-BROKER-CONTRACTS-001",
        "uaf_profile": "FA3-UNIFIED-ACTION-FABRIC-001",
        "ai_comms_profile": "FA3-AI-COMMS-001",
        "model_routing_authority": "FA3-AUTH-MODEL-ROUTER-001",
        "decision_fabric_jev": "OPTIONAL_ADVISORY_NO_CANDIDATE_EXPANSION",
        "reconciliation_status": "GLOBAL_PROJECTION_RECONCILED_REFERENCE_PASS_PROVIDER_RUNTIME_ADMISSION_SEPARATE",
        "current_host_runtime_promotion_claim": False,
        "global_promotion_claim": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": capability_count,
    }

    projection["inference_provider_current_host_reconciliation"] = {
        "conformance_id": "FA3-INFERENCE-PROVIDER-CURRENT-HOST-CONFORMANCE-001",
        "profile_id": "FA3-INFERENCE-PORTABILITY-001",
        "contract_id": "FA3-INFERENCE-PORTABILITY-CONTRACTS-001",
        "decision_id": "FA3-DEC-INFERENCE-PROVIDER-CURRENT-HOST-2026-09-23",
        "parent_gate_id": "FA3-INFERENCE-PORTABILITY-GATESET-001",
        "materialization_subgate_id": "FA3-INFERENCE-PROVIDER-CURRENT-HOST-MATERIALIZATION-001",
        "current_host_gate_id": "FA3-GATE-INFERENCE-PROVIDER-CURRENT-HOST-001",
        "provider_ids": ["FA3-PROVIDER-OPENVINO-001","FA3-PROVIDER-ONNXRUNTIME-001","FA3-PROVIDER-TENSORRT-001","FA3-PROVIDER-TENSORRT-RTX-001"],
        "reference_evidence": "evidence/reference/inference-provider-current-host-materialization-ci-2026-09-23.json",
        "dynamic_aggregate_receipt": "evidence/receipts/inference-provider-current-host.json",
        "reconciliation_status": "MATERIALIZED_SCOPE_BOUND_CURRENT_HOST_PROVIDER_ADMISSION_DYNAMIC_EVIDENCE",
        "provider_absence_global_failure": False,
        "source_decision_obligation": False,
        "existing_429_closure_reopened": False,
        "current_host_obligation_delta": 0,
        "global_promotion_claim": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": capability_count,
    }

    projection["marketing_agent_native_reconciliation"] = {
        "profile_id": "FA3-MARKETING-001",
        "contract_id": "FA3-MARKETING-DECISION-FABRIC-CONTRACTS-001",
        "decision_id": "FA3-DEC-MARKETING-AGENT-NATIVE-JEV-2026-09-23",
        "gate_id": "FA3-MARKETING-AGENT-NATIVE-GATESET-001",
        "action_count": 15,
        "reference_evidence": "evidence/reference/marketing-agent-native-ci-2026-09-23.json",
        "reference_evidence_status": "STATIC_AND_REFERENCE_PASS_NOT_RUNTIME",
        "current_host_conformance_id": "FA3-MARKETING-RUNTIME-CONFORMANCE-001",
        "current_host_required_evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "current_host_status": "PENDING_CURRENT_HOST_PRODUCTION_E2E",
        "production_provider_admission": False,
        "global_promotion_claim": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": capability_count,
    }

    projection["skill_distribution_fabric_reconciliation"] = {
        "skill_profile_id": "FA3-SKILL-FABRIC-001",
        "distribution_profile_id": "FA3-DISTRIBUTION-COMPLIANCE-001",
        "decision_id": "FA3-DEC-SKILL-DISCOVERY-DISTRIBUTION-FABRIC-2026-09-23",
        "skill_gate_id": "FA3-SKILL-FABRIC-GATESET-001",
        "distribution_gate_id": "FA3-DISTRIBUTION-COMPLIANCE-GATESET-001",
        "autoskills_reference_id": "FA3-AUTOSKILLS-UPSTREAM-REFERENCE-2026-09-23",
        "autoskills_distribution_class": "REFERENCE_ONLY",
        "external_redistributable_supported": True,
        "auto_bundle_external_redistributable": False,
        "capability_count_after": capability_count,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
    }

    projection["quality_anti_slop_reconciliation"] = {
        "profile_id": "FA3-QUALITY-ANTI-SLOP-001",
        "contract_id": "FA3-QUALITY-ANTI-SLOP-CONTRACTS-001",
        "decision_id": "FA3-DEC-QUALITY-ANTI-SLOP-NATIVE-2026-09-23",
        "decision_assessment_id": "FA3-QUALITY-ANTI-SLOP-NATIVE-2026-09-23",
        "gate_id": "FA3-QUALITY-ANTI-SLOP-GATESET-001",
        "rule_registry_id": "FA3-QUALITY-RULE-REGISTRY-001",
        "upstream_reference_id": "FA3-ANTI-SLOP-UPSTREAM-REFERENCE-2026-09-23",
        "upstream_distribution_class": "REFERENCE_ONLY",
        "native_quality_skill_count": 5,
        "upstream_runtime_dependency": False,
        "upstream_installer_dependency": False,
        "current_host_runtime_promotion_claim": False,
        "capability_count_after": capability_count,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
    }

    projection["gui_current_host_closure_reconciliation"] = {
        "profile_id": "FA3-DESKTOP-001",
        "conformance_id": "FA3-GUI-RUNTIME-CONFORMANCE-001",
        "gate_id": "FA3-GUI-CURRENT-HOST-GATESET-001",
        "gate_record_id": "FA3-GATE-GUI-CURRENT-HOST-001",
        "workflow": ".github/workflows/fa3-gui-current-host.yml",
        "collector": "evidence/collect-gui-current-host.py",
        "required_evidence_level": "CURRENT_HOST_ADMITTED_DESKTOP_SESSION_RUNTIME_PASS",
        "status": gui_conformance.get("status"),
        "current_host_receipt_present": gui_conformance.get("current_host_receipt_present") is True,
        "production_admitted": gui_conformance.get("production_admitted") is True,
        "runtime_promotion_claim": gui_runtime_pass,
        "global_promotion_claim": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": capability_count,
        "reconciliation_status": (
            "CURRENT_HOST_PHYSICAL_GUI_RUNTIME_PASS"
            if gui_runtime_pass
            else "EXECUTABLE_CLOSURE_MATERIALIZED_CURRENT_HOST_PENDING"
        ),
    }

    projection["agency_agents_agent_definition_reconciliation"] = {
        "source_provider_id": "FA3-PROVIDER-AGENCY-AGENTS-001",
        "source_reference_id": "FA3-AGENCY-AGENTS-UPSTREAM-REFERENCE-2026-09-23",
        "candidate_catalog_id": "FA3-AGENCY-AGENTS-CURATED-CANDIDATES-001",
        "profile_id": "FA3-AGENT-DEFINITION-001",
        "contract_id": "FA3-AGENT-DEFINITION-CONTRACTS-001",
        "registry_id": "FA3-AGENT-DEFINITION-REGISTRY-001",
        "agency_gate_id": "FA3-AGENCY-AGENTS-GATESET-001",
        "agent_definition_gate_id": "FA3-AGENT-DEFINITION-GATESET-001",
        "canonical_role_definition_count": 12,
        "canonical_template_definition_count": 5,
        "upstream_bodies_vendored": False,
        "source_distribution_class": "EXTERNAL_REDISTRIBUTABLE",
        "source_release_bundle_status": "EXCLUDED",
        "normalized_definition_distribution_class": "FA3_NATIVE",
        "gui_surface_id": "agency-agents.imported-pack",
        "gui_parent_route": "agents.workflows",
        "gui_mode": "READ_ONLY_CANONICAL_DEFINITIONS",
        "gui_current_host_status": "CURRENT_HOST_PASS" if gui_runtime_pass else "PENDING_CURRENT_HOST",
        "gui_runtime_promotion_claim": gui_runtime_pass,
        "runtime_provider_admission_by_reference_provider": False,
        "global_promotion_claim": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": capability_count,
        "reconciliation_status": (
            "CANONICAL_SOURCE_NORMALIZED_TO_FA3_DEFINITIONS_GUI_CURRENT_HOST_PASS"
            if gui_runtime_pass
            else "CANONICAL_SOURCE_NORMALIZED_TO_FA3_DEFINITIONS_GUI_STATIC_RECONCILED_CURRENT_HOST_PENDING"
        ),
    }

    ls = run_z(root, "ls-tree", "-rz", "--full-tree", snapshot)
    manifest = []
    for record in ls.split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        mode, obj_type, sha = meta.split()
        if obj_type != "blob" or path == projection_rel or mutable_path(path):
            continue
        manifest.append({
            "path": path,
            "git_blob_sha": sha,
            "baseline_delta_status": status_by_path.get(path, "unchanged"),
        })
    manifest.sort(key=lambda x: x["path"])
    projection["manifest"] = manifest
    projection["manifest_entry_count"] = len(manifest)
    projection["manifest_scope"] = {
        "repository_release_surface_complete": True,
        "self_excluded_path": projection_rel,
        "mutable_runtime_evidence_receipts_excluded": True,
        "mutable_runtime_paths_excluded": [
            "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache",
            "__pycache__", "evidence/receipts/* except .gitkeep",
        ],
    }
    projection["self_hash_policy"] = {
        "excluded_path": projection_rel,
        "reason": "SELF_REFERENTIAL_HASH_EXCLUSION",
    }

    writej(projection_path, projection)
    return {
        "snapshot": snapshot,
        "root_tree": root_tree,
        "canonical_tree": canonical_tree,
        "commit_count": commit_count,
        "delta_files": len(rows),
        "manifest_entries": len(manifest),
        "projection": projection_rel,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the FA3 unified release projection from an immutable Git snapshot")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--projection", default=DEFAULT_PROJECTION)
    parser.add_argument("--policy", default=DEFAULT_POLICY)
    args = parser.parse_args()
    result = reconcile(Path(args.root).resolve(), args.projection, args.policy)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
