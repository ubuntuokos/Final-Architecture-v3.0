#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REG = Path("canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json")
DELTA = Path("canonical/deltas/FA3-DONOR-HAIR-GROOM-SOURCES-2026-10-03.json")
DOC = Path("docs/donor-hair-groom-sources-2026-10-03.md")
TEST = Path("tests/test_donor_hair_groom_sources_20261003.py")

PARENT_MAIN = "0a5641204c6f8caaf65e2e4bfc4af928b5579d54"
PARENT_REGISTRY_BLOB = "ee3a274e842471a3362c343f1ffa2eee935f85f0"
PARENT_COUNT = 1405
RESULT_COUNT = 1421

SOURCES = [
    {"submitted": "https://github.com/kyleolsz", "url": "https://github.com/kyleolsz", "name": "kyleolsz", "kind": "github", "class": "profile-discovery"},
    {"submitted": "https://github.com/facebookresearch/iphg", "url": "https://github.com/facebookresearch/iphg", "name": "facebookresearch/iphg", "kind": "github", "class": "repository-reference"},
    {"submitted": "https://github.com/SamurAIGPT/ai-hair-style-simulator", "url": "https://github.com/SamurAIGPT/ai-hair-style-simulator", "name": "SamurAIGPT/ai-hair-style-simulator", "kind": "github", "class": "repository-reference"},
    {"submitted": "https://github.com/facebookresearch/CT2Hair", "url": "https://github.com/facebookresearch/CT2Hair", "name": "facebookresearch/CT2Hair", "kind": "github", "class": "repository-reference"},
    {
        "submitted": "https://github.com/Vanessi k",
        "url": "https://github.com/Vanessik",
        "name": "Vanessik",
        "kind": "github",
        "class": "profile-discovery",
        "note": "Owner-submitted locator contained a space; resolved and verified as https://github.com/Vanessik before canonical registration.",
    },
    {"submitted": "https://haiminluo.github.io/hairgpt/", "url": "https://haiminluo.github.io/hairgpt/", "name": "HairGPT", "kind": "reference", "class": "research-project"},
    {"submitted": "https://github.com/c-he", "url": "https://github.com/c-he", "name": "c-he", "kind": "github", "class": "profile-discovery"},
    {"submitted": "https://github.com/MengZephyr", "url": "https://github.com/MengZephyr", "name": "MengZephyr", "kind": "github", "class": "profile-discovery"},
    {"submitted": "https://github.com/Xiaojiu-z", "url": "https://github.com/Xiaojiu-z", "name": "Xiaojiu-z", "kind": "github", "class": "profile-discovery"},
    {"submitted": "https://github.com/cychungg", "url": "https://github.com/cychungg", "name": "cychungg", "kind": "github", "class": "profile-discovery"},
    {"submitted": "https://github.com/AIRI-Institute", "url": "https://github.com/AIRI-Institute", "name": "AIRI-Institute", "kind": "github", "class": "organization-discovery"},
    {"submitted": "https://github.com/jin-cao-tma", "url": "https://github.com/jin-cao-tma", "name": "jin-cao-tma", "kind": "github", "class": "profile-discovery"},
    {"submitted": "https://github.com/yimin-pan", "url": "https://github.com/yimin-pan", "name": "yimin-pan", "kind": "github", "class": "profile-discovery"},
    {"submitted": "https://chufengxiao.github.io/SketchHairSalon/", "url": "https://chufengxiao.github.io/SketchHairSalon/", "name": "SketchHairSalon", "kind": "reference", "class": "research-project"},
    {"submitted": "https://github.com/topics/hair-color", "url": "https://github.com/topics/hair-color", "name": "github-topic-hair-color", "kind": "github", "class": "topic-discovery"},
    {"submitted": "https://github.com/deepmancer", "url": "https://github.com/deepmancer", "name": "deepmancer", "kind": "github", "class": "profile-discovery"},
]


