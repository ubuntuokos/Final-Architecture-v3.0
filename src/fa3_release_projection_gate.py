#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

PROJECTION_ID = "FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30"
PROJECTION_PATH = "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
DECISION_PATH = "canonical/decisions/FA3-DEC-UNIFIED-POST-V3.0.11-PROJECTION-2026-08-30.json"
BASE_RELEASE = "2026-08-23/v3.0.11"
BASE_COMMIT = "1d8a3ffaa2b4d11abcc6003250ff66b4798eef60"
CAPABILITY_COUNT = 143
EXPECTED_SOURCE_GRAPH_SHA256 = "0418528b52fd9a29d993fc69c1ea508f57cd527d96e234d738c6b8fc553c4f16"
EXPECTED_SOURCE_GRAPH_NODES = 1615
EXPECTED_SOURCE_GRAPH_EDGES = 6144
SNAPSHOT_SEMANTICS = "PRE_MAINTENANCE_CANONICAL_MAIN_ANCHOR"
KANBOARD_PROVIDER_ID = "FA3-PROVIDER-KANBOARD-001"
KANBOARD_GATE_ID = "FA3-KANBOARD-GATESET-001"
KANBOARD_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-KANBOARD-001.json"
KANBOARD_DECISION_PATH = "canonical/decisions/FA3-DEC-KANBOARD-2026-08-30.json"
KANBOARD_REFERENCE_PATH = "canonical/references/FA3-KANBOARD-UPSTREAM-REFERENCE-2026-08-30.json"
KANBOARD_EVIDENCE_PATH = "evidence/reference/kanboard-ci-2026-08-30.json"
KANBOARD_ENFORCEMENT_PATH = "canonical/kanboard-enforcement.json"
KANBOARD_GATE_PATH = "src/fa3_kanboard_gate.py"
KANBOARD_TEST_PATH = "tests/test_kanboard_gate.py"
KANBOARD_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED"
PRESENTON_PROVIDER_ID = "FA3-PROVIDER-PRESENTON-001"
PRESENTON_GATE_ID = "FA3-PRESENTON-GATESET-001"
PRESENTON_CONTRACT_ID = "FA3-PRESENTON-CONTRACTS-001"
PRESENTON_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-PRESENTON-001.json"
PRESENTON_DECISION_PATH = "canonical/decisions/FA3-DEC-PRESENTON-2026-08-30.json"
PRESENTON_REFERENCE_PATH = "canonical/references/FA3-PRESENTON-UPSTREAM-REFERENCE-2026-08-30.json"
PRESENTON_EVIDENCE_PATH = "evidence/reference/presenton-provider-ci-2026-08-30.json"
PRESENTON_CONTRACT_PATH = "canonical/contracts/FA3-PRESENTON-CONTRACTS-001.json"
PRESENTON_ENFORCEMENT_PATH = "canonical/presenton-enforcement.json"
PRESENTON_GATE_PATH = "src/fa3_presenton_gate.py"
PRESENTON_TEST_PATH = "tests/test_presenton_gate.py"
PRESENTON_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_CURRENT_HOST_PENDING"
AUTOGPT_PROVIDER_ID = "FA3-PROVIDER-AUTOGPT-001"
AUTOGPT_GATE_ID = "FA3-AUTOGPT-GATESET-001"
AUTOGPT_PROVIDER_PATH = "canonical/providers/FA3-PROVIDER-AUTOGPT-001.json"
AUTOGPT_DECISION_PATH = "canonical/decisions/FA3-DEC-AUTOGPT-2026-08-30.json"
AUTOGPT_REFERENCE_PATH = "canonical/references/FA3-AUTOGPT-UPSTREAM-REFERENCE-2026-08-30.json"
AUTOGPT_EVIDENCE_PATH = "evidence/reference/autogpt-ci-2026-08-30.json"
AUTOGPT_RECONCILIATION_EVIDENCE_PATH = "evidence/reference/autogpt-global-reconciliation-ci-2026-08-30.json"
AUTOGPT_ENFORCEMENT_PATH = "canonical/autogpt-enforcement.json"
AUTOGPT_ADMISSION_PATH = "canonical/autogpt-runtime-admission.json"
AUTOGPT_GATE_PATH = "src/fa3_autogpt_gate.py"
AUTOGPT_TEST_PATH = "tests/test_autogpt_gate.py"
AUTOGPT_CAPABILITY_ID = "CAP-028"
AUTOGPT_RECONCILIATION_STATUS = "GLOBAL_PROJECTION_RECONCILED_RUNTIME_NOT_ADMITTED"

