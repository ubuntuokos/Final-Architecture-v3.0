#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REG = Path("canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json")
DELTA = Path("canonical/deltas/FA3-DONOR-VANESSIK-2026-10-03.json")
DOC = Path("docs/donor-vanessik-2026-10-03.md")
TEST = Path("tests/test_donor_vanessik_20261003.py")

PARENT_MAIN = "e5fb23319d57844b6c8b018e06e8f8281d8dc269"
PARENT_REGISTRY_BLOB = "637efbe7aa85079f42f32b597ef19b9b9c239002"
PARENT_COUNT = 1420
RESULT_COUNT = 1421
SOURCE = "https://github.com/Vanessik"

def main() -> None:
    before_registry = json.loads(REG.read_text(encoding="utf-8"))
    before = len(before_registry["entries"])
    if before != PARENT_COUNT:
        raise SystemExit(f"UNEXPECTED_PARENT_ENTRY_COUNT:{before}")
    if before_registry.get("backfill", {}).get("entry_count") != before:
        raise SystemExit("BACKFILL_COUNT_DRIFT_BEFORE_MUTATION")

    cmd = [
        "./bin/fa3-donor-capture",
        "--owner-submitted-link",
        "--owner-donor-marker", "donornak",
        "--name", "Vanessik",
        "--source", SOURCE,
        "--source-kind", "github",
        "--date", "2026-10-03",
        "--discovered-from", "owner:chatgpt:2026-10-03-explicit-vanessik-followup",
        "--tag", "hair-groom",
        "--tag", "profile-discovery",
        "--note", "Owner explicitly approved registration of the corrected Vanessik profile in the follow-up immediately after the prior unresolved malformed submission was reported.",
    ]
    result = json.loads(subprocess.check_output(cmd, text=True))
    if result.get("status") != "ACCEPTED_REFERENCE":
        raise SystemExit(f"UNEXPECTED_STATUS:{result}")
    if not result.get("created"):
        raise SystemExit(f"EXPECTED_NEW_SOURCE:{result}")
    if result.get("normalized_key") != "github:vanessik":
        raise SystemExit(f"UNEXPECTED_NORMALIZED_KEY:{result}")

    after_registry = json.loads(REG.read_text(encoding="utf-8"))
    after = len(after_registry["entries"])
    if after != RESULT_COUNT:
        raise SystemExit(f"UNEXPECTED_RESULT_COUNT:{after}")
    if after_registry.get("backfill", {}).get("entry_count") != after:
        raise SystemExit("BACKFILL_COUNT_NOT_REFRESHED")

    delta = {
        "schema": "fa3.donor-intake-delta.v1",
        "delta_id": "FA3-DONOR-VANESSIK-2026-10-03",
        "target_registry": "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
        "status": "MATERIALIZED_PENDING_EXACT_HEAD_GATES",
        "parent_main": PARENT_MAIN,
        "parent_registry_blob_sha": PARENT_REGISTRY_BLOB,
        "parent_entry_count": PARENT_COUNT,
        "submitted_url_count": 1,
        "unique_source_count": 1,
        "new_source_count": 1,
        "resulting_entry_count": RESULT_COUNT,
        "capability_baseline": 175,
        "capability_delta": 0,
        "authority_delta": 0,
        "usage_edges_created": 0,
        "resolves_prior_unresolved_submission": {
            "delta_id": "FA3-DONOR-HAIR-GROOM-SOURCES-2026-10-03",
            "submitted": "https://github.com/Vanessi k",
            "corrected_candidate": SOURCE,
            "resolution": "NEW_EXPLICIT_OWNER_APPROVAL_AS_SEPARATE_INTAKE",
        },
        "requirements": [
            "The corrected Vanessik URL is explicitly approved by the owner as a separate donor intake.",
            "The profile is a discovery/reference source only and does not recursively admit child repositories.",
            "Registration does not copy or admit code, models, weights, datasets, providers or runtimes.",
            "License & Rights, provenance, Security, Software Coexistence and Hardware Safety remain fail-closed prerequisites for any later material reuse.",
            "No donor usage edge is created by this intake.",
            "Capability baseline remains 175 and no architectural authority is created.",
        ],
        "sources": [[SOURCE, result["donor_id"]]],
        "serialization_scope": "EXCLUSIVE_DONOR_MAINTENANCE",
        "serialization_order": "OLDEST_OPEN_INTAKE_FIRST",
    }
    DELTA.write_text(json.dumps(delta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "# Vanessik donor intake — 2026-10-03\n\n"
        "## Owner approval\n\n"
        "The owner explicitly approved the corrected source https://github.com/Vanessik as a separate donor intake after the earlier malformed submission https://github.com/Vanessi k had been preserved as unresolved analysis-only provenance.\n\n"
        f"- published parent main: {PARENT_MAIN}\n"
        f"- parent donor registry blob: {PARENT_REGISTRY_BLOB}\n"
        f"- registry: {PARENT_COUNT} -> {RESULT_COUNT}\n"
        f"- donor ID: {result['donor_id']}\n"
        f"- normalized key: {result['normalized_key']}\n"
        "- status: ACCEPTED_REFERENCE\n"
        "- capability baseline: 175\n"
        "- capability delta: 0\n"
        "- architectural authority delta: 0\n"
        "- donor usage edges created: 0\n\n"
        "## Boundary\n\n"
        "Vanessik is registered as a GitHub profile-discovery reference. This does not recursively admit repositories under the profile and does not authorize code/model/dataset/runtime/provider adoption.\n\n"
        "Any later reuse remains subject to source-specific provenance, License & Rights, Security, Software Coexistence, Hardware Safety/model-runtime review, and explicit donor usage-edge registration.\n",
        encoding="utf-8",
    )

    expected_id = repr(result["donor_id"])
    test_source = """import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-VANESSIK-2026-10-03.json"
DONOR_ID = __DONOR_ID__


class VanessikDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.by_id = {row["donor_id"]: row for row in cls.registry["entries"]}

    def test_append_only_registry_and_historical_delta(self):
        entries = self.registry["entries"]
        self.assertEqual(self.registry["backfill"]["entry_count"], len(entries))
        self.assertGreaterEqual(len(entries), self.delta["resulting_entry_count"])
        self.assertEqual(self.delta["parent_entry_count"], 1420)
        self.assertEqual(self.delta["new_source_count"], 1)
        self.assertEqual(self.delta["resulting_entry_count"], 1421)
        self.assertEqual(self.delta["capability_baseline"], 175)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)
        self.assertEqual(self.delta["usage_edges_created"], 0)

    def test_vanessik_is_reference_only(self):
        row = self.by_id[DONOR_ID]
        self.assertEqual(row["source"]["normalized_key"], "github:vanessik")
        self.assertEqual(row["source"]["locator"], "https://github.com/Vanessik")
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
            self.assertFalse(row[flag], (DONOR_ID, flag))
        self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")

    def test_prior_unresolved_submission_is_resolved_by_new_approval(self):
        resolution = self.delta["resolves_prior_unresolved_submission"]
        self.assertEqual(resolution["delta_id"], "FA3-DONOR-HAIR-GROOM-SOURCES-2026-10-03")
        self.assertEqual(resolution["corrected_candidate"], "https://github.com/Vanessik")
        self.assertEqual(resolution["resolution"], "NEW_EXPLICIT_OWNER_APPROVAL_AS_SEPARATE_INTAKE")


if __name__ == "__main__":
    unittest.main()
""".replace("__DONOR_ID__", expected_id)
    TEST.write_text(test_source, encoding="utf-8")

    print(json.dumps({
        "parent_entry_count": before,
        "created": 1,
        "resulting_entry_count": after,
        "donor_id": result["donor_id"],
        "normalized_key": result["normalized_key"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
