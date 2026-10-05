"""Exact owner-marked mail/CRM/ERP/groupware/sync donor intake regression tests."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-MAIL-CRM-ERP-GROUPWARE-SYNC-2026-09-30.json"
EXPECTED = {
  "github:bnfy/blanc": [
    "FA3-DONOR-BNFY-BLANC-001",
    "https://github.com/bnfy/blanc",
    "GITHUB"
  ],
  "github:topics/mail-client": [
    "FA3-DONOR-MAIL-CLIENT-TOPIC-001",
    "https://github.com/topics/mail-client",
    "GITHUB_TOPIC"
  ],
  "github:mail-0/zero": [
    "FA3-DONOR-MAIL-0-ZERO-001",
    "https://github.com/mail-0/zero",
    "GITHUB"
  ],
  "github:topics/email-management?o=asc&s=forks": [
    "FA3-DONOR-EMAIL-MANAGEMENT-FORKS-ASC-TOPIC-001",
    "https://github.com/topics/email-management?o=asc&s=forks",
    "GITHUB_TOPIC"
  ],
  "github:topics/webmail-client": [
    "FA3-DONOR-WEBMAIL-CLIENT-TOPIC-001",
    "https://github.com/topics/webmail-client",
    "GITHUB_TOPIC"
  ],
  "github:topics/email-integration": [
    "FA3-DONOR-EMAIL-INTEGRATION-TOPIC-001",
    "https://github.com/topics/email-integration",
    "GITHUB_TOPIC"
  ],
  "github:m66b/fairemail": [
    "FA3-DONOR-M66B-FAIREMAIL-001",
    "https://github.com/m66b/fairemail",
    "GITHUB"
  ],
  "github:topics/mailserver": [
    "FA3-DONOR-MAILSERVER-TOPIC-001",
    "https://github.com/topics/mailserver",
    "GITHUB_TOPIC"
  ],
  "github:topics/crm": [
    "FA3-DONOR-CRM-TOPIC-001",
    "https://github.com/topics/crm",
    "GITHUB_TOPIC"
  ],
  "github:topics/crm-system": [
    "FA3-DONOR-CRM-SYSTEM-TOPIC-001",
    "https://github.com/topics/crm-system",
    "GITHUB_TOPIC"
  ],
  "github:trycompai/crm": [
    "FA3-DONOR-TRYCOMPAI-CRM-001",
    "https://github.com/trycompai/crm",
    "GITHUB"
  ],
  "github:topics/crm-system?l=php&o=desc&s=updated": [
    "FA3-DONOR-CRM-SYSTEM-PHP-UPDATED-DESC-TOPIC-001",
    "https://github.com/topics/crm-system?l=php&o=desc&s=updated",
    "GITHUB_TOPIC"
  ],
  "github:topics/crm-platform?l=javascript": [
    "FA3-DONOR-CRM-PLATFORM-JAVASCRIPT-TOPIC-001",
    "https://github.com/topics/crm-platform?l=javascript",
    "GITHUB_TOPIC"
  ],
  "github:topics/customer-relationship-management": [
    "FA3-DONOR-CUSTOMER-RELATIONSHIP-MANAGEMENT-TOPIC-001",
    "https://github.com/topics/customer-relationship-management",
    "GITHUB_TOPIC"
  ],
  "github:topics/crm?l=shell": [
    "FA3-DONOR-CRM-SHELL-TOPIC-001",
    "https://github.com/topics/crm?l=shell",
    "GITHUB_TOPIC"
  ],
  "github:topics/erp-software": [
    "FA3-DONOR-ERP-SOFTWARE-TOPIC-001",
    "https://github.com/topics/erp-software",
    "GITHUB_TOPIC"
  ],
  "github:topics/erp-system?l=php": [
    "FA3-DONOR-ERP-SYSTEM-PHP-TOPIC-001",
    "https://github.com/topics/erp-system?l=php",
    "GITHUB_TOPIC"
  ],
  "github:topics/erp?o=asc&s=forks": [
    "FA3-DONOR-ERP-FORKS-ASC-TOPIC-001",
    "https://github.com/topics/erp?o=asc&s=forks",
    "GITHUB_TOPIC"
  ],
  "github:frappe/erpnext": [
    "FA3-DONOR-FRAPPE-ERPNEXT-001",
    "https://github.com/frappe/erpnext",
    "GITHUB"
  ],
  "github:topics/erp-software?l=c%23&o=asc&s=updated": [
    "FA3-DONOR-ERP-SOFTWARE-CSHARP-UPDATED-ASC-TOPIC-001",
    "https://github.com/topics/erp-software?l=c%23&o=asc&s=updated",
    "GITHUB_TOPIC"
  ],
  "github:topics/erp-application?l=c%23&o=desc&s=stars": [
    "FA3-DONOR-ERP-APPLICATION-CSHARP-STARS-DESC-TOPIC-001",
    "https://github.com/topics/erp-application?l=c%23&o=desc&s=stars",
    "GITHUB_TOPIC"
  ],
  "github:aureuserp": [
    "FA3-DONOR-AUREUSERP-ORG-001",
    "https://github.com/aureuserp",
    "GITHUB_ORGANIZATION"
  ],
  "github:topics/erp-application?l=python&o=desc&s=stars": [
    "FA3-DONOR-ERP-APPLICATION-PYTHON-STARS-DESC-TOPIC-001",
    "https://github.com/topics/erp-application?l=python&o=desc&s=stars",
    "GITHUB_TOPIC"
  ],
  "github:topics/erp-finance": [
    "FA3-DONOR-ERP-FINANCE-TOPIC-001",
    "https://github.com/topics/erp-finance",
    "GITHUB_TOPIC"
  ],
  "github:topics/groupware?l=go&o=asc&s=forks": [
    "FA3-DONOR-GROUPWARE-GO-FORKS-ASC-TOPIC-001",
    "https://github.com/topics/groupware?l=go&o=asc&s=forks",
    "GITHUB_TOPIC"
  ],
  "github:egroupware": [
    "FA3-DONOR-EGROUPWARE-ORG-001",
    "https://github.com/EGroupware",
    "GITHUB_ORGANIZATION"
  ],
  "github:intermesh": [
    "FA3-DONOR-INTERMESH-ORG-001",
    "https://github.com/Intermesh",
    "GITHUB_ORGANIZATION"
  ],
  "github:tine-groupware": [
    "FA3-DONOR-TINE-GROUPWARE-ORG-001",
    "https://github.com/tine-groupware",
    "GITHUB_ORGANIZATION"
  ],
  "github:horde": [
    "FA3-DONOR-HORDE-ORG-001",
    "https://github.com/horde",
    "GITHUB_ORGANIZATION"
  ],
  "github:topics/file-sync?l=c%23&o=desc&s=forks": [
    "FA3-DONOR-FILE-SYNC-CSHARP-FORKS-DESC-TOPIC-001",
    "https://github.com/topics/file-sync?l=c%23&o=desc&s=forks",
    "GITHUB_TOPIC"
  ],
  "github:polius": [
    "FA3-DONOR-POLIUS-PROFILE-001",
    "https://github.com/polius",
    "GITHUB_PROFILE"
  ],
  "github:topics/file-synchronization?l=c%2B%2B": [
    "FA3-DONOR-FILE-SYNCHRONIZATION-CPP-TOPIC-001",
    "https://github.com/topics/file-synchronization?l=c%2B%2B",
    "GITHUB_TOPIC"
  ],
  "github:syncthing": [
    "FA3-DONOR-SYNCTHING-ORG-001",
    "https://github.com/syncthing",
    "GITHUB_ORGANIZATION"
  ],
  "github:marketplace/actions/team-ai-sync": [
    "FA3-DONOR-TEAM-AI-SYNC-MARKETPLACE-001",
    "https://github.com/marketplace/actions/team-ai-sync",
    "GITHUB_MARKETPLACE"
  ],
  "github:topics/file-synchronization?o=desc&s=stars": [
    "FA3-DONOR-FILE-SYNCHRONIZATION-STARS-DESC-TOPIC-001",
    "https://github.com/topics/file-synchronization?o=desc&s=stars",
    "GITHUB_TOPIC"
  ],
  "github:lbb00/ai-rules-sync": [
    "FA3-DONOR-LBB00-AI-RULES-SYNC-001",
    "https://github.com/lbb00/ai-rules-sync",
    "GITHUB"
  ]
}
FLAGS = ("authority", "automatic_selection", "automatic_fetch", "automatic_install",
         "automatic_activation", "automatic_dependency", "automatic_code_import",
         "automatic_provider_admission", "automatic_model_selection")

class MailCrmErpGroupwareSyncIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {entry["source"]["normalized_key"]: entry for entry in cls.entries}

    def test_registry_integrity_and_historical_delta_counts(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["source_count"], 36)
        self.assertEqual(self.delta["unique_source_key_count"], 36)
        self.assertEqual(self.delta["previous_registry_count"], 1232)
        self.assertEqual(self.delta["expected_registry_count"], 1268)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertFalse(self.delta["authority"])

    def test_all_exact_owner_marked_urls_reference_only(self):
        self.assertEqual(len(EXPECTED), 36)
        self.assertEqual(set(EXPECTED), {x["normalized_source_key"] for x in self.delta["sources"]})
        for key, (donor_id, url, kind) in EXPECTED.items():
            with self.subTest(key=key):
                row = self.by_key[key]
                self.assertEqual(row["donor_id"], donor_id)
                self.assertEqual(row["source"]["locator"], url)
                self.assertEqual(row["source"]["kind"], kind)
                self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
                self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
                self.assertFalse(row["submission_review"]["second_registry_approval_required"])
                self.assertTrue(all(row[flag] is False for flag in FLAGS))
                self.assertTrue(row["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))

    def test_filtered_topic_views_remain_distinct(self):
        keys = {
            "github:topics/crm",
            "github:topics/crm?l=shell",
            "github:topics/crm-system",
            "github:topics/crm-system?l=php&o=desc&s=updated",
            "github:topics/erp-software",
            "github:topics/erp-software?l=c%23&o=asc&s=updated",
            "github:topics/erp-application?l=c%23&o=desc&s=stars",
            "github:topics/erp-application?l=python&o=desc&s=stars",
            "github:topics/file-synchronization?l=c%2B%2B",
            "github:topics/file-synchronization?o=desc&s=stars",
        }
        self.assertTrue(keys.issubset(self.by_key))
        self.assertEqual(self.by_key["github:topics/crm?l=shell"]["discovery_filter"]["language"], "shell")
        self.assertEqual(self.by_key["github:topics/file-synchronization?l=c%2B%2B"]["discovery_filter"]["language"], "c++")

    def test_verified_direct_repository_license_observations(self):
        self.assertEqual(self.by_key["github:bnfy/blanc"]["license"]["declared"], "MIT")
        self.assertEqual(self.by_key["github:mail-0/zero"]["license"]["declared"], "MIT")
        self.assertEqual(self.by_key["github:m66b/fairemail"]["license"]["declared"], "GPL-3.0")
        self.assertEqual(self.by_key["github:trycompai/crm"]["license"]["declared"], "MIT")
        self.assertEqual(self.by_key["github:frappe/erpnext"]["license"]["declared"], "GPL-3.0")
        self.assertEqual(self.by_key["github:lbb00/ai-rules-sync"]["license"]["declared"], "Unlicense")

    def test_indexes_are_not_recursive_admission(self):
        for key in (
            "github:aureuserp","github:egroupware","github:intermesh",
            "github:tine-groupware","github:horde","github:polius","github:syncthing"
        ):
            self.assertEqual(self.by_key[key]["donor_modes"][0], "DISCOVERY_INDEX")
        self.assertEqual(self.by_key["github:marketplace/actions/team-ai-sync"]["source"]["kind"], "GITHUB_MARKETPLACE")

if __name__ == "__main__":
    unittest.main()
