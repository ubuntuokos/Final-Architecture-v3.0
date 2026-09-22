import json
import tempfile
import unittest
from pathlib import Path

from fa3_model_router_runtime import (
    AUTHORITY_ID,
    CATALOG_SCHEMA,
    ROUTES_SCHEMA,
    RouterDenied,
    compile_litellm_config,
    resolve,
)


class ModelRouterRuntimeTests(unittest.TestCase):
    def _write(self, root: Path, name: str, obj: dict) -> Path:
        p = root / name
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p

    def test_dynamic_local_preferred_selection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            routes = self._write(root, "routes.json", {
                "schema": ROUTES_SCHEMA,
                "authority": AUTHORITY_ID,
                "routes": [{"route":"fa3-x","required_capabilities":["text"],"preferred_capabilities":["reasoning"],"allow_external":False}],
            })
            catalog = self._write(root, "catalog.json", {
                "schema": CATALOG_SCHEMA,
                "provider_neutral": True,
                "candidates": [
                    {"candidate_id":"a","provider_id":"P-A","runtime":"OPENAI_COMPATIBLE","model_id":"m-a","litellm_model":"openai/m-a","api_base":"http://127.0.0.1:1/v1","locality":"LOCAL","admitted":True,"available":True,"capabilities":["text"],"priority":1},
                    {"candidate_id":"b","provider_id":"P-B","runtime":"OPENAI_COMPATIBLE","model_id":"m-b","litellm_model":"openai/m-b","api_base":"http://127.0.0.1:2/v1","locality":"LOCAL","admitted":True,"available":True,"capabilities":["text","reasoning"],"priority":50},
                ],
            })
            out = resolve(catalog, routes)
            self.assertEqual(out["routes"][0]["candidate_id"] if "candidate_id" in out["routes"][0] else out["routes"][0]["selected_candidate_id"], "b")
            self.assertFalse(out["physical_model_pinned"])

    def test_remote_denied_when_route_local_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            routes = self._write(root, "routes.json", {
                "schema": ROUTES_SCHEMA,
                "authority": AUTHORITY_ID,
                "routes": [{"route":"fa3-x","required_capabilities":["text"],"preferred_capabilities":[],"allow_external":False}],
            })
            catalog = self._write(root, "catalog.json", {
                "schema": CATALOG_SCHEMA,
                "provider_neutral": True,
                "candidates": [{"candidate_id":"r","provider_id":"P-R","runtime":"OPENAI_COMPATIBLE","model_id":"m","litellm_model":"openai/m","api_base":"https://example.invalid/v1","locality":"REMOTE","admitted":True,"available":True,"capabilities":["text"]}],
            })
            with self.assertRaises(RouterDenied):
                resolve(catalog, routes)

    def test_generated_config_uses_route_alias(self):
        resolution = {
            "authority": AUTHORITY_ID,
            "routes": [{"route":"fa3-route","litellm_model":"openai/runtime-model","api_base":"http://127.0.0.1:9000/v1","credential_env":None}],
        }
        text = compile_litellm_config(resolution)
        self.assertIn('model_name: "fa3-route"', text)
        self.assertIn('model: "openai/runtime-model"', text)
        self.assertIn("os.environ/FA3_LITELLM_MASTER_KEY", text)


if __name__ == "__main__":
    unittest.main()
