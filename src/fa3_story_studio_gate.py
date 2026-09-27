#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fa3_story_studio import (
    PRODUCTION_PROFILES,
    RELEASE_POLICIES,
    new_reference_project,
    validate_project,
)

REQUIRED_FILES = [
    "canonical/profiles/FA3-STORY-STUDIO-001.json",
    "canonical/contracts/FA3-STORY-STUDIO-CONTRACTS-001.json",
    "canonical/intents/FA3-STORY-STUDIO-APPLICATION-INTENT-001.json",
    "canonical/assessments/FA3-STORY-STUDIO-REUSE-ASSESSMENT-001.json",
    "canonical/decisions/FA3-DEC-STORY-STUDIO-UNIFIED-2026-09-27.json",
    "canonical/story-studio-enforcement.json",
    "apps/fa3-control-center/qml/StoryStudioPage.qml",
    "src/fa3_story_studio.py",
]


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: Path) -> list[str]:
    failures: list[str] = []
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            failures.append(f"missing:{rel}")
    if failures:
        return failures

    profile = loadj(root / REQUIRED_FILES[0])
    contract = loadj(root / REQUIRED_FILES[1])
    intent = loadj(root / REQUIRED_FILES[2])
    assessment = loadj(root / REQUIRED_FILES[3])
    enforcement = loadj(root / "canonical/story-studio-enforcement.json")
    qml = (root / "apps/fa3-control-center/qml/StoryStudioPage.qml").read_text(encoding="utf-8")

    checks = [
        (profile.get("id") == "FA3-STORY-STUDIO-001", "profile-id"),
        (profile.get("capability_count") == 175, "capability-count"),
        (profile.get("new_capability") is False, "new-capability"),
        (profile.get("new_architectural_authority") is False, "new-authority"),
        (profile.get("application_surface", {}).get("separate_application_forbidden") is True, "single-app"),
        (set(profile.get("production_profiles", [])) == PRODUCTION_PROFILES, "production-profiles"),
        (profile.get("collaboration", {}).get("concurrent_multi_author_editing_required") is True, "collaboration"),
        (profile.get("collaboration", {}).get("designated_final_publishers_required") is True, "final-publisher"),
        (set(profile.get("collaboration", {}).get("release_policies", [])) == RELEASE_POLICIES, "release-policies"),
        (profile.get("rejected_content", {}).get("save_as_note_required") is True, "stash-note"),
        (profile.get("interchange", {}).get("import_export_symmetry_required") is True, "codec-symmetry"),
        (profile.get("hardware_audit", {}).get("cpu_only_core_required") is True, "cpu-only"),
        (contract.get("id") == "FA3-STORY-STUDIO-CONTRACTS-001", "contract-id"),
        ("MULTI_AUTHOR_ATTRIBUTION_REQUIRED" in contract.get("invariants", []), "author-attribution"),
        ("FINAL_PUBLISHER_MUST_BE_EXPLICITLY_DESIGNATED" in contract.get("invariants", []), "publisher-invariant"),
        ("REJECTED_CONTENT_RECOVERABLE_AND_EXPORTABLE_AS_NOTE" in contract.get("invariants", []), "stash-invariant"),
        ("STALE_CONCURRENT_EDIT_MUST_FAIL_CLOSED" in contract.get("invariants", []), "concurrent-edit-conflict"),
        (contract.get("collaboration", {}).get("silent_last_writer_wins") is False, "no-silent-last-writer-wins"),
        (intent.get("declared_new_capabilities") == [], "intent-capabilities"),
        (assessment.get("result") == "PASS", "reuse-assessment"),
        (enforcement.get("fail_closed") is True, "fail-closed"),
        (enforcement.get("current_host_runtime_promotion_claim") is False, "no-runtime-overclaim"),
    ]
    for ok, code in checks:
        if not ok:
            failures.append(code)

    for token in [
        "FA3 Story Studio", "Production Profile", "Collaboration", "Final Publisher",
        "Story Branches", "Rejected / Stash", "Writer Goals", "Interchange",
        "Feature Film", "TV Series", "Commercial", "Live Broadcast",
    ]:
        if token not in qml:
            failures.append(f"qml:{token}")

    try:
        validate_project(new_reference_project())
    except Exception as exc:
        failures.append(f"reference-project:{exc}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    failures = validate(Path(args.root).resolve())
    if failures:
        print("FA3 Story Studio gate: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("FA3 Story Studio gate: PASS")
    print("capabilities=175 new_capabilities=0 new_authorities=0 current_host_runtime_promotion=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
