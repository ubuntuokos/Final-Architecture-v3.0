from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
import sys
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_OPTIONAL_IMPORT_ERROR: ModuleNotFoundError | None = None
try:
    from fastapi.testclient import TestClient
    from blackhole_api import (
        AuthenticationDenied,
        BrokerLeaseFileVerifier,
        LeaseDenied,
        SQLiteJobStore,
        create_app,
    )
except ModuleNotFoundError as exc:
    # The permanent repository-wide invariant suite intentionally runs in a
    # minimal stdlib-only environment. Feature-specific Blackhole CI installs
    # the pinned FastAPI/Pydantic/HTTPX dependencies and exercises this class.
    _OPTIONAL_IMPORT_ERROR = exc
    TestClient = None  # type: ignore[assignment]
    AuthenticationDenied = RuntimeError  # type: ignore[assignment,misc]
    BrokerLeaseFileVerifier = None  # type: ignore[assignment]
    LeaseDenied = RuntimeError  # type: ignore[assignment,misc]
    SQLiteJobStore = None  # type: ignore[assignment]
    create_app = None  # type: ignore[assignment]


class StaticAuthenticator:
    def authenticate(self, authorization):
        if authorization != "Bearer test-token":
            raise AuthenticationDenied("denied")
        return "FA3-MARKETING-STUDIO"


class ValidLeaseVerifier:
    def verify(self, lease_id, *, minimum_tu, required_features):
        return {
            "lease_id": lease_id,
            "device_uuid": "GPU-TEST",
            "pci_bdf": "0000:01:00.0",
            "broker_validation": "VALID",
            "virtual_tu": minimum_tu,
            "capabilities": sorted(required_features),
            "purpose_scope": ["BLACKHOLE_NEURAL_MEDIA"],
        }


class DenyLeaseVerifier:
    def verify(self, lease_id, *, minimum_tu, required_features):
        raise LeaseDenied("HRB rejected lease")


def payload(request_id=None):
    return {
        "schema_version": "fa3.blackhole.request.v3",
        "request_id": str(request_id or uuid4()),
        "lease_id": "ACC-LEASE-8831",
        "requirements": {
            "minimum_tu": 1.5,
            "required_features": ["cuda", "nvenc", "onnxruntime-gpu", "zero-copy"],
        },
        "pipeline": {
            "operation": "neural_media_enhance",
            "model_id": "FA3-MODEL-MEDIA-ENHANCER-V3",
            "input_asset_id": "FA3-ASSET-PROMO-NYERS-001",
            "output_profile": "1080p-h264",
        },
    }


