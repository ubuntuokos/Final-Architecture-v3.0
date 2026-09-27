import base64
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_authenticated_approval import (
    ApprovalVerificationError,
    SECURITY_AUTHORITY,
    TRUST_PROFILE,
    canonical_bytes,
    certificate_fingerprint,
    consume_promotion_receipts,
    ensure_promotion_receipts_unconsumed,
    sha256_bytes,
    verify_authenticated_receipt,
)
from fa3_enforce import receipt_ok


@unittest.skipUnless(shutil.which("openssl"), "openssl required")
class AuthenticatedApprovalTests(unittest.TestCase):
    SOURCE = "a" * 40
    IDENTITY = "spiffe://fa3.test/reviewer"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._run("genrsa", "-out", "root.key", "2048")
        self._run(
            "req", "-x509", "-new", "-key", "root.key",
            "-out", "root.crt", "-days", "1",
            "-subj", "/CN=FA3 Test Root"
        )
        self._run("genrsa", "-out", "leaf.key", "2048")
        self._run(
            "req", "-new", "-key", "leaf.key",
            "-out", "leaf.csr", "-subj", "/CN=reviewer"
        )
        (self.root / "leaf.ext").write_text(
            f"subjectAltName=URI:{self.IDENTITY}\n"
            "basicConstraints=CA:FALSE\n"
            "keyUsage=digitalSignature\n"
            "extendedKeyUsage=clientAuth\n",
            encoding="utf-8",
        )
        self._run(
            "x509", "-req", "-in", "leaf.csr",
            "-CA", "root.crt", "-CAkey", "root.key",
            "-CAcreateserial", "-out", "leaf.crt",
            "-days", "1", "-extfile", "leaf.ext"
        )
        self._run("genrsa", "-out", "security.key", "2048")
        self._run("rsa", "-in", "security.key", "-pubout", "-out", "security.pub")
        self.cert_pem = (self.root / "leaf.crt").read_text(encoding="utf-8")
        self.cert_fp = certificate_fingerprint(self.cert_pem)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        cp = subprocess.run(
            [shutil.which("openssl"), *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        if cp.returncode != 0:
            raise AssertionError(cp.stderr)
        return cp

    def _sign_bytes(self, key_name, data):
        data_path = self.root / "data.bin"
        sig_path = self.root / "sig.bin"
        data_path.write_bytes(data)
        self._run("dgst", "-sha256", "-sign", key_name, "-out", "sig.bin", "data.bin")
        return base64.b64encode(sig_path.read_bytes()).decode("ascii")

    def _receipt(self, *, receipt_type="INDEPENDENT_REVIEW", role="INDEPENDENT_REVIEWER",
                 identity_class="HUMAN", producer_identity="spiffe://fa3.test/producer"):
        now = datetime.now(timezone.utc)
        grant = {
            "schema": "fa3.authorization-role-grant.v1",
            "authority": SECURITY_AUTHORITY,
            "identity": self.IDENTITY,
            "identity_class": identity_class,
            "certificate_sha256": self.cert_fp,
            "roles": [role],
            "receipt_types": [receipt_type],
            "scope": "FA3_RELEASE_ACCEPTANCE",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
        }
        grant_sig = self._sign_bytes("security.key", canonical_bytes(grant))
        payload = {
            "producer_identity": producer_identity,
            "decision": "APPROVE",
            "subject": "release",
        }
        receipt = {
            "schema": "fa3.authenticated-approval-receipt.v2",
            "status": "PASS",
            "receipt_id": "APR-TEST-00000001",
            "receipt_type": receipt_type,
            "source_commit": self.SOURCE,
            "issued_at": (now - timedelta(seconds=30)).isoformat(),
            "expires_at": (now + timedelta(minutes=30)).isoformat(),
            "nonce": "nonce_0123456789abcdef",
            "single_use": True,
            "content_sha256": sha256_bytes(canonical_bytes(payload)),
            "payload": payload,
            "signer": {
                "identity": self.IDENTITY,
                "certificate_sha256": self.cert_fp,
                "certificate_pem": self.cert_pem,
                "intermediate_certificates_pem": [],
            },
            "signature": {
                "algorithm": "RSA-SHA256",
                "value_b64": "",
            },
            "authorization": {
                "authority": SECURITY_AUTHORITY,
                "trust_profile": TRUST_PROFILE,
                "algorithm": "RSA-SHA256",
                "grant": grant,
                "value_b64": grant_sig,
            },
        }
        signed = {
            "schema": receipt["schema"],
            "status": receipt["status"],
            "receipt_id": receipt["receipt_id"],
            "receipt_type": receipt["receipt_type"],
            "source_commit": receipt["source_commit"],
            "issued_at": receipt["issued_at"],
            "expires_at": receipt["expires_at"],
            "nonce": receipt["nonce"],
            "single_use": receipt["single_use"],
            "content_sha256": receipt["content_sha256"],
            "payload": receipt["payload"],
            "signer_identity": receipt["signer"]["identity"],
            "signer_certificate_sha256": receipt["signer"]["certificate_sha256"],
        }
        receipt["signature"]["value_b64"] = self._sign_bytes("leaf.key", canonical_bytes(signed))
        return receipt

    def _verify(self, receipt, **kwargs):
        return verify_authenticated_receipt(
            receipt,
            expected_receipt_type=kwargs.pop("expected_receipt_type", "INDEPENDENT_REVIEW"),
            required_role=kwargs.pop("required_role", "INDEPENDENT_REVIEWER"),
            expected_source_commit=self.SOURCE,
            root_ca=self.root / "root.crt",
            security_public_key=self.root / "security.pub",
            strict_host_permissions=False,
            require_independent=kwargs.pop("require_independent", True),
            **kwargs,
        )

    def test_valid_signed_authorized_independent_receipt_qualifies(self):
        result = self._verify(self._receipt())
        self.assertTrue(result["qualified"], result)

    def test_boolean_only_legacy_receipt_is_rejected(self):
        legacy = {"status": "PASS", "signed": True, "approved": True, "independent": True}
        result = self._verify(legacy)
        self.assertFalse(result["qualified"])

    def test_enforcer_receipt_path_rejects_boolean_only_legacy_receipt(self):
        receipt_dir = self.root / "evidence/receipts"
        receipt_dir.mkdir(parents=True)
        path = receipt_dir / "independent-review.json"
        path.write_text(json.dumps({
            "status": "PASS",
            "signed": True,
            "approved": True,
            "independent": True,
        }), encoding="utf-8")
        ok, why, _ = receipt_ok(self.root, path, self.SOURCE)
        self.assertFalse(ok)
        self.assertNotEqual(why, "PASS")

    def test_tampered_payload_is_rejected(self):
        receipt = self._receipt()
        receipt["payload"]["decision"] = "DENY"
        result = self._verify(receipt)
        self.assertFalse(result["qualified"])
        self.assertIn("approval payload content digest mismatch", result["findings"])

    def test_wrong_role_grant_is_rejected(self):
        receipt = self._receipt(role="RELEASE_PROMOTER")
        result = self._verify(receipt)
        self.assertFalse(result["qualified"])
        self.assertIn("required authorization role missing", result["findings"])

    def test_reviewer_must_differ_from_authenticated_producer(self):
        receipt = self._receipt(producer_identity=self.IDENTITY)
        result = self._verify(receipt)
        self.assertFalse(result["qualified"])
        self.assertIn("reviewer identity is not independent from producer", result["findings"])

    def test_human_promotion_requires_human_identity_class(self):
        receipt = self._receipt(
            receipt_type="HUMAN_PROMOTION",
            role="RELEASE_PROMOTER",
            identity_class="WORKLOAD",
        )
        result = verify_authenticated_receipt(
            receipt,
            expected_receipt_type="HUMAN_PROMOTION",
            required_role="RELEASE_PROMOTER",
            expected_source_commit=self.SOURCE,
            root_ca=self.root / "root.crt",
            security_public_key=self.root / "security.pub",
            strict_host_permissions=False,
            require_human=True,
        )
        self.assertFalse(result["qualified"])
        self.assertIn("human promotion requires HUMAN identity class", result["findings"])

    def test_promotion_receipt_consumption_is_single_use(self):
        receipt_dir = self.root / "evidence/receipts"
        receipt_dir.mkdir(parents=True)
        paths = []
        for filename in ("release-integrity.json", "independent-review.json", "human-promotion-receipt.json"):
            data = self._receipt()
            data["receipt_id"] = f"APR-{filename}-00000001"
            path = receipt_dir / filename
            path.write_text(json.dumps(data), encoding="utf-8")
            paths.append(path)
        before = ensure_promotion_receipts_unconsumed(self.root, paths)
        self.assertTrue(before["available"])
        result = consume_promotion_receipts(
            self.root,
            paths,
            source_commit=self.SOURCE,
            acceptance_report_sha256="b" * 64,
        )
        self.assertEqual(result["status"], "CONSUMED")
        after = ensure_promotion_receipts_unconsumed(self.root, paths)
        self.assertFalse(after["available"])


if __name__ == "__main__":
    unittest.main()
