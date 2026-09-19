import copy
import tempfile
import unittest
from pathlib import Path

from src.fa3_mat004_media_authoring_verification_current_host import (
    CAPABILITIES,
    audio_job_allowed,
    document_record_allowed,
    exact_rollback,
    media_job_allowed,
    publication_record_allowed,
    verification_manifest_valid,
)


class Mat004MediaAuthoringVerificationCurrentHostTests(unittest.TestCase):
    def test_batch_identity(self):
        self.assertEqual(
            CAPABILITIES,
            ("CAP-016", "CAP-017", "CAP-018", "CAP-019", "CAP-020"),
        )

    def test_media_job_is_fail_closed(self):
        good = {
            "execution_scope": "CURRENT_HOST",
            "network_fetch": False,
            "human_approved": True,
            "overwrite_source": False,
            "output_inside_artifact_scope": True,
            "provider_fallback_unapproved": False,
        }
        self.assertTrue(media_job_allowed(good))
        self.assertFalse(media_job_allowed({**good, "network_fetch": True}))
        self.assertFalse(media_job_allowed({**good, "human_approved": False}))
        self.assertFalse(media_job_allowed({**good, "overwrite_source": True}))
        self.assertFalse(media_job_allowed({**good, "output_inside_artifact_scope": False}))
        self.assertFalse(media_job_allowed({**good, "provider_fallback_unapproved": True}))

    def test_audio_job_validates_format_and_processing_policy(self):
        good = {
            "execution_scope": "CURRENT_HOST",
            "network_fetch": False,
            "sample_rate_hz": 48000,
            "channels": 1,
            "gain_db": -3.0,
            "implicit_double_denoise": False,
            "overwrite_source": False,
        }
        self.assertTrue(audio_job_allowed(good))
        self.assertFalse(audio_job_allowed({**good, "sample_rate_hz": 100}))
        self.assertFalse(audio_job_allowed({**good, "channels": 0}))
        self.assertFalse(audio_job_allowed({**good, "gain_db": float("nan")}))
        self.assertFalse(audio_job_allowed({**good, "implicit_double_denoise": True}))
        self.assertFalse(audio_job_allowed({**good, "network_fetch": True}))

    def test_document_authoring_preserves_human_and_source_authority(self):
        good = {
            "status": "APPROVED",
            "human_approval_id": "approval",
            "source_authoritative": True,
            "derived_index_authoritative": False,
            "automatic_publication": False,
            "title": "Title",
            "body": "Body",
            "citations": ["local:source"],
        }
        self.assertTrue(document_record_allowed(good))
        self.assertFalse(document_record_allowed({**good, "status": "DRAFT"}))
        self.assertFalse(document_record_allowed({**good, "citations": []}))
        self.assertFalse(document_record_allowed({**good, "derived_index_authoritative": True}))
        self.assertFalse(document_record_allowed({**good, "automatic_publication": True}))

    def test_verification_manifest_binds_hash_and_separation_of_duties(self):
        payload = b"artifact"
        import hashlib
        good = {
            "schema": "fa3.verification-manifest.v1",
            "artifact_sha256": hashlib.sha256(payload).hexdigest(),
            "independent_verification": True,
            "auto_repair_during_verification": False,
            "verdict": "PASS",
            "global_promotion_claim": False,
        }
        self.assertTrue(verification_manifest_valid(good, payload))
        bad_hash = dict(good)
        bad_hash["artifact_sha256"] = "0" * 64
        self.assertFalse(verification_manifest_valid(bad_hash, payload))
        self.assertFalse(verification_manifest_valid({**good, "independent_verification": False}, payload))
        self.assertFalse(verification_manifest_valid({**good, "auto_repair_during_verification": True}, payload))
        self.assertFalse(verification_manifest_valid({**good, "global_promotion_claim": True}, payload))

    def _publication(self):
        return {
            "status": "APPROVED_FOR_PUBLICATION",
            "human_approval_id": "approval",
            "automatic_external_push": False,
            "automatic_content_rewrite_from_feedback": False,
            "title": "Title",
            "body": "Body",
            "citations": ["local:source"],
            "geo_metadata": {
                "machine_readable_summary": True,
                "provenance_exposed": True,
            },
            "feedback_policy": {
                "append_only": True,
                "human_review_before_action": True,
            },
        }

    def test_publication_feedback_cannot_auto_publish_or_rewrite(self):
        good = self._publication()
        self.assertTrue(publication_record_allowed(good))
        draft = copy.deepcopy(good)
        draft["status"] = "DRAFT"
        self.assertFalse(publication_record_allowed(draft))
        no_citation = copy.deepcopy(good)
        no_citation["citations"] = []
        self.assertFalse(publication_record_allowed(no_citation))
        auto_push = copy.deepcopy(good)
        auto_push["automatic_external_push"] = True
        self.assertFalse(publication_record_allowed(auto_push))
        auto_rewrite = copy.deepcopy(good)
        auto_rewrite["automatic_content_rewrite_from_feedback"] = True
        self.assertFalse(publication_record_allowed(auto_rewrite))
        no_review = copy.deepcopy(good)
        no_review["feedback_policy"]["human_review_before_action"] = False
        self.assertFalse(publication_record_allowed(no_review))

    def test_exact_rollback_restores_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            result = exact_rollback(
                Path(td),
                "state.json",
                b'{"state":"SAFE"}\n',
                b'{"state":"FAULT"}\n',
            )
            self.assertTrue(result["rollback_hash_equal"])
            self.assertEqual(result["pre_sha256"], result["post_sha256"])
            self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])


if __name__ == "__main__":
    unittest.main()
