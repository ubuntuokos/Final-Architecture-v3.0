from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_blackhole_client import BlackholeBridgeClient, BlackholeCredentialError


class FakeResponse:
    status_code = 202
    text = '{"state":"ACCEPTED"}'

    def json(self):
        return {"state": "ACCEPTED"}

    def raise_for_status(self):
        raise AssertionError("raise_for_status must not be called for 202")


class RecordingSession:
    def __init__(self):
        self.call = None

    def post(self, url, **kwargs):
        self.call = (url, kwargs)
        return FakeResponse()


class BlackholeClientTests(unittest.TestCase):
    def _vault(self, directory: str) -> Path:
        path = Path(directory) / "vault.json"
        path.write_text(json.dumps({"api_tokens": {"blackhole_bridge": "secret"}}), encoding="utf-8")
        return path

    def test_missing_vault_raises_exception_not_system_exit(self):
        with self.assertRaises(BlackholeCredentialError):
            BlackholeBridgeClient("http://localhost:8000", "/definitely/missing/vault.json")

    def test_payload_is_declarative_and_timeout_is_mandatory(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = RecordingSession()
            client = BlackholeBridgeClient(
                "http://localhost:8000/",
                self._vault(tmp),
                session=session,
                timeout=(3.0, 30.0),
            )
            receipt = client.submit_zero_copy_job(
                input_asset_id="FA3-ASSET-PROMO-001",
                lease_id="ACC-LEASE-8831",
                request_id=uuid4(),
            )

        self.assertEqual("ACCEPTED", receipt["state"])
        _, kwargs = session.call
        self.assertEqual((3.0, 30.0), kwargs["timeout"])
        body = kwargs["json"]
        serialized = json.dumps(body)
        for forbidden in (
            "ffmpeg_binary_override",
            "environment_variables",
            "CUDA_LAUNCH_BLOCKING",
            "allowed_sm_architectures",
            "execution_priority",
            "owner",
            "neural_model_path",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_request_id_is_uuid(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = BlackholeBridgeClient("http://localhost:8000", self._vault(tmp), session=RecordingSession())
            body = client.build_request(input_asset_id="FA3-ASSET-PROMO-001", lease_id="ACC-LEASE-8831")
        uuid4_type = type(uuid4())
        self.assertIsInstance(uuid4_type(body["request_id"]), uuid4_type)


if __name__ == "__main__":
    unittest.main()
