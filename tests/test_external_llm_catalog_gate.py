import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.fa3_external_llm_catalog import (
    normalize_markdown,
    runtime_eligible,
    transition_allowed,
    validate_runtime_catalog,
)
from src.fa3_external_llm_catalog_gate import UPSTREAM_COMMIT, reference_check

ROOT = Path(__file__).resolve().parents[1]


class ExternalLlmCatalogTests(unittest.TestCase):
    def setUp(self):
        text = (ROOT / "tests/fixtures/freellm-readme-mini.md").read_text(encoding="utf-8")
        self.catalog = normalize_markdown(
            text,
            source_commit=UPSTREAM_COMMIT,
            observed_at="2026-09-24",
        )

    def test_reference_gate_passes(self):
        report = reference_check(ROOT)
        self.assertEqual("PASS", report["result"], report.get("findings"))

    def test_fixture_normalizes_three_discovered_providers(self):
        self.assertEqual(3, len(self.catalog["providers"]))
        self.assertEqual({"DISCOVERED"}, {row["discovery_state"] for row in self.catalog["providers"]})
        names = {row["provider_name"] for row in self.catalog["providers"]}
        self.assertEqual({"Google Gemini", "Groq", "OpenRouter"}, names)

    def test_api_key_links_are_not_carried_into_catalog(self):
        serialized = json.dumps(self.catalog).lower()
        self.assertNotIn("get key", serialized)
        self.assertNotIn("example.invalid", serialized)
        self.assertEqual([], validate_runtime_catalog(self.catalog))

    def test_forbidden_credential_value_field_fails_validation(self):
        bad = copy.deepcopy(self.catalog)
        bad["providers"][0]["api_key"] = "should-never-be-here"
        findings = validate_runtime_catalog(bad)
        self.assertTrue(any("forbidden credential-value field" in item for item in findings))

    def test_state_machine_is_sequential_and_fail_closed(self):
        self.assertTrue(transition_allowed("DISCOVERED", "OBSERVED"))
        self.assertTrue(transition_allowed("OBSERVED", "VERIFIED"))
        self.assertTrue(transition_allowed("VERIFIED", "ADMITTED"))
        self.assertTrue(transition_allowed("ADMITTED", "ENABLED"))
        self.assertFalse(transition_allowed("DISCOVERED", "VERIFIED"))
        self.assertFalse(transition_allowed("DISCOVERED", "ENABLED"))
        self.assertFalse(transition_allowed("VERIFIED", "ENABLED"))

    def test_discovered_provider_is_never_runtime_eligible(self):
        row = self.catalog["providers"][0]
        self.assertFalse(
            runtime_eligible(
                row,
                security_privacy_admitted=True,
                egress_policy_admitted=True,
                credential_required=False,
            )
        )

    def test_admitted_provider_requires_full_chain(self):
        row = copy.deepcopy(self.catalog["providers"][0])
        row["discovery_state"] = "ADMITTED"
        row["admission"] = {
            "fa3_provider_id": "FA3-PROVIDER-TEST-EXTERNAL-001",
            "admission_receipt": "evidence/receipts/test-external.json",
            "explicit_external_policy": True,
            "credential_handle_present": True,
            "live_capability_probe": True,
        }
        self.assertTrue(
            runtime_eligible(
                row,
                security_privacy_admitted=True,
                egress_policy_admitted=True,
                credential_required=True,
            )
        )
        no_receipt = copy.deepcopy(row)
        no_receipt["admission"]["admission_receipt"] = None
        self.assertFalse(
            runtime_eligible(
                no_receipt,
                security_privacy_admitted=True,
                egress_policy_admitted=True,
                credential_required=True,
            )
        )
        no_egress = copy.deepcopy(row)
        no_egress["admission"]["explicit_external_policy"] = False
        self.assertFalse(
            runtime_eligible(
                no_egress,
                security_privacy_admitted=True,
                egress_policy_admitted=True,
                credential_required=True,
            )
        )

    def test_source_commit_must_be_immutable(self):
        text = (ROOT / "tests/fixtures/freellm-readme-mini.md").read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            normalize_markdown(text, source_commit="main", observed_at="2026-09-24")

    def test_runtime_catalog_can_be_written_without_network(self):
        text = (ROOT / "tests/fixtures/freellm-readme-mini.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "catalog.json"
            catalog = normalize_markdown(text, source_commit=UPSTREAM_COMMIT, observed_at="2026-09-24")
            path.write_text(json.dumps(catalog), encoding="utf-8")
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual([], validate_runtime_catalog(loaded))


if __name__ == "__main__":
    unittest.main()
