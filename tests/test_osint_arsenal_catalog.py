from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_osint_arsenal_catalog import (
    CatalogError, git_blob_sha1, load_pin, normalize, read_catalog, safe_source_url,
)


def fixture(*, duplicate: bool = False, conflicting: bool = False):
    rows = [
        {"id": "example", "name": "Example", "category": "username-social",
         "url": "", "install": {"method": "manual", "raw": "DO_NOT_EXECUTE"}},
    ]
    if duplicate:
        rows.append({
            "id": "example", "name": "Alternate",
            "category": "username-social",
            "url": "https://example.org/a" if not conflicting else "https://example.org/b",
            "install": {"method": "web", "raw": "DO_NOT_EXECUTE"},
        })
        if conflicting:
            rows[0]["url"] = "https://example.org/a"
    raw = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    pin = {
        "upstream_catalog_git_blob_sha1": git_blob_sha1(raw),
        "source": "https://example.org/catalog",
        "upstream_commit": "a" * 40,
        "snapshot_records": len(rows),
        "unique_tool_ids": 1,
        "normalized_categories": 1,
        "records_without_direct_url": 1 if not conflicting else 0,
        "duplicate_id": "example" if duplicate else None,
    }
    return raw, pin


class OsintArsenalCatalogTests(unittest.TestCase):
    def test_checked_in_source_is_exactly_pinned(self):
        catalog = read_catalog(ROOT)
        self.assertEqual(catalog["upstream_commit"], "2c6475a1d5b941cc598b3612419ef22e6d903ce8")
        self.assertEqual(catalog["counts"], {
            "snapshot_records": 753, "unique_tool_ids": 752,
            "normalized_categories": 26, "records_without_direct_url": 264,
            "duplicate_records": 1,
        })
        self.assertEqual(catalog["duplicate_merges"][0]["id"], "social-searcher")
        self.assertFalse(catalog["authority"])
        self.assertFalse(catalog["automatic_install"])
        self.assertFalse(catalog["automatic_provider_admission"])

    def test_checked_in_pin_is_non_authoritative(self):
        pin = load_pin(ROOT / "research/external-project-radar/osint/awesome-osint-arsenal/pin.json")
        self.assertEqual(pin["snapshot_policy"], "IMMUTABLE_OFFLINE_REFERENCE_ONLY")
        self.assertFalse(pin["automatic_fetch"])
        self.assertFalse(pin["automatic_install"])

    def test_missing_url_remains_unresolved_not_guessed(self):
        content, pin = fixture()
        result = normalize(content, pin)
        self.assertIsNone(result["records"][0]["url"])
        self.assertEqual(result["records"][0]["url_status"], "MISSING")
        self.assertEqual(result["records"][0]["status"], "DISCOVERED_METADATA_ONLY")
        self.assertNotIn("raw", json.dumps(result))
        self.assertNotIn("DO_NOT_EXECUTE", json.dumps(result))

    def test_duplicate_merges_alias_and_validated_url_without_installing(self):
        content, pin = fixture(duplicate=True)
        result = normalize(content, pin)
        row = result["records"][0]
        self.assertEqual(result["counts"]["duplicate_records"], 1)
        self.assertEqual(row["names"], ["Alternate", "Example"])
        self.assertEqual(row["url"], "https://example.org/a")
        self.assertEqual(row["source_positions"], [0, 1])
        self.assertFalse(row["automatic_activation"])

    def test_duplicate_conflicting_urls_fails_closed(self):
        content, pin = fixture(duplicate=True, conflicting=True)
        with self.assertRaisesRegex(CatalogError, "conflicting duplicate"):
            normalize(content, pin)

    def test_modified_upstream_blob_fails_closed(self):
        content, pin = fixture()
        tampered = content.replace(b"Example", b"Modified")
        with self.assertRaisesRegex(CatalogError, "immutable upstream pin"):
            normalize(tampered, pin)

    def test_unknown_install_method_fails_closed(self):
        content, pin = fixture()
        parsed = json.loads(content)
        parsed[0]["install"]["method"] = "shell"
        changed = json.dumps(parsed).encode()
        pin["upstream_catalog_git_blob_sha1"] = git_blob_sha1(changed)
        with self.assertRaisesRegex(CatalogError, "unknown install method"):
            normalize(changed, pin)

    def test_invalid_source_urls_are_not_accepted(self):
        self.assertIsNone(safe_source_url("file:///etc/passwd"))
        self.assertIsNone(safe_source_url("https://user:secret@example.org"))
        self.assertIsNone(safe_source_url("javascript:alert(1)"))
        self.assertEqual(safe_source_url("https://example.org/tool"), "https://example.org/tool")

    def test_restricted_category_never_bypasses_admission(self):
        content, pin = fixture()
        parsed = json.loads(content)
        parsed[0]["category"] = "red-team-offensive"
        changed = json.dumps(parsed).encode()
        pin["upstream_catalog_git_blob_sha1"] = git_blob_sha1(changed)
        result = normalize(changed, pin)
        row = result["records"][0]
        self.assertEqual(row["review_class"], "RESTRICTED_REVIEW")
        self.assertEqual(row["capability_hints"], [])
        self.assertFalse(row["automatic_provider_admission"])
        self.assertEqual(row["downstream_license"], "UNVERIFIED_PER_TOOL")


if __name__ == "__main__":
    unittest.main()
