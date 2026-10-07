import sys
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cfa3_donor_source_graph as graph

class SourceGraphTests(unittest.TestCase):
    def registry(self):
        return {"entries": [
            {"donor_id": "D-A", "status": "ACCEPTED_REFERENCE", "source": {"normalized_key": "github:a/root", "locator": "https://github.com/a/root", "kind": "GITHUB"}},
            {"donor_id": "D-B", "status": "CANDIDATE", "source": {"normalized_key": "github:b/existing", "locator": "https://github.com/b/existing", "kind": "GITHUB"}},
        ]}

    def test_fast_source_classes_enter_root_queue_first(self):
        registry = {"entries": [
            {"donor_id": "D-Z", "name": "ordinary", "status": "CANDIDATE", "source": {"normalized_key": "https://z.example/", "locator": "https://z.example/", "kind": "WEBSITE"}},
            {"donor_id": "D-SDK", "name": "Agent SDK", "status": "ACCEPTED_REFERENCE", "source": {"normalized_key": "github:x/sdk", "locator": "https://github.com/x/sdk", "kind": "GITHUB"}, "tags": ["sdk", "agent"]},
        ]}
        value = graph.seed_graph(registry)
        self.assertEqual(value["queue"][0]["root_donor_id"], "D-SDK")

    def test_depth_is_provenance_not_ranking(self):
        value = graph.seed_graph(self.registry()); value.pop("queue")
        graph.add_discovery(value, parent_key="github:a/root", child_url="https://github.com/x/sdk", depth=5, relation_type="SDK", root_donor_id="D-A", evidence={"ref": "x"})
        node = value["nodes"]["github:x/sdk"]
        self.assertEqual(node["min_depth"], 5)
        self.assertEqual(node["assessment"]["strategic_value"], "CRITICAL")
        self.assertFalse(node["assessment"]["depth_is_ranking_factor"])

    def test_unknown_rights_keeps_sdk_in_fast_review_band(self):
        priority = graph.classify_priority("SDK")
        self.assertEqual(priority["strategic_value"], "CRITICAL")
        self.assertEqual(priority["integration_priority"], "P1")
        self.assertIn("RIGHTS_REVIEW_REQUIRED", priority["blockers"])

    def test_known_rights_sdk_can_be_p0(self):
        self.assertEqual(graph.classify_priority("SDK", license_spdx="MIT")["integration_priority"], "P0")

    def test_canonical_identity_is_reused_not_duplicated(self):
        value = graph.seed_graph(self.registry()); value.pop("queue")
        graph.add_discovery(value, parent_key="github:a/root", child_url="https://github.com/b/existing", depth=1, relation_type="LIBRARY", root_donor_id="D-A", evidence={"ref": "x"}, canonical_record=self.registry()["entries"][1])
        self.assertEqual(len(value["nodes"]), 2)
        self.assertEqual(value["nodes"]["github:b/existing"]["canonical_donor_id"], "D-B")

    def test_p0_p1_fast_access_index(self):
        value = graph.seed_graph(self.registry()); value.pop("queue")
        graph.add_discovery(value, parent_key="github:a/root", child_url="https://github.com/x/sdk", depth=2, relation_type="SDK", root_donor_id="D-A", evidence={"ref": "x"})
        graph.add_discovery(value, parent_key="github:a/root", child_url="https://github.com/x/docs", depth=2, relation_type="DOCUMENTATION", root_donor_id="D-A", evidence={"ref": "y"})
        index = graph.build_indexes(value)
        self.assertIn("github:x/sdk", index["fast_access_p0_p1"])
        self.assertNotIn("github:x/docs", index["fast_access_p0_p1"])

    def test_five_is_max_depth(self):
        value = graph.seed_graph(self.registry()); value.pop("queue")
        with self.assertRaises(ValueError):
            graph.add_discovery(value, parent_key="github:a/root", child_url="https://github.com/x/y", depth=6, relation_type="SDK", root_donor_id="D-A", evidence={})

    def test_parallel_crawl_preserves_depth_and_canonical_identity(self):
        registry = self.registry()

        def fake_discover(url, token):
            if url == "https://github.com/a/root":
                return ([{"url": "https://github.com/x/sdk", "normalized_key": "github:x/sdk", "context": "agent sdk"}], {})
            if url == "https://github.com/x/sdk":
                return ([{"url": "https://github.com/b/existing", "normalized_key": "github:b/existing", "context": "shared library"}], {})
            return ([], {})

        with mock.patch.object(graph, "discover_url", side_effect=fake_discover):
            value = graph.crawl(registry, workers=4)

        self.assertEqual(value["validation"]["result"], "PASS")
        self.assertEqual(value["nodes"]["github:x/sdk"]["min_depth"], 1)
        self.assertEqual(value["nodes"]["github:b/existing"]["canonical_donor_id"], "D-B")
        self.assertLessEqual(value["nodes"]["github:b/existing"]["min_depth"], 2)
        self.assertEqual(value["crawl"]["workers"], 4)

    def test_graph_validation(self):
        value = graph.seed_graph(self.registry()); value.pop("queue")
        graph.add_discovery(value, parent_key="github:a/root", child_url="https://github.com/x/y", depth=1, relation_type="AGENT_SDK", root_donor_id="D-A", evidence={})
        self.assertEqual(graph.validate_graph(value)["result"], "PASS")

if __name__ == "__main__":
    unittest.main()
