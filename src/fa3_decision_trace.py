#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def default_trace_path() -> Path:
    state = os.environ.get("XDG_STATE_HOME")
    if state:
        return Path(state) / "fa3" / "decision-traces.jsonl"
    return Path.home() / ".local" / "state" / "fa3" / "decision-traces.jsonl"


class DecisionTraceStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_trace_path()

    def append(self, trace: dict[str, Any]) -> None:
        if trace.get("schema") != "fa3.decision-trace.v1":
            raise ValueError("invalid decision trace schema")
        if trace.get("authority") is not False or trace.get("candidate_set_expanded") is not False:
            raise ValueError("unsafe trace cannot be persisted as valid decision trace")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        line = json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n"
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)

    def tail(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows = self.path.read_text(encoding="utf-8").splitlines()
        out: list[dict[str, Any]] = []
        for line in rows[-max(0, limit):]:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and value.get("schema") == "fa3.decision-trace.v1":
                out.append(value)
        return out
