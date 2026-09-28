#!/usr/bin/env python3
"""Scoped, read-only deja-vu search provider for the existing FA3 MCP Gateway.

No direct MCP server, automatic agent wiring, global index scan, embed, sync,
update or external network access. Runtime admission remains a separate gate.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

from fa3_mcp_gateway import Adapter, GatewayDenied

PROVIDER_ID = "FA3-PROVIDER-DEJA-VU-001"
ADAPTER_ID = "fa3.adapter.deja-vu.retrieve"
UPSTREAM_SHA = "73ad34e5fdc2b0c245a0fb69b65a17f3cbb123c8"
FORMAT = "fa3.deja.scoped-runtime.v1"
ALLOWED_STORES = {"claude": "DEJA_CLAUDE_ROOT", "codex": "DEJA_CODEX_ROOT"}
PROJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.S),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})\b"),
    re.compile(r"(?i)\b(?:api_key|access_token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9+/_=-]{12,}"),
)


def _deny(code: str) -> None:
    raise GatewayDenied(code, code)


def _private_dir(path: Path) -> Path:
    if not path.is_absolute() or not path.is_dir() or path.is_symlink():
        _deny("UNTRUSTED_PARTITION")
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        _deny("UNTRUSTED_PARTITION")
    return path.resolve(strict=True)


def _under(path: Path, root: Path) -> bool:
    try:
        return path.is_relative_to(root)
    except (ValueError, TypeError):
        return False


def _string(value: Any, *, max_length: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        _deny("INVALID_INPUT")
    return value.strip()


def _redact(value: str) -> str:
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[redacted:fa3]", value)
    return value


def _load_runtime(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.is_absolute() or manifest_path.is_symlink():
        _deny("INVALID_MANIFEST_PATH")
    st = manifest_path.stat()
    if st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077:
        _deny("UNTRUSTED_MANIFEST")
    try:
        config = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        _deny("INVALID_MANIFEST")
    if not isinstance(config, dict) or config.get("schema") != FORMAT:
        _deny("INVALID_MANIFEST")
    if config.get("upstream_sha") != UPSTREAM_SHA:
        _deny("UPSTREAM_PIN_MISMATCH")
    if config.get("admission_status") != "RUNTIME_ADMITTED":
        _deny("PROVIDER_NOT_ADMITTED")
    base = _private_dir(Path(_string(config.get("partition_root"), max_length=4096)))
    binary = Path(_string(config.get("binary_path"), max_length=4096))
    if not binary.is_absolute() or binary.is_symlink() or not binary.is_file():
        _deny("INVALID_BINARY")
    digest = _string(config.get("binary_sha256"), max_length=64)
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        _deny("INVALID_BINARY_DIGEST")
    if hashlib.sha256(binary.read_bytes()).hexdigest() != digest:
        _deny("BINARY_DIGEST_MISMATCH")
    projects = config.get("projects")
    if not isinstance(projects, dict) or not projects:
        _deny("NO_ADMITTED_PROJECTS")
    return {"root": base, "binary": binary, "projects": projects}


class DejaRecall:
    """A local read adapter. External FA3 policy must authorize project_id first."""

    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path

    def retrieve(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            _deny("INVALID_INPUT")
        if set(arguments) - {"project_id", "query", "max_items", "max_context_chars"}:
            _deny("UNSUPPORTED_ARGUMENT")
        project = _string(arguments.get("project_id"), max_length=128)
        if not PROJECT_RE.fullmatch(project) or project in {".", ".."}:
            _deny("INVALID_PROJECT_ID")
        query = _string(arguments.get("query"))
        count = arguments.get("max_items", 5)
        budget = arguments.get("max_context_chars", 2400)
        if type(count) is not int or not 1 <= count <= 10:
            _deny("INVALID_BUDGET")
        if type(budget) is not int or not 160 <= budget <= 8000:
            _deny("INVALID_BUDGET")

        runtime = _load_runtime(self.manifest_path)
        spec = runtime["projects"].get(project)
        if not isinstance(spec, dict):
            _deny("PROJECT_NOT_ADMITTED")
        part = _private_dir(Path(_string(spec.get("partition_dir"), max_length=4096)))
        if not _under(part, runtime["root"]) or part == runtime["root"]:
            _deny("INVALID_PROJECT_PARTITION")
        index = part / "index"
        home = _private_dir(part / "home")
        _private_dir(index)
        roots = spec.get("stores")
        if not isinstance(roots, dict) or not roots or set(roots) - set(ALLOWED_STORES):
            _deny("INVALID_SOURCE_SCOPE")
        allowed_roots: dict[str, Path] = {}
        for name, path_value in roots.items():
            src = _private_dir(Path(_string(path_value, max_length=4096)))
            if not _under(src, part) or src == part:
                _deny("INVALID_SOURCE_SCOPE")
            allowed_roots[name] = src
        aliases = spec.get("exact_project_aliases", [project])
        if not isinstance(aliases, list) or not aliases or any(
            not isinstance(x, str) or not x or len(x) > 128 for x in aliases
        ):
            _deny("INVALID_PROJECT_ALIAS")
        # Upstream's --project is substring-based. Partition isolation happens
        # BEFORE invoking deja; result filtering then requires exact aliases.
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "DEJA_INDEX_DIR": str(index),
            "DEJA_STORES": ",".join(sorted(allowed_roots)),
            "DEJA_MOVED": "0",
            "NO_COLOR": "1",
        }
        for name, src in allowed_roots.items():
            env[ALLOWED_STORES[name]] = str(src)
        try:
            completed = subprocess.run(
                [str(runtime["binary"]), "search", "--json", "--limit", str(count), query],
                cwd=str(part), env=env, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=6, check=False,
            )
        except subprocess.TimeoutExpired:
            _deny("UPSTREAM_TIMEOUT")
        except OSError:
            _deny("UPSTREAM_UNAVAILABLE")
        if completed.returncode != 0 or len(completed.stdout) > 4 * 1024 * 1024:
            _deny("UPSTREAM_FAILURE")
        try:
            payload = json.loads(completed.stdout)
        except (UnicodeError, ValueError):
            _deny("INVALID_UPSTREAM_OUTPUT")
        if not isinstance(payload, dict) or payload.get("schema_version") != 2:
            _deny("UPSTREAM_SCHEMA_MISMATCH")
        if payload.get("semantic") is True or payload.get("tier") not in {
            "exact", "close", "stemmed", "error", "relevance",
        } or not isinstance(payload.get("hits"), list):
            _deny("UNADMITTED_RETRIEVAL_TIER")

        results: list[dict[str, Any]] = []
        remaining = budget
        for hit in payload["hits"]:
            if not isinstance(hit, dict):
                _deny("INVALID_UPSTREAM_OUTPUT")
            if payload["tier"] == "relevance" and hit.get("strict") is not True:
                continue
            session = hit.get("session")
            if not isinstance(session, dict) or session.get("project") not in aliases:
                # Cross-project rows must never be returned or reranked as hits.
                continue
            harness = session.get("harness")
            src_value = session.get("path")
            if harness not in allowed_roots or not isinstance(src_value, str):
                continue
            source_path = Path(src_value)
            if not source_path.is_absolute() or not _under(
                source_path.resolve(), allowed_roots[harness]
            ):
                continue
            sid = session.get("id")
            if not isinstance(sid, str) or not sid or len(sid) > 256:
                continue
            snippets = hit.get("snippets")
            if not isinstance(snippets, list):
                _deny("INVALID_UPSTREAM_OUTPUT")
            excerpts: list[str] = []
            for snippet in snippets[:3]:
                if not isinstance(snippet, str):
                    _deny("INVALID_UPSTREAM_OUTPUT")
                safe = _redact(snippet[:min(600, remaining)])
                if safe:
                    excerpts.append(safe)
                    remaining -= len(safe)
                if remaining <= 0:
                    break
            score = hit.get("score", 0)
            score = float(score) if type(score) in {int, float} else 0.0
            results.append({
                "source_ref": "FA3-DEJA-" + hashlib.sha256(
                    (str(source_path.resolve()) + "\0" + sid).encode("utf-8")
                ).hexdigest()[:24].upper(),
                "session_id": sid,
                "project_id": project,
                "harness": harness,
                "tier": str(hit.get("tier") or payload["tier"]),
                "score": score if math.isfinite(score) else 0.0,
                "snippets": excerpts,
                "lifecycle": hit.get("lifecycle") if hit.get("lifecycle") in {
                    "accepted", "rejected", "superseded", "stale"
                } else "raw",
                "non_authoritative": True,
            })
            if len(results) >= count or remaining <= 0:
                break
        return {
            "schema": "fa3.deja.recall-result.v1",
            "provider_id": PROVIDER_ID,
            "project_id": project,
            "retrieval_tier": payload["tier"],
            "items": results,
            "item_count": len(results),
            "source_authority": False,
            "derived": True,
            "model_used": False,
            "context_budget_remaining": remaining,
        }


def factory() -> Adapter:
    manifest = os.environ.get("FA3_DEJA_RUNTIME_MANIFEST")
    if not manifest:
        _deny("PROVIDER_NOT_ADMITTED")
    recall = DejaRecall(Path(manifest))
    # Resolve admission and binary integrity before publishing this adapter.
    runtime = _load_runtime(recall.manifest_path)
    audit = runtime["root"] / "retrieval-audit.jsonl"

    def audit_receipt(request: dict[str, Any], receipt: dict[str, Any]) -> None:
        # No query text, snippets, private paths, or source transcripts in audit.
        row = {
            "schema": "fa3.deja.recall-audit.v1",
            "actor_id": receipt.get("actor_id"),
            "capability_id": receipt.get("capability_id"),
            "policy_decision_id": receipt.get("policy_decision_id"),
            "request_sha256": receipt.get("request_sha256"),
            "status": receipt.get("result_status"),
            "project_id": request.get("arguments", {}).get("project_id"),
        }
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(audit, flags, 0o600)
        try:
            with os.fdopen(fd, "a", encoding="utf-8") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            # fdopen owns fd on success.
            pass

    return Adapter(
        adapter_id=ADAPTER_ID, provider_id=PROVIDER_ID,
        handler=recall.retrieve, receipt_handler=audit_receipt,
    )
