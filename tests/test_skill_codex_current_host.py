from __future__ import annotations

import base64
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_authenticated_approval import (
    SECURITY_AUTHORITY, TRUST_PROFILE, _signed_receipt_content,
    canonical_bytes, sha256_bytes,
)
from fa3_codex_adapter import (
    ADAPTER_ID, ARCHIVE_SHA256, CODE_MODE_HOST_ARCHIVE_SHA256, CODEX_VERSION, PROVIDER_ID,
)
from fa3_skill_codex_current_host import (
    BUNDLE_SCHEMA, REPORT, SCHEMA, TRUST_SCHEMA, SkillHostDenied,
    check_bundle, load_trust_pin, run_observation,
)
from fa3_skill_host_gate import (
    EVIDENCE_SCHEMA, RECEIPT_PATH, verify_signed_host_evidence,
)


class SkillHostStaticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pin_path = (self.root / "root-managed-simulated.json").resolve()
        self.pin = {
            "schema": TRUST_SCHEMA, "source_commit": "c" * 40,
            "registry_sha256": "a" * 64, "approved_provider_id": PROVIDER_ID,
            "codex_archive_sha256": ARCHIVE_SHA256,
            "codex_code_mode_host_archive_sha256": CODE_MODE_HOST_ARCHIVE_SHA256,
            "trust_profile": "FA3-TRUST-PKI-001",
            "security_authority": "FA3-AUTH-SECURITY-GOV-001",
        }
        self.pin_path.write_text(json.dumps(self.pin), encoding="utf-8")

    def test_root_managed_config_layout_reference_only(self):
        self.assertEqual(load_trust_pin(self.pin_path, strict=False), self.pin)
        altered = dict(self.pin, codex_archive_sha256="0" * 64)
        self.pin_path.write_text(json.dumps(altered), encoding="utf-8")
        with self.assertRaises(SkillHostDenied):
            load_trust_pin(self.pin_path, strict=False)
        missing = dict(self.pin)
        missing.pop("codex_code_mode_host_archive_sha256")
        self.pin_path.write_text(json.dumps(missing), encoding="utf-8")
        with self.assertRaises(SkillHostDenied):
            load_trust_pin(self.pin_path, strict=False)

    def test_absent_or_unsigned_current_host_evidence_fails_closed(self):
        self.assertEqual(verify_signed_host_evidence(
            self.root, expected_source_commit="c" * 40)["result"], "FAIL")
        # No synthetic PASS report or an unsigned boolean can be accepted.
        self.root.joinpath("reports").mkdir()
        self.root.joinpath("evidence/receipts").mkdir(parents=True)
        (self.root / REPORT).write_text('{"schema":"fake","result":"OBSERVED_PASS"}')
        (self.root / RECEIPT_PATH).write_text('{"status":"PASS","signed":true}')
        self.assertEqual(verify_signed_host_evidence(
            self.root, expected_source_commit="c" * 40)["result"], "FAIL")

    def test_workflow_generates_real_provider_receipt_before_skill_probe(self):
        workflow = (ROOT / ".github/workflows/fa3-skill-codex-current-host.yml"
                    ).read_text(encoding="utf-8")
        provider = workflow.find("bash bin/fa3-codex-current-host.sh")
        skill = workflow.find("PYTHONPATH=src python src/fa3_skill_codex_current_host.py")
        self.assertGreaterEqual(provider, 0)
        self.assertGreater(skill, provider)
        self.assertIn("fa3-current-host", workflow)
        self.assertNotIn("synthetic PASS", workflow)

    def test_real_host_probe_denies_missing_execution_markers(self):
        import os
        prior = {k: os.environ.get(k) for k in (
            "FA3_CURRENT_HOST", "FA3_EXECUTION_SCOPE")}
        try:
            os.environ.pop("FA3_CURRENT_HOST", None)
            os.environ.pop("FA3_EXECUTION_SCOPE", None)
            with self.assertRaises(SkillHostDenied):
                run_observation(self.root, self.pin_path, self.pin_path,
                                self.root / "fake-codex", self.root / "fake.tar.gz")
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


