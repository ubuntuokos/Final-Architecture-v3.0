"""Cryptographic integration tests: real X.509, Security Governance grant and skill receipts.

The test CA and signer keys are ephemeral; they must never be reused by FA3
or treated as production issuer evidence.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_developer_agent_coordination as dac
from fa3_authenticated_approval import (
    SECURITY_AUTHORITY, TRUST_PROFILE, canonical_bytes, certificate_fingerprint,
    _signed_receipt_content, sha256_bytes,
)
from fa3_skill_fabric_gate import good_package, good_use_receipt
from fa3_skill_materialization import snapshot_digests, task_activation_lease, verify_admitted_snapshot
from fa3_skill_task_binding import SkillTaskBinding
from fa3_skill_signed_authority import KIND_POLICY, SignedSkillAuthorityVerifier
from fa3_skill_task_projection import SkillProjectionDenied, SkillTaskPreflight


@unittest.skipUnless(shutil.which("openssl"), "openssl required for real signature tests")
class SignedSkillAuthorityTests(unittest.TestCase):
    SOURCE = "c" * 40
    IDENTITY = "spiffe://fa3.test/skill-issuer"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="fa3-skill-signed-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self._openssl("genrsa", "-out", "root.key", "2048")
        self._openssl("req", "-x509", "-new", "-key", "root.key",
                      "-out", "root.crt", "-days", "1", "-subj", "/CN=FA3 Skill Test CA")
        self._openssl("genrsa", "-out", "issuer.key", "2048")
        self._openssl("req", "-new", "-key", "issuer.key",
                      "-out", "issuer.csr", "-subj", "/CN=Skill Issuer")
        (self.root / "issuer.ext").write_text(
            f"subjectAltName=URI:{self.IDENTITY}\n"
            "basicConstraints=CA:FALSE\nkeyUsage=digitalSignature\nextendedKeyUsage=clientAuth\n",
            encoding="utf-8")
        self._openssl("x509", "-req", "-in", "issuer.csr", "-CA", "root.crt",
                      "-CAkey", "root.key", "-CAcreateserial", "-out", "issuer.crt",
                      "-days", "1", "-extfile", "issuer.ext")
        self._openssl("genrsa", "-out", "governance.key", "2048")
        self._openssl("rsa", "-in", "governance.key", "-pubout", "-out", "governance.pub")
        self.cert = (self.root / "issuer.crt").read_text(encoding="utf-8")
        self.fingerprint = certificate_fingerprint(self.cert)
        self._fixture()

    def _openssl(self, *args):
        process = subprocess.run([shutil.which("openssl"), *args],
                                 cwd=self.root, text=True, capture_output=True, check=False)
        if process.returncode:
            raise AssertionError(process.stderr)

    def _sign(self, key: str, payload: bytes) -> str:
        process = subprocess.run([shutil.which("openssl"), "dgst", "-sha256",
                                  "-sign", str(self.root / key)],
                                 input=payload, capture_output=True, check=False)
        if process.returncode:
            raise AssertionError(process.stderr)
        return base64.b64encode(process.stdout).decode("ascii")

    def _issue(self, kind: str, claim: dict, task_id: str = "TASK-1", *,
               scope: str = "FA3_SKILL_RUNTIME", expiry_seconds: int = 600,
               role_override: str | None = None):
        receipt_type, role = KIND_POLICY[kind]
        now = datetime.now(timezone.utc)
        grant = {
            "schema": "fa3.authorization-role-grant.v1",
            "authority": SECURITY_AUTHORITY,
            "identity": self.IDENTITY,
            "identity_class": "WORKLOAD",
            "certificate_sha256": self.fingerprint,
            "roles": [role_override or role],
            "receipt_types": [receipt_type],
            "scope": scope,
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
        }
        payload = {"schema": "fa3.skill-authority-binding.v1",
                   "kind": kind, "task_id": task_id, "claim": copy.deepcopy(claim)}
        result = {
            "schema": "fa3.authenticated-approval-receipt.v2",
            "status": "PASS",
            "receipt_id": f"SKILL-{kind}-{task_id}",
            "receipt_type": receipt_type,
            "source_commit": self.SOURCE,
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(seconds=expiry_seconds)).isoformat(),
            "nonce": "nonce_abcdef1234567890",
            "single_use": True,
            "content_sha256": sha256_bytes(canonical_bytes(payload)),
            "payload": payload,
            "signer": {
                "identity": self.IDENTITY, "certificate_sha256": self.fingerprint,
                "certificate_pem": self.cert, "intermediate_certificates_pem": [],
            },
            "signature": {"algorithm": "RSA-SHA256", "value_b64": ""},
            "authorization": {
                "authority": SECURITY_AUTHORITY, "trust_profile": TRUST_PROFILE,
                "algorithm": "RSA-SHA256",
                "grant": grant,
                "value_b64": self._sign("governance.key", canonical_bytes(grant)),
            },
        }
        result["signature"]["value_b64"] = self._sign(
            "issuer.key", canonical_bytes(_signed_receipt_content(result)))
        return result

    def _fixture(self):
        asset = self.root / "skills/example/SKILL.md"
        asset.parent.mkdir(parents=True)
        asset.write_bytes(b"---\nname: example\n---\nSigned Skill Fabric test.\n")
        self.package = good_package()
        self.package["compatibility"]["task_classes"] = ["developer"]
        observed = snapshot_digests(self.root, ["skills/example/SKILL.md"])
        content_hash = observed["files"][0]["sha256"]
        self.package["digests"].update(
            content_sha256=content_hash, manifest_sha256=observed["manifest_sha256"])
        self.package["hash_attestation"]["sha256"] = content_hash
        self.package["evaluation"]["bound_content_sha256"] = content_hash
        self.entry = {
            "skill_id": "example", "package_id": self.package["package_id"],
            "version": "1.0.0", "entrypoint": "skills/example/SKILL.md",
            "admission_status": "ADMITTED",
            "eligibility": {"task_classes": ["developer"]},
        }
        (self.root / "canonical").mkdir()
        self.registry_path = self.root / "canonical/skill-registry.json"
        self.registry_path.write_text(json.dumps({
            "id": "FA3-SKILL-REGISTRY-001", "entries": [self.entry],
        }), encoding="utf-8")
        self.registry_hash = hashlib.sha256(self.registry_path.read_bytes()).hexdigest()
        self.admission = {
            "receipt_ref": "skill-admit:signed:1", "result": "PASS",
            "package_id": self.package["package_id"],
            "content_sha256": content_hash,
            "manifest_sha256": observed["manifest_sha256"],
            "dependency_digest_sha256": self.package["dependencies"]["digest_sha256"],
        }
        self.selection = {
            "receipt_ref": "skill-select:signed:1",
            "package_id": self.package["package_id"],
            "skill_id": "example", "task_scope": "developer",
            "eligible_skill_ids": ["example"],
        }
        self.language = {
            "primary_language": "hu-HU", "secondary_language": "en-US",
            "user_language": "hu-HU", "work_language": "en-US",
            "output_language": "hu-HU",
            "admitted_language_status": {"hu-HU": "BRIDGED", "en-US": "NATIVE"},
        }
        self.task = dac.AgentTask(
            "TASK-1", "agent-1", dac.FIXTURE_PROVIDER_ID,
            "work/a.txt", "verified\n", required_skill_ids=("example",))
        original_verified = verify_admitted_snapshot(
            self.root, self.package, self.entry, self.admission,
            self.selection, "developer")
        self.lease = task_activation_lease(original_verified, task_id="TASK-1")
        self.intent = {k: good_use_receipt()[k] for k in (
            "tool_intent", "model_intent", "resource_intent", "secret_intent")}

    def _signed_binding(self):
        adm = copy.deepcopy(self.admission)
        sel = copy.deepcopy(self.selection)
        language = copy.deepcopy(self.language)
        for kind, row in (("package_admission", adm),
                          ("task_selection", sel), ("language_admission", language)):
            row["authority_receipt"] = self._issue(kind, row)
        binding = SkillTaskBinding(
            self.root, self.package, self.entry, adm, sel, self.lease, self.intent)
        verifier = SignedSkillAuthorityVerifier(
            source_commit=self.SOURCE, registry_sha256=self.registry_hash,
            root_ca=self.root / "root.crt",
            security_public_key=self.root / "governance.pub",
            strict_host_permissions=False)
        return binding, language, verifier

    def test_full_signed_production_path_with_real_fixture_worker(self):
        binding, language, verifier = self._signed_binding()
        preflight = SkillTaskPreflight(
            {"example": binding}, language, self.root, authority_verifier=verifier)
        projection = preflight.prepare_task(self.task)
        self.assertEqual(projection["evidence_scope"], "PKI_AND_SECURITY_GOVERNANCE_SIGNED")
        self.assertEqual(projection["skills"][0]["skill_id"], "example")
        repo = self.root / "repo"
        dac._init_fixture_repo(repo, {"work/a.txt": "baseline\n",
                                     "work/b.txt": "baseline\n"})
        workers = [self.task, dac.AgentTask(
            "TASK-2", "agent-2", dac.FIXTURE_PROVIDER_ID,
            "work/b.txt", "plain\n")]
        result = dac.Coordinator(repo, self.root / "control").run(
            workers, dac.BuiltinDeterministicAdapter(), skill_preflight=preflight)
        self.assertEqual(result["status"], "PASS")
        worker = json.loads(
            (self.root / "control/results/TASK-1.json").read_text(encoding="utf-8"))
        self.assertEqual(worker["verified_skill_ids"], ["example"])

    def test_wrong_task_tampered_claim_and_missing_signed_receipt_are_denied(self):
        binding, language, verifier = self._signed_binding()
        self.assertTrue(verifier("task_selection", binding.selection, "TASK-1"))
        self.assertFalse(verifier("task_selection", binding.selection, "TASK-OTHER"))
        altered = copy.deepcopy(binding.selection)
        altered["eligible_skill_ids"] = ["example", "unadmitted"]
        self.assertFalse(verifier("task_selection", altered, "TASK-1"))
        altered.pop("authority_receipt")
        self.assertFalse(verifier("task_selection", altered, "TASK-1"))
        language["admitted_language_status"]["hu-HU"] = "UNVERIFIED"
        self.assertFalse(verifier("language_admission", language, "TASK-1"))

    def test_release_scope_wrong_role_and_expired_receipts_denied(self):
        _, _, verifier = self._signed_binding()
        for opts in ({"scope": "FA3_RELEASE_ACCEPTANCE"},
                     {"role_override": "RELEASE_PROMOTER"},
                     {"expiry_seconds": -5}):
            claim = copy.deepcopy(self.selection)
            claim["authority_receipt"] = self._issue("task_selection", claim, **opts)
            self.assertFalse(verifier("task_selection", claim, "TASK-1"), opts)

    def test_trust_pins_are_mandatory_and_wrong_root_is_denied(self):
        binding, language, verifier = self._signed_binding()
        with self.assertRaises(ValueError):
            SignedSkillAuthorityVerifier(source_commit="main", registry_sha256=self.registry_hash)
        verifier.registry_sha256 = "0" * 64
        with self.assertRaises(SkillProjectionDenied):
            SkillTaskPreflight({"example": binding}, language, self.root,
                               authority_verifier=verifier).prepare_task(self.task)
        verifier.registry_sha256 = self.registry_hash
        verifier.root_ca = self.root / "nonexistent.crt"
        self.assertFalse(verifier("task_selection", binding.selection, "TASK-1"))

    def test_boolean_only_callback_denied(self):
        binding, language, _ = self._signed_binding()
        with self.assertRaises(SkillProjectionDenied):
            SkillTaskPreflight({"example": binding}, language, self.root,
                               authority_verifier=lambda *_: True)


if __name__ == "__main__":
    unittest.main()
