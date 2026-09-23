from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fa3_language_gateway_current_host_gate import _is_loopback_url, validate_receipt


class LanguageGatewayCurrentHostGateTests(unittest.TestCase):
    def test_missing_real_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = validate_receipt(Path(tmp), require_live=True)
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(any(x["code"] == "LANG-HOST-001" for x in report["findings"]))

    def test_only_loopback_gateway_urls_are_accepted(self):
        self.assertTrue(_is_loopback_url("http://127.0.0.1:4000"))
        self.assertTrue(_is_loopback_url("http://localhost:4000/"))
        self.assertFalse(_is_loopback_url("https://example.com"))
        self.assertFalse(_is_loopback_url("http://user:pass@127.0.0.1:4000"))


if __name__ == "__main__":
    unittest.main()
