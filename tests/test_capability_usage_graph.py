from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_capability_usage_graph import build_capability_usage_graph

BASE_SOURCES = (
    "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json",
    "canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
    "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
    "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
    "canonical/FA3-CAPABILITY-MODEL-175-001.json",
)
BINDING_PROFILE = "canonical/profiles/FA3-EXTERNAL-LLM-CATALOG-001.json"


def fixture(root: Path) -> None:
    for rel in BASE_SOURCES + (BINDING_PROFILE,):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / rel).read_bytes())


def add_usage(root: Path, **overrides) -> tuple[dict, dict]:
    donor_path = root / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
    links_path = root / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
    registry = json.loads(donor_path.read_text())
    links = json.loads(links_path.read_text())
    donor = registry["entries"][0]
    usage = {
        "id": "FA3-USAGE-CAPABILITY-GRAPH-TEST-001",
        "donor_id": donor["donor_id"],
        "donor_capability_key": "external-llm-discovery",
        "usage_kind": "CAPABILITY_PATTERN",
        "status": "ACTIVE",
        "fa3_binding_refs": ["FA3-EXTERNAL-LLM-CATALOG-001"],
        "consumers": [
            {
                "kind": "APPLICATION",
                "id": "fa3.quickclip",
                "relationship": "INDIRECT_SHARED",
            },
            {
                "kind": "PROFILE",
                "id": "FA3-EXTERNAL-LLM-CATALOG-001",
                "relationship": "DIRECT",
            },
        ],
        "current_host_impact": "STRUCTURAL_REASSESSMENT_REQUIRED",
        "provenance": {"mapping_revision": 1},
    }
    usage.update(overrides)
    links["donor_usage_records"] = [usage]
    links_path.write_text(json.dumps(links), encoding="utf-8")
    return registry, usage


class CapabilityUsageGraphTests(unittest.TestCase):
    def test_repository_graph_is_derived_and_non_authoritative(self):
        graph = build_capability_usage_graph(ROOT)
        self.assertEqual(graph["validation"]["result"], "PASS", graph["validation"]["findings"])
        self.assertTrue(graph["derived"])
        self.assertFalse(graph["authority"])
        self.assertFalse(graph["runtime_promotion"])
        self.assertEqual(graph["capability_count"], 175)
        self.assertFalse(graph["new_capability"])
        self.assertFalse(graph["new_architectural_authority"])

    def test_binding_is_derived_from_canonical_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            _, usage = add_usage(root)
            graph = build_capability_usage_graph(root)
            self.assertEqual(graph["validation"]["result"], "PASS", graph["validation"]["findings"])
            edge = graph["edges"][0]
            self.assertEqual(edge["id"], usage["id"])
            self.assertEqual(edge["binding_status"], "RESOLVED")
            self.assertEqual(edge["capability_ids"], ["CAP-005", "CAP-140"])

            donor = graph["views"]["by_donor"][usage["donor_id"]]
            self.assertEqual(donor["capabilities"], ["CAP-005", "CAP-140"])
            self.assertIn("APPLICATION:fa3.quickclip", donor["consumers"])

            cap = graph["views"]["by_capability"]["CAP-005"]
            self.assertIn(usage["donor_id"], cap["donors"])
            self.assertIn("APPLICATION:fa3.quickclip", cap["consumers"])

            consumer = graph["views"]["by_consumer"]["APPLICATION:fa3.quickclip"]
            self.assertEqual(consumer["capabilities"], ["CAP-005", "CAP-140"])
            self.assertIn(usage["donor_id"], consumer["donors"])

    def test_manual_capability_ids_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            add_usage(root, capability_ids=["CAP-999"])
            graph = build_capability_usage_graph(root)
            codes = {row["code"] for row in graph["validation"]["findings"]}
            self.assertIn("MANUAL_CAPABILITY_IDS_FORBIDDEN", codes)

    def test_unknown_binding_ref_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            add_usage(root, fa3_binding_refs=["FA3-UNKNOWN-PROFILE-001"])
            graph = build_capability_usage_graph(root)
            codes = {row["code"] for row in graph["validation"]["findings"]}
            self.assertIn("UNKNOWN_CANONICAL_BINDING_REF", codes)
            self.assertIn("ACTIVE_USAGE_REQUIRES_RESOLVED_CAPABILITY_BINDING", codes)

    def test_donor_change_resolves_capability_consumer_and_current_host_impact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            old, usage = add_usage(root)
            donor_path = root / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
            new = copy.deepcopy(old)
            new["entries"][0]["notes"] = ["changed upstream observation"]
            donor_path.write_text(json.dumps(new), encoding="utf-8")

            graph = build_capability_usage_graph(root, previous_registry=old)
            self.assertEqual(graph["validation"]["result"], "PASS", graph["validation"]["findings"])
            change = graph["update_impact"][0]
            self.assertIn("CAP-005", change["affected_capabilities"])
            self.assertIn("APPLICATION:fa3.quickclip", change["affected_consumers"])
            self.assertIn("PROFILE:FA3-EXTERNAL-LLM-CATALOG-001", change["affected_consumers"])
            self.assertTrue(change["current_host_reconciliation_required"])
            self.assertIn(
                "DONOR_TO_CAPABILITY_TO_CONSUMER_REVERSE_IMPACT_LOOKUP",
                change["required_actions"],
            )
            self.assertIn(usage["donor_id"], change["donor_ids"])

    def test_new_usage_requires_explicit_current_host_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            add_usage(root, current_host_impact=None)
            graph = build_capability_usage_graph(root)
            codes = {row["code"] for row in graph["validation"]["findings"]}
            self.assertIn("CURRENT_HOST_IMPACT_REQUIRED", codes)


if __name__ == "__main__":
    unittest.main()
