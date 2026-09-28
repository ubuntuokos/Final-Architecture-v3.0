from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_osint_case import (
    CaseContractError, candidate_disposition, maigret_reference_plan,
    observation_projection, validate_case_request,
)

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def case():
    return {
        "schema": "fa3.osint-investigation-request.v1",
        "case_id": "synthetic-test-case",
        "purpose": "Contract regression on synthetic fixture",
        "scope_class": "AUTHORIZED_SUBJECT",
        "target_scope": ["fictional_user"],
        "data_classes": ["PUBLIC_USERNAME"],
        "authorization_reference": "synthetic-security-approval-not-a-real-token",
        "human_approval_reference": "synthetic-human-approval-not-a-real-token",
        "security_policy_receipt_ref": "synthetic-policy-ref-not-a-real-token",
        "expires_at": "2030-09-28T12:00:00+00:00",
    }


def source_record():
    return {
        "id": "maigret", "category": "username-social",
        "url": "https://github.com/soxoj/maigret",
        "status": "DISCOVERED_METADATA_ONLY",
        "url_status": "UNVERIFIED_EXTERNAL_LINK",
        "review_class": "STANDARD_REVIEW",
        "source_positions": [100],
    }


class OsintCaseTests(unittest.TestCase):
    def test_structural_preflight_is_never_authorization(self):
        out = validate_case_request(case(), now=NOW)
        self.assertEqual(out["result"], "PENDING_INDEPENDENT_SECURITY_AUTHORITY_VERIFICATION")
        self.assertFalse(out["verification_performed"])
        self.assertFalse(out["provider_admitted"])
        self.assertFalse(out["runtime_execution_allowed"])

    def test_subject_search_requires_external_refs(self):
        v = case()
        v.pop("human_approval_reference")
        with self.assertRaisesRegex(CaseContractError, "human_approval_reference"):
            validate_case_request(v, now=NOW)

    def test_expired_case_fails_closed(self):
        v = case()
        v["expires_at"] = "2026-09-27T12:00:00Z"
        with self.assertRaisesRegex(CaseContractError, "expired"):
            validate_case_request(v, now=NOW)

    def test_aggregate_person_lookup_fails_closed(self):
        v = case()
        v["scope_class"] = "PUBLIC_AGGREGATE"
        v["data_classes"] = ["PERSON_IDENTIFIERS"]
        with self.assertRaisesRegex(CaseContractError, "prohibited"):
            validate_case_request(v, now=NOW)

    def test_owned_assets_require_ownership_reference(self):
        v = case()
        v["scope_class"] = "OWNED_ASSET"
        v.pop("ownership_reference", None)
        with self.assertRaisesRegex(CaseContractError, "ownership_reference"):
            validate_case_request(v, now=NOW)

    def test_unverified_license_blocks_candidate(self):
        review = {}
        out = candidate_disposition(source_record(), review)
        self.assertEqual(out["result"], "BLOCKED")
        self.assertIn("MISSING_REVIEW:independent_license_verified", out["findings"])
        self.assertFalse(out["provider_admitted"])

    def test_fully_declared_review_remains_non_admitted(self):
        flags = {
            "independent_license_verified": True,
            "upstream_source_pinned": True,
            "supply_chain_review_pass": True,
            "privacy_and_terms_review_pass": True,
            "host_coexistence_review_pass": True,
            "network_egress_review_pass": True,
        }
        out = candidate_disposition(source_record(), flags)
        self.assertEqual(out["result"], "PENDING_SEPARATE_PROVIDER_ADMISSION")
        self.assertFalse(out["review_evidence_is_authenticated"])
        self.assertFalse(out["runtime_execution_allowed"])

    def test_restricted_category_never_self_admits(self):
        source = source_record()
        source["category"] = "data-breach"
        source["review_class"] = "RESTRICTED_REVIEW"
        out = candidate_disposition(source, {})
        self.assertIn("SENSITIVE_CATEGORY_REQUIRES_SPECIAL_SEPARATE_REVIEW", out["findings"])

    def test_missing_source_url_blocks_observation(self):
        src = source_record()
        src["url"] = None
        with self.assertRaisesRegex(CaseContractError, "source reference"):
            observation_projection(case(), src, artifact=b"synthetic",
                collected_at="2026-09-28T11:00:00Z", extracted_fields={}, uncertainty="unverified",
                now=NOW)

    def test_observation_preserves_artifact_digest_but_not_runtime_claim(self):
        value = b"synthetic fixture artifact with no real personal data"
        out = observation_projection(case(), source_record(), artifact=value,
            collected_at="2026-09-28T11:00:00Z",
            extracted_fields={"synthetic": True}, uncertainty="single synthetic fixture",
            now=NOW)
        self.assertEqual(out["original_artifact_sha256"], hashlib.sha256(value).hexdigest())
        self.assertEqual(out["target_evidence_contract"], "FA3-EVIDENCE-ENVELOPE-001")
        self.assertEqual(out["result"], "UNTRUSTED_OBSERVATION_PENDING_EVIDENCE_AUTHORITY")
        self.assertFalse(out["current_host_pass_claim"])
        self.assertFalse(out["authority"])

    def test_ai_inference_cannot_be_mixed_with_source_facts(self):
        with self.assertRaisesRegex(CaseContractError, "separate"):
            observation_projection(case(), source_record(), artifact=b"synthetic",
                collected_at="2026-09-28T11:00:00Z",
                extracted_fields={"inferred_identity": "fictional"}, uncertainty="unknown",
                now=NOW)

    def test_maigret_plan_requires_exact_case_scope_and_never_executes(self):
        with self.assertRaisesRegex(CaseContractError, "outside case scope"):
            maigret_reference_plan(case(), "other_person", now=NOW)
        good = maigret_reference_plan(case(), "fictional_user", now=NOW)
        self.assertEqual(good["result"], "NON_EXECUTABLE_PLAN_PENDING_ADMISSION_AND_SCOPE_VERIFICATION")
        self.assertIsNone(good["shell_command"])
        self.assertIsNone(good["network_request"])
        self.assertFalse(good["runtime_execution_allowed"])

    def test_injection_like_username_rejected(self):
        with self.assertRaisesRegex(CaseContractError, "invalid username"):
            maigret_reference_plan(case(), "fictional_user;rm -rf", now=NOW)


if __name__ == "__main__":
    unittest.main()
