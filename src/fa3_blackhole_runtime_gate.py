#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

GATE_ID = "FA3-BLACKHOLE-RUNTIME-PROMOTION-GATESET-001"
PROFILE_ID = "FA3-BLACKHOLE-API-001"
DECISION_ID = "FA3-DEC-BLACKHOLE-RUNTIME-PROMOTION-2026-09-14"
REFERENCE_REPORT = "reports/blackhole-runtime-reference-gate-report.json"
CURRENT_HOST_REPORT = "reports/blackhole-runtime-current-host-report.json"
FFMPEG_CURRENT_HOST_GATE_REPORT = "reports/ffmpeg-ai-current-host-gate-report.json"

CHECKOUT_SHA = "11d5960a326750d5838078e36cf38b85af677262"
SETUP_PYTHON_SHA = "a26af69be951a213d495a4c3e4e4022e16d87065"
UPLOAD_ARTIFACT_SHA = "ea165f8d65b6e75b540449e92b4886f43607fa02"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def reference_gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    decision_path = root / "canonical/decisions/FA3-DEC-BLACKHOLE-RUNTIME-PROMOTION-2026-09-14.json"
    enforcement_path = root / "canonical/blackhole-runtime-promotion-enforcement.json"
    try:
        decision = _load(decision_path)
        enforcement = _load(enforcement_path)
    except Exception as exc:
        report = {
            "schema": "fa3.blackhole-runtime-reference-gate-report.v1",
            "gate_id": GATE_ID,
            "profile_id": PROFILE_ID,
            "result": "FAIL",
            "findings": [_finding("BLACKHOLE-RUNTIME-000", "canonical decision/enforcement unavailable", error=repr(exc))],
            "promotion_effect": "BLOCK_BLACKHOLE_COMPONENT_PROMOTION",
        }
        _write(root / REFERENCE_REPORT, report)
        return report

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("decision") == "IMPLEMENT"
        and decision.get("profile_id") == PROFILE_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
    ):
        findings.append(_finding("BLACKHOLE-RUNTIME-001", "canonical decision identity/status/authority drift"))

    required_files = enforcement.get("required_files", [])
    if not isinstance(required_files, list) or not required_files:
        findings.append(_finding("BLACKHOLE-RUNTIME-002", "required_files contract missing"))
    else:
        missing = [rel for rel in required_files if not (root / rel).is_file()]
        if missing:
            findings.append(_finding("BLACKHOLE-RUNTIME-003", "required runtime artifacts missing", paths=missing))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("profile_id") == PROFILE_ID
        and enforcement.get("status") == "CANONICAL"
        and enforcement.get("fail_closed") is True
        and enforcement.get("reference_oci_may_claim_production") is False
        and enforcement.get("zero_copy_claim_allowed") is False
        and enforcement.get("current_host_required_for_component_promotion") is True
        and enforcement.get("ffmpeg_ai_current_host_receipt_required") is True
        and enforcement.get("exact_ffmpeg_binary_digest_binding_required") is True
        and enforcement.get("runtime_uid") == 10002
    ):
        findings.append(_finding("BLACKHOLE-RUNTIME-004", "enforcement semantics weakened"))

    try:
        containerfile = (root / "deployment/containers/blackhole-api.Containerfile").read_text(encoding="utf-8")
        required_container_tokens = (
            "USER 10002:10002",
            "REFERENCE_OCI_NOT_PRODUCTION",
            'io.fa3.zero-copy-claimed="false"',
            "HEALTHCHECK",
            "ffmpeg",
        )
        for token in required_container_tokens:
            if token not in containerfile:
                findings.append(_finding("BLACKHOLE-RUNTIME-005", "Containerfile invariant missing", token=token))
        lowered = containerfile.lower()
        if ":latest" in lowered or "touch bin/ffmpeg" in lowered or "mock ffmpeg" in lowered:
            findings.append(_finding("BLACKHOLE-RUNTIME-006", "mutable/latest or mock FFmpeg promotion pattern detected"))
    except Exception as exc:
        findings.append(_finding("BLACKHOLE-RUNTIME-007", "Containerfile unreadable", error=repr(exc)))

    try:
        requirements = (root / "apps/blackhole-api/requirements.lock").read_text(encoding="utf-8").splitlines()
        pinned = [line.strip() for line in requirements if line.strip() and not line.lstrip().startswith("#")]
        if not pinned or any(not re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+", line) for line in pinned):
            findings.append(_finding("BLACKHOLE-RUNTIME-008", "Blackhole direct dependencies are not exact-version pinned"))
        names = {line.split("==", 1)[0].lower() for line in pinned if "==" in line}
        if not {"fastapi", "pydantic", "uvicorn"}.issubset(names):
            findings.append(_finding("BLACKHOLE-RUNTIME-009", "required FastAPI runtime dependencies are missing"))
    except Exception as exc:
        findings.append(_finding("BLACKHOLE-RUNTIME-010", "dependency lock unreadable", error=repr(exc)))

    try:
        api_source = (root / "apps/blackhole-api/main.py").read_text(encoding="utf-8")
        admission_index = api_source.find("validate_request(payload, _lease_root())")
        execution_index = api_source.find("prepare_media(")
        if admission_index < 0 or execution_index < 0 or admission_index > execution_index:
            findings.append(_finding("BLACKHOLE-RUNTIME-011", "HRB admission is not provably ordered before media execution"))
        for token in ('ConfigDict(extra="forbid")', "append_event", '"zero_copy_claimed": False'):
            if token not in api_source:
                findings.append(_finding("BLACKHOLE-RUNTIME-012", "API fail-closed invariant missing", token=token))
    except Exception as exc:
        findings.append(_finding("BLACKHOLE-RUNTIME-013", "API source unreadable", error=repr(exc)))

    try:
        audit_source = (root / "src/fa3_audit_chain.py").read_text(encoding="utf-8")
        for token in ("hmac.new", "hmac.compare_digest", "fcntl.flock", "os.fsync"):
            if token not in audit_source:
                findings.append(_finding("BLACKHOLE-RUNTIME-014", "audit-chain integrity primitive missing", token=token))
    except Exception as exc:
        findings.append(_finding("BLACKHOLE-RUNTIME-015", "audit-chain source unreadable", error=repr(exc)))

    for rel in (".github/workflows/fa3-permanent-enforcement.yml", ".github/workflows/fa3-current-host.yml"):
        try:
            workflow = (root / rel).read_text(encoding="utf-8")
            required_pins = (
                f"actions/checkout@{CHECKOUT_SHA}",
                f"actions/setup-python@{SETUP_PYTHON_SHA}",
                f"actions/upload-artifact@{UPLOAD_ARTIFACT_SHA}",
            )
            for token in required_pins:
                if token not in workflow:
                    findings.append(_finding("BLACKHOLE-RUNTIME-016", "touched workflow action is not immutable-SHA pinned", workflow=rel, token=token))
            if "actions/checkout@v4" in workflow or "actions/setup-python@v5" in workflow or "actions/upload-artifact@v4" in workflow:
                findings.append(_finding("BLACKHOLE-RUNTIME-017", "mutable major action tag remains in touched workflow", workflow=rel))
        except Exception as exc:
            findings.append(_finding("BLACKHOLE-RUNTIME-018", "workflow unreadable", workflow=rel, error=repr(exc)))

    report = {
        "schema": "fa3.blackhole-runtime-reference-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "reference_oci_production_claim": False,
        "zero_copy_claimed": False,
        "promotion_effect": "REFERENCE_PASS_DOES_NOT_PROMOTE_BLACKHOLE_COMPONENT",
    }
    _write(root / REFERENCE_REPORT, report)
    return report


def current_host_gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    reference = reference_gate(root)
    findings: list[dict[str, Any]] = []
    if reference.get("result") != "PASS":
        findings.append(_finding("BLACKHOLE-HOST-001", "reference runtime gate failed"))

    try:
        ffmpeg_gate = _load(root / FFMPEG_CURRENT_HOST_GATE_REPORT)
        if ffmpeg_gate.get("result") != "PASS":
            findings.append(_finding("BLACKHOLE-HOST-002", "FFmpeg-AI current-host gate is not PASS"))
    except Exception as exc:
        ffmpeg_gate = {}
        findings.append(_finding("BLACKHOLE-HOST-003", "FFmpeg-AI current-host gate report missing", error=repr(exc)))

    try:
        runtime = _load(root / CURRENT_HOST_REPORT)
        required = {
            "mode": "CURRENT_HOST_PRODUCTION",
            "result": "PASS",
            "rootless": True,
            "runtime_uid": 10002,
            "api_health": "PASS",
            "audit_chain": "PASS",
            "ffmpeg_digest_matches_current_host_receipt": True,
            "zero_copy_claimed": False,
            "production_image_immutable": True,
        }
        for key, expected in required.items():
            if runtime.get(key) != expected:
                findings.append(_finding("BLACKHOLE-HOST-004", "current-host runtime evidence mismatch", field=key, expected=expected, actual=runtime.get(key)))
    except Exception as exc:
        runtime = {}
        findings.append(_finding("BLACKHOLE-HOST-005", "Blackhole current-host runtime report missing", error=repr(exc)))

    report = {
        "schema": "fa3.blackhole-runtime-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "zero_copy_claimed": False,
        "blackhole_component_promotion_allowed": not findings,
        "global_fa3_promotion_claim": False,
    }
    _write(root / "reports/blackhole-runtime-current-host-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Blackhole REST/OCI runtime promotion gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--current-host", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = current_host_gate(root) if args.current_host else reference_gate(root)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
