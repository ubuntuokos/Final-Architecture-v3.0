#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import load_active_release_baseline

GATE_ID = "FA3-CANONICAL-REGISTRY-INTEGRITY-GATESET-001"
CONFIG = Path("canonical/FA3-CANONICAL-REGISTRY-INTEGRITY-001.json")
REGISTRY_ROOT = Path("canonical/profiles/FA3-REGISTRY-001.json")
REPORT = Path("reports/canonical-registry-integrity-report.json")
GRAPH = Path("reports/fa3-canonical-registry-graph.json")
SUPERSEDENCE_KEYS = {"supersedes", "superseded_by", "replaces", "replacement_of"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _top_level_records(root: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    ids: dict[str, str] = {}
    duplicates: list[dict[str, Any]] = []
    for path in sorted((root / "canonical").rglob("*.json")):
        try:
            row = _load(path)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if not isinstance(rid, str) or not rid.startswith("FA3-"):
            continue
        rel = path.relative_to(root).as_posix()
        if rid in ids:
            duplicates.append({"id": rid, "first": ids[rid], "second": rel})
        else:
            ids[rid] = rel
    return ids, duplicates


def _iter_supersedence(obj: Any, source_id: str) -> list[tuple[str, str, str]]:
    edges: list[tuple[str, str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in SUPERSEDENCE_KEYS:
                vals = value if isinstance(value, list) else [value]
                for target in vals:
                    if isinstance(target, str) and target.startswith("FA3-"):
                        if key in {"superseded_by", "replacement_of"}:
                            edges.append((target, source_id, key))
                        else:
                            edges.append((source_id, target, key))
            edges.extend(_iter_supersedence(value, source_id))
    elif isinstance(obj, list):
        for value in obj:
            edges.extend(_iter_supersedence(value, source_id))
    return edges


def _cycle_nodes(edges: list[tuple[str, str, str]]) -> list[str]:
    graph: dict[str, set[str]] = {}
    for src, dst, _ in edges:
        graph.setdefault(src, set()).add(dst)
    seen: set[str] = set()
    active: set[str] = set()
    cycles: set[str] = set()

    def visit(node: str) -> None:
        if node in active:
            cycles.add(node)
            return
        if node in seen:
            return
        seen.add(node)
        active.add(node)
        for nxt in graph.get(node, set()):
            if nxt in active:
                cycles.update({node, nxt})
            else:
                visit(nxt)
        active.remove(node)

    for node in sorted(graph):
        visit(node)
    return sorted(cycles)


def build_graph(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    ids, duplicates = _top_level_records(root)
    edges: list[tuple[str, str, str]] = []
    providers_with_authority: list[str] = []
    nodes: list[dict[str, str]] = []

    for rid, rel in sorted(ids.items()):
        row = _load(root / rel)
        nodes.append({"id": rid, "path": rel})
        edges.extend(_iter_supersedence(row, rid))
        if rel.startswith("canonical/providers/") and row.get("new_architectural_authority") is True:
            providers_with_authority.append(rid)

    unresolved = sorted({
        target
        for src, target, _ in edges
        if target.startswith("FA3-") and target not in ids
    } | {
        src
        for src, target, _ in edges
        if src.startswith("FA3-") and src not in ids
    })

    graph = {
        "schema": "fa3.canonical-registry-graph.v1",
        "role": "DERIVED_DIAGNOSTIC_NON_AUTHORIZING",
        "creates_authority": False,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": [
            {"source": s, "target": d, "relation": rel}
            for s, d, rel in sorted(set(edges))
        ],
        "duplicate_top_level_ids": duplicates,
        "unresolved_supersedence_ids": unresolved,
        "supersedence_cycle_nodes": _cycle_nodes(edges),
        "providers_declaring_new_architectural_authority": sorted(providers_with_authority),
    }
    _write(root / GRAPH, graph)
    return graph


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    try:
        config = _load(root / CONFIG)
        registry = _load(root / REGISTRY_ROOT)
        baseline = load_active_release_baseline(root)
        graph = build_graph(root)
    except Exception as exc:
        report = {
            "schema": "fa3.canonical-registry-integrity-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "findings": [{"code": "CRI-000", "message": str(exc)}],
        }
        _write(root / REPORT, report)
        return report

    if config.get("gate_id") != GATE_ID:
        findings.append({"code": "CRI-001", "message": "gate identity drift"})
    if config.get("capability_count") != baseline.capability_count:
        findings.append({"code": "CRI-002", "message": "integrity config baseline drift"})
    if registry.get("capability_count") != baseline.capability_count:
        findings.append({
            "code": "CRI-003",
            "message": "active canonical registry root does not follow active release baseline",
            "registry_count": registry.get("capability_count"),
            "active_count": baseline.capability_count,
        })
    if "CAPABILITY_COUNT_FOLLOWS_ACTIVE_RELEASE_BASELINE_AND_REQUIRES_EXPLICIT_CANONICAL_DECISION_TO_CHANGE" not in registry.get("invariants", []):
        findings.append({"code": "CRI-004", "message": "registry baseline invariant missing"})
    if graph["duplicate_top_level_ids"]:
        findings.append({"code": "CRI-010", "message": "duplicate canonical top-level IDs", "details": graph["duplicate_top_level_ids"]})
    if graph["unresolved_supersedence_ids"]:
        findings.append({"code": "CRI-011", "message": "unresolved supersedence references", "ids": graph["unresolved_supersedence_ids"]})
    if graph["supersedence_cycle_nodes"]:
        findings.append({"code": "CRI-012", "message": "supersedence cycle detected", "ids": graph["supersedence_cycle_nodes"]})
    if graph["providers_declaring_new_architectural_authority"]:
        findings.append({
            "code": "CRI-013",
            "message": "provider record attempts to declare new architectural authority",
            "ids": graph["providers_declaring_new_architectural_authority"],
        })

    report = {
        "schema": "fa3.canonical-registry-integrity-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "capability_count": baseline.capability_count,
        "graph_path": GRAPH.as_posix(),
        "graph_summary": {
            "nodes": graph["node_count"],
            "edges": graph["edge_count"],
            "duplicates": len(graph["duplicate_top_level_ids"]),
            "unresolved_supersedence": len(graph["unresolved_supersedence_ids"]),
            "supersedence_cycles": len(graph["supersedence_cycle_nodes"]),
        },
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "current_host_runtime_promotion_claim": False,
        "findings": findings,
    }
    _write(root / REPORT, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    result = gate(Path(args.root))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