_MUTABLE_TOP_LEVEL = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache"}
_MUTABLE_DIR_NAMES = {"__pycache__"}


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def finding(code: str, message: str, **extra):
    return {"code": code, "severity": "P0", "message": message, **extra}


def is_mutable_runtime_path(rel: str) -> bool:
    parts = Path(rel).parts
    if not parts:
        return True
    if parts[0] in _MUTABLE_TOP_LEVEL:
        return True
    if any(part in _MUTABLE_DIR_NAMES for part in parts):
        return True
    if rel.startswith("evidence/receipts/") and rel != "evidence/receipts/.gitkeep":
        return True
    return False


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed with rc={proc.returncode}: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def _git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    raise RuntimeError(
        f"git merge-base --is-ancestor failed with rc={proc.returncode}: {proc.stderr.strip()}"
    )


def _diff_rows(root: Path, snapshot_head: str):
    raw = _git(root, "diff", "--name-status", "--find-renames", BASE_COMMIT, snapshot_head)
    rows = []
    for line in raw.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith(("R", "C")):
            if len(parts) < 3:
                raise RuntimeError(f"unparseable rename/copy row: {line}")
            path = parts[-1]
        else:
            if len(parts) < 2:
                raise RuntimeError(f"unparseable name-status row: {line}")
            path = parts[1]
        rows.append((status, path))
    return rows


def collect_git_snapshot_facts(root: Path, snapshot_head: str):
    root = Path(root).resolve()
    if not snapshot_head:
        raise RuntimeError("source_snapshot.pre_projection_head_sha is empty")

    rows = _diff_rows(root, snapshot_head)
    paths = [path for _, path in rows]

    def prefixed(prefix: str):
        return sorted(path for path in paths if path.startswith(prefix))

    added = sum(status.startswith("A") for status, _ in rows)
    modified = sum(status.startswith("M") for status, _ in rows)
    removed = sum(status.startswith("D") for status, _ in rows)
    other = len(rows) - added - modified - removed

    return {
        "snapshot_head_sha": _git(root, "rev-parse", snapshot_head),
        "current_head_sha": _git(root, "rev-parse", "HEAD"),
        "root_tree_sha": _git(root, "rev-parse", f"{snapshot_head}^{{tree}}"),
        "canonical_tree_sha": _git(root, "rev-parse", f"{snapshot_head}:canonical"),
        "baseline_is_ancestor": _git_is_ancestor(root, BASE_COMMIT, snapshot_head),
        "snapshot_is_ancestor_of_current_head": _git_is_ancestor(root, snapshot_head, "HEAD"),
        "commit_count": int(_git(root, "rev-list", "--count", f"{BASE_COMMIT}..{snapshot_head}")),
        "delta_file_count": len(rows),
        "delta_added_files": added,
        "delta_modified_files": modified,
        "delta_removed_files": removed,
        "delta_other_files": other,
        "area_counts": {
            "canonical_files_in_post_baseline_delta": len(prefixed("canonical/")),
            "evidence_files_in_post_baseline_delta": len(prefixed("evidence/")),
            "source_files_in_post_baseline_delta": len(prefixed("src/")),
            "test_files_in_post_baseline_delta": len(prefixed("tests/")),
            "workflow_files_in_post_baseline_delta": len(prefixed(".github/workflows/")),
        },
        "record_lists": {
            "provider_records": prefixed("canonical/providers/"),
            "profile_records": prefixed("canonical/profiles/"),
            "contract_records": prefixed("canonical/contracts/"),
            "decision_records": prefixed("canonical/decisions/"),
            "upstream_reference_records": prefixed("canonical/references/"),
            "reference_evidence_records": prefixed("evidence/reference/"),
        },
    }


