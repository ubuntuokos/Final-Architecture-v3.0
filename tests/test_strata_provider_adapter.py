from __future__ import annotations

import importlib.util
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fa3_strata_provider_adapter", ROOT / "src/fa3_strata_provider_adapter.py")
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_GET(self):
        if self.path == "/health":
            body = {"status": "ok", "max_context": 262144, "model": "live-model", "images": True, "api_key": False}
        elif self.path == "/v1/models":
            body = {"object": "list", "data": [{"id": "live-model", "object": "model"}]}
        else:
            self.send_response(404)
            self.end_headers()
            return
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class StrataProviderAdapterTests(unittest.TestCase):
    def test_regression(self):
        self.assertEqual(mod.regression_check()["result"], "PASS")

    def test_external_endpoint_is_fail_closed(self):
        with self.assertRaises(mod.ProbeError):
            mod._base_url("https://example.com:8080/v1")

    def test_loopback_probe_without_promotion_claim(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            out = mod.probe(f"http://127.0.0.1:{server.server_address[1]}/v1")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(out["result"], "PASS")
        self.assertEqual(out["model_ids"], ["live-model"])
        self.assertFalse(out["network_egress_performed"])
        self.assertFalse(out["application_path_proven"])
        self.assertFalse(out["current_host_runtime_promotion_claim"])
        self.assertFalse(out["runtime_identity"]["immutable_identity_verified"])

    def test_runtime_digest_can_be_bound_without_promoting(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            out = mod.probe(f"http://127.0.0.1:{server.server_address[1]}", runtime_sha256="a" * 64)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertTrue(out["runtime_identity"]["immutable_identity_verified"])
        self.assertFalse(out["current_host_runtime_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
