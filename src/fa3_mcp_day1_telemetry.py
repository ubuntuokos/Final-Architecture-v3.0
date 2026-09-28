#!/usr/bin/env python3
"""Privacy-bounded observation for the existing FA3 Central MCP Gateway.

This is not a policy, evidence, promotion, resource or Temporal authority.
Only allowlisted receipt facts are logged: no request body, actor identity,
session identifier, policy/approval token, lease identifier or provider output.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
import time
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "fa3.mcp.gateway.telemetry.v1"
MAX_READ_BYTES = 64 * 1024 * 1024
_IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{1,96}\Z")


def _safe_identifier(value: Any) -> str:
    return value if isinstance(value, str) and _IDENTIFIER.fullmatch(value) else "REDACTED"


class ReceiptTelemetry:
    """Append final MCP receipts to a rootless private JSONL observation log.

    The gateway invokes this *after* execution and any provider-specific audit.
    I/O failure propagates, preventing an observable PASS response. It cannot
    undo side effects already committed by a provider; canonical execution
    evidence and provider audit remain separately mandatory.
    """

    def __init__(self, path: Path):
        self.path = Path(path).expanduser()

    def __call__(self, receipt: dict[str, Any]) -> None:
        # Unknown capability/identity can be attacker-supplied: never persist it.
        reason = str(receipt.get("reason_code", "UNKNOWN"))
        capability_id = (
            "REDACTED"
            if reason in {"UNKNOWN_CAPABILITY", "UNKNOWN_IDENTITY"}
            else _safe_identifier(receipt.get("capability_id"))
        )
        row = {
            "schema": SCHEMA,
            "timestamp_epoch": int(receipt["timestamp_epoch"]),
            "source_profile": "FA3-MCP-CURRENT-HOST-001",
            "capability_id": capability_id,
            "provider_id": _safe_identifier(receipt.get("provider_id")),
            "result_status": receipt["result_status"],
            "reason_code": _safe_identifier(reason),
            "duration_ms": max(0, int(receipt["duration_ms"])),
            "global_promotion_claim": False,
        }
        if row["result_status"] not in {"success", "denied"}:
            raise ValueError("Unrecognized MCP receipt status")
        line = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.path, flags, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or (stat.S_IMODE(info.st_mode) & 0o077):
                raise PermissionError("MCP telemetry must be a private regular file (0600)")
            # One append under an advisory lock: concurrent server threads cannot
            # interleave JSONL records written by cooperating gateway instances.
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                if os.write(fd, line) != len(line):
                    raise OSError("Incomplete MCP telemetry append")
                os.fsync(fd)
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def summarize(path: Path, hours: float = 24.0, *, now: float | None = None) -> dict[str, Any]:
    """Produce an observation-only day-1 summary. Missing/corrupt logs fail."""
    if not 0 < hours <= 168:
        raise ValueError("hours must be between 0 and 168")
    path = Path(path).expanduser()
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or (stat.S_IMODE(info.st_mode) & 0o077):
        raise PermissionError("Refusing non-private or non-regular telemetry log")
    if info.st_size > MAX_READ_BYTES:
        raise ValueError("Telemetry file exceeds maximum safe read size")
    cutoff = (now if now is not None else time.time()) - hours * 3600
    statuses: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    durations: list[int] = []
    total = 0
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
                if (
                    not isinstance(row, dict)
                    or row.get("schema") != SCHEMA
                    or row.get("result_status") not in {"success", "denied"}
                    or type(row.get("timestamp_epoch")) is not int
                    or type(row.get("duration_ms")) is not int
                    or row["duration_ms"] < 0
                    or row.get("global_promotion_claim") is not False
                ):
                    raise ValueError("invalid telemetry row")
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"Corrupt telemetry at line {line_number}") from exc
            if row["timestamp_epoch"] < cutoff:
                continue
            total += 1
            statuses[row["result_status"]] += 1
            reasons[str(row.get("reason_code", "UNKNOWN"))] += 1
            durations.append(row["duration_ms"])
    durations.sort()
    return {
        "schema": "fa3.mcp.day1.summary.v1",
        "status": "OBSERVATION_ONLY",
        "hours": hours,
        "events": total,
        "success": statuses["success"],
        "denied": statuses["denied"],
        "reason_counts": dict(sorted(reasons.items())),
        "p95_duration_ms": durations[math.ceil(0.95 * len(durations)) - 1] if durations else None,
        "evidence_level": "LOCAL_TELEMETRY_NOT_CURRENT_HOST_PROMOTION_EVIDENCE",
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 MCP first-day transaction observation")
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--hours", type=float, default=24.0)
    parser.add_argument("--require-events", action="store_true")
    args = parser.parse_args()
    try:
        report = summarize(args.jsonl, args.hours)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": type(exc).__name__}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.require_events and not report["events"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
