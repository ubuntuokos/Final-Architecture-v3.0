#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fa3_stable_audio_3_gate import gate as stable_audio_3_gate

GATE_ID = "FA3-STABILITY-PORTFOLIO-GATESET-001"
PROFILE_ID = "FA3-STABILITY-PORTFOLIO-001"
CONTRACT_ID = "FA3-STABILITY-PORTFOLIO-CONTRACTS-001"
CAPABILITY_COUNT = 143
BLOCKED = {"FA3-PROVIDER-SD35-NVIDIA-NIM-001"}


def loadj(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    profile_path = root / "canonical/profiles/FA3-STABILITY-PORTFOLIO-001.json"
    contract_path = root / "canonical/contracts/FA3-STABILITY-PORTFOLIO-CONTRACTS-001.json"
    nim_path = root / "canonical/providers/FA3-PROVIDER-SD35-NVIDIA-NIM-001.json"
    for p in (profile_path, contract_path, nim_path):
        if not p.is_file():
            findings.append(finding("STAB-FREE-001", "required free-only stability artifact missing", path=str(p)))
    if findings:
        return {"gate_id": GATE_ID, "result": "FAIL", "findings": findings}

    profile = loadj(profile_path)
    contract = loadj(contract_path)
    nim = loadj(nim_path)
    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("economics_policy") == "FA3-FREE-SELF-HOSTED-ONLY-001"
        and profile.get("paid_provider_fallback") is False
    ):
        findings.append(finding("STAB-FREE-002", "Stability profile free-only baseline drift"))
    active = set(profile.get("providers", []))
    if active & BLOCKED:
        findings.append(finding("STAB-FREE-003", "paid NIM provider returned to active Stability portfolio", providers=sorted(active & BLOCKED)))
    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("capability_count") == CAPABILITY_COUNT
        and contract.get("provider_neutral") is True
        and contract.get("economics_policy") == "FA3-FREE-SELF-HOSTED-ONLY-001"
        and contract.get("runtime_policy", {}).get("paid_cloud_fallback") is False
        and contract.get("runtime_policy", {}).get("free_route_required") is True
    ):
        findings.append(finding("STAB-FREE-004", "Stability contract economics/admission drift"))
    if not (
        nim.get("active") is False
        and nim.get("routing_eligible") is False
        and nim.get("production_admission") == "DENY"
        and nim.get("runtime_surface") == "ABSENT"
    ):
        findings.append(finding("STAB-FREE-005", "NVIDIA NIM tombstone became active or routable"))

    for provider_id in sorted(active):
        path = root / f"canonical/providers/{provider_id}.json"
        if not path.is_file():
            findings.append(finding("STAB-FREE-006", "active Stability provider record missing", provider=provider_id))
            continue
        d = loadj(path)
        if any(d.get(k) is not False for k in ("canonical_root", "architectural_authority", "new_capability")) or d.get("capability_count") != CAPABILITY_COUNT:
            findings.append(finding("STAB-FREE-007", "active Stability provider authority/capability drift", provider=provider_id))

    child = stable_audio_3_gate(root)
    if child.get("result") != "PASS":
        findings.append(finding("STAB-FREE-008", "Stable Audio free-only child gate failed", child_gate=child))

    report = {
        "schema": "fa3.stability-portfolio-gate-report.v2",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "contract_id": CONTRACT_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "providers_checked": len(active),
        "paid_provider_fallback": False,
        "stable_audio_3_child_gate_result": child.get("result"),
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
    }
    out = root / "reports/stability-portfolio-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
