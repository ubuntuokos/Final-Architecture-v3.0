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

    def test_parallel_crawl_caches_duplicate_source_fetches(self):
        registry = self.registry()
        calls = {}

        def fake_discover(url, token):
            calls[url] = calls.get(url, 0) + 1
            if url in {"https://github.com/a/root", "https://github.com/b/existing"}:
                return ([{"url": "https://github.com/x/shared", "normalized_key": "github:x/shared", "context": "shared library"}], {})
            if url == "https://github.com/x/shared":
                return ([{"url": "https://github.com/x/deep", "normalized_key": "github:x/deep", "context": "agent sdk"}], {})
            return ([], {})

        with mock.patch.object(graph, "discover_url", side_effect=fake_discover):
            value = graph.crawl(registry, workers=4)

        self.assertEqual(value["validation"]["result"], "PASS")
        self.assertEqual(calls["https://github.com/x/shared"], 1)
        self.assertLess(value["crawl"]["network_fetches"], value["crawl"]["expanded_parent_root_pairs"])
        self.assertEqual(len(value["edges"]), 4)

    def test_crawl_ignores_non_candidate_links_and_expands_relevant_chain(self):
        registry = {"entries": [
            {"donor_id": "D-ROOT", "status": "ACCEPTED_REFERENCE", "source": {"normalized_key": "https://root.example/", "locator": "https://root.example/", "kind": "WEBSITE"}},
        ]}
        calls = []

        def fake_discover(url, token):
            calls.append(url)
            if url == "https://root.example/":
                return ([
                    {"url": "https://noise.example/page", "normalized_key": "https://noise.example/page", "context": "community page"},
                    {"url": "https://github.com/example/unrelated", "normalized_key": "github:example/unrelated", "context": "community page"},
                    {"url": "https://github.com/example/sdk", "normalized_key": "github:example/sdk", "context": "agent sdk"},
                ], {})
            if url == "https://github.com/example/sdk":
                return ([
                    {"url": "https://github.com/example/plugin", "normalized_key": "github:example/plugin", "context": "plugin framework"},
                ], {})
            return ([], {})

        with mock.patch.object(graph, "discover_url", side_effect=fake_discover):
            value = graph.crawl(registry, workers=4)

        self.assertEqual(value["validation"]["result"], "PASS")
        self.assertNotIn("https://noise.example/page", value["nodes"])
        self.assertNotIn("github:example/unrelated", value["nodes"])
        self.assertIn("github:example/sdk", value["nodes"])
        self.assertIn("github:example/plugin", value["nodes"])
        self.assertIn("https://github.com/example/sdk", calls)
        self.assertIn("https://github.com/example/plugin", calls)
        self.assertGreaterEqual(value["crawl"]["ignored_non_candidate_links"], 2)

    def test_branch_stops_when_source_has_no_relevant_children(self):
        registry = {"entries": [
            {"donor_id": "D-ROOT", "status": "ACCEPTED_REFERENCE", "source": {"normalized_key": "https://root.example/", "locator": "https://root.example/", "kind": "WEBSITE"}},
        ]}
        calls = []

        def fake_discover(url, token):
            calls.append(url)
            return ([
                {"url": "https://noise.example/page", "normalized_key": "https://noise.example/page", "context": "navigation"},
            ], {})

        with mock.patch.object(graph, "discover_url", side_effect=fake_discover):
            value = graph.crawl(registry, workers=2)

        self.assertEqual(calls, ["https://root.example/"])
        self.assertEqual(len(value["edges"]), 0)
        self.assertEqual(set(value["nodes"]), {"https://root.example/"})
        self.assertEqual(value["validation"]["result"], "PASS")

    def test_discovery_index_members_are_candidates_not_automatic_donors(self):
        relevant, relation = graph.classify_discovery_candidate(
            "GitHub topic member",
            "https://github.com/example/tool",
            None,
        )
        self.assertTrue(relevant)
        self.assertEqual(relation, "DISCOVERY_INDEX")

    def test_root_shards_partition_canonical_roots(self):
        registry = self.registry()
        seen = {0: [], 1: []}

        def run_shard(index):
            def fake_discover(url, token):
                seen[index].append(url)
                return ([], {})
            with mock.patch.object(graph, "discover_url", side_effect=fake_discover):
                return graph.crawl(registry, workers=2, root_shard_index=index, root_shard_count=2)

        left = run_shard(0)
        right = run_shard(1)
        roots = {"https://github.com/a/root", "https://github.com/b/existing"}
        self.assertEqual(set(seen[0]) | set(seen[1]), roots)
        self.assertFalse(set(seen[0]) & set(seen[1]))
        self.assertEqual(left["crawl"]["root_shard_count"], 2)
        self.assertEqual(right["crawl"]["root_shard_count"], 2)

    def test_merge_shards_preserves_discovered_provenance(self):
        registry = self.registry()

        def fake_discover(url, token):
            if url == "https://github.com/a/root":
                return ([{"url": "https://github.com/x/a", "normalized_key": "github:x/a", "context": "agent sdk"}], {})
            if url == "https://github.com/b/existing":
                return ([{"url": "https://github.com/x/b", "normalized_key": "github:x/b", "context": "shared library"}], {})
            return ([], {})

        shards = []
        for index in range(2):
            with mock.patch.object(graph, "discover_url", side_effect=fake_discover):
                shards.append(graph.crawl(registry, workers=2, root_shard_index=index, root_shard_count=2))
        merged = graph.merge_graphs(list(reversed(shards)), expected_shards=2)
        self.assertEqual(merged["validation"]["result"], "PASS")
        self.assertTrue(merged["crawl"]["complete"])
        self.assertEqual(merged["crawl"]["root_shards_merged"], [0, 1])
        self.assertIn("github:x/a", merged["nodes"])
        self.assertIn("github:x/b", merged["nodes"])
        self.assertEqual(len(merged["edges"]), 2)

    def test_graph_validation(self):
        value = graph.seed_graph(self.registry()); value.pop("queue")
        graph.add_discovery(value, parent_key="github:a/root", child_url="https://github.com/x/y", depth=1, relation_type="AGENT_SDK", root_donor_id="D-A", evidence={})
        self.assertEqual(graph.validate_graph(value)["result"], "PASS")

if __name__ == "__main__":
    unittest.main()
