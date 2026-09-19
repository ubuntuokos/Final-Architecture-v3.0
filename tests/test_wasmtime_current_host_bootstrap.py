from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WasmtimeBootstrapTests(unittest.TestCase):
    def test_dependency_record_and_bootstrap_pin_match(self):
        record = json.loads(
            (ROOT / "canonical/FA3-WASMTIME-CURRENT-HOST-DEPENDENCY-001.json").read_text()
        )
        script = (ROOT / "bin/fa3-wasmtime-bootstrap").read_text()
        self.assertEqual("48.0.2", record["version"])
        self.assertRegex(record["asset_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn(f'EXPECTED_VERSION="{record["version"]}"', script)
        self.assertIn(f'EXPECTED_SHA256="{record["asset_sha256"]}"', script)
        self.assertIn("bytecodealliance/wasmtime/releases/download", script)
        self.assertIn("--proto '=https'", script)
        self.assertIn("must run rootless", script)
        self.assertIn("global_promotion_claim", script)

    def test_dependency_is_non_authoritative_and_nonpromoting(self):
        record = json.loads(
            (ROOT / "canonical/FA3-WASMTIME-CURRENT-HOST-DEPENDENCY-001.json").read_text()
        )
        self.assertFalse(record["current_host_runtime_pass_claim"])
        self.assertFalse(record["global_promotion_claim"])
        self.assertEqual(0, record["capability_delta"])
        self.assertEqual(0, record["architectural_authority_delta"])
        self.assertEqual(["CAP-028"], record["capability_bindings"])


if __name__ == "__main__":
    unittest.main()
