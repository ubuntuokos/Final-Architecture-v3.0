#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Mapping

SCALE_SUBJECT_ID = "FA3-EXTERNAL-SCALE-TOOLKIT"
SCALE_RIGHTS_RECEIPT_SCHEMA = "fa3.scale-execution-rights-receipt.v1"
SCALE_RIGHTS_AUTHORITY = "FA3-AUTH-SECURITY-GOV-001"


def _run(argv: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            argv,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", type(exc).__name__
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _normalize_bdf(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().lower()
    match = re.search(r"([0-9a-f]{2,8}):([0-9a-f]{2}):([0-9a-f]{2}\.[0-7])", text)
    if not match:
        return None
    domain = match.group(1)[-4:].zfill(4)
    return f"{domain}:{match.group(2)}:{match.group(3)}"


def _first_version(text: str) -> str | None:
    for pattern in (
        r"\b(?:release|version)\s+([0-9]+(?:\.[0-9]+){1,3}(?:[-+._a-zA-Z0-9]*)?)",
        r"\b([0-9]+(?:\.[0-9]+){1,3}(?:[-+._a-zA-Z0-9]*)?)\b",
    ):
        match = re.search(pattern, text or "", flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def parse_scaleinfo(text: str) -> dict[str, dict[str, str]]:
    """Parse SCALE's documented device summary into exact PCI-BDF keyed rows."""
    devices: dict[str, dict[str, str]] = {}
    line_re = re.compile(
        r"^\s*Device\s+(?P<ordinal>\d+)\s+\((?P<bdf>[^)]+)\):\s*"
        r"(?P<name>.*?)\s+-\s+(?P<target>(?:gfx|sm_)[0-9a-z]+)\s+"
        r"\((?P<vendor>AMD|NVIDIA)\)",
        flags=re.IGNORECASE,
    )
    for raw in str(text or "").splitlines():
        match = line_re.search(raw)
        if not match:
            continue
        bdf = _normalize_bdf(match.group("bdf"))
        if not bdf:
            continue
        devices[bdf] = {
            "ordinal": match.group("ordinal"),
            "name": match.group("name").strip(),
            "target": match.group("target").lower(),
            "vendor": match.group("vendor").upper(),
        }
    return devices


def _scaleinfo_path(environ: Mapping[str, str]) -> str | None:
    configured = str(environ.get("FA3_SCALE_DIR", "")).strip()
    if configured:
        candidate = Path(configured).expanduser() / "bin" / "scaleinfo"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
    return shutil.which("scaleinfo")


def probe_scale(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Read-only SCALE discovery. It never installs, activates, or mutates SCALE."""
    env = os.environ if environ is None else environ
    scaleinfo = _scaleinfo_path(env)
    if not scaleinfo:
        return {
            "detected": False,
            "usable": False,
            "version": None,
            "scaleinfo_path": None,
            "devices": {},
            "evidence": (),
        }

    rc, out, err = _run([scaleinfo])
    devices = parse_scaleinfo(out if rc == 0 else "")
    version = None
    nvcc = Path(scaleinfo).parent / "nvcc"
    if nvcc.is_file() and os.access(nvcc, os.X_OK):
        vrc, vout, verr = _run([str(nvcc), "--version"])
        if vrc == 0:
            version = _first_version("\n".join((vout, verr)))

    return {
        "detected": True,
        "usable": rc == 0 and bool(devices),
        "version": version,
        "scaleinfo_path": str(Path(scaleinfo).resolve()),
        "devices": devices,
        "evidence": (
            f"scaleinfo:rc={rc}",
            f"scaleinfo:device-count={len(devices)}",
            "scale-discovery:read-only",
            "scale-auto-install:false",
            "scale-auto-activation:false",
        ) + ((f"scaleinfo:error={err}",) if err and rc != 0 else ()),
    }


def evaluate_scale_execution_rights(
    receipt: Mapping[str, Any] | None,
    *,
    commercial_context: bool = True,
) -> dict[str, Any]:
    """Fail-closed admission check for an external SCALE runtime entitlement."""
    findings: list[str] = []
    row = dict(receipt or {})
    if row.get("schema") != SCALE_RIGHTS_RECEIPT_SCHEMA:
        findings.append("SCALE_RIGHTS_RECEIPT_SCHEMA_MISMATCH")
    if row.get("authority") != SCALE_RIGHTS_AUTHORITY:
        findings.append("SCALE_RIGHTS_AUTHORITY_MISMATCH")
    if row.get("subject_id") != SCALE_SUBJECT_ID:
        findings.append("SCALE_RIGHTS_SUBJECT_MISMATCH")
    if row.get("result") != "PASS":
        findings.append("SCALE_RIGHTS_NOT_PASS")
    if row.get("execution_allowed") is not True:
        findings.append("SCALE_EXECUTION_NOT_ALLOWED")
    if row.get("raw_secret_material_present") is True:
        findings.append("SCALE_RAW_SECRET_MATERIAL_FORBIDDEN")

    if commercial_context:
        if row.get("commercial_use_allowed") is not True:
            findings.append("SCALE_COMMERCIAL_USE_NOT_ALLOWED")
        if not str(row.get("entitlement_reference") or "").strip():
            findings.append("SCALE_COMMERCIAL_ENTITLEMENT_REFERENCE_MISSING")

    return {
        "result": "PASS" if not findings else "FAIL",
        "admitted": not findings,
        "commercial_context": bool(commercial_context),
        "findings": findings,
    }
