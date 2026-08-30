#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROJECTION_ID = "FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30"
PROJECTION_PATH = "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
DECISION_PATH = "canonical/decisions/FA3-DEC-UNIFIED-POST-V3.0.11-PROJECTION-2026-08-30.json"
BASE_RELEASE = "2026-08-23/v3.0.11"
CAPABILITY_COUNT = 143
EXPECTED_SOURCE_GRAPH_SHA256 = "0418528b52fd9a29d993fc69c1ea508f57cd527d96e234d738c6b8fc553c4f16"
EXPECTED_SOURCE_GRAPH_NODES = 1615
EXPECTED_SOURCE_GRAPH_EDGES = 6144

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
        or projection.get("projection_semantics") != "NO_BASELINE_SEMANTIC_CHANGE_IMPLEMENTATION_PROJECTION_UPDATE"
    ):
        findings.append(finding("FA3-RELEASE-PROJECTION-002", "Baseline release or projection semantics changed"))

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
        },
    }
    writej(root / "reports/release-projection-gate-report.json", report)
    return report
