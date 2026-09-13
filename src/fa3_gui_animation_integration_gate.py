#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    failures: list[str] = []
    profile_path = ROOT / "canonical/profiles/FA3-GUI-SETTINGS-001.json"
    contract_path = ROOT / "canonical/contracts/FA3-GUI-SETTINGS-CONTRACTS-001.json"
    panel_path = ROOT / "apps/fa3-control-center/qml/AnimationIntegrationPanel.qml"
    shell_path = ROOT / "apps/fa3-control-center/qml/AnimationAwareAppShell.qml"
    cmake_path = ROOT / "apps/fa3-control-center/CMakeLists.txt"
    main_path = ROOT / "apps/fa3-control-center/src/main.cpp"

    for path in [profile_path, contract_path, panel_path, shell_path, cmake_path, main_path]:
        if not path.exists():
            failures.append(f"missing:{path.relative_to(ROOT)}")
    if failures:
        return failures

    profile = load_json(profile_path)
    contract = load_json(contract_path)
    expected = ["OpenToonz", "Krita", "Synfig Studio"]

    if profile.get("capability_count") != 143:
        failures.append("capability-count")
    if profile.get("new_architectural_authority") is not False:
        failures.append("new-authority")
    if profile.get("integration_defaults", {}).get("animation") != expected:
        failures.append("profile-animation-integrations")
    if "ANIMATION_INTEGRATION_PREFERENCE_DOES_NOT_IMPLY_PROVIDER_ADMISSION" not in profile.get("invariants", []):
        failures.append("profile-animation-preference-boundary")

    if contract.get("integration_roles", {}).get("animation") != expected:
        failures.append("contract-animation-integrations")
    animation = contract.get("animation_integration", {})
    if animation.get("canonical_profile_reference") != "FA3-ANIMATION-PRODUCTION-001":
        failures.append("animation-profile-reference")
    if animation.get("provider_admission_implied") is not False:
        failures.append("provider-admission-boundary")
    if animation.get("krita_graphics_and_animation_roles_may_coexist") is not True:
        failures.append("krita-dual-role")

    panel = panel_path.read_text(encoding="utf-8")
    for token in [
        "OpenToonz", "Krita", "Synfig Studio", "integrations/animationEditor",
        "integrations/opentoonzEnabled", "integrations/kritaAnimationEnabled",
        "integrations/synfigStudioEnabled", "FA3-ANIMATION-PRODUCTION-001",
    ]:
        if token not in panel:
            failures.append(f"panel-missing:{token}")

    shell = shell_path.read_text(encoding="utf-8")
    for token in ["LanguageAwareAppShell", "AnimationIntegrationPanel", "indexForKey(\"integrations\")"]:
        if token not in shell:
            failures.append(f"shell-missing:{token}")

    cmake = cmake_path.read_text(encoding="utf-8")
    for token in ["AnimationAwareAppShell.qml", "AnimationIntegrationPanel.qml"]:
        if token not in cmake:
            failures.append(f"cmake-missing:{token}")

    main = main_path.read_text(encoding="utf-8")
    if "AnimationAwareAppShell.qml" not in main:
        failures.append("main-animation-shell-not-loaded")

    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("FA3 GUI Animation Integration Gate: FAIL")
        for failure in failures:
            print(" -", failure)
        return 1
    print("FA3 GUI Animation Integration Gate: PASS")
    print("animation=OpenToonz/Krita/Synfig Studio capabilities=143 new_authorities=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
