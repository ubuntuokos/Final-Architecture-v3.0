#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

SCAN_ROOTS = ("src", "tests", "tools", "scripts", "evidence", "examples", "bin")
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "venv"}


def _python_files(root: Path):
    for base in SCAN_ROOTS:
        start = root / base
        if not start.exists():
            continue
        for path in start.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS or part.startswith(".venv") for part in path.parts):
                continue
            if path.suffix == ".py":
                yield path
            elif base == "bin":
                try:
                    first = path.open("r", encoding="utf-8").readline()
                except (UnicodeDecodeError, OSError):
                    continue
                if "python" in first:
                    yield path


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    parsed = 0
    for path in sorted(set(_python_files(root))):
        rel = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel)
        except Exception as exc:
            findings.append({"path": rel, "line": None, "code": "PYIMPORT-003", "detail": f"parse failure: {exc}"})
            continue
        parsed += 1
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "src" and any(alias.name.startswith("fa3_") for alias in node.names):
                    findings.append({"path": rel, "line": node.lineno, "code": "PYIMPORT-001", "detail": "from src import fa3_* creates a second module namespace"})
                elif module.startswith("src.fa3_"):
                    findings.append({"path": rel, "line": node.lineno, "code": "PYIMPORT-001", "detail": f"package-style import forbidden: {module}"})
                if node.level and module.startswith("fa3_"):
                    findings.append({"path": rel, "line": node.lineno, "code": "PYIMPORT-002", "detail": f"relative FA3 import forbidden: level={node.level} module={module}"})
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("src.fa3_"):
                        findings.append({"path": rel, "line": node.lineno, "code": "PYIMPORT-001", "detail": f"package-style import forbidden: {alias.name}"})
    return {
        "schema": "fa3.python-import-audit.v1",
        "result": "PASS" if not findings else "FAIL",
        "canonical_module_namespace": "fa3_*",
        "pythonpath": "src",
        "parsed_python_files": parsed,
        "blocking_findings": len(findings),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    report = audit(Path(args.root))
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