@unittest.skipUnless(shutil.which("openssl"), "openssl required for signed evidence drill")
class SkillHostSignedEvidenceTests(unittest.TestCase):
    SOURCE = "c" * 40

    def setUp(self):
        from tests.test_skill_signed_authority import SignedSkillAuthorityTests
        self.fixture = SignedSkillAuthorityTests(
            methodName="test_full_signed_production_path_with_real_fixture_worker")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        registry = self.root / "canonical/skill-registry.json"
        self.registry_sha256 = hashlib.sha256(registry.read_bytes()).hexdigest()
        self.report = {
            "schema": SCHEMA, "result": "OBSERVED_PASS",
            "evidence_level": "UNSIGNED_HOST_OBSERVATION_AWAITING_EXISTING_EVIDENCE_AUTHORITY",
            "source_commit": self.SOURCE,
            "skill_id": "example", "task_id": "TASK-1",
            "provider_id": PROVIDER_ID, "adapter_id": ADAPTER_ID,
            "provider_binary_sha256": "1" * 64,
            "provider_archive_sha256": ARCHIVE_SHA256,
            "provider_runtime_version": CODEX_VERSION,
            "registry_sha256": self.registry_sha256,
            "skill_content_sha256": self.fixture.package["digests"]["content_sha256"],
            "worker_skill_context_sha256": "2" * 64,
            "synthetic_provider": False, "global_promotion_claim": False,
            "cross_host_replay_claim": False,
        }
        target = self.root / REPORT
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.report, indent=2) + "\n", encoding="utf-8")
        self.receipt_path = self.root / RECEIPT_PATH
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)

    def _issue_evidence(self):
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        grant = {
            "schema": "fa3.authorization-role-grant.v1",
            "authority": SECURITY_AUTHORITY,
            "identity": self.fixture.IDENTITY,
            "identity_class": "WORKLOAD",
            "certificate_sha256": self.fixture.fingerprint,
            "roles": ["CURRENT_HOST_EVIDENCE_SIGNER"],
            "receipt_types": ["CURRENT_HOST_EVIDENCE_SIGNING"],
            "scope": "FA3_RELEASE_ACCEPTANCE",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
        }
        payload = {
            "schema": EVIDENCE_SCHEMA,
            "artifact_sha256": hashlib.sha256((self.root / REPORT).read_bytes()).hexdigest(),
            "subject_id": "CAP-080", "provider_id": PROVIDER_ID,
            "source_commit": self.SOURCE, "qualification_id": "FA3-TEST-CAP080",
        }
        receipt = {
            "schema": "fa3.authenticated-approval-receipt.v2",
            "status": "PASS", "receipt_id": "SKILL-CAP080-EVIDENCE-TEST",
            "receipt_type": "CURRENT_HOST_EVIDENCE_SIGNING",
            "source_commit": self.SOURCE,
            "issued_at": (now - timedelta(seconds=30)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
            "nonce": "nonce_skill_host_evidence_12345", "single_use": True,
            "content_sha256": sha256_bytes(canonical_bytes(payload)),
            "payload": payload,
            "signer": {
                "identity": self.fixture.IDENTITY,
                "certificate_sha256": self.fixture.fingerprint,
                "certificate_pem": self.fixture.cert,
                "intermediate_certificates_pem": [],
            },
            "signature": {"algorithm": "RSA-SHA256", "value_b64": ""},
            "authorization": {
                "authority": SECURITY_AUTHORITY, "trust_profile": TRUST_PROFILE,
                "algorithm": "RSA-SHA256", "grant": grant,
                "value_b64": self.fixture._sign(
                    "governance.key", canonical_bytes(grant)),
            },
        }
        receipt["signature"]["value_b64"] = self.fixture._sign(
            "issuer.key", canonical_bytes(_signed_receipt_content(receipt)))
        self.receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return receipt

    def _verify(self):
        return verify_signed_host_evidence(
            self.root, expected_source_commit=self.SOURCE,
            root_ca=self.root / "root.crt",
            security_public_key=self.root / "governance.pub",
            strict_host_permissions=False,
        )

    def test_signed_existing_evidence_role_verifies_exact_report(self):
        self._issue_evidence()
        outcome = self._verify()
        self.assertEqual(outcome["result"], "PASS", outcome)
        self.assertFalse(outcome["global_promotion_claim"])
        self.assertFalse(outcome["current_host_promotion_claim"])
        self.assertFalse(outcome["cross_host_replay_claim"])

    def test_changed_observation_and_invalid_signed_role_denied(self):
        receipt = self._issue_evidence()
        self.report["skill_content_sha256"] = "f" * 64
        (self.root / REPORT).write_text(json.dumps(self.report, indent=2) + "\n")
        self.assertEqual(self._verify()["result"], "FAIL")
        receipt["authorization"]["grant"]["roles"] = ["RELEASE_PROMOTER"]
        self.receipt_path.write_text(json.dumps(receipt))
        self.assertEqual(self._verify()["result"], "FAIL")

    def test_wrong_source_and_missing_registry_denied(self):
        self._issue_evidence()
        self.assertEqual(verify_signed_host_evidence(
            self.root, expected_source_commit="d" * 40,
            root_ca=self.root / "root.crt",
            security_public_key=self.root / "governance.pub",
            strict_host_permissions=False)["result"], "FAIL")
        (self.root / "canonical/skill-registry.json").unlink()
        self.assertEqual(self._verify()["result"], "FAIL")

    def test_native_bundle_must_match_canonical_registry_snapshot(self):
        entry = self.fixture.entry
        entry["snapshot"] = {
            "source_commit": self.SOURCE,
            "content_sha256": self.fixture.package["digests"]["content_sha256"],
            "manifest_sha256": self.fixture.package["digests"]["manifest_sha256"],
        }
        registry = {"id": "FA3-SKILL-REGISTRY-001", "entries": [entry]}
        (self.root / "canonical/skill-registry.json").write_text(json.dumps(registry))
        config = {
            "registry_sha256": hashlib.sha256(
                (self.root / "canonical/skill-registry.json").read_bytes()).hexdigest(),
        }
        bundle = {
            "schema": BUNDLE_SCHEMA, "provider_id": PROVIDER_ID,
            "task_id": "TASK-1", "skill_id": "example", "registry_entry": entry,
            "package": dict(self.fixture.package,
                            source=dict(self.fixture.package["source"], commit=self.SOURCE)),
            "admission": self.fixture.admission,
            "selection": dict(self.fixture.selection, task_id="TASK-1"),
            "lease": self.fixture.lease, "intent": self.fixture.intent,
            "language_context": self.fixture.language,
        }
        task_id, binding, _, skill_id = check_bundle(self.root, bundle, config)
        self.assertEqual((task_id, skill_id), ("TASK-1", "example"))
        self.assertEqual(binding.package["package_id"], self.fixture.package["package_id"])
        tampered = copy.deepcopy(bundle)
        tampered["package"]["digests"]["content_sha256"] = "9" * 64
        with self.assertRaises(SkillHostDenied):
            check_bundle(self.root, tampered, config)


if __name__ == "__main__":
    unittest.main()