def capture(row: dict[str, str]) -> dict:
    command = [
        "./bin/fa3-donor-capture",
        "--owner-submitted-link",
        "--owner-donor-marker",
        "donornak",
        "--name",
        row["name"],
        "--source",
        row["url"],
        "--source-kind",
        row["kind"],
        "--date",
        "2026-10-03",
        "--discovered-from",
        "owner:chatgpt:2026-10-03-hair-groom-donor-batch",
        "--tag",
        "hair-groom",
        "--tag",
        row["class"],
    ]
    if row.get("note"):
        command += ["--note", row["note"]]
    result = json.loads(subprocess.check_output(command, text=True))
    if result.get("status") != "ACCEPTED_REFERENCE":
        raise SystemExit(f"UNEXPECTED_STATUS:{row['url']}:{result}")
    return result


def main() -> None:
    registry_before = json.loads(REG.read_text(encoding="utf-8"))
    before = len(registry_before["entries"])
    if before != PARENT_COUNT:
        raise SystemExit(f"UNEXPECTED_PARENT_ENTRY_COUNT:{before}")
    if registry_before.get("backfill", {}).get("entry_count") != before:
        raise SystemExit("BACKFILL_COUNT_DRIFT_BEFORE_MUTATION")

    results = []
    for source in SOURCES:
        results.append({**source, **capture(source)})

    created = sum(1 for row in results if row.get("created"))
    if created != 16:
        collisions = [
            {"url": row["url"], "donor_id": row["donor_id"], "created": row["created"]}
            for row in results
            if not row.get("created")
        ]
        raise SystemExit("EXPECTED_16_NEW_SOURCES:" + json.dumps(collisions, ensure_ascii=False))

    normalized_keys = [row["normalized_key"] for row in results]
    if len(set(normalized_keys)) != 16:
        raise SystemExit("NORMALIZED_SOURCE_COLLISION")

    registry_after = json.loads(REG.read_text(encoding="utf-8"))
    after = len(registry_after["entries"])
    if after != RESULT_COUNT:
        raise SystemExit(f"UNEXPECTED_RESULT_COUNT:{after}")
    if registry_after.get("backfill", {}).get("entry_count") != after:
        raise SystemExit("BACKFILL_COUNT_NOT_REFRESHED")

    delta = {
        "schema": "fa3.donor-intake-delta.v1",
        "delta_id": "FA3-DONOR-HAIR-GROOM-SOURCES-2026-10-03",
        "target_registry": "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
        "status": "MATERIALIZED_PENDING_EXACT_HEAD_GATES",
        "parent_main": PARENT_MAIN,
        "parent_registry_blob_sha": PARENT_REGISTRY_BLOB,
        "parent_entry_count": PARENT_COUNT,
        "submitted_url_count": 16,
        "duplicate_submission_count": 0,
        "canonical_alias_collapse_count": 0,
        "source_resolution_count": 1,
        "unique_source_count": 16,
        "new_source_count": created,
        "resulting_entry_count": after,
        "capability_baseline": 175,
        "capability_delta": 0,
        "authority_delta": 0,
        "usage_edges_created": 0,
        "source_resolutions": [
            {
                "submitted": "https://github.com/Vanessi k",
                "canonical": "https://github.com/Vanessik",
                "reason": "MALFORMED_WHITESPACE_LOCATOR_RESOLVED_TO_VERIFIED_PROFILE",
            }
        ],
        "requirements": [
            "All owner-marked links are reference-registration metadata only.",
            "GitHub profile, organization and topic pages are discovery indexes and do not recursively admit child repositories.",
            "Concrete repositories and research project pages do not imply code, model, weight, dataset, provider or runtime admission.",
            "License and rights remain fail-closed for material reuse; UNKNOWN or non-commercial/research-only terms block source copying until reviewed.",
            "GPU/CUDA-oriented upstream implementations cannot become mandatory because FA3 retains CPU-only viability and Hardware Safety governance.",
            "No donor usage edge is created by this intake.",
            "Capability baseline remains 175 and no architectural authority is created.",
        ],
        "sources": [[row["url"], row["donor_id"]] for row in results],
        "submitted_sources": [[row["submitted"], row["donor_id"]] for row in results],
        "serialization_scope": "EXCLUSIVE_DONOR_MAINTENANCE",
        "serialization_order": "OLDEST_OPEN_INTAKE_FIRST",
    }
    DELTA.parent.mkdir(parents=True, exist_ok=True)
    DELTA.write_text(json.dumps(delta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Hair / Groom donor intake — 2026-10-03",
        "",
        "## Owner-marked intake",
        "",
        "The owner explicitly marked **16 submitted sources** as `donornak`.",
        "",
        f"- published parent main: `{PARENT_MAIN}`",
        f"- parent donor registry blob: `{PARENT_REGISTRY_BLOB}`",
        f"- registry: **{PARENT_COUNT} → {after}**",
        "- capability baseline: **175**",
        "- capability delta: **0**",
        "- architectural authority delta: **0**",
        "- donor usage edges created: **0**",
        "",
        "All 16 records are metadata/reference-only `ACCEPTED_REFERENCE` entries.",
        "",
        "## Canonical source resolution",
        "",
        "The submitted `https://github.com/Vanessi k` locator contained whitespace and is not a valid GitHub URL. "
        "It is preserved in intake provenance and canonically registered as the verified profile `https://github.com/Vanessik`.",
        "",
        "## Sources",
        "",
        "| Submitted source | Canonical source | Class | Donor ID |",
        "| --- | --- | --- | --- |",
    ]
    for row in results:
        lines.append(
            f"| {row['submitted']} | {row['url']} | {row['class']} | `{row['donor_id']}` |"
        )
    lines += [
        "",
        "## Boundaries",
        "",
        "- GitHub profile, organization and topic pages are **discovery indexes only**; their child repositories are not recursively admitted.",
        "- Repository/project registration does not copy code, weights, datasets or assets and does not install dependencies.",
        "- No model, provider, hosted service, MCP endpoint or runtime is admitted by this intake.",
        "- License & Rights, provenance, Security, Software Coexistence, Hardware Safety/model-runtime review and Universal Capability Access remain mandatory before material reuse.",
        "- Upstream GPU/CUDA requirements may be studied as references but may not replace FA3 CPU-only viability or the Host Resource Broker / Model Router authorities.",
        "- This intake does not create an application donor usage edge; any later adoption must register an explicit usage edge.",
        "",
        "## Relationship to Shared Hair & Groom Fabric",
        "",
        "The open Shared Hair & Groom Fabric work is separate from this registry intake. These newly registered references are not consumed by that pending branch unless a later, separately approved adoption/reconciliation explicitly creates usage edges.",
        "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8")

    expected = [(row["donor_id"], row["normalized_key"], row["url"]) for row in results]
    test_source = f'''import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-HAIR-GROOM-SOURCES-2026-10-03.json"
EXPECTED = {expected!r}


class HairGroomDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.by_id = {{row["donor_id"]: row for row in cls.registry["entries"]}}

    def test_registry_count_and_baseline(self):
        self.assertEqual(len(self.registry["entries"]), 1421)
        self.assertEqual(self.registry["backfill"]["entry_count"], 1421)
        self.assertEqual(self.delta["parent_entry_count"], 1405)
        self.assertEqual(self.delta["new_source_count"], 16)
        self.assertEqual(self.delta["resulting_entry_count"], 1421)
        self.assertEqual(self.delta["capability_baseline"], 175)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)
        self.assertEqual(self.delta["usage_edges_created"], 0)

    def test_expected_sources_are_reference_only(self):
        for donor_id, key, locator in EXPECTED:
            row = self.by_id[donor_id]
            self.assertEqual(row["source"]["normalized_key"], key)
            self.assertEqual(row["source"]["locator"], locator)
            self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
            self.assertFalse(row["authority"])
            for flag in (
                "automatic_selection",
                "automatic_fetch",
                "automatic_install",
                "automatic_activation",
                "automatic_dependency",
                "automatic_code_import",
                "automatic_provider_admission",
                "automatic_model_selection",
            ):
                self.assertFalse(row[flag], (donor_id, flag))
            self.assertEqual(
                row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY"
            )

    def test_submitted_resolution_is_preserved(self):
        resolutions = self.delta["source_resolutions"]
        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0]["submitted"], "https://github.com/Vanessi k")
        self.assertEqual(resolutions[0]["canonical"], "https://github.com/Vanessik")


if __name__ == "__main__":
    unittest.main()
'''
    TEST.write_text(test_source, encoding="utf-8")

    print(json.dumps({
        "parent_entry_count": before,
        "created": created,
        "resulting_entry_count": after,
        "donors": [
            {
                "submitted": row["submitted"],
                "canonical": row["url"],
                "donor_id": row["donor_id"],
                "normalized_key": row["normalized_key"],
            }
            for row in results
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
