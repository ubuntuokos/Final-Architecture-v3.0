#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

SCAN_ROOTS = ("src", "tests", "tools", "evidence")
EXCLUDED_DIRS = {"__pycache__", ".venv", ".venv-fa3-test"}


def python_files(root: Path):
    for base_name in SCAN_ROOTS:
        base = root / base_name
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            yield path


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    files = list(python_files(root))
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (OSError, SyntaxError) as exc:
            findings.append({"path": rel, "line": getattr(exc, "lineno", None), "code": "PYNS-000", "message": f"unparseable Python source: {exc}"})
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "src" or module.startswith("src."):
                    findings.append({"path": rel, "line": node.lineno, "code": "PYNS-001", "message": "package-style src.* import is forbidden; use the canonical top-level fa3_* module namespace"})
                if node.level and module.startswith("fa3_"):
                    findings.append({"path": rel, "line": node.lineno, "code": "PYNS-002", "message": "relative FA3 module import is forbidden; use the canonical top-level fa3_* module namespace"})
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "src" or alias.name.startswith("src."):
                        findings.append({"path": rel, "line": node.lineno, "code": "PYNS-001", "message": "package-style src.* import is forbidden; use the canonical top-level fa3_* module namespace"})
    return {
        "schema": "fa3.python-namespace-audit.v1",
        "result": "PASS" if not findings else "FAIL",
        "canonical_namespace": "TOP_LEVEL_FA3_MODULES_VIA_SRC_ON_SYS_PATH",
        "findings": findings,
        "files_scanned": len(files),
    }
