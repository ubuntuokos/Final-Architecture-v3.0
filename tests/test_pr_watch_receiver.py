"""Opt-in loopback transport tests. No external network or credentials."""
import hashlib
import hmac
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_pr_watch import ProjectionStore
from fa3_pr_watch_receiver import make_handler, main

SECRET = b"FA3-local-receiver-test-secret-000"
DATA = json.dumps({
    "action": "opened", "repository": {"full_name": "ubuntuokos/Final-Architecture-v3.0"},
    "sender": {"login": "developer"},
    "issue": {"number": 101, "title": "Real signed issue", "updated_at": "2026-09-28T20:00:00Z"}
}).encode()


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = ProjectionStore(Path(self.tmp.name) / "state")
        self.store._ensure_dir()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(SECRET, self.store))
        self.worker = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        self.addCleanup(self.worker.join)

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=3)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally:
            conn.close()

    def test_health_is_non_authoritative(self):
        status, data = self.request("GET", "/health")
        self.assertEqual(200, status)
        self.assertFalse(data["execution_enabled"])
        self.assertFalse(data["authority"])

    def test_real_http_hmac_ingestion_and_duplicate(self):
        headers = {
            "Content-Length": str(len(DATA)),
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-101",
            "X-Hub-Signature-256": "sha256=" + hmac.new(SECRET, DATA, hashlib.sha256).hexdigest(),
        }
        status, first = self.request("POST", "/github", DATA, headers)
        self.assertEqual(202, status)
        self.assertEqual("INGESTED", first["status"])
        status, second = self.request("POST", "/github", DATA, headers)
        self.assertEqual(200, status)
        self.assertEqual("DUPLICATE", second["status"])
        self.assertEqual(1, self.store.operator_projection()["count"])

    def test_unsigned_request_denied_without_state_change(self):
        status, body = self.request("POST", "/github", DATA, {
            "X-GitHub-Event": "issues", "X-GitHub-Delivery": "unsigned",
        })
        self.assertEqual(403, status)
        self.assertEqual("DENIED", body["status"])
        self.assertEqual(0, self.store.operator_projection()["count"])

    def test_wrong_path_rejected(self):
        code, data = self.request("POST", "/admin", DATA)
        self.assertEqual(404, code)

    def test_non_loopback_is_denied_without_socket_creation(self):
        self.assertEqual(2, main(["--bind", "0.0.0.0", "--secret-fd", "1"]))


if __name__ == "__main__":
    unittest.main()
