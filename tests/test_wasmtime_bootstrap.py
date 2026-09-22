import re
import unittest
from pathlib import Path


class WasmtimeBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.script = (self.root / "bin/fa3-bootstrap-wasmtime").read_text(encoding="utf-8")
        self.workflow = (self.root / ".github/workflows/fa3-global-current-host-closure.yml").read_text(encoding="utf-8")

    def test_bootstrap_is_version_and_digest_pinned(self):
        self.assertIn('VERSION="48.0.2"', self.script)
        self.assertIn(
            'EXPECTED_SHA256="f2b0ad1ce9253f2f9a38793c2c42cd1cba4e90b27dc40d685eaf723dc8438d94"',
            self.script,
        )
        self.assertRegex(self.script, r"sha256sum .*archive")
        self.assertNotIn("releases/latest", self.script)

    def test_bootstrap_is_rootless_and_workspace_scoped(self):
        self.assertIn(".fa3-current-host/tooling/wasmtime-v", self.script)
        self.assertNotRegex(self.script, r"\bsudo\b")
        self.assertNotIn("/usr/local/bin", self.script)

    def test_workflow_bootstraps_before_identity_proof(self):
        bootstrap = self.workflow.index("Bootstrap pinned Wasmtime when absent")
        identity = self.workflow.index("Prove runner control-plane identity")
        self.assertLess(bootstrap, identity)
        self.assertIn('echo "$tool_bin" >> "$GITHUB_PATH"', self.workflow)
        self.assertIn("command -v wasmtime", self.workflow)


if __name__ == "__main__":
    unittest.main()
