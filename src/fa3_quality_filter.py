#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

RULE_REGISTRY = "canonical/quality/FA3-QUALITY-RULE-REGISTRY-001.json"
JUSTIFICATION_RE = re.compile(r"FA3-QUALITY-JUSTIFY\s+([A-Z0-9-]+)\s*:\s*(\S(?:.*\S)?)\s*$", re.MULTILINE)
UI_SUFFIXES = {".qml", ".html", ".htm", ".tsx", ".jsx", ".vue", ".svelte"}
CODE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".cpp", ".cc", ".c", ".h", ".hpp", ".rs", ".go", ".java", ".kt", ".sh"}
TEXT_SUFFIXES = UI_SUFFIXES | CODE_SUFFIXES | {".md", ".txt"}
SELF_EXCLUDED_PREFIXES = ("skills/fa3-quality-",)
IGNORED_PREFIXES = ("reports/", "acceptance/", "promotion/", "canonical/", "docs/", "tests/", "research/", "evidence/")
MAX_BYTES = 2_000_000

def load_rules(root: Path) -> dict[str, Any]:
    return json.loads((Path(root) / RULE_REGISTRY).read_text(encoding="utf-8"))

def content_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def parse_justifications(text: str) -> dict[str, str]:
    return {m.group(1): m.group(2).strip() for m in JUSTIFICATION_RE.finditer(text) if m.group(2).strip()}

def infer_concerns(path: str) -> set[str]:
    p = Path(path)
    suffix = p.suffix.lower()
    rel = p.as_posix()
    if any(rel.startswith(prefix) for prefix in SELF_EXCLUDED_PREFIXES):
        return set()
    if suffix in UI_SUFFIXES and rel.startswith("apps/"):
        return {"CORE", "UI", "COPY", "HUMAN", "RESPONSIVE", "FA3"}
    if suffix in CODE_SUFFIXES and rel.startswith("src/"):
        return {"CODE"}
    if suffix in {".md", ".txt"} and rel.startswith(("apps/", "marketing/", "publishing/")):
        return {"CORE", "COPY", "FA3"}
    return set()

def select_quality_skills(task_classes: Iterable[str]) -> list[str]:
    t = {x.lower() for x in task_classes}
    out: list[str] = []
    mapping = [
        ("fa3-quality-ui", {"ui", "gui", "frontend", "layout"}),
        ("fa3-quality-copy", {"copy", "text", "marketing", "publishing", "ui"}),
        ("fa3-quality-human", {"ui", "gui", "accessibility", "human"}),
        ("fa3-quality-responsive", {"ui", "gui", "frontend", "responsive", "mobile"}),
        ("fa3-quality-code", {"code", "source", "developer"}),
    ]
    for skill, keys in mapping:
        if t & keys:
            out.append(skill)
    return out

def analyze_text(path: str, text: str, registry: dict[str, Any], concerns: set[str] | None = None) -> dict[str, Any]:
    active = concerns if concerns is not None else infer_concerns(path)
    justifications = parse_justifications(text)
    findings: list[dict[str, Any]] = []
    for rule in registry.get("rules", []):
        if rule.get("concern") not in active:
            continue
        try:
            rx = re.compile(str(rule["pattern"]))
        except re.error as exc:
            findings.append({
                "rule_id": rule.get("id", "UNKNOWN"),
                "path": path,
                "tier": rule.get("tier", "HARD_GATE"),
                "status": "FAIL",
                "message": f"Invalid canonical rule regex: {exc}",
                "blocking": True,
            })
            continue
        match = rx.search(text)
        if not match:
            continue
        rid = str(rule["id"])
        tier = str(rule["tier"])
        blocking = bool(rule.get("blocking"))
        if tier == "PURPOSE_GATE" and rid in justifications:
            continue
        status = "FAIL" if blocking else "WARN"
        line = text.count("\n", 0, match.start()) + 1
        findings.append({
            "rule_id": rid,
            "path": path,
            "tier": tier,
            "status": status,
            "message": str(rule["message"]),
            "line": line,
            "blocking": blocking,
        })
    failures = [f for f in findings if f["status"] == "FAIL"]
    return {
        "schema": "fa3.quality-report.v1",
        "path": path,
        "content_sha256": content_digest(text),
        "concerns": sorted(active),
        "findings": findings,
        "blocking_findings": len(failures),
        "warnings": sum(f["status"] == "WARN" for f in findings),
        "result": "PASS" if not failures else "FAIL",
    }

def _git_changed_paths(root: Path, base: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", f"{base}...HEAD"],
        text=True, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff failed for {base}: {proc.stderr.strip()}")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

def _candidate_paths(root: Path, scope: str, changed_from: str | None) -> list[str]:
    if changed_from:
        candidates = _git_changed_paths(root, changed_from)
    elif scope == "gui":
        qml = root / "apps" / "fa3-control-center" / "qml"
        candidates = [p.relative_to(root).as_posix() for p in qml.rglob("*") if p.is_file()] if qml.is_dir() else []
    else:
        candidates = []
        for prefix in ("apps", "src"):
            base = root / prefix
            if base.is_dir():
                candidates.extend(p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file())
    out = []
    for rel in sorted(set(candidates)):
        if not (root / rel).is_file():
            continue
        if scope == "gui" and not rel.startswith("apps/fa3-control-center/qml/"):
            continue
        if any(rel.startswith(x) for x in SELF_EXCLUDED_PREFIXES):
            continue
        if changed_from is None and any(rel.startswith(x) for x in IGNORED_PREFIXES):
            continue
        if Path(rel).suffix.lower() not in TEXT_SUFFIXES:
            continue
        if not infer_concerns(rel):
            continue
        out.append(rel)
    return out

def scan(root: Path, *, scope: str = "repo", changed_from: str | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    registry = load_rules(root)
    artifacts = []
    read_errors = []
    for rel in _candidate_paths(root, scope, changed_from):
        p = root / rel
        try:
            if p.stat().st_size > MAX_BYTES:
                read_errors.append({"path": rel, "error": "FILE_TOO_LARGE"})
                continue
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            read_errors.append({"path": rel, "error": str(exc)})
            continue
        artifacts.append(analyze_text(rel, text, registry))
    failures = sum(a["blocking_findings"] for a in artifacts) + len(read_errors)
    return {
        "schema": "fa3.quality-scan.v1",
        "scope": scope,
        "changed_from": changed_from,
        "artifacts_scanned": len(artifacts),
        "blocking_findings": failures,
        "warnings": sum(a["warnings"] for a in artifacts),
        "read_errors": read_errors,
        "artifacts": artifacts,
        "result": "PASS" if failures == 0 else "FAIL",
    }