def gate(root: Path):
    root = Path(root).resolve()
    findings = []

    projection = loadj(root / PROJECTION_PATH)
    policy = loadj(root / "canonical/enforcement-policy.json")
    attestation = loadj(root / "canonical/source-graph-attestation.json")
    evidence = loadj(root / "evidence/evidence-registry.json")
    decision = loadj(root / DECISION_PATH)

    if (
        projection.get("schema") != "fa3.canonical-release-projection.v1"
        or projection.get("id") != PROJECTION_ID
        or projection.get("status") != "CANONICAL_PROJECTED"
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-001", "Projection identity/schema/status mismatch"))

    if (
        projection.get("base_release") != BASE_RELEASE
        or projection.get("base_release_commit") != BASE_COMMIT
        or projection.get("projection_semantics") != "NO_BASELINE_SEMANTIC_CHANGE_IMPLEMENTATION_PROJECTION_UPDATE"
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-002", "Baseline release/commit or projection semantics changed"))

    invariants = projection.get("invariants", {})
    if (
        invariants.get("canonical_capability_count") != CAPABILITY_COUNT
        or invariants.get("new_capabilities") != 0
        or invariants.get("new_architectural_authorities") != 0
        or invariants.get("baseline_semantics_frozen") is not True
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-003", "Capability/authority/baseline invariant mismatch"))

    if (
        policy.get("architecture_release") != BASE_RELEASE
        or policy.get("canonical_capability_count") != CAPABILITY_COUNT
        or policy.get("canonical_release_projection") != PROJECTION_ID
        or policy.get("canonical_release_projection_path") != PROJECTION_PATH
        or policy.get("projection_semantics") != projection.get("projection_semantics")
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-004", "Global enforcement policy is not bound to the unified projection"))

    source_graph = projection.get("baseline_source_graph", {})
    if (
        attestation.get("release") != BASE_RELEASE
        or attestation.get("sha256") != EXPECTED_SOURCE_GRAPH_SHA256
        or attestation.get("graph_nodes") != EXPECTED_SOURCE_GRAPH_NODES
        or attestation.get("graph_edges") != EXPECTED_SOURCE_GRAPH_EDGES
        or source_graph.get("sha256") != EXPECTED_SOURCE_GRAPH_SHA256
        or source_graph.get("graph_nodes") != EXPECTED_SOURCE_GRAPH_NODES
        or source_graph.get("graph_edges") != EXPECTED_SOURCE_GRAPH_EDGES
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-005", "v3.0.11 source-graph anchor drift"))

    records = evidence.get("records", [])
    if (
        evidence.get("architecture_release") != BASE_RELEASE
        or evidence.get("canonical_capability_count") != CAPABILITY_COUNT
        or len(records) != CAPABILITY_COUNT
        or [r.get("subject_id") for r in records] != [f"CAP-{i:03d}" for i in range(1, CAPABILITY_COUNT + 1)]
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-006", "Evidence Registry release/cardinality invariant mismatch"))

    projection_gates = set(projection.get("mandatory_reference_gates", []))
    policy_gates = set(policy.get("mandatory_reference_gates", []))
    if not projection_gates or projection_gates != policy_gates:
        findings.append(finding("FA3-RELEASE-PROJECTION-007", "Projection/global mandatory reference gate set mismatch"))

    manifest = projection.get("manifest", [])
    manifest_paths = {m.get("path") for m in manifest}
    if projection.get("manifest_entry_count") != len(manifest) or len(manifest_paths) != len(manifest):
        findings.append(finding("FA3-RELEASE-PROJECTION-008", "Projection manifest cardinality/uniqueness mismatch"))

    kanboard = projection.get("kanboard_reconciliation", {})
    inventory = projection.get("overlay_inventory", {})
    required_kanboard_manifest_paths = {
        KANBOARD_PROVIDER_PATH,
        KANBOARD_DECISION_PATH,
        KANBOARD_REFERENCE_PATH,
        KANBOARD_EVIDENCE_PATH,
        KANBOARD_ENFORCEMENT_PATH,
        KANBOARD_GATE_PATH,
        KANBOARD_TEST_PATH,
    }
    missing_overlay_members = []
    for key, required in {
        "provider_records": KANBOARD_PROVIDER_PATH,
        "decision_records": KANBOARD_DECISION_PATH,
        "upstream_reference_records": KANBOARD_REFERENCE_PATH,
        "reference_evidence_records": KANBOARD_EVIDENCE_PATH,
    }.items():
        if required not in inventory.get(key, []):
            missing_overlay_members.append({"inventory": key, "path": required})

    kanboard_provider = loadj(root / KANBOARD_PROVIDER_PATH) if (root / KANBOARD_PROVIDER_PATH).is_file() else {}
    kanboard_evidence = loadj(root / KANBOARD_EVIDENCE_PATH) if (root / KANBOARD_EVIDENCE_PATH).is_file() else {}
    kanboard_manifest_missing = sorted(required_kanboard_manifest_paths - manifest_paths)
    if (
        kanboard.get("provider_id") != KANBOARD_PROVIDER_ID
        or kanboard.get("gate_id") != KANBOARD_GATE_ID
        or kanboard.get("classification") != "OPTIONAL_REFERENCE_PROVIDER"
        or kanboard.get("reconciliation_status") != KANBOARD_RECONCILIATION_STATUS
        or kanboard.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or kanboard.get("new_capabilities") != 0
        or kanboard.get("new_architectural_authorities") != 0
        or kanboard.get("capability_count_after") != CAPABILITY_COUNT
        or KANBOARD_GATE_ID not in projection_gates
        or KANBOARD_GATE_ID not in policy_gates
        or missing_overlay_members
        or kanboard_manifest_missing
        or kanboard_provider.get("id") != KANBOARD_PROVIDER_ID
        or kanboard_provider.get("canonical_root") is not False
        or kanboard_provider.get("architectural_authority") is not False
        or kanboard_provider.get("new_capability") is not False
        or kanboard_provider.get("capability_count") != CAPABILITY_COUNT
        or "OPTIONAL_PROVIDER" not in kanboard_provider.get("classification", [])
        or kanboard_evidence.get("provider_id") != KANBOARD_PROVIDER_ID
        or kanboard_evidence.get("gate_id") != KANBOARD_GATE_ID
        or kanboard_evidence.get("status") != "PASS"
        or kanboard_evidence.get("new_capabilities") != 0
        or kanboard_evidence.get("new_architectural_authorities") != 0
        or kanboard_evidence.get("capability_count_after") != CAPABILITY_COUNT
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-021",
                "Kanboard global projection/inventory reconciliation invariant mismatch",
                reconciliation_status=kanboard.get("reconciliation_status"),
                missing_overlay_members=missing_overlay_members,
                missing_manifest_paths=kanboard_manifest_missing,
            )
        )

    presenton = projection.get("presenton_reconciliation", {})
    required_presenton_manifest_paths = {
        PRESENTON_PROVIDER_PATH,
        PRESENTON_DECISION_PATH,
        PRESENTON_REFERENCE_PATH,
        PRESENTON_EVIDENCE_PATH,
        PRESENTON_CONTRACT_PATH,
        PRESENTON_ENFORCEMENT_PATH,
        PRESENTON_GATE_PATH,
        PRESENTON_TEST_PATH,
        "evidence/collect-presenton-current-host.py",
        "bin/fa3-presenton-current-host.sh",
        ".github/workflows/fa3-presenton-current-host.yml",
        "deployment/presenton/README.md",
        "deployment/presenton/ai-creative.target",
        "deployment/presenton/postgresql-bootstrap.sql",
        "deployment/presenton/presenton.caddy",
        "deployment/presenton/presenton.container",
    }
    presenton_overlay_requirements = {
        "provider_records": PRESENTON_PROVIDER_PATH,
        "decision_records": PRESENTON_DECISION_PATH,
        "upstream_reference_records": PRESENTON_REFERENCE_PATH,
        "reference_evidence_records": PRESENTON_EVIDENCE_PATH,
        "contract_records": PRESENTON_CONTRACT_PATH,
    }
    missing_presenton_overlay_members = [
        {"inventory": key, "path": required}
        for key, required in presenton_overlay_requirements.items()
        if required not in inventory.get(key, [])
    ]
    presenton_manifest_missing = sorted(required_presenton_manifest_paths - manifest_paths)
    presenton_provider = loadj(root / PRESENTON_PROVIDER_PATH) if (root / PRESENTON_PROVIDER_PATH).is_file() else {}
    presenton_evidence = loadj(root / PRESENTON_EVIDENCE_PATH) if (root / PRESENTON_EVIDENCE_PATH).is_file() else {}
    cap033 = next((item for item in evidence.get("records", []) if item.get("subject_id") == "CAP-033"), {})
    if (
        presenton.get("provider_id") != PRESENTON_PROVIDER_ID
        or presenton.get("contract_id") != PRESENTON_CONTRACT_ID
        or presenton.get("gate_id") != PRESENTON_GATE_ID
        or presenton.get("classification") != "OPTIONAL_PRODUCTION_CANDIDATE_PROVIDER"
        or presenton.get("reconciliation_status") != PRESENTON_RECONCILIATION_STATUS
        or presenton.get("current_host_production_e2e") != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        or presenton.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or presenton.get("new_capabilities") != 0
        or presenton.get("new_architectural_authorities") != 0
        or presenton.get("capability_count_after") != CAPABILITY_COUNT
        or PRESENTON_GATE_ID not in projection_gates
        or PRESENTON_GATE_ID not in policy_gates
        or missing_presenton_overlay_members
        or presenton_manifest_missing
        or presenton_provider.get("id") != PRESENTON_PROVIDER_ID
        or presenton_provider.get("canonical_root") is not False
        or presenton_provider.get("architectural_authority") is not False
        or presenton_provider.get("new_capability") is not False
        or presenton_provider.get("capability_count") != CAPABILITY_COUNT
        or "OPTIONAL_PROVIDER" not in presenton_provider.get("classification", [])
        or presenton_evidence.get("provider_id") != PRESENTON_PROVIDER_ID
        or presenton_evidence.get("gate_id") != PRESENTON_GATE_ID
        or presenton_evidence.get("status") != "PASS"
        or presenton_evidence.get("current_host_production_e2e", {}).get("status") != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        or "FA3-DEC-PRESENTON-2026-08-30" not in cap033.get("source_decision_ids", [])
        or PRESENTON_EVIDENCE_PATH not in cap033.get("evidence_artifacts", [])
        or cap033.get("status") != "PENDING_CURRENT_HOST"
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-022",
                "Presenton global projection/inventory/evidence reconciliation invariant mismatch",
                reconciliation_status=presenton.get("reconciliation_status"),
                current_host_production_e2e=presenton.get("current_host_production_e2e"),
                missing_overlay_members=missing_presenton_overlay_members,
                missing_manifest_paths=presenton_manifest_missing,
            )
        )

    autogpt = projection.get("autogpt_reconciliation", {})
    required_autogpt_manifest_paths = {
        AUTOGPT_PROVIDER_PATH,
        AUTOGPT_DECISION_PATH,
        AUTOGPT_REFERENCE_PATH,
        AUTOGPT_EVIDENCE_PATH,
        AUTOGPT_RECONCILIATION_EVIDENCE_PATH,
        AUTOGPT_ENFORCEMENT_PATH,
        AUTOGPT_ADMISSION_PATH,
        AUTOGPT_GATE_PATH,
        AUTOGPT_TEST_PATH,
        "evidence/evidence-registry.json",
    }
    autogpt_overlay_requirements = {
        "provider_records": AUTOGPT_PROVIDER_PATH,
        "decision_records": AUTOGPT_DECISION_PATH,
        "upstream_reference_records": AUTOGPT_REFERENCE_PATH,
        "reference_evidence_records": AUTOGPT_EVIDENCE_PATH,
    }
    missing_autogpt_overlay_members = [
        {"inventory": key, "path": required}
        for key, required in autogpt_overlay_requirements.items()
        if required not in inventory.get(key, [])
    ]
    autogpt_manifest_missing = sorted(required_autogpt_manifest_paths - manifest_paths)
    autogpt_provider = loadj(root / AUTOGPT_PROVIDER_PATH) if (root / AUTOGPT_PROVIDER_PATH).is_file() else {}
    autogpt_evidence = loadj(root / AUTOGPT_EVIDENCE_PATH) if (root / AUTOGPT_EVIDENCE_PATH).is_file() else {}
    autogpt_reconciliation_evidence = loadj(root / AUTOGPT_RECONCILIATION_EVIDENCE_PATH) if (root / AUTOGPT_RECONCILIATION_EVIDENCE_PATH).is_file() else {}
    autogpt_admission = loadj(root / AUTOGPT_ADMISSION_PATH) if (root / AUTOGPT_ADMISSION_PATH).is_file() else {}
    cap028 = next((item for item in records if item.get("subject_id") == AUTOGPT_CAPABILITY_ID), {})
    if (
        autogpt.get("provider_id") != AUTOGPT_PROVIDER_ID
        or autogpt.get("gate_id") != AUTOGPT_GATE_ID
        or autogpt.get("capability_id") != AUTOGPT_CAPABILITY_ID
        or autogpt.get("classification") != "OPTIONAL_AGENTIC_WORKFLOW_REFERENCE_PROVIDER"
        or autogpt.get("reconciliation_status") != AUTOGPT_RECONCILIATION_STATUS
        or autogpt.get("runtime_activation_status") != "NOT_PROMOTED_REFERENCE_ONLY"
        or autogpt.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or autogpt.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or autogpt.get("new_capabilities") != 0
        or autogpt.get("new_architectural_authorities") != 0
        or autogpt.get("capability_count_after") != CAPABILITY_COUNT
        or AUTOGPT_GATE_ID not in projection_gates
        or AUTOGPT_GATE_ID not in policy_gates
        or missing_autogpt_overlay_members
        or autogpt_manifest_missing
        or autogpt_provider.get("id") != AUTOGPT_PROVIDER_ID
        or autogpt_provider.get("canonical_root") is not False
        or autogpt_provider.get("architectural_authority") is not False
        or autogpt_provider.get("new_capability") is not False
        or autogpt_provider.get("capability_count") != CAPABILITY_COUNT
        or "OPTIONAL_PROVIDER" not in autogpt_provider.get("classification", [])
        or autogpt_provider.get("runtime_activation_status") != "NOT_PROMOTED_REFERENCE_ONLY"
        or autogpt_evidence.get("provider_id") != AUTOGPT_PROVIDER_ID
        or autogpt_evidence.get("gate_id") != AUTOGPT_GATE_ID
        or autogpt_evidence.get("status") != "PASS"
        or autogpt_evidence.get("current_host_runtime_evidence") != "NOT_CLAIMED"
        or autogpt_reconciliation_evidence.get("provider_id") != AUTOGPT_PROVIDER_ID
        or autogpt_reconciliation_evidence.get("capability_id") != AUTOGPT_CAPABILITY_ID
        or autogpt_reconciliation_evidence.get("status") != "PASS"
        or autogpt_reconciliation_evidence.get("conclusion") != "GLOBAL_RELEASE_INVENTORY_EVIDENCE_RECONCILIATION_PASS"
        or autogpt_admission.get("provider_id") != AUTOGPT_PROVIDER_ID
        or autogpt_admission.get("status") != "NOT_ADMITTED"
        or autogpt_admission.get("fail_closed") is not True
        or autogpt_admission.get("current_host_evidence_required") is not True
        or "FA3-DEC-AUTOGPT-2026-08-30" not in cap028.get("source_decision_ids", [])
        or AUTOGPT_EVIDENCE_PATH not in cap028.get("evidence_artifacts", [])
        or AUTOGPT_RECONCILIATION_EVIDENCE_PATH not in cap028.get("evidence_artifacts", [])
        or cap028.get("runtime_conformance") != "EVIDENCE-PENDING"
        or cap028.get("status") != "PENDING_CURRENT_HOST"
        or cap028.get("promotion_state") != "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-023",
                "AutoGPT global release/inventory/evidence reconciliation invariant mismatch",
                reconciliation_status=autogpt.get("reconciliation_status"),
                runtime_activation_status=autogpt.get("runtime_activation_status"),
                missing_overlay_members=missing_autogpt_overlay_members,
                missing_manifest_paths=autogpt_manifest_missing,
                cap028_evidence_artifacts=cap028.get("evidence_artifacts", []),
            )
        )

    missing = []
    drift = []
    for entry in manifest:
        rel = entry.get("path")
        expected = entry.get("git_blob_sha")
        if not rel or not expected:
            drift.append(rel)
            continue
        path = root / rel
        if not path.is_file():
            missing.append(rel)
            continue
        actual = git_blob_sha(path)
        if actual != expected:
            drift.append({"path": rel, "expected": expected, "actual": actual})

    if missing:
        findings.append(finding("FA3-RELEASE-PROJECTION-009", "Projected file missing", count=len(missing), sample=missing[:20]))
    if drift:
        findings.append(finding("FA3-RELEASE-PROJECTION-010", "Projected Git-blob identity drift", count=len(drift), sample=drift[:20]))

    self_hash = projection.get("self_hash_policy", {})
    if (
        self_hash.get("excluded_path") != PROJECTION_PATH
        or self_hash.get("reason") != "SELF_REFERENTIAL_HASH_EXCLUSION"
        or not (root / PROJECTION_PATH).is_file()
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-011", "Projection self-hash exclusion is invalid"))

    if (
        decision.get("id") != "FA3-DEC-UNIFIED-POST-V3.0.11-PROJECTION-2026-08-30"
        or decision.get("status") != "CANONICAL"
        or decision.get("capability_count_after") != CAPABILITY_COUNT
        or decision.get("new_capabilities") != 0
        or decision.get("new_architectural_authorities") != 0
        or decision.get("projection_id") != PROJECTION_ID
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-012", "Canonical projection decision invariant mismatch"))

    promotion = projection.get("promotion", {})
    if (
        promotion.get("fail_closed") is not True
        or promotion.get("current_host_evidence_required") is not True
        or promotion.get("acceptance_criteria_required") != 19
        or promotion.get("document_only_promotion_forbidden") is not True
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-013", "Promotion safety semantics weakened"))

    tracked_surface = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == PROJECTION_PATH or is_mutable_runtime_path(rel):
            continue
        tracked_surface.append(rel)
    unmanifested = sorted(set(tracked_surface) - manifest_paths)
    if unmanifested:
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-014",
                "Repository release-surface contains unmanifested file",
                count=len(unmanifested),
                sample=unmanifested[:20],
            )
        )

    scope = projection.get("manifest_scope", {})
    if (
        scope.get("repository_release_surface_complete") is not True
        or scope.get("self_excluded_path") != PROJECTION_PATH
        or scope.get("mutable_runtime_evidence_receipts_excluded") is not True
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-015", "Manifest scope contract mismatch"))

    snapshot = projection.get("source_snapshot", {})
    snapshot_head = snapshot.get("pre_projection_head_sha")
    facts = None
    if (
        snapshot.get("snapshot_semantics") != SNAPSHOT_SEMANTICS
        or snapshot.get("baseline_commit_sha") != BASE_COMMIT
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-016",
                "Source snapshot semantics or baseline anchor mismatch",
            )
        )

    try:
        facts = collect_git_snapshot_facts(root, snapshot_head)
    except Exception as exc:
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-016",
                "Source snapshot Git facts unavailable",
                error=str(exc),
            )
        )

    if facts is not None:
        if (
            facts.get("snapshot_head_sha") != snapshot_head
            or facts.get("baseline_is_ancestor") is not True
            or facts.get("snapshot_is_ancestor_of_current_head") is not True
        ):
            findings.append(
                finding(
                    "FA3-RELEASE-PROJECTION-016",
                    "Source snapshot lineage mismatch",
                    snapshot_head=snapshot_head,
                    current_head=facts.get("current_head_sha"),
                )
            )

        if (
            snapshot.get("pre_projection_root_tree_sha") != facts.get("root_tree_sha")
            or snapshot.get("pre_projection_canonical_tree_sha") != facts.get("canonical_tree_sha")
        ):
            findings.append(
                finding(
                    "FA3-RELEASE-PROJECTION-017",
                    "Source snapshot tree identity drift",
                    expected_root_tree=facts.get("root_tree_sha"),
                    declared_root_tree=snapshot.get("pre_projection_root_tree_sha"),
                    expected_canonical_tree=facts.get("canonical_tree_sha"),
                    declared_canonical_tree=snapshot.get("pre_projection_canonical_tree_sha"),
                )
            )

        expected_delta = {
            "commits_ahead_of_v3_0_11_conformance_commit": facts.get("commit_count"),
            "total_post_baseline_commits": facts.get("commit_count"),
            "delta_file_count": facts.get("delta_file_count"),
            "delta_added_files": facts.get("delta_added_files"),
            "delta_modified_files": facts.get("delta_modified_files"),
            "delta_removed_files": facts.get("delta_removed_files"),
            "delta_other_files": facts.get("delta_other_files"),
        }
        delta_mismatches = {
            key: {"expected": expected, "declared": snapshot.get(key)}
            for key, expected in expected_delta.items()
            if snapshot.get(key) != expected
        }
        if delta_mismatches:
            findings.append(
                finding(
                    "FA3-RELEASE-PROJECTION-018",
                    "Source snapshot Git-delta metadata drift",
                    mismatches=delta_mismatches,
                )
            )

        inventory = projection.get("overlay_inventory", {})
        count_mismatches = {
            key: {"expected": expected, "declared": inventory.get(key)}
            for key, expected in facts.get("area_counts", {}).items()
            if inventory.get(key) != expected
        }
        if count_mismatches:
            findings.append(
                finding(
                    "FA3-RELEASE-PROJECTION-019",
                    "Overlay inventory count drift",
                    mismatches=count_mismatches,
                )
            )

        record_mismatches = {}
        for key, expected in facts.get("record_lists", {}).items():
            declared = sorted(inventory.get(key, []))
            if declared != expected:
                record_mismatches[key] = {
                    "expected_count": len(expected),
                    "declared_count": len(declared),
                    "missing": sorted(set(expected) - set(declared))[:20],
                    "extra": sorted(set(declared) - set(expected))[:20],
                }
        if record_mismatches:
            findings.append(
                finding(
                    "FA3-RELEASE-PROJECTION-020",
                    "Overlay inventory record set is incomplete or stale",
                    mismatches=record_mismatches,
                )
            )

    result = "PASS" if not findings else "FAIL"
    report = {
        "schema": "fa3.release-projection-gate-report.v1",
        "projection_id": PROJECTION_ID,
        "base_release": BASE_RELEASE,
        "result": result,
        "blocking_findings": len(findings),
        "findings": findings,
        "details": {
            "manifest_entries": len(manifest),
            "tracked_release_surface_files": len(tracked_surface),
            "canonical_capability_count": CAPABILITY_COUNT,
            "mandatory_reference_gates": len(projection_gates),
            "source_graph_sha256": EXPECTED_SOURCE_GRAPH_SHA256,
            "projection_semantics": projection.get("projection_semantics"),
            "snapshot_anchor": snapshot_head,
            "snapshot_commit_count": facts.get("commit_count") if facts else None,
            "snapshot_delta_files": facts.get("delta_file_count") if facts else None,
            "kanboard_reconciliation": kanboard.get("reconciliation_status"),
            "presenton_reconciliation": presenton.get("reconciliation_status"),
            "presenton_current_host_production_e2e": presenton.get("current_host_production_e2e"),
            "autogpt_reconciliation": autogpt.get("reconciliation_status"),
            "autogpt_runtime_activation_status": autogpt.get("runtime_activation_status"),
        },
    }
    writej(root / "reports/release-projection-gate-report.json", report)
    return report
