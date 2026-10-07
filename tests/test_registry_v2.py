"""FA3 Donor Registry v2 growth, volume and shadow-migration regressions."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_registry_v2 import (
    capacity_for_used,
    classify_categories,
    derive_growth_profile,
    plan_rebalance,
    project_legacy_registry,
    rebalance_bytes_required,
    rebalance_volume,
    resolve_category,
    resolve_donor,
    shadow_migrate,
    verify_shadow,
    volume_state,
)


class RegistryV2PolicyTests(unittest.TestCase):
    def test_capacity_restores_thirty_percent_free_space(self):
        self.assertEqual(capacity_for_used(700), 1000)
        self.assertEqual(capacity_for_used(70), 100)

    def test_rollover_and_rebalance_thresholds(self):
        self.assertEqual(volume_state(89, 100), "OPEN")
        self.assertEqual(volume_state(90, 100), "ROLLOVER")
        self.assertEqual(volume_state(94, 100), "ROLLOVER")
        self.assertEqual(volume_state(95, 100), "REBALANCE_REQUIRED")
        self.assertEqual(rebalance_bytes_required(95, 100), 25)

    def test_rebalance_moves_minimum_until_thirty_percent_reserve_is_restored(self):
        source = {
            "schema": "fa3.donor-registry-volume.v1",
            "dataset": "donors.video",
            "volume_id": "video.001",
            "state": "REBALANCE_REQUIRED",
            "capacity": {
                "handling_limit_bytes": 1000,
                "used_bytes": 950,
                "fill_percent": 95.0,
                "free_percent": 5.0,
            },
            "entries": [
                {"donor_id": "D-A", "payload": "x" * 220},
                {"donor_id": "D-B", "payload": "y" * 120},
                {"donor_id": "D-C", "payload": "z" * 80},
            ],
        }
        plan = plan_rebalance(source)
        self.assertTrue(plan["open_next_volume"])
        self.assertGreaterEqual(plan["selected_record_bytes"], plan["bytes_required"])
        target = {
            "schema": "fa3.donor-registry-volume.v1",
            "dataset": "donors.video",
            "volume_id": "video.002",
            "state": "OPEN",
            "capacity": {"handling_limit_bytes": 1000},
            "entries": [],
        }
        result = rebalance_volume(source, target)
        self.assertLessEqual(result["source"]["capacity"]["fill_percent"], 70.0)
        self.assertLess(result["target"]["capacity"]["fill_percent"], 90.0)

    def test_high_activity_donor_gets_dedicated_series(self):
        result = derive_growth_profile({
            "donor_id": "FA3-DONOR-X-001",
            "observed_at": "2026-10-01",
            "source_refs": ["https://example.invalid/history"],
            "commits_90d": 120,
            "releases_12m": 14,
            "registry_changes_90d": 2,
        })
        self.assertEqual(result["upstream_activity"], "HIGH")
        self.assertEqual(result["storage_class"], "DEDICATED_SERIES")

    def test_high_registry_growth_gets_dedicated_series(self):
        result = derive_growth_profile({
            "donor_id": "FA3-DONOR-X-001",
            "observed_at": "2026-10-01",
            "source_refs": ["evidence:registry-history"],
            "commits_90d": 1,
            "releases_12m": 1,
            "registry_changes_90d": 12,
        })
        self.assertEqual(result["registry_growth_impact"], "HIGH")
        self.assertEqual(result["storage_class"], "DEDICATED_SERIES")

    def test_category_is_indexable_without_changing_identity(self):
        donor = {
            "donor_id": "FA3-DONOR-X-001",
            "domain_hints": ["video editing", "audio workflow"],
            "target_hints": ["FA3 Video Editor"],
            "tags": [],
            "capability_hints": [],
            "problem_hints": [],
        }
        result = classify_categories(donor)
        self.assertEqual(result["primary_category"], "video")
        self.assertIn("audio", result["categories"])


class RegistryV2RepositoryIntegrationTests(unittest.TestCase):
    def test_shadow_migration_preserves_all_ids_and_175(self):
        with tempfile.TemporaryDirectory() as directory:
            shadow = Path(directory) / "shadow"
            result = shadow_migrate(ROOT, shadow, handling_limit_bytes=1024 * 1024)
            self.assertEqual(result["verification"]["result"], "PASS")
            check = verify_shadow(ROOT, shadow)
            self.assertEqual(check["result"], "PASS")
            snapshot = shadow / "migration/source-snapshot.json"
            self.assertTrue(snapshot.is_file())
            projected = Path(directory) / "legacy-projection.json"
            projection = project_legacy_registry(shadow, projected)
            self.assertEqual(projection["result"], "PASS")
            self.assertEqual(
                json.loads(projected.read_text(encoding="utf-8")),
                json.loads((ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json").read_text(encoding="utf-8")),
            )
            self.assertEqual(check["legacy_count"], check["shadow_count"])
            self.assertEqual(check["capability_count"], 175)
            manifest = json.loads((shadow / "registry-manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["canonical_cutover"])
            self.assertEqual(manifest["capacity_policy"]["reserve_percent"], 30)
            for volume in manifest["volumes"]:
                self.assertLessEqual(volume["capacity"]["fill_percent"], 70.0)
            locations = json.loads((shadow / "indexes/donor-location-index.json").read_text(encoding="utf-8"))["locations"]
            donor_id = next(iter(locations))
            resolved = resolve_donor(shadow, donor_id)
            self.assertEqual(resolved["record"]["donor_id"], donor_id)
            categories = json.loads((shadow / "indexes/category-index.json").read_text(encoding="utf-8"))["categories"]
            category = next(iter(categories))
            category_view = resolve_category(shadow, category)
            self.assertEqual(category_view["donor_ids"], sorted(categories[category]))
            self.assertTrue(category_view["loads_only_indexed_volumes"])


if __name__ == "__main__":
    unittest.main()
