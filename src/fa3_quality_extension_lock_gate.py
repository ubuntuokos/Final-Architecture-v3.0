#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_audio_preflight_gate import gate as audio_preflight_gate
from fa3_extension_boundary_gate import gate as extension_boundary_gate
from fa3_upstream_lock_gate import gate as upstream_lock_gate


QUALITY_POLICY = Path("canonical/FA3-VOICE-QUALITY-ROUTING-001.json")
DECISION = Path("canonical/decisions/FA3-DEC-QUALITY-EXTENSIONS-PINNING-VALIDATION-2026-09-14.json")
EVIDENCE = Path("evidence/reference/quality-extension-lock-validation-2026-09-14.json")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, str]] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str) -> None:
        checks.append({"name": name, "result": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            findings.append({"check": name, "message": detail})

    ext = extension_boundary_gate(root)
    locks = upstream_lock_gate(root)
    audio = audio_preflight_gate(root)
    check("extension_boundary", ext.get("result") == "PASS", "capability-neutral extension boundary must be fail-closed")
    check("managed_upstream_locks", locks.get("result") == "PASS", "managed immutable upstream lock registry must pass")
    check("layered_audio_preflight", audio.get("result") == "PASS" and audio.get("layer_count") == 6, "six-layer provider-neutral audio preflight must pass")

    quality = _load(root / QUALITY_POLICY)
    eligibility = quality.get("provider_quality_eligibility", {})
    marketing = quality.get("workflow_overrides", {}).get("MARKETING_PRODUCTION", {})
    piper = eligibility.get("FA3-PROVIDER-PIPER-001", [])
    xtts = eligibility.get("FA3-PROVIDER-XTTS-001", [])
    check("piper_retained_basic_standard", "BASIC" in piper and "STANDARD" in piper, "Piper must remain available for BASIC/STANDARD")
    check("piper_denied_production", "PRODUCTION" not in piper and "FA3-PROVIDER-PIPER-001" in marketing.get("forbidden_provider_ids", []), "Piper must be denied for MARKETING_PRODUCTION")
    check("xtts_production_candidate", "PRODUCTION" in xtts and "PREMIUM_CLONING" in xtts, "XTTS must remain eligible for production/cloning quality classes")
    check("silent_quality_downgrade_forbidden", quality.get("routing_policy", {}).get("silent_quality_downgrade_forbidden") is True, "silent quality downgrade must be forbidden")
    check("hrb_required_for_accelerator", quality.get("routing_policy", {}).get("accelerator_execution_requires_hrb_lease") is True, "accelerator voice routing must require HRB lease")

    decision = _load(root / DECISION)
    check("zero_capability_delta", decision.get("new_capabilities") == 0 and decision.get("capability_count_change") == 0, "materialization must not change capability count")
    check("zero_authority_delta", decision.get("new_architectural_authorities") == 0, "materialization must not create architectural authority")

    whisper = (root / "bin/fa3-whisper-bootstrap.sh").read_text(encoding="utf-8")
    demucs = (root / "bin/fa3-demucs-bootstrap.sh").read_text(encoding="utf-8")
    check("whisper_consumes_lock_registry", "FA3-UPSTREAM-LOCK-REGISTRY-001.json" in whisper and 'o["locks"]["whisper"]' in whisper, "Whisper bootstrap must consume central lock registry")
    check("demucs_consumes_lock_registry", "FA3-UPSTREAM-LOCK-REGISTRY-001.json" in demucs and 'o["locks"]["demucs"]' in demucs, "Demucs bootstrap must consume central lock registry")

    evidence = _load(root / EVIDENCE)
    check("evidence_no_false_production_claim", evidence.get("current_host_production_claim") is False and evidence.get("promotion_allowed") is False, "repository materialization evidence must not claim production promotion")

    report = {
        "schema": "fa3.quality-extension-lock-gate-report.v1",
        "gate_id": "FA3-QUALITY-EXTENSION-LOCK-GATESET-001",
        "result": "PASS" if not findings else "FAIL",
        "passed": sum(item["result"] == "PASS" for item in checks),
        "total": len(checks),
        "checks": checks,
        "findings": findings,
        "capability_delta": 0,
        "architectural_authority_delta": 0,
    }
    out = root / "reports/quality-extension-lock-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
