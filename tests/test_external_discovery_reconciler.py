import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_external_discovery_reconciler import (
    build_reconciliation,
    reconcile_candidate,
    validate_reconciliation,
)
from fa3_external_discovery_store import build_candidate_store


def candidate():
    return {
        "candidate_id": "EXTDISC-TEST",
        "listing_names": ["Transcript Actor"],
        "discovery_terms": ["transcript", "audio"],
        "source_categories": ["ai-apis-1555"],
        "provider_identity": "apify",
        "service_identity": "apify:example/transcript",
        "canonical_locator": "https://apify.com/example/transcript",
    }


def app_index():
    return {
        "counts": {"total_apps": 3},
        "applications": [
            {"application_id": "app.story", "name": "Story", "aliases": ["Story Studio"]},
            {"application_id": "app.video", "name": "Video Editor", "aliases": ["Video"]},
            {"application_id": "app.crm", "name": "CRM", "aliases": ["CRM"]},
        ],
        "capability_consumer_map": {
            "edges": [
                {
                    "id": "USE-1",
                    "consumers": [
                        {"kind": "APPLICATION", "id": "app.story"},
                        {"kind": "APPLICATION", "id": "app.video"},
                    ],
                }
            ],
            "views": {"by_capability": {"CAP-011": ["USE-1"]}},
        },
        "shared_capability_consumer_map": {
            "edges": [],
            "views": {"by_capability": {}},
        },
        "validation": {"result": "PASS", "findings": []},
    }


