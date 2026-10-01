import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_api_mega_list_adapter import parse_api_mega_list_markdown, sanitize_locator
from fa3_external_api_discovery_pipeline import (
    create_snapshot_manifest,
    drift_report,
    ingest_snapshot,
    validate_snapshot_manifest,
)
from fa3_external_discovery_store import validate_candidate_store, volume_action

COMMIT = "a" * 40


class ExternalAPIDiscoveryPipelineTests(unittest.TestCase):
    def _snapshot(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        mcp = root / "mcp-servers-apis-289"
        video = root / "videos-apis-705"
        mcp.mkdir(parents=True)
        video.mkdir(parents=True)
        (mcp / "README.md").write_text(
            "- [Transcript Actor](https://apify.com/example/transcript?fpr=partner&utm_source=test&api_key=TOPSECRET) sponsored\n"
            "- [Tool Repo](https://github.com/example/tool/?utm_campaign=x)\n",
            encoding="utf-8",
        )
        (video / "README.md").write_text(
            "- [Transcript Actor](https://apify.com/example/transcript)\n",
            encoding="utf-8",
        )
        manifest = create_snapshot_manifest(root, source_commit=COMMIT)
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return td, root

    def test_locator_neutralizes_affiliate_and_secret_values(self):
        row = sanitize_locator(
            "HTTPS://APIFY.COM:443/example/transcript/?fpr=abc&utm_source=x&api_key=SECRET&mode=fast"
        )
        self.assertEqual(
            "https://apify.com/example/transcript?mode=fast",
            row["canonical_locator"],
        )
        self.assertTrue(row["affiliate_or_tracking_present"])
        self.assertTrue(row["secret_parameter_present"])
        self.assertNotIn("SECRET", json.dumps(row))

    def test_markdown_parser_is_non_authoritative(self):
        rows = parse_api_mega_list_markdown(
            "- [Example](https://apify.com/example/tool?fpr=partner)\n",
            source_path="agents-apis-623/README.md",
        )
        self.assertEqual(1, len(rows))
        self.assertFalse(rows[0]["authority"])
        self.assertFalse(rows[0]["runtime_provider"])
        self.assertFalse(rows[0]["ranking_signal_allowed"])
        self.assertFalse(rows[0]["authorization_signal_allowed"])

    def test_ingest_deduplicates_cross_category_tracking_variants(self):
        td, root = self._snapshot()
        try:
            store, receipt = ingest_snapshot(root)
            self.assertEqual("PASS", receipt["result"])
            self.assertEqual(2, store["candidate_count"])
            self.assertEqual([], validate_candidate_store(store))
            transcript = next(
                row for row in store["candidates"]
                if row["service_identity"] == "apify:example/transcript"
            )
            self.assertEqual(2, len(transcript["observations"]))
            self.assertTrue(transcript["affiliate_or_tracking_observed"])
            self.assertTrue(transcript["secret_parameter_observed"])
            self.assertEqual("https://apify.com/example/transcript", transcript["canonical_locator"])
            serialized = json.dumps(store)
            self.assertNotIn("TOPSECRET", serialized)
            self.assertFalse(transcript["automatic_donor_creation"])
            self.assertFalse(transcript["automatic_provider_admission"])
            self.assertFalse(transcript["automatic_mcp_registration"])
        finally:
            td.cleanup()

    def test_snapshot_hash_drift_fails_closed(self):
        td, root = self._snapshot()
        try:
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            path = root / "mcp-servers-apis-289" / "README.md"
            path.write_text(path.read_text(encoding="utf-8") + "- [Drift](https://example.com/new)\n", encoding="utf-8")
            findings = validate_snapshot_manifest(root, manifest)
            self.assertTrue(any(row["code"] == "EXTDISC-SNAPSHOT-HASH-DRIFT" for row in findings))
        finally:
            td.cleanup()

    def test_invalid_floating_commit_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text("- [X](https://example.com/x)\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                create_snapshot_manifest(root, source_commit="main")

    def test_drift_reports_added_candidate_without_replacing_canonical_state(self):
        td, root = self._snapshot()
        try:
            before, _ = ingest_snapshot(root)
            path = root / "videos-apis-705" / "README.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "- [New Service](https://services.example/new)\n",
                encoding="utf-8",
            )
            manifest = create_snapshot_manifest(root, source_commit=COMMIT)
            (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            after, _ = ingest_snapshot(root)
            report = drift_report(before, after)
            self.assertTrue(report["has_drift"])
            self.assertEqual(1, len(report["added_candidate_ids"]))
            self.assertFalse(report["canonical_state_replacement_allowed"])
        finally:
            td.cleanup()

    def test_candidate_store_tamper_fails_closed(self):
        td, root = self._snapshot()
        try:
            store, _ = ingest_snapshot(root)
            store["automatic_provider_admission"] = True
            findings = validate_candidate_store(store)
            self.assertTrue(any(row["code"] == "EXTDISC-STORE-AUTHORITY" for row in findings))
        finally:
            td.cleanup()

    def test_capacity_policy_uses_90_and_95_percent_thresholds(self):
        self.assertEqual("NO_CAPACITY_ACTION", volume_action(current_records=89, planned_capacity=100)["action"])
        self.assertEqual("OPEN_NEXT_CONTINUATION_VOLUME", volume_action(current_records=90, planned_capacity=100)["action"])
        self.assertEqual(
            "REBALANCE_TO_70_PERCENT_AND_USE_CONTINUATION_VOLUME",
            volume_action(current_records=95, planned_capacity=100)["action"],
        )


if __name__ == "__main__":
    unittest.main()
