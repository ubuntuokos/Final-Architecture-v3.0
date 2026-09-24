#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_reuse_resolver import resolve


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def assess_intent(root: Path, intent: dict[str, Any]) -> dict[str, Any]:
    resolution = resolve(root, intent)
    blocking = []
    if resolution["authority_collisions"]:
        blocking.append("AUTHORITY_COLLISION")
    if resolution["coexistence_findings"]:
        blocking.append("COEXISTENCE_INVALID")
    if resolution["hardware_findings"]:
        blocking.append("HARDWARE_AUDIT_INVALID")
    if resolution["duplicate_declared_capabilities"]:
        blocking.append("DUPLICATE_CAPABILITY_DECLARATION")

    declared_gaps = list(intent.get("declared_gaps", []))
    discovered_gaps = [row["capability"] for row in resolution["gaps"]]
    all_gaps = sorted(set(declared_gaps + discovered_gaps))
    readiness = "BLOCKED" if blocking else ("PENDING_GAPS" if all_gaps else "READY_FOR_NORMAL_ADMISSION")

    selected = [
        {
            "id": row["candidate_id"],
            "class": row["candidate_class"],
            "reuse_mode": row["reuse_mode"],
            "score": row["score"],
            "source_path": row["source_path"],
        }
        for row in resolution["candidates"][:20]
    ]
    return {
        "schema": "fa3.reuse-assessment.generated.v1",
        "project_id": intent.get("project_id"),
        "intent_id": intent.get("id"),
        "result": "FAIL" if blocking else "PASS",
        "blocking_findings": blocking,
        "selected_reuse": selected,
        "gaps": all_gaps,
        "existing_authority_bindings": resolution["existing_authority_bindings"],
        "authority_collisions": resolution["authority_collisions"],
        "hardware_findings": resolution["hardware_findings"],
        "coexistence_findings": resolution["coexistence_findings"],
        "implementation_readiness": readiness,
        "candidate_set_expansion": False,
        "runtime_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess reuse for one FA3 ApplicationIntent")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--intent", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    intent_path = Path(args.intent)
    if not intent_path.is_absolute():
        intent_path = root / intent_path
    result = assess_intent(root, load_json(intent_path))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