@unittest.skipIf(
    _OPTIONAL_IMPORT_ERROR is not None,
    f"Blackhole API feature dependencies are not installed in this test environment: {_OPTIONAL_IMPORT_ERROR}",
)
class BlackholeApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        store = SQLiteJobStore(Path(self.temp.name) / "jobs.sqlite3")
        self.client = TestClient(
            create_app(
                authenticator=StaticAuthenticator(),
                lease_verifier=ValidLeaseVerifier(),
                store=store,
            )
        )

    def tearDown(self):
        self.temp.cleanup()

    @property
    def headers(self):
        return {"Authorization": "Bearer test-token"}

    def test_accepts_declarative_request_only_after_persistence(self):
        response = self.client.post("/api/v3/bridge/submit", json=payload(), headers=self.headers)
        self.assertEqual(202, response.status_code, response.text)
        receipt = response.json()
        self.assertEqual("ACCEPTED", receipt["state"])
        status_response = self.client.get(receipt["status_uri"], headers=self.headers)
        self.assertEqual(200, status_response.status_code)
        self.assertEqual(receipt["job_id"], status_response.json()["job_id"])

    def test_runtime_execution_controls_are_forbidden(self):
        body = payload()
        body["runtime_environment"] = {
            "ffmpeg_binary_override": "/tmp/evil",
            "environment_variables": {"CUDA_LAUNCH_BLOCKING": "1"},
        }
        response = self.client.post("/api/v3/bridge/submit", json=body, headers=self.headers)
        self.assertEqual(422, response.status_code)

    def test_owner_priority_and_filesystem_model_path_are_forbidden(self):
        body = payload()
        body["owner"] = "attacker"
        body["execution_priority"] = "CRITICAL"
        body["pipeline"]["neural_model_path"] = "/etc/passwd"
        response = self.client.post("/api/v3/bridge/submit", json=body, headers=self.headers)
        self.assertEqual(422, response.status_code)

    def test_incomplete_capability_set_fails_closed(self):
        body = payload()
        body["requirements"]["required_features"] = ["cuda", "nvenc"]
        response = self.client.post("/api/v3/bridge/submit", json=body, headers=self.headers)
        self.assertEqual(412, response.status_code)

    def test_hrb_failure_returns_412(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(
                create_app(
                    authenticator=StaticAuthenticator(),
                    lease_verifier=DenyLeaseVerifier(),
                    store=SQLiteJobStore(Path(tmp) / "jobs.sqlite3"),
                )
            )
            response = client.post("/api/v3/bridge/submit", json=payload(), headers=self.headers)
        self.assertEqual(412, response.status_code)

    def test_authentication_failure_returns_401(self):
        response = self.client.post("/api/v3/bridge/submit", json=payload())
        self.assertEqual(401, response.status_code)

    def test_idempotent_replay_returns_same_job(self):
        rid = uuid4()
        first = self.client.post("/api/v3/bridge/submit", json=payload(rid), headers=self.headers)
        second = self.client.post("/api/v3/bridge/submit", json=payload(rid), headers=self.headers)
        self.assertEqual(202, first.status_code)
        self.assertEqual(first.json()["job_id"], second.json()["job_id"])
        self.assertTrue(second.json()["idempotent_replay"])

    def test_real_hrb_adapter_rejects_underprovisioned_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lease_dir = root / "leases"
            lease_dir.mkdir()
            broker = root / "fa3-host-resource-broker"
            broker.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            broker.chmod(0o755)
            lease = {
                "lease_id": "ACC-LEASE-8831",
                "virtual_tu": 1.0,
                "capabilities": ["cuda", "nvenc", "onnxruntime-gpu", "zero-copy"],
                "purpose_scope": ["BLACKHOLE_NEURAL_MEDIA"],
            }
            (lease_dir / "ACC-LEASE-8831.json").write_text(json.dumps(lease), encoding="utf-8")
            verifier = BrokerLeaseFileVerifier(lease_dir, broker)
            with self.assertRaises(LeaseDenied):
                verifier.verify(
                    "ACC-LEASE-8831",
                    minimum_tu=1.5,
                    required_features={"cuda", "nvenc", "onnxruntime-gpu", "zero-copy"},
                )

    def test_real_hrb_adapter_accepts_broker_validated_sufficient_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lease_dir = root / "leases"
            lease_dir.mkdir()
            broker = root / "fa3-host-resource-broker"
            broker.write_text("#!/bin/sh\n[ \"$1\" = validate-lease ] && [ -f \"$2\" ]\n", encoding="utf-8")
            broker.chmod(0o755)
            lease = {
                "lease_id": "ACC-LEASE-8831",
                "virtual_tu": 2.0,
                "capabilities": ["cuda", "nvenc", "onnxruntime-gpu", "zero-copy"],
                "purpose_scope": ["BLACKHOLE_NEURAL_MEDIA"],
            }
            (lease_dir / "ACC-LEASE-8831.json").write_text(json.dumps(lease), encoding="utf-8")
            verifier = BrokerLeaseFileVerifier(lease_dir, broker)
            verified = verifier.verify(
                "ACC-LEASE-8831",
                minimum_tu=1.5,
                required_features={"cuda", "nvenc", "onnxruntime-gpu", "zero-copy"},
            )
            self.assertEqual(2.0, verified["virtual_tu"])

    def test_real_hrb_adapter_rejects_symlinked_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lease_dir = root / "leases"
            lease_dir.mkdir()
            broker = root / "fa3-host-resource-broker"
            broker.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            broker.chmod(0o755)
            target = root / "outside.json"
            target.write_text(json.dumps({"lease_id": "ACC-LEASE-8831"}), encoding="utf-8")
            os.symlink(target, lease_dir / "ACC-LEASE-8831.json")
            verifier = BrokerLeaseFileVerifier(lease_dir, broker)
            with self.assertRaises(LeaseDenied):
                verifier.verify(
                    "ACC-LEASE-8831",
                    minimum_tu=1.5,
                    required_features={"cuda", "nvenc", "onnxruntime-gpu", "zero-copy"},
                )

    def test_request_id_reuse_with_modified_payload_returns_409(self):
        rid = uuid4()
        first_body = payload(rid)
        self.assertEqual(
            202,
            self.client.post("/api/v3/bridge/submit", json=first_body, headers=self.headers).status_code,
        )
        second_body = payload(rid)
        second_body["requirements"]["minimum_tu"] = 2.0
        response = self.client.post("/api/v3/bridge/submit", json=second_body, headers=self.headers)
        self.assertEqual(409, response.status_code)


if __name__ == "__main__":
    unittest.main()
