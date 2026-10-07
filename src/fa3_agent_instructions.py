#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-AGENT-INSTRUCTIONS-001"
META_SCHEMA = "fa3.agent-instruction-projection.v1"
NON_CANONICAL_AUTHORITY = "NON_CANONICAL_PROJECTION"
META_RE = re.compile(r"<!--\s*FA3_AGENT_META\s+(\{[^\n]*\})\s*-->")

@dataclass(frozen=True)
class AgentInstructionDocument:
    path: str
    scope: str
    authority: str
    sha256: str
    content: str

def parse_metadata(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    matches = META_RE.findall(text)
    if len(matches) != 1:
        return None, [f"EXPECTED_EXACTLY_ONE_METADATA_BLOCK:{len(matches)}"]
    try:
        meta = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        return None, [f"INVALID_METADATA_JSON:{exc.msg}"]
    return meta, []

def _safe_target(root: Path, target: Path) -> Path:
    root = root.resolve()
    absolute = target if target.is_absolute() else root / target
    absolute = absolute.resolve(strict=False)
    try:
        absolute.relative_to(root)
    except ValueError as exc:
        raise ValueError("TARGET_OUTSIDE_REPOSITORY") from exc
    return absolute

def _target_directory(root: Path, target: Path) -> Path:
    absolute = _safe_target(root, target)
    if absolute.exists() and absolute.is_dir():
        return absolute
    return absolute.parent

def candidate_instruction_paths(root: Path, target: Path) -> list[Path]:
    root = root.resolve()
    directory = _target_directory(root, target)
    rel = directory.relative_to(root)
    dirs = [root]
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        dirs.append(cursor)
    return [directory / "AGENTS.md" for directory in dirs]

def load_instruction(path: Path, root: Path) -> AgentInstructionDocument:
    text = path.read_text(encoding="utf-8")
    meta, errors = parse_metadata(text)
    if errors or meta is None:
        raise ValueError(f"INVALID_AGENT_INSTRUCTION_METADATA:{path}:{','.join(errors)}")
    if meta.get("schema") != META_SCHEMA:
        raise ValueError(f"INVALID_AGENT_INSTRUCTION_SCHEMA:{path}")
    if meta.get("profile") != PROFILE_ID:
        raise ValueError(f"INVALID_AGENT_INSTRUCTION_PROFILE:{path}")
    if meta.get("authority") != NON_CANONICAL_AUTHORITY:
        raise ValueError(f"AGENT_INSTRUCTION_AUTHORITY_ESCALATION:{path}")
    return AgentInstructionDocument(
        path=path.relative_to(root.resolve()).as_posix(),
        scope=str(meta.get("scope")),
        authority=str(meta.get("authority")),
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        content=text,
    )

def resolve_instruction_chain(root: Path, target: Path) -> list[AgentInstructionDocument]:
    root = root.resolve()
    docs = []
    for path in candidate_instruction_paths(root, target):
        if path.is_file():
            docs.append(load_instruction(path, root))
    return docs

def resolve_report(root: Path, target: Path) -> dict[str, Any]:
    root = root.resolve()
    absolute = _safe_target(root, target)
    docs = resolve_instruction_chain(root, target)
    nearest_first = [doc.path for doc in reversed(docs)]
    return {
        "schema":"fa3.agent-instruction-resolution.v1",
        "profile_id":PROFILE_ID,
        "target":absolute.relative_to(root).as_posix(),
        "authority":NON_CANONICAL_AUTHORITY,
        "merge_order":"ROOT_TO_NEAREST",
        "effective_precedence":"NEAREST_SCOPE_WINS",
        "documents":[asdict(doc) for doc in docs],
        "precedence_nearest_first":nearest_first,
        "document_count":len(docs),
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve FA3 scoped repository agent instructions")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--target", required=True)
    parser.add_argument("--format", choices=("json","markdown"), default="json")
    args = parser.parse_args()
    report = resolve_report(Path(args.root), Path(args.target))
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for document in report["documents"]:
            print(f"\n<!-- resolved:{document['path']} scope:{document['scope']} -->\n")
            print(document["content"].rstrip())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
