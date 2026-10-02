#!/usr/bin/env python3
"""Collect real current-host CHIF positive/negative/rollback evidence."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_change_graph import explicit_pairs, make_edge
from fa3_change_history import ChangeHistoryError, DerivedChangeIndex, build_record
from fa3_change_explain import explain
from fa3_change_projector import classify_scope


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    cases: list[dict[str, object]] = []
    findings: list[dict[str, str]] = []

    def check(case_id: str, ok: bool, detail: str) -> None:
        cases.append({"id": case_id, "result": "PASS" if ok else "FAIL", "detail": detail})
        if not ok:
            findings.append({"code": case_id, "message": detail})

    runner = os.environ.get("FA3_RUNNER_CLASS", "")
    expected = os.environ.get("FA3_EXPECTED_SOURCE_SHA", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    check("CHIF-CH-001", runner == "fa3-current-host", "self-hosted runner class bound")
    check("CHIF-CH-002", repository == "ubuntuokos/Final-Architecture-v3.0", "repository identity bound")
    check("CHIF-CH-003", len(expected) == 40 and expected == actual, "exact Git source head bound")
    check("CHIF-CH-004", os.geteuid() != 0, "non-root execution required")
    check("CHIF-CH-005", (os.cpu_count() or 0) > 0, "CPU-only path available")

    source_paths = [
        ROOT / "canonical/profiles/FA3-JOURNAL-001.json",
        ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
        ROOT / "canonical/enforcement-policy.json",
    ]
    before = {str(p.relative_to(ROOT)): sha256(p) for p in source_paths}

    with tempfile.TemporaryDirectory(prefix="fa3-chif-") as td:
        index_path = Path(td) / "change-history.sqlite3"
        records = [
            build_record(
                record_id="CHIF-CH-R1", timestamp="2026-10-02T00:00:00Z",
                source_kind="CURRENT_HOST_FIXTURE", source_ref="current-host:r1",
                object_type="PROFILE", object_id="FA3-JOURNAL-001",
                operation="OBSERVED", payload={"status": "CANONICAL"},
            ),
            build_record(
                record_id="CHIF-CH-R2", timestamp="2026-10-02T00:01:00Z",
                source_kind="CURRENT_HOST_FIXTURE", source_ref="current-host:r2",
                object_type="PROFILE", object_id="FA3-CHANGE-HISTORY-INTELLIGENCE-001",
                operation="MATERIALIZED", payload={"password": "must-not-leak", "status": "STATIC"},
            ),
        ]
        edges = [
            make_edge(
                edge_id="CHIF-CH-E1", source_id="CHIF-CH-R2", target_id="CHIF-CH-R1",
                relation="DEPENDS_ON", provenance={"source": "current-host-fixture"},
            )
        ]
        index = DerivedChangeIndex(index_path)
        first = index.rebuild(records, edges)
        history = index.history("PROFILE", "FA3-CHANGE-HISTORY-INTELLIGENCE-001")
        check("CHIF-CH-POS", len(history) == 1 and history[0]["truth_class"] == "FACT",
              "positive rebuild/query path")
        check("CHIF-CH-SECRET", "must-not-leak" not in json.dumps(history),
              "secret value redacted from derived records")
        second = index.rebuild(records, edges)
        check("CHIF-CH-DETERMINISM", first == second, "repeated rebuild binary digest stable")

        negative_ok = False
        try:
            explicit_pairs(["a", "b"], ["x", "y"], None)
        except ChangeHistoryError:
            negative_ok = True
        check("CHIF-CH-NEG", negative_ok, "implicit cartesian lineage fails closed")

        calls = []
        off = explain(records, {"affected_ids": [], "invalidated_ids": [], "requalification_ids": [], "risk_context": {}},
                      ai_mode="OFF", router=lambda req: calls.append(req) or "unexpected")
        check("CHIF-CH-AI-OFF", not calls and off["ai_invoked"] is False,
              "AI OFF performs no Model Router call")
        advisory = explain(
            records,
            {"affected_ids": [], "invalidated_ids": [], "requalification_ids": [], "risk_context": {}},
            ai_mode="ADVISORY", router=lambda req: "advisory-only"
        )
        check("CHIF-CH-AI-ADVISORY",
              advisory["ai_output"]["truth_class"] == "AI_INFERENCE"
              and advisory["ai_output"]["promotable_to_fact"] is False,
              "advisory output remains AI_INFERENCE")

        scope = classify_scope(
            ["src/fa3_change_history.py", "unrelated/runtime.py"],
            ["src/fa3_change_*.py"], ["docs/**"]
        )
        check("CHIF-CH-SCOPE", scope["src/fa3_change_history.py"] == "EXPECTED"
              and scope["unrelated/runtime.py"] == "OUT_OF_SCOPE",
              "scope classification deterministic")
        rollback = index.rollback_projection()
        check("CHIF-CH-ROLLBACK", rollback["source_mutation"] is False
              and rollback["derived_index_action"] == "DELETE_AND_REBUILD",
              "rollback affects derived index only")

    after = {str(p.relative_to(ROOT)): sha256(p) for p in source_paths}
    check("CHIF-CH-READONLY", before == after, "authoritative source files remain unmodified")

    result = "PASS" if not findings else "FAIL"
    receipt = {
        "schema": "fa3.change-history-current-host-receipt.v1",
        "evidence_id": "EVID-FA3-CHANGE-HISTORY-CURRENT-HOST-001",
        "gate_id": "FA3-CHANGE-HISTORY-CURRENT-HOST-GATESET-001",
        "result": result,
        "evidence_level": "CURRENT_HOST_POSITIVE_NEGATIVE_ROLLBACK_PASS" if result == "PASS" else "CURRENT_HOST_FAIL",
        "source_binding": {
            "repository": repository,
            "source_commit": actual,
            "expected_source_commit": expected,
            "exact": actual == expected,
        },
        "host": {"runner_class": runner, "non_root": os.geteuid() != 0, "cpu_count": os.cpu_count()},
        "capability_count": 175,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "hardware_mutation": False,
        "global_promotion_claim": False,
        "cases": cases,
        "findings": findings,
    }
    out = ROOT / "reports/change-history-current-host.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if result == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
