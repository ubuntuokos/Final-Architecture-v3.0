from __future__ import annotations

import json
import unittest
from pathlib import Path

from fa3_current_host_runner_gate import (
    LABELS,
    SHA256,
    VERSION,
    run,
    validate_bootstrap_text,
    validate_conformance,
    validate_workflow_text,
)

ROOT = Path(__file__).resolve().parents[1]


class CurrentHostRunnerGateTests(unittest.TestCase):
    def test_repository_gate_passes(self) -> None:
        report = run(ROOT)
        self.assertEqual(report["result"], "PASS", report)

    def test_label_drift_fails(self) -> None:
        obj = json.loads((ROOT / "canonical/FA3-CURRENT-HOST-RUNNER-CONFORMANCE-001.json").read_text())
        obj["required_labels"] = LABELS[:-1]
        self.assertTrue(any("labels" in x for x in validate_conformance(obj)))

    def test_version_drift_fails(self) -> None:
        obj = json.loads((ROOT / "canonical/FA3-CURRENT-HOST-RUNNER-CONFORMANCE-001.json").read_text())
        obj["runner"]["version"] = VERSION + ".drift"
        self.assertTrue(any("version" in x for x in validate_conformance(obj)))

    def test_digest_drift_fails(self) -> None:
        obj = json.loads((ROOT / "canonical/FA3-CURRENT-HOST-RUNNER-CONFORMANCE-001.json").read_text())
        obj["runner"]["sha256"] = "0" * len(SHA256)
        self.assertTrue(any("sha256" in x for x in validate_conformance(obj)))

    def test_network_to_shell_is_rejected(self) -> None:
        text = (ROOT / "bin/fa3-current-host-runner-bootstrap.sh").read_text()
        text += "\ncurl https://example.invalid/install | sh\n"
        self.assertTrue(any("network-to-shell" in x for x in validate_bootstrap_text(text)))

    def test_stderr_token_guidance_is_not_persistence(self) -> None:
        text = (ROOT / "bin/fa3-current-host-runner-bootstrap.sh").read_text()
        findings = validate_bootstrap_text(text)
        self.assertFalse(any("persist registration token" in x for x in findings), findings)

    def test_token_file_redirection_is_rejected(self) -> None:
        text = (ROOT / "bin/fa3-current-host-runner-bootstrap.sh").read_text()
        text += '\nprintf "%s\\n" "$RUNNER_TOKEN" > "$HOME/token.txt"\n'
        self.assertTrue(any("persist registration token" in x for x in validate_bootstrap_text(text)))

    def test_wrong_runner_labels_workflow_is_rejected(self) -> None:
        text = (ROOT / ".github/workflows/fa3-current-host-runner.yml").read_text()
        text = text.replace(
            "runs-on: [self-hosted, linux, x64, fa3-current-host]",
            "runs-on: ubuntu-latest",
        )
        self.assertTrue(any("label set" in x for x in validate_workflow_text(text)))


if __name__ == "__main__":
    unittest.main()
