#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_canonical_registry_integrity import _cycle_nodes, build_graph, gate


class CanonicalRegistryIntegrityTests(unittest.TestCase):
    def test_repository_registry_integrity_passes(self):
        result = gate(ROOT)
        self.assertEqual(result["result"], "PASS", result["findings"])
        self.assertEqual(result["capability_count"], 175)
        graph = json.loads((ROOT / "reports/fa3-canonical-registry-graph.json").read_text(encoding="utf-8"))
        self.assertFalse(graph["creates_authority"])
        self.assertEqual(graph["duplicate_top_level_ids"], [])
        self.assertEqual(graph["unresolved_supersedence_ids"], [])
        self.assertEqual(graph["supersedence_cycle_nodes"], [])

    def test_cycle_detector_fails_closed_on_cycle_shape(self):
        edges = [
            ("FA3-A-001", "FA3-B-001", "supersedes"),
            ("FA3-B-001", "FA3-A-001", "supersedes"),
        ]
        self.assertEqual(set(_cycle_nodes(edges)), {"FA3-A-001", "FA3-B-001"})

    def test_live_graph_detects_duplicate_top_level_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "canonical/a").mkdir(parents=True)
            (root / "canonical/b").mkdir(parents=True)
            (root / "canonical/a/one.json").write_text(
                json.dumps({"id": "FA3-DUP-001"}), encoding="utf-8"
            )
            (root / "canonical/b/two.json").write_text(
                json.dumps({"id": "FA3-DUP-001"}), encoding="utf-8"
            )
            graph = build_graph(root)
            self.assertEqual(len(graph["duplicate_top_level_ids"]), 1)


if __name__ == "__main__":
    unittest.main()
