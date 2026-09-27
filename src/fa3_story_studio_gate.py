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
    "canonical/assessments/FA3-STORY-STUDIO-DECISION-ASSESSMENT-2026-09-27.json",
    "canonical/decisions/FA3-DEC-STORY-STUDIO-UNIFIED-2026-09-27.json",
    "canonical/story-studio-enforcement.json",
    "canonical/enforcement-policy.json",
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
    decision_assessment = loadj(root / "canonical/assessments/FA3-STORY-STUDIO-DECISION-ASSESSMENT-2026-09-27.json")
    enforcement = loadj(root / "canonical/story-studio-enforcement.json")
    policy = loadj(root / "canonical/enforcement-policy.json")
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
        (profile.get("presentation_interop", {}).get("capability") == "CAP-018", "presentation-capability"),
        (profile.get("presentation_interop", {}).get("optional_generation_provider") == "FA3-PROVIDER-PRESENTON-001", "presentation-provider"),
        (profile.get("presentation_interop", {}).get("silent_story_mutation_from_slides_forbidden") is True, "presentation-no-silent-writeback"),
        ("DUBBING_LOCALIZATION" in profile.get("production_profiles", []), "dubbing-profile"),
        (profile.get("dubbing_localization", {}).get("frame_accurate_timing_required") is True, "dubbing-timing"),
        (profile.get("dubbing_localization", {}).get("final_as_recorded_script_must_match_delivered_audio") is True, "dubbing-as-recorded"),
        (profile.get("spoiler_derivatives", {}).get("status") == "MANDATORY", "spoiler-mandatory"),
        (profile.get("spoiler_derivatives", {}).get("source_node_lineage_required") is True, "spoiler-lineage"),
        (profile.get("spoiler_derivatives", {}).get("cross_branch_detail_mixing_forbidden") is True, "spoiler-branch-isolation"),
        (profile.get("spoiler_derivatives", {}).get("external_publication_requires_release_approval") is True, "spoiler-release-approval"),
        (profile.get("trailer_teaser_derivatives", {}).get("status") == "MANDATORY", "trailer-mandatory"),
        (profile.get("trailer_teaser_derivatives", {}).get("spoiler_ceiling_required") is True, "trailer-spoiler-ceiling"),
        (profile.get("trailer_teaser_derivatives", {}).get("source_node_lineage_required") is True, "trailer-lineage"),
        (profile.get("trailer_teaser_derivatives", {}).get("generated_visuals_must_be_marked_as_generated_or_previs") is True, "trailer-generated-label"),
        (profile.get("trailer_teaser_derivatives", {}).get("editorial_handoff") == "OTIO_KDENLIVE", "trailer-otio"),
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
        (set(decision_assessment.get("covered_ids", [])) >= {"FA3-STORY-001", "FA3-STORY-STUDIO-001"}, "decision-assessment-covered"),
        (decision_assessment.get("project_radar_checked") is True, "decision-project-radar"),
        (enforcement.get("fail_closed") is True, "fail-closed"),
        ("FA3-STORY-STUDIO-GATESET-001" in policy.get("mandatory_reference_gates", []), "global-policy-gate-binding"),
        (policy.get("story_studio_capability_bindings") == ["CAP-014", "CAP-017", "CAP-018", "CAP-041", "CAP-168", "CAP-170", "CAP-171", "CAP-172", "CAP-173"], "global-policy-capability-bindings"),
        (policy.get("story_studio_mandatory_p0_rules") == enforcement.get("rules"), "global-policy-p0-rules"),
        (enforcement.get("current_host_runtime_promotion_claim") is False, "no-runtime-overclaim"),
    ]
    for ok, code in checks:
        if not ok:
            failures.append(code)

    for token in [
        "FA3 Story Studio", "Production Profile", "Collaboration", "Final Publisher",
        "Story Branches", "Rejected / Stash", "Writer Goals", "Interchange",
        "Presentation Layer", "Dubbing / ADR Script", "Teaser / Trailer", "Spoiler / Recap", "Final Publisher",
        "Feature Film", "TV Series", "Commercial", "Live Broadcast", "Dubbing / Localization",
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
