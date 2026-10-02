from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_shared_module_pattern_catalogue import validate
from fa3_reuse_catalog import build_catalog

SOURCES = (
    "canonical/FA3-SHARED-MODULE-PATTERN-CATALOGUE-001.json",
    "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
    "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
    "canonical/profiles/FA3-SHARED-AI-INTERACTION-001.json",
    "canonical/contracts/FA3-SHARED-AI-INTERACTION-CONTRACTS-001.json",
    "canonical/profiles/FA3-SHARED-KNOWLEDGE-RETRIEVAL-001.json",
    "canonical/contracts/FA3-SHARED-KNOWLEDGE-RETRIEVAL-CONTRACTS-001.json",
    "canonical/profiles/FA3-SHARED-MULTIMODAL-SOURCE-001.json",
    "canonical/contracts/FA3-SHARED-MULTIMODAL-SOURCE-CONTRACTS-001.json",
    "canonical/profiles/FA3-SHARED-CONVERSATION-SESSION-001.json",
    "canonical/contracts/FA3-SHARED-CONVERSATION-SESSION-CONTRACTS-001.json",
    "canonical/profiles/FA3-SHARED-TOOL-ACTION-MEDIATION-001.json",
    "canonical/contracts/FA3-SHARED-TOOL-ACTION-MEDIATION-CONTRACTS-001.json",
    "canonical/profiles/FA3-SHARED-AGENT-WEB-INTERACTION-001.json",
    "canonical/contracts/FA3-SHARED-AGENT-WEB-INTERACTION-CONTRACTS-001.json",
)

def fixture(root: Path) -> None:
    for rel in SOURCES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)

class SharedModulePatternCatalogueTests(unittest.TestCase):
    def test_canonical_catalogue_passes(self):
        report = validate(ROOT)
        self.assertEqual(report["validation"]["result"], "PASS", report["validation"]["findings"])
        self.assertEqual(report["capability_baseline"], 175)
        self.assertGreaterEqual(report["summary"]["patterns"], 10)
        self.assertGreaterEqual(report["summary"]["shared_module_targets"], 10)

    def test_composite_reference_pattern_is_retained(self):
        catalogue = json.loads((ROOT / SOURCES[0]).read_text())
        row = next(x for x in catalogue["patterns"]
                   if x["id"] == "FA3-MULTIMODAL-ASSISTANT-WORKBENCH-REFERENCE-PATTERN-001")
        self.assertEqual(row["class"], "COMPOSITE_REFERENCE_PATTERN")
        self.assertEqual(row["reuse_status"], "COMPOSITE_REFERENCE")
        self.assertIn("FA3-SHARED-AI-COMPOSITION-PATTERN-001", row["shared_module_ids"])

    def test_analysis_only_sources_require_owner_marker(self):
        catalogue = json.loads((ROOT / SOURCES[0]).read_text())
        self.assertTrue(catalogue["analysis_only_sources"])
        self.assertTrue(all(x["registration_status"] == "OWNER_MARKER_REQUIRED"
                            for x in catalogue["analysis_only_sources"]))
        self.assertTrue(all("donor_id" not in x for x in catalogue["analysis_only_sources"]))

    def test_canonical_donor_references_resolve(self):
        report = validate(ROOT)
        unknown = [x for x in report["validation"]["findings"]
                   if x["code"] == "UNKNOWN_CANONICAL_DONOR"]
        self.assertEqual(unknown, [])

    def test_reuse_discovery_indexes_patterns_not_analysis_sources(self):
        reuse = build_catalog(ROOT)
        by_id = {row["candidate_id"]: row for row in reuse["entries"]}
        pattern_id = "FA3-MULTIMODAL-ASSISTANT-WORKBENCH-REFERENCE-PATTERN-001"
        self.assertEqual(by_id[pattern_id]["candidate_class"], "SHARED_MODULE_PATTERN")
        self.assertFalse(by_id[pattern_id]["analysis_sources_are_donors"])
        self.assertNotIn("ANALYSIS-IMMICH", by_id)

    def test_exact_six_materialized_shared_components(self):
        report = validate(ROOT)
        self.assertEqual(report["validation"]["result"], "PASS",
                         report["validation"]["findings"])
        self.assertEqual(report["summary"]["materialized_shared_components"], 6)
        catalogue = json.loads((ROOT / SOURCES[0]).read_text())
        self.assertEqual(
            {row["id"] for row in catalogue["materialized_shared_components"]},
            {
                "FA3-SHARED-AI-INTERACTION-001",
                "FA3-SHARED-KNOWLEDGE-RETRIEVAL-001",
                "FA3-SHARED-MULTIMODAL-SOURCE-001",
                "FA3-SHARED-CONVERSATION-SESSION-001",
                "FA3-SHARED-TOOL-ACTION-MEDIATION-001",
                "FA3-SHARED-AGENT-WEB-INTERACTION-001",
            },
        )

    def test_materialized_profile_contract_binding_parity_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            path = root / "canonical/profiles/FA3-SHARED-AI-INTERACTION-001.json"
            profile = json.loads(path.read_text())
            profile["capability_bindings"].append("CAP-176")
            path.write_text(json.dumps(profile), encoding="utf-8")
            findings = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn("MATERIALIZED_COMPONENT_BINDING_PARITY_INVALID", findings)
            self.assertIn("MATERIALIZED_COMPONENT_CAPABILITY_ID_OUT_OF_BASELINE", findings)

    def test_materialized_app_link_cannot_manual_bind_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            path = root / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
            links = json.loads(path.read_text())
            links["shared_capabilities"][0]["fa3_bindings"]["capability_ids"] = ["CAP-005"]
            path.write_text(json.dumps(links), encoding="utf-8")
            findings = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn(
                "MATERIALIZED_COMPONENT_MANUAL_CAPABILITY_BINDING_FORBIDDEN",
                findings,
            )

    def test_analysis_source_cannot_self_promote(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            path = root / SOURCES[0]
            catalogue = json.loads(path.read_text())
            catalogue["analysis_only_sources"][0]["registration_status"] = "ACCEPTED_REFERENCE"
            path.write_text(json.dumps(catalogue), encoding="utf-8")
            findings = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn("ANALYSIS_SOURCE_PRETENDS_DONOR", findings)

    def test_unknown_donor_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            path = root / SOURCES[0]
            catalogue = json.loads(path.read_text())
            catalogue["patterns"][0]["canonical_donor_ids"] = ["FA3-DONOR-NOT-REAL-001"]
            path.write_text(json.dumps(catalogue), encoding="utf-8")
            findings = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn("UNKNOWN_CANONICAL_DONOR", findings)

    def test_single_consumer_shared_module_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            path = root / SOURCES[0]
            catalogue = json.loads(path.read_text())
            catalogue["shared_module_targets"][0]["consumer_application_ids"] = ["fa3.video-editor"]
            path.write_text(json.dumps(catalogue), encoding="utf-8")
            findings = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn("SHARED_MODULE_REQUIRES_MULTIPLE_CONSUMERS", findings)

if __name__ == "__main__":
    unittest.main()