class ExternalDiscoveryReconciliationTests(unittest.TestCase):
    def test_exact_donor_match_can_confirm_existing_capability(self):
        catalog = [
            {
                "candidate_id": "FA3-DONOR-EXAMPLE-001",
                "candidate_class": "DONOR_REFERENCE",
                "source_locator": "https://apify.com/example/transcript?fpr=legacy",
                "tokens": ["transcript", "audio"],
                "capabilities": ["CAP-011"],
            }
        ]
        row = reconcile_candidate(candidate(), catalog_entries=catalog, provider_index=[], app_index=app_index())
        self.assertEqual("EXISTING_DONOR", row["donor_reconciliation"]["status"])
        self.assertEqual("EXACT_EXISTING_CAPABILITY", row["capability_reconciliation"]["status"])
        self.assertEqual(["CAP-011"], row["capability_reconciliation"]["confirmed_capability_ids"])
        self.assertEqual("SHARED_REUSE_CANDIDATE", row["shared_reconciliation"]["status"])
        self.assertEqual(2, row["application_impact"]["affected_application_count"])
        self.assertEqual(3, row["application_impact"]["all_registered_applications_scanned"])
        self.assertFalse(row["donor_reconciliation"]["donor_intake_allowed"])

    def test_token_only_donor_match_never_confirms_capability(self):
        catalog = [
            {
                "candidate_id": "FA3-DONOR-OTHER-001",
                "candidate_class": "DONOR_REFERENCE",
                "source_locator": "https://other.example/tool",
                "tokens": ["transcript", "audio", "apify"],
                "capabilities": ["CAP-011"],
            }
        ]
        row = reconcile_candidate(candidate(), catalog_entries=catalog, provider_index=[], app_index=app_index())
        self.assertEqual("POSSIBLE_EXISTING_DONOR_REVIEW", row["donor_reconciliation"]["status"])
        self.assertEqual([], row["capability_reconciliation"]["confirmed_capability_ids"])
        self.assertEqual("EXISTING_CAPABILITY_SUBFUNCTION_REVIEW", row["capability_reconciliation"]["status"])

    def test_exact_provider_match_is_not_provider_admission(self):
        providers = [{
            "provider_id": "FA3-PROVIDER-EXAMPLE-001",
            "status": "PENDING_CURRENT_HOST",
            "source_path": "canonical/providers/example.json",
            "locators": ["https://apify.com/example/transcript"],
            "tokens": ["transcript", "audio"],
            "capabilities": ["CAP-011"],
        }]
        row = reconcile_candidate(candidate(), catalog_entries=[], provider_index=providers, app_index=app_index())
        self.assertEqual("EXISTING_PROVIDER", row["provider_reconciliation"]["status"])
        self.assertFalse(row["provider_reconciliation"]["automatic_provider_registration"])
        self.assertFalse(row["provider_reconciliation"]["automatic_mcp_registration"])
        self.assertFalse(row["provider_reconciliation"]["automatic_runtime_activation"])

    def test_existing_shared_match_is_preferred(self):
        index = app_index()
        index["shared_capability_consumer_map"] = {
            "edges": [{
                "id": "SHARED:FA3-SHARED-TRANSCRIPT-001",
                "shared_capability_id": "FA3-SHARED-TRANSCRIPT-001",
                "consumers": [
                    {"kind": "APPLICATION", "id": "app.story"},
                    {"kind": "APPLICATION", "id": "app.video"},
                ],
            }],
            "views": {"by_capability": {"CAP-011": ["SHARED:FA3-SHARED-TRANSCRIPT-001"]}},
        }
        providers = [{
            "provider_id": "FA3-PROVIDER-EXAMPLE-001",
            "status": "ACTIVE",
            "source_path": "canonical/providers/example.json",
            "locators": ["https://apify.com/example/transcript"],
            "tokens": ["transcript", "audio"],
            "capabilities": ["CAP-011"],
        }]
        row = reconcile_candidate(candidate(), catalog_entries=[], provider_index=providers, app_index=index)
        self.assertEqual("EXISTING_SHARED_MATCH", row["shared_reconciliation"]["status"])
        self.assertIn("FA3-SHARED-TRANSCRIPT-001", row["shared_reconciliation"]["existing_shared_ids"])

    def test_unmapped_candidate_does_not_create_capability(self):
        blank = candidate()
        blank["listing_names"] = ["Novel Unique Thing"]
        blank["discovery_terms"] = ["novel", "unique", "thing"]
        blank["canonical_locator"] = "https://new.example/novel"
        row = reconcile_candidate(blank, catalog_entries=[], provider_index=[], app_index=app_index())
        self.assertEqual("UNMAPPED_FUNCTIONAL_GAP_REVIEW", row["capability_reconciliation"]["status"])
        self.assertFalse(row["capability_reconciliation"]["new_capability_id_creation_allowed"])
        self.assertEqual(175, row["capability_reconciliation"]["capability_baseline"])

    def test_repository_integration_queries_reuse_donor_provider_and_application_sources(self):
        store = build_candidate_store(
            source_snapshot={
                "source_id": "FA3-SOURCE-API-MEGA-LIST-001",
                "source_repository": "cporter202/API-mega-list",
                "source_commit": "a" * 40,
                "manifest_digest": "b" * 64,
                "file_count": 1,
                "immutable": True,
                "network_fetch_performed": False,
            },
            observations=[{
                "source_id": "FA3-SOURCE-API-MEGA-LIST-001",
                "source_path": "ai-apis-1555/README.md",
                "source_line": 1,
                "source_category": "ai-apis-1555",
                "source_listing_digest": "c" * 64,
                "listing_name": "FA3 reconciliation probe",
                "canonical_locator": "https://probe.invalid/service",
                "provider_identity": "probe.invalid",
                "service_identity": "probe.invalid:service",
                "affiliate_or_tracking_present": False,
                "secret_parameter_present": False,
                "sponsorship_or_featured_present": False,
                "ranking_signal_allowed": False,
                "authorization_signal_allowed": False,
                "discovery_terms": ["reconciliation", "probe"],
                "authority": False,
                "runtime_provider": False,
            }],
        )
        projection = build_reconciliation(ROOT, store)
        self.assertEqual("FA3-EXTERNAL-DISCOVERY-RECONCILIATION-001", projection["policy_id"])
        self.assertEqual("FA3-REUSE-CATALOG-001", projection["reuse_catalog_policy_id"])
        self.assertGreater(projection["reuse_catalog_entry_count"], 0)
        self.assertGreater(projection["registered_application_count"], 0)
        self.assertEqual(1, projection["result_count"])
        self.assertEqual([], validate_reconciliation(projection))
        row = projection["results"][0]
        self.assertTrue(row["donor_reconciliation"]["explicit_owner_marker_required_for_new_donor"])
        self.assertEqual(
            projection["registered_application_count"],
            row["application_impact"]["all_registered_applications_scanned"],
        )

    def test_projection_validator_blocks_authority_and_capability_overflow(self):
        projection = {
            "schema": "fa3.external-discovery-reconciliation-projection.v1",
            "policy_id": "FA3-EXTERNAL-DISCOVERY-RECONCILIATION-001",
            "authority": False,
            "canonical_source_of_truth": False,
            "derived": True,
            "rebuildable": True,
            "automatic_donor_creation": False,
            "automatic_provider_admission": False,
            "automatic_mcp_registration": False,
            "automatic_shared_materialization": False,
            "automatic_application_mutation": False,
            "capability_count": 175,
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "result_count": 1,
            "results": [{
                "candidate_id": "EXTDISC-X",
                "capability_reconciliation": {
                    "confirmed_capability_ids": ["CAP-176"],
                    "suggested_capabilities": [],
                },
                "donor_reconciliation": {"donor_intake_allowed": False},
                "provider_reconciliation": {"automatic_provider_registration": False},
                "shared_reconciliation": {"automatic_shared_materialization": False},
            }],
        }
        projection["projection_digest"] = "invalid"
        findings = validate_reconciliation(projection)
        self.assertTrue(any(x["code"] == "EXTREC-CAPABILITY-ID" for x in findings))
        self.assertTrue(any(x["code"] == "EXTREC-DIGEST" for x in findings))


if __name__ == "__main__":
    unittest.main()
