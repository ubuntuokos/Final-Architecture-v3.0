#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITY_ID = "CAP-074"
CATALOG_PATH = "canonical/FA3-CANONICAL-SERVICE-CATALOG-001.json"
MODES = ("positive", "negative", "rollback")


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


def _service_cycle(service_ids: set[str], edges: list[dict[str, Any]]) -> bool:
    graph = {sid: [] for sid in service_ids}
    for edge in edges:
        src = edge.get("source")
        dst = edge.get("target")
        if src in service_ids and dst in service_ids:
            graph[src].append(dst)
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph.get(node, []):
            if dfs(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(dfs(node) for node in sorted(service_ids))


def validate_catalog(root: Path, catalog: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if catalog.get("schema") != "fa3.service-catalog-dependency-graph.v1":
        findings.append("catalog schema mismatch")
    if catalog.get("id") != "FA3-CANONICAL-SERVICE-CATALOG-001":
        findings.append("catalog id mismatch")
    if catalog.get("status") != "CANONICAL":
        findings.append("catalog status must be CANONICAL")
    if catalog.get("capability_id") != CAPABILITY_ID:
        findings.append("catalog capability binding mismatch")
    if catalog.get("provider_neutral") is not True:
        findings.append("catalog must remain provider-neutral")
    if catalog.get("new_capability") is not False or catalog.get("new_architectural_authority") is not False:
        findings.append("catalog cannot create capability or authority")
    if catalog.get("capability_count") != module_active_capability_count(__file__):
        findings.append("capability count drift")

    services = catalog.get("services")
    resources = catalog.get("resources")
    edges = catalog.get("edges")
    if not isinstance(services, list) or not services:
        findings.append("service catalog is empty")
        services = []
    if not isinstance(resources, list) or not resources:
        findings.append("resource catalog is empty")
        resources = []
    if not isinstance(edges, list) or not edges:
        findings.append("dependency graph is empty")
        edges = []

    service_ids: set[str] = set()
    service_paths: dict[str, Path] = {}
    for row in services:
        if not isinstance(row, dict):
            findings.append("service row must be object")
            continue
        sid = row.get("id")
        rel = row.get("source_path")
        if not isinstance(sid, str) or not sid.startswith("svc:"):
            findings.append("service id invalid")
            continue
        if sid in service_ids:
            findings.append(f"duplicate service id {sid}")
            continue
        service_ids.add(sid)
        if not isinstance(rel, str) or not rel:
            findings.append(f"{sid}: source_path missing")
            continue
        path = (root / rel).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            findings.append(f"{sid}: source_path missing or escapes repository")
        else:
            service_paths[sid] = path

    resource_ids: set[str] = set()
    for row in resources:
        if not isinstance(row, dict):
            findings.append("resource row must be object")
            continue
        rid = row.get("id")
        if not isinstance(rid, str) or not rid.startswith("res:"):
            findings.append("resource id invalid")
            continue
        if rid in resource_ids or rid in service_ids:
            findings.append(f"duplicate node id {rid}")
            continue
        resource_ids.add(rid)
        if row.get("kind") == "CANONICAL_ARTIFACT":
            rel = row.get("path")
            path = (root / str(rel)).resolve() if rel else None
            if path is None or root.resolve() not in path.parents or not path.is_file():
                findings.append(f"{rid}: canonical artifact resource missing")

    nodes = service_ids | resource_ids
    edge_keys: set[tuple[str, str, str]] = set()
    services_with_edges: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            findings.append("edge must be object")
            continue
        src = edge.get("source")
        dst = edge.get("target")
        relation = edge.get("relation")
        token = edge.get("evidence_token")
        if src not in service_ids:
            findings.append(f"edge source is not known service: {src}")
        else:
            services_with_edges.add(src)
        if dst not in nodes:
            findings.append(f"dangling dependency target: {dst}")
        if not isinstance(relation, str) or not relation:
            findings.append(f"{src}->{dst}: relation missing")
        key = (str(src), str(dst), str(relation))
        if key in edge_keys:
            findings.append(f"duplicate dependency edge: {src}->{dst}:{relation}")
        edge_keys.add(key)
        if src in service_paths:
            if not isinstance(token, str) or not token:
                findings.append(f"{src}->{dst}: evidence token missing")
            elif token not in service_paths[src].read_text(encoding="utf-8"):
                findings.append(f"{src}->{dst}: evidence token not present in deployment source")

    missing_edges = sorted(service_ids - services_with_edges)
    if missing_edges:
        findings.append("services without dependency evidence: " + ",".join(missing_edges))
    if _service_cycle(service_ids, edges):
        findings.append("service dependency cycle detected")

    semantics = catalog.get("graph_semantics", {})
    required = {
        "service_source_must_exist": True,
        "every_service_requires_dependency_evidence": True,
        "dangling_dependencies_forbidden": True,
        "duplicate_edges_forbidden": True,
        "service_dependency_cycles_forbidden": True,
        "dependency_evidence_must_be_present_in_source": True,
    }
    for key, expected in required.items():
        if semantics.get(key) is not expected:
            findings.append(f"graph semantic invariant disabled: {key}")
    return findings


def _run_positive(root: Path, scope: Path) -> dict[str, Any]:
    path = root / CATALOG_PATH
    catalog = _load(path)
    findings = validate_catalog(root, catalog)
    if findings:
        raise RuntimeError("service catalog validation failed: " + "; ".join(findings))
    return {
        "mode": "positive",
        "status": "PASS",
        "service_count": len(catalog["services"]),
        "resource_count": len(catalog["resources"]),
        "edge_count": len(catalog["edges"]),
        "catalog_sha256": _sha256(path),
        "source_bound_edges": True,
        "service_cycle_free": True,
    }


def _run_negative(root: Path, scope: Path) -> dict[str, Any]:
    baseline = _load(root / CATALOG_PATH)

    dangling = json.loads(json.dumps(baseline))
    dangling["edges"][0]["target"] = "res:missing-current-host-dependency"
    dangling_findings = validate_catalog(root, dangling)
    if not any("dangling dependency target" in item for item in dangling_findings):
        raise RuntimeError("dangling dependency was not rejected")

    cyclic = json.loads(json.dumps(baseline))
    first = cyclic["services"][0]["id"]
    second = cyclic["services"][1]["id"]
    token_first = Path(root / cyclic["services"][0]["source_path"]).read_text(encoding="utf-8").splitlines()[0]
    token_second = Path(root / cyclic["services"][1]["source_path"]).read_text(encoding="utf-8").splitlines()[0]
    cyclic["edges"].append({"source": first, "target": second, "relation": "TEST_DEPENDS_ON", "evidence_token": token_first})
    cyclic["edges"].append({"source": second, "target": first, "relation": "TEST_DEPENDS_ON", "evidence_token": token_second})
    cycle_findings = validate_catalog(root, cyclic)
    if not any("service dependency cycle detected" in item for item in cycle_findings):
        raise RuntimeError("service dependency cycle was not rejected")

    return {
        "mode": "negative",
        "status": "PASS",
        "dangling_dependency_rejected": True,
        "service_cycle_rejected": True,
        "dangling_findings": dangling_findings,
        "cycle_findings": cycle_findings,
    }


def _run_rollback(root: Path, scope: Path) -> dict[str, Any]:
    original = (root / CATALOG_PATH).read_bytes()
    pre_hash = _sha256_bytes(original)
    scratch = scope / "service-catalog.rollback.json"
    scratch.write_bytes(original)
    baseline_findings = validate_catalog(root, _load(scratch))
    if baseline_findings:
        raise RuntimeError("rollback baseline invalid: " + "; ".join(baseline_findings))

    mutated = _load(scratch)
    mutated["edges"][0]["target"] = "res:rollback-fault"
    _write_json(scratch, mutated)
    mutated_hash = _sha256(scratch)
    fault_findings = validate_catalog(root, _load(scratch))
    if not fault_findings:
        raise RuntimeError("rollback failure injection was not detected")

    scratch.write_bytes(original)
    post_hash = _sha256(scratch)
    restored_findings = validate_catalog(root, _load(scratch))
    if restored_findings:
        raise RuntimeError("restored catalog invalid: " + "; ".join(restored_findings))
    if post_hash != pre_hash:
        raise RuntimeError("rollback did not restore exact catalog bytes")
    if mutated_hash == pre_hash:
        raise RuntimeError("failure injection did not change catalog digest")

    return {
        "mode": "rollback",
        "status": "PASS",
        "pre_sha256": pre_hash,
        "mutated_sha256": mutated_hash,
        "post_sha256": post_hash,
        "fault_detected": True,
        "rollback_hash_equal": post_hash == pre_hash,
        "restored_catalog_valid": True,
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
    parser = argparse.ArgumentParser(description="CAP-074 current-host service catalog dependency qualification producer")
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if _required_env("FA3_CURRENT_HOST") != "1":
            raise RuntimeError("real current-host execution marker required")
        if _required_env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("CURRENT_HOST execution scope required")
        if _required_env("FA3_CAPABILITY_ID") != CAPABILITY_ID:
            raise RuntimeError("producer is bound only to CAP-074")
        root = Path(_required_env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(_required_env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        result = run_mode(root, scope, args.mode)
        artifact = scope / "cap074-service-catalog-evidence.json"
        payload = {
            "schema": "fa3.cap074-service-catalog-current-host-evidence.v1",
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
