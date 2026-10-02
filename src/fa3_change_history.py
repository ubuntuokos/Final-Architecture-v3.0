#!/usr/bin/env python3
"""FA3 Change-History Intelligence core.

The module owns no source-of-truth state. It validates and stores a rebuildable
derived projection of already-authoritative FA3 history and evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Iterable

TRUTH_CLASSES = {"FACT", "DERIVED_FACT", "INFERENCE", "USER_NOTE", "AI_INFERENCE"}
AI_MODES = {"OFF", "SHADOW", "ADVISORY"}
RELATIONS = {"CAUSED_BY", "AFFECTS", "DEPENDS_ON", "INVALIDATES", "REQUALIFIES", "ROLLED_BACK_BY"}
SECRET_KEY = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|credential|private[_-]?key|authorization)")
REDACTED = "<redacted>"


class ChangeHistoryError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def redact(value: Any, key: str = "") -> Any:
    if SECRET_KEY.search(key):
        return REDACTED
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def validate_record(record: dict[str, Any]) -> None:
    required = ("id", "timestamp", "truth_class", "source_kind", "source_ref",
                "object_type", "object_id", "operation", "provenance")
    missing = [key for key in required if not record.get(key)]
    if missing:
        raise ChangeHistoryError("missing change-record fields: " + ",".join(missing))
    if record["truth_class"] not in TRUTH_CLASSES:
        raise ChangeHistoryError("unsupported truth_class")
    if not isinstance(record["provenance"], dict):
        raise ChangeHistoryError("provenance must be an object")
    if record["truth_class"] in {"FACT", "DERIVED_FACT"}:
        digest = record["provenance"].get("source_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ChangeHistoryError("facts require source_sha256 provenance")


def validate_edge(edge: dict[str, Any]) -> None:
    required = ("id", "source_id", "target_id", "relation", "provenance")
    missing = [key for key in required if not edge.get(key)]
    if missing:
        raise ChangeHistoryError("missing change-edge fields: " + ",".join(missing))
    if edge["relation"] not in RELATIONS:
        raise ChangeHistoryError("unsupported change relation")
    if not isinstance(edge["provenance"], dict):
        raise ChangeHistoryError("edge provenance must be an object")


def build_record(*, record_id: str, timestamp: str, source_kind: str, source_ref: str,
                 object_type: str, object_id: str, operation: str, payload: Any,
                 truth_class: str = "FACT", provenance: dict[str, Any] | None = None,
                 details: dict[str, Any] | None = None) -> dict[str, Any]:
    clean_payload = redact(payload)
    prov = dict(provenance or {})
    prov.setdefault("source_sha256", sha256_json(clean_payload))
    row = {
        "id": record_id,
        "timestamp": timestamp,
        "truth_class": truth_class,
        "source_kind": source_kind,
        "source_ref": source_ref,
        "object_type": object_type,
        "object_id": object_id,
        "operation": operation,
        "details": redact(details or {}),
        "provenance": redact(prov),
    }
    validate_record(row)
    return row


def _default_cache_path() -> Path:
    root = os.environ.get("XDG_CACHE_HOME")
    base = Path(root).expanduser() if root else Path.home() / ".cache"
    return base / "fa3" / "change-history" / "change-history.sqlite3"


class DerivedChangeIndex:
    """Rebuildable SQLite projection. No source document is ever mutated."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path is not None else _default_cache_path()

    @staticmethod
    def _initialize(conn: sqlite3.Connection) -> None:
        conn.executescript("""
        PRAGMA journal_mode=DELETE;
        CREATE TABLE records(
          id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, truth_class TEXT NOT NULL,
          source_kind TEXT NOT NULL, source_ref TEXT NOT NULL,
          object_type TEXT NOT NULL, object_id TEXT NOT NULL,
          operation TEXT NOT NULL, payload TEXT NOT NULL, source_sha256 TEXT NOT NULL
        );
        CREATE TABLE edges(
          id TEXT PRIMARY KEY, source_id TEXT NOT NULL, target_id TEXT NOT NULL,
          relation TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE INDEX idx_records_object ON records(object_type, object_id, timestamp);
        CREATE INDEX idx_edges_source ON edges(source_id, relation);
        CREATE INDEX idx_edges_target ON edges(target_id, relation);
        """)

    def rebuild(self, records: Iterable[dict[str, Any]], edges: Iterable[dict[str, Any]]) -> str:
        records = list(records)
        edges = list(edges)
        for row in records:
            validate_record(row)
        for row in edges:
            validate_edge(row)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, raw = tempfile.mkstemp(prefix=".change-history-", suffix=".sqlite3", dir=str(self.path.parent))
        os.close(fd)
        tmp = Path(raw)
        try:
            conn = sqlite3.connect(tmp)
            try:
                self._initialize(conn)
                conn.executemany(
                    "INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [(
                        r["id"], r["timestamp"], r["truth_class"], r["source_kind"],
                        r["source_ref"], r["object_type"], r["object_id"], r["operation"],
                        canonical_json(r), r["provenance"]["source_sha256"],
                    ) for r in sorted(records, key=lambda x: x["id"])]
                )
                conn.executemany(
                    "INSERT INTO edges VALUES (?,?,?,?,?)",
                    [(
                        e["id"], e["source_id"], e["target_id"], e["relation"],
                        canonical_json(e),
                    ) for e in sorted(edges, key=lambda x: x["id"])]
                )
                conn.commit()
            finally:
                conn.close()
            os.replace(tmp, self.path)
        finally:
            if tmp.exists():
                tmp.unlink()
        return self.digest()

    def _connect_ro(self) -> sqlite3.Connection:
        if not self.path.is_file():
            raise ChangeHistoryError("derived change-history index does not exist")
        return sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)

    def history(self, object_type: str, object_id: str) -> list[dict[str, Any]]:
        conn = self._connect_ro()
        try:
            rows = conn.execute(
                "SELECT payload FROM records WHERE object_type=? AND object_id=? ORDER BY timestamp,id",
                (object_type, object_id),
            ).fetchall()
            return [json.loads(row[0]) for row in rows]
        finally:
            conn.close()

    def edge_rows(self) -> list[dict[str, Any]]:
        conn = self._connect_ro()
        try:
            return [json.loads(row[0]) for row in conn.execute("SELECT payload FROM edges ORDER BY id")]
        finally:
            conn.close()

    def digest(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def rollback_projection(self) -> dict[str, Any]:
        return {
            "derived_index_action": "DELETE_AND_REBUILD",
            "source_mutation": False,
            "path": str(self.path),
        }
