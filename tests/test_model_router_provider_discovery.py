from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_model_router_provider_discovery as discovery


class TestModelRouterProviderDiscovery(unittest.TestCase):
    def _root(self, providers):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        receipt = root / discovery.RECEIPT_REL
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({"status": "PASS", "providers": providers}), encoding="utf-8")
        return tmp, root

    def test_only_admitted_and_live_providers_are_emitted(self):
        tmp, root = self._root({
            discovery.LM_STUDIO_PROVIDER_ID: {"status": "PASS", "selected_model_key": "runtime-proven-model"},
            discovery.OLLAMA_PROVIDER_ID: {"status": "UNAVAILABLE_OR_FAILED"},
        })
        try:
            output = root / "providers.json"
            with patch.object(discovery, "models_live", return_value=True):
                registry = discovery.discover(root, output, 0.1)
            self.assertTrue(registry["provider_neutral"])
            self.assertFalse(registry["physical_model_pins"])
            self.assertEqual(len(registry["providers"]), 1)
            row = registry["providers"][0]
            self.assertEqual(row["provider_id"], discovery.LM_STUDIO_PROVIDER_ID)
            self.assertEqual(row["priority"], 50)
            self.assertEqual(row["selection_origin"], "CURRENT_HOST_LIVE_ENDPOINT_DISCOVERY")
            self.assertEqual(row["preferred_models"], ["runtime-proven-model"])
            self.assertEqual(row["model_preference_origin"], "CURRENT_HOST_ADMISSION_EVIDENCE")
            self.assertFalse(registry["physical_model_pins"])
        finally:
            tmp.cleanup()

    def test_no_admitted_live_provider_fails_closed(self):
        tmp, root = self._root({
            discovery.LM_STUDIO_PROVIDER_ID: {"status": "UNAVAILABLE_OR_FAILED"},
            discovery.OLLAMA_PROVIDER_ID: {"status": "UNAVAILABLE_OR_FAILED"},
        })
        try:
            with patch.object(discovery, "models_live", return_value=True):
                with self.assertRaises(RuntimeError):
                    discovery.discover(root, root / "providers.json", 0.1)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
