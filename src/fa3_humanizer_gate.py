#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

CAPABILITY_COUNT = 175
PROFILE = "FA3-HUMANIZATION-FABRIC-001"
CAPABILITY = "CAP-125"

REQUIRED = [
    "canonical/profiles/FA3-HUMANIZATION-FABRIC-001.json",
    "canonical/contracts/FA3-HUMANIZATION-CONTRACTS-001.json",
    "canonical/intents/FA3-HUMANIZATION-APPLICATION-INTENT-001.json",
    "canonical/assessments/FA3-HUMANIZATION-REUSE-ASSESSMENT-001.json",
    "canonical/decisions/FA3-DEC-HUMANIZATION-SHARED-FABRIC-2026-09-30.json",
    "canonical/FA3-HUMANIZER-UI-BINDINGS-001.json",
    "canonical/FA3-HUMANIZER-CURRENT-HOST-001.json",
    "canonical/humanizer-enforcement.json",
    "apps/shared/humanizer/HumanizerSettingsService.h",
    "apps/shared/humanizer/HumanizerSettingsService.cpp",
    "apps/shared/humanizer/qml/HumanizerSettingsPanel.qml",
    "apps/fa3-humanizer/CMakeLists.txt",
    "apps/fa3-humanizer/qml/Main.qml",
    "apps/fa3-humanizer/src/main.cpp",
]

def load(root: Path, rel: str):
    return json.loads((root / rel).read_text(encoding="utf-8"))

def gate(root: Path) -> dict:
    findings = []
    for rel in REQUIRED:
        if not (root / rel).is_file():
            findings.append({"code":"HUM-001","message":"required file missing","path":rel})
    if findings:
        return {"schema":"fa3.humanizer-gate-report.v1","result":"FAIL","findings":findings}

    profile = load(root, REQUIRED[0])
    contracts = load(root, REQUIRED[1])
    reuse = load(root, REQUIRED[3])
    bindings = load(root, REQUIRED[5])
    current = load(root, REQUIRED[6])
    enforcement = load(root, REQUIRED[7])

    if profile.get("id") != PROFILE or profile.get("capability_bindings") != [CAPABILITY]:
        findings.append({"code":"HUM-002","message":"profile/capability binding drift"})
    for name, row in {
        "profile": profile,
        "contracts": contracts,
        "current": current,
        "enforcement": enforcement,
    }.items():
        if row.get("capability_count") != CAPABILITY_COUNT:
            findings.append({"code":"HUM-003","message":"capability baseline drift","source":name})

    if profile.get("architectural_authority") is not False or profile.get("capability_delta") != 0:
        findings.append({"code":"HUM-004","message":"Humanizer gained authority or capability delta"})
    if not profile.get("deterministic_ai_off_path_required"):
        findings.append({"code":"HUM-005","message":"AI-OFF path not mandatory"})
    if not profile.get("direct_provider_calls_forbidden") or not profile.get("silent_fallback_forbidden"):
        findings.append({"code":"HUM-006","message":"provider/silent-fallback boundary weakened"})

    if reuse.get("result") != "PASS" or reuse.get("donor_count") != 1233:
        findings.append({"code":"HUM-007","message":"Reuse Assessment missing exact published registry review"})
    if reuse.get("adopted_donors") != []:
        findings.append({"code":"HUM-008","message":"unexpected donor runtime adoption"})

    if bindings.get("duplicate_settings_core_forbidden") is not True:
        findings.append({"code":"HUM-009","message":"shared settings duplicate guard missing"})

    if current.get("physical_current_host_pass_claim") is not False:
        findings.append({"code":"HUM-010","message":"physical Current Host PASS was invented"})
    if current.get("host_requalification_required_now") is not True:
        findings.append({"code":"HUM-011","message":"Current Host requalification not required for new GUI/runtime"})

    code = (root / "apps/shared/humanizer/HumanizerSettingsService.cpp").read_text(encoding="utf-8")
    forbidden = ["QNetwork", "api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com"]
    for token in forbidden:
        if token in code:
            findings.append({"code":"HUM-012","message":"direct provider/network dependency found","token":token})
    required_tokens = [
        "DENIED_AI_DISABLED",
        "ROUTE_REQUIRED_NOT_EXECUTED",
        "model_router_required",
        "uaf_required",
        "hrb_required_for_execution",
        "QSettings::UserScope",
    ]
    for token in required_tokens:
        if token not in code:
            findings.append({"code":"HUM-013","message":"shared runtime invariant missing","token":token})

    app_cmake = (root / "apps/fa3-humanizer/CMakeLists.txt").read_text(encoding="utf-8")
    app_qml = (root / "apps/fa3-humanizer/qml/Main.qml").read_text(encoding="utf-8")
    if "../shared/humanizer/qml/HumanizerSettingsPanel.qml" not in app_cmake:
        findings.append({"code":"HUM-014","message":"standalone app does not package shared settings panel"})
    if "HumanizerSettingsPanel" not in app_qml:
        findings.append({"code":"HUM-015","message":"standalone app does not consume shared settings panel"})

    expected_rules = {f"HUM-{i:03d}" for i in range(1, 11)}
    actual_rules = {r.split("_",1)[0] for r in enforcement.get("rules", [])}
    if expected_rules != actual_rules:
        findings.append({"code":"HUM-016","message":"enforcement rule set drift"})

    return {
        "schema":"fa3.humanizer-gate-report.v1",
        "profile_id":PROFILE,
        "capability_id":CAPABILITY,
        "capability_count":CAPABILITY_COUNT,
        "result":"PASS" if not findings else "FAIL",
        "findings":findings,
        "runtime_promotion_claim":False,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
