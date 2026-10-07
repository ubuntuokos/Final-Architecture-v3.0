import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_api_mega_list_adapter import (
    OPENCLAW_SOURCE_ID,
    OPENCLAW_SOURCE_REPOSITORY,
    SOURCE_ID,
    parse_api_mega_list_markdown,
    parse_external_catalog_markdown,
    sanitize_locator,
)
from fa3_external_api_discovery_pipeline import (
    ADMISSION_REVIEW_STAGES,
    build_admission_review_plan,
    create_snapshot_manifest,
    drift_report,
    ingest_snapshot,
    ingest_snapshots,
    validate_admission_review_plan,
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

    def test_openclaw_snapshot_uses_same_non_authoritative_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mcp = root / "mcp-servers-apis-131"
            mcp.mkdir(parents=True)
            (root / "OPENCLAW_RECOMMENDED.md").write_text(
                "| [Google Maps MCP](https://apify.com/crawlerbros/google-maps-mcp?fpr=p2hrc6) | maps |\n",
                encoding="utf-8",
            )
            (mcp / "README.md").write_text(
                "| [Google Maps MCP](https://apify.com/crawlerbros/google-maps-mcp?fpr=p2hrc6&utm_source=openclaw) | maps |\n",
                encoding="utf-8",
            )
            manifest = create_snapshot_manifest(
                root,
                source_commit=COMMIT,
                source_id=OPENCLAW_SOURCE_ID,
                source_repository=OPENCLAW_SOURCE_REPOSITORY,
            )
            (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            store, receipt = ingest_snapshot(root)
            self.assertEqual("PASS", receipt["result"])
            self.assertEqual(OPENCLAW_SOURCE_ID, receipt["source_snapshot"]["source_id"])
            self.assertEqual(1, store["candidate_count"])
            candidate = store["candidates"][0]
            self.assertEqual("apify", candidate["provider_identity"])
            self.assertEqual("https://apify.com/crawlerbros/google-maps-mcp", candidate["canonical_locator"])
            self.assertTrue(candidate["affiliate_or_tracking_observed"])
            self.assertFalse(candidate["automatic_provider_admission"])
            self.assertFalse(candidate["automatic_mcp_registration"])

    def test_openclaw_metadata_extracts_description_hints_and_actor_identity(self):
        rows = parse_external_catalog_markdown(
            "# MCP servers (plug in directly)\n"
            "| API | What it does | OpenClaw use |\n"
            "| [Brave Search MCP Server](https://apify.com/agentify/brave-search-mcp-server?fpr=p2hrc6) | Private search via Brave | Web search from the assistant |\n",
            source_path="OPENCLAW_RECOMMENDED.md",
            source_id=OPENCLAW_SOURCE_ID,
            source_repository=OPENCLAW_SOURCE_REPOSITORY,
        )
        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("Private search via Brave", row["listing_description"])
        self.assertTrue(row["mcp_hint"])
        self.assertFalse(row["skill_hint"])
        self.assertFalse(row["webhook_hint"])
        self.assertEqual("agentify/brave-search-mcp-server", row["apify_actor_identity"])
        self.assertNotIn("p2hrc6", json.dumps(row))

        skill_rows = parse_external_catalog_markdown(
            "# Integrations & productivity (great as skills)\n"
            "| [Calendar Helper](https://example.com/calendar) | Create events | Use as a skill |\n"
            "| [Webhook Relay](https://example.com/hook) | Outbound webhook delivery | Automation |\n",
            source_path="OPENCLAW_RECOMMENDED.md",
            source_id=OPENCLAW_SOURCE_ID,
            source_repository=OPENCLAW_SOURCE_REPOSITORY,
        )
        self.assertTrue(skill_rows[0]["skill_hint"])
        self.assertTrue(skill_rows[1]["webhook_hint"])

    def test_multi_source_reconcile_deduplicates_api_mega_and_openclaw(self):
        with tempfile.TemporaryDirectory() as api_td, tempfile.TemporaryDirectory() as openclaw_td:
            api_root = Path(api_td)
            api_cat = api_root / "maps-apis-1"
            api_cat.mkdir(parents=True)
            (api_cat / "README.md").write_text(
                "- [Google Maps MCP](https://apify.com/crawlerbros/google-maps-mcp?utm_source=mega)\n",
                encoding="utf-8",
            )
            api_manifest = create_snapshot_manifest(api_root, source_commit="a" * 40)
            (api_root / "manifest.json").write_text(json.dumps(api_manifest, indent=2) + "\n", encoding="utf-8")

            openclaw_root = Path(openclaw_td)
            (openclaw_root / "OPENCLAW_RECOMMENDED.md").write_text(
                "# MCP servers\n"
                "| [Google Maps MCP](https://apify.com/crawlerbros/google-maps-mcp?fpr=p2hrc6) | Businesses and reviews | Assistant maps |\n",
                encoding="utf-8",
            )
            openclaw_manifest = create_snapshot_manifest(
                openclaw_root,
                source_commit="b" * 40,
                source_id=OPENCLAW_SOURCE_ID,
                source_repository=OPENCLAW_SOURCE_REPOSITORY,
            )
            (openclaw_root / "manifest.json").write_text(
                json.dumps(openclaw_manifest, indent=2) + "\n",
                encoding="utf-8",
            )

            store, receipt = ingest_snapshots([api_root, openclaw_root])
            reversed_store, _ = ingest_snapshots([openclaw_root, api_root])
            self.assertEqual(store["store_digest"], reversed_store["store_digest"])
            self.assertEqual("PASS", receipt["result"])
            self.assertEqual(2, receipt["source_count"])
            self.assertEqual(1, store["candidate_count"])
            candidate = store["candidates"][0]
            self.assertEqual(
                "https://apify.com/crawlerbros/google-maps-mcp",
                candidate["canonical_locator"],
            )
            self.assertEqual(
                ["crawlerbros/google-maps-mcp"],
                candidate["apify_actor_identities"],
            )
            self.assertEqual(
                {SOURCE_ID, OPENCLAW_SOURCE_ID},
                {obs["source_id"] for obs in candidate["observations"]},
            )
            self.assertEqual(
                {"a" * 40, "b" * 40},
                {obs["source_commit"] for obs in candidate["observations"]},
            )
            self.assertFalse(candidate["automatic_provider_admission"])
            self.assertFalse(candidate["automatic_mcp_registration"])

    def test_candidate_review_plan_is_inert_and_stage_gated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "OPENCLAW_RECOMMENDED.md").write_text(
                "# MCP servers\n"
                "| [Google Maps MCP](https://apify.com/crawlerbros/google-maps-mcp?fpr=p2hrc6) | Businesses and reviews | Assistant maps |\n",
                encoding="utf-8",
            )
            manifest = create_snapshot_manifest(
                root,
                source_commit="c" * 40,
                source_id=OPENCLAW_SOURCE_ID,
                source_repository=OPENCLAW_SOURCE_REPOSITORY,
            )
            (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            store, _ = ingest_snapshot(root)
            candidate = store["candidates"][0]
            plan = build_admission_review_plan(
                store,
                candidate_id=candidate["candidate_id"],
                target_kind="mcp",
            )
            self.assertEqual([], validate_admission_review_plan(plan))
            self.assertEqual("DRAFT_REVIEW_REQUIRED", plan["review_status"])
            self.assertEqual("MCP", plan["requested_target_kind"])
            self.assertFalse(plan["authority"])
            self.assertFalse(plan["runtime_effect"])
            self.assertFalse(plan["registry_mutation_permitted"])
            self.assertFalse(plan["network_probe_performed"])
            self.assertFalse(plan["secret_resolution_performed"])
            self.assertFalse(plan["admission_ready"])
            self.assertFalse(plan["automatic_provider_admission"])
            self.assertFalse(plan["automatic_mcp_registration"])
            self.assertFalse(plan["inherits_apify_org_donor_status"])
            self.assertFalse(plan["donor_usage_edge_created"])
            self.assertEqual(
                ["DISCOVER", "NORMALIZE", "DEDUPLICATE"],
                [row["stage"] for row in plan["stages"] if row["status"] == "PASS_FROM_DERIVED_DISCOVERY"],
            )
            self.assertEqual(
                list(ADMISSION_REVIEW_STAGES[3:]),
                [row["stage"] for row in plan["stages"] if row["status"] == "PENDING_REVIEW"],
            )
            self.assertTrue(plan["candidate_summary"]["mcp_hint_observed"])
            self.assertEqual(
                ["crawlerbros/google-maps-mcp"],
                plan["candidate_summary"]["apify_actor_identities"],
            )
            self.assertEqual("FA3-AUTH-MCP-GATEWAY-001", plan["bindings"]["mcp_authority_id"])
            self.assertEqual("FA3-SECRET-BROKER-001", plan["bindings"]["secret_authority_id"])
            self.assertEqual("FA3-LICENSE-RIGHTS-CONTRACTS-001", plan["bindings"]["license_rights_contract_id"])

    def test_candidate_review_plan_requires_explicit_supported_target(self):
        td, root = self._snapshot()
        try:
            store, _ = ingest_snapshot(root)
            candidate = store["candidates"][0]
            with self.assertRaises(ValueError):
                build_admission_review_plan(store, candidate_id=candidate["candidate_id"], target_kind="")
            with self.assertRaises(ValueError):
                build_admission_review_plan(store, candidate_id=candidate["candidate_id"], target_kind="AUTO_FROM_HINTS")
            with self.assertRaises(ValueError):
                build_admission_review_plan(store, candidate_id="EXTDISC-NOT-PRESENT", target_kind="provider")
        finally:
            td.cleanup()

    def test_candidate_review_plan_rejects_tampered_store(self):
        td, root = self._snapshot()
        try:
            store, _ = ingest_snapshot(root)
            candidate_id = store["candidates"][0]["candidate_id"]
            store["automatic_provider_admission"] = True
            with self.assertRaises(ValueError):
                build_admission_review_plan(store, candidate_id=candidate_id, target_kind="provider")
        finally:
            td.cleanup()

    def test_source_id_repository_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text("- [X](https://example.com/x)\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                create_snapshot_manifest(
                    root,
                    source_commit=COMMIT,
                    source_id=OPENCLAW_SOURCE_ID,
                    source_repository="cporter202/API-mega-list",
                )

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
