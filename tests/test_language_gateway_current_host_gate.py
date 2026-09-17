from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_language_gateway_current_host_gate import validate_receipt


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestLanguageGatewayCurrentHostGate(unittest.TestCase):
    def _fixture_root(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "evidence/receipts").mkdir(parents=True)
        (root / "evidence/runtime/language-gateway-current-host").mkdir(parents=True)
        (root / "deployment/litellm").mkdir(parents=True)
        (root / "evidence").mkdir(exist_ok=True)
        shutil.copy2(ROOT / "evidence/collect-language-gateway-current-host.py", root / "evidence/collect-language-gateway-current-host.py")
        shutil.copy2(ROOT / "deployment/litellm/config.yaml", root / "deployment/litellm/config.yaml")

        runtime_path = root / "evidence/runtime/language-gateway-current-host/execution.json"
        runtime = {
            "schema": "fa3.language-gateway-current-host-execution.v1",
            "status": "PASS",
            "gateway_calls_real": True,
            "raw_credentials_recorded": False,
            "raw_samples_recorded": False,
        }
        runtime_path.write_text(json.dumps(runtime), encoding="utf-8")

        def direction(source: str, target: str) -> dict:
            return {
                "status": "PASS",
                "source_language": source,
                "target_language": target,
                "source_sample_sha256": "sha256:" + "1" * 64,
                "source_sample_bytes": 32,
                "output_sha256": "sha256:" + "2" * 64,
                "output_bytes": 48,
                "translation_response_model": "backend-model",
                "validation_response_model": "backend-model",
                "validator_independence": "SAME_GATEWAY_MODEL_NOT_INDEPENDENT",
                "bridge_receipt": {
                    "native_or_mediated": "MEDIATED",
                    "provider_locality": "LOCAL",
                    "protected_token_validation": "PASS",
                    "protected_token_count": 4,
                    "semantic_validation": "PASS",
                    "authority_expanded_by_mediation": False,
                    "current_host_production_claim": False,
                },
            }

        receipt = {
            "schema": "fa3.language-gateway-current-host-receipt.v1",
            "status": "PASS",
            "evidence_level": "CURRENT_HOST_GATEWAY_BRIDGE_E2E_PASS",
            "current_host_execution": True,
            "test_fixture": True,
            "production_promotion_claim": False,
            "translation_quality_claim": False,
            "host": {"fingerprint_sha256": "sha256:" + "a" * 64, "runner_class": "fa3-current-host"},
            "languages": {"primary": "hu-HU", "secondary": "en-US"},
            "gateway": {
                "base_url": "http://127.0.0.1:4000",
                "loopback": True,
                "authenticated": True,
                "credential_material_logged": False,
                "models_endpoint_pass": True,
                "requested_alias_listed": True,
                "model_alias": "fa3-local-primary",
            },
            "directions": [direction("hu-HU", "en-US"), direction("en-US", "hu-HU")],
            "integrity": {
                "collector_sha256": sha256(root / "evidence/collect-language-gateway-current-host.py"),
                "litellm_config_sha256": sha256(root / "deployment/litellm/config.yaml"),
            },
            "execution_evidence": {
                "path": "evidence/runtime/language-gateway-current-host/execution.json",
                "sha256": sha256(runtime_path),
            },
        }
        (root / "evidence/receipts/language-gateway-current-host.json").write_text(json.dumps(receipt), encoding="utf-8")
        return root

    def test_fixture_validates_only_when_explicitly_allowed(self) -> None:
        root = self._fixture_root()
        self.assertEqual(validate_receipt(root, require_live=False)["result"], "PASS")
        live = validate_receipt(root, require_live=True)
        self.assertEqual(live["result"], "FAIL")
        self.assertTrue(any(item["code"] == "LANG-HOST-006" for item in live["findings"]))

    def test_promotion_overclaim_fails_closed(self) -> None:
        root = self._fixture_root()
        path = root / "evidence/receipts/language-gateway-current-host.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["production_promotion_claim"] = True
        path.write_text(json.dumps(receipt), encoding="utf-8")
        checked = validate_receipt(root, require_live=False)
        self.assertEqual(checked["result"], "FAIL")
        self.assertTrue(any(item["code"] == "LANG-HOST-007" for item in checked["findings"]))

    def test_non_loopback_gateway_fails_closed(self) -> None:
        root = self._fixture_root()
        path = root / "evidence/receipts/language-gateway-current-host.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["gateway"]["base_url"] = "https://example.com"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        checked = validate_receipt(root, require_live=False)
        self.assertEqual(checked["result"], "FAIL")
        self.assertTrue(any(item["code"] == "LANG-HOST-009" for item in checked["findings"]))

    def test_missing_bidirectional_route_fails_closed(self) -> None:
        root = self._fixture_root()
        path = root / "evidence/receipts/language-gateway-current-host.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["directions"] = receipt["directions"][:1]
        path.write_text(json.dumps(receipt), encoding="utf-8")
        checked = validate_receipt(root, require_live=False)
        self.assertEqual(checked["result"], "FAIL")
        self.assertTrue(any(item["code"] in {"LANG-HOST-024", "LANG-HOST-033"} for item in checked["findings"]))


if __name__ == "__main__":
    unittest.main()
