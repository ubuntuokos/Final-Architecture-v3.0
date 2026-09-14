#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_marketing_security import run_security_regressions

GATE_ID = "FA3-MARKETING-SECURITY-GATESET-001"
PROFILE_ID = "FA3-MARKETING-001"
VOICE_PROFILE_ID = "FA3-VOICE-001"
CONTRACT_ID = "FA3-MARKETING-SECURITY-CONTRACTS-001"
EVIDENCE_PATH = "evidence/reference/marketing-security-ci-2026-09-14.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    contract_path = root / "canonical/contracts/FA3-MARKETING-SECURITY-CONTRACTS-001.json"
    enforcement_path = root / "canonical/marketing-security-enforcement.json"
    marketing_path = root / "canonical/profiles/FA3-MARKETING-001.json"
    voice_path = root / "canonical/profiles/FA3-VOICE-001.json"
    voice_contract_path = root / "canonical/contracts/FA3-VOICE-CONTRACTS-001.json"
    evidence_path = root / EVIDENCE_PATH
    for code, path in (
        ("MKTSEC-CANON-001", contract_path),
        ("MKTSEC-CANON-002", enforcement_path),
        ("MKTSEC-CANON-003", marketing_path),
        ("MKTSEC-CANON-004", voice_path),
        ("MKTSEC-CANON-005", voice_contract_path),
        ("MKTSEC-CANON-006", evidence_path),
    ):
        if not path.is_file():
            findings.append({"code": code, "severity": "P0", "message": f"Missing artifact: {path.relative_to(root)}"})

    if not findings:
        contract = _load(contract_path)
        enforcement = _load(enforcement_path)
        marketing = _load(marketing_path)
        voice = _load(voice_path)
        voice_contract = _load(voice_contract_path)
        evidence = _load(evidence_path)
        if contract.get("id") != CONTRACT_ID or contract.get("profile_id") != PROFILE_ID or contract.get("provider_neutral") is not True:
            findings.append({"code":"MKTSEC-CANON-010","severity":"P0","message":"Marketing security contract identity/provider-neutrality drift"})
        if contract.get("voice_governance", {}).get("voice_contract_id") != "FA3-VOICE-CONTRACTS-001":
            findings.append({"code":"MKTSEC-CANON-011","severity":"P0","message":"Marketing security no longer delegates voice consent to Voice Fabric"})
        if contract.get("voice_governance", {}).get("revoked_consent_blocks_all_cloning_fallback") is not True:
            findings.append({"code":"MKTSEC-CANON-012","severity":"P0","message":"Revoked voice consent no longer blocks cloning fallback"})
        if contract.get("suppression", {}).get("backend_unavailable_fail_closed") is not True:
            findings.append({"code":"MKTSEC-CANON-013","severity":"P0","message":"Suppression backend outage is not fail-closed"})
        if marketing.get("id") != PROFILE_ID or voice.get("id") != VOICE_PROFILE_ID:
            findings.append({"code":"MKTSEC-CANON-014","severity":"P0","message":"Parent profile identity drift"})
        consent_rules = voice_contract.get("contracts", {}).get("consent", {}).get("rules", [])
        if not any("revoked consent MUST fail closed" in rule for rule in consent_rules):
            findings.append({"code":"MKTSEC-CANON-015","severity":"P0","message":"Voice consent revocation fail-closed rule missing"})
        if enforcement.get("gate_id") != GATE_ID or enforcement.get("fail_closed") is not True or enforcement.get("regression_case_count") != 28:
            findings.append({"code":"MKTSEC-CANON-016","severity":"P0","message":"Marketing security enforcement drift"})
        if evidence.get("status") != "PASS" or evidence.get("current_host_runtime_claim") is not False:
            findings.append({"code":"MKTSEC-CANON-017","severity":"P0","message":"Reference evidence boundary drift"})

    regressions = run_security_regressions()
    ok = not findings and regressions["result"] == "PASS"
    report = {
        "schema": "fa3.marketing-security-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if ok else "FAIL",
        "findings": findings,
        "regressions": regressions,
        "current_host_runtime_claim": False,
    }
    _write(root / "reports/marketing-security-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
