from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_canonical_language_gate import run_conformance


class TestCanonicalLanguageGate(unittest.TestCase):
    def test_repository_contract_passes(self) -> None:
        report = run_conformance(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["passed"], 8)
        self.assertEqual(report["total"], 8)
        self.assertFalse(report["current_host_production_claim"])

    def test_user_locale_cannot_replace_canonical_english(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "canonical/profiles").mkdir(parents=True)
            shutil.copy2(
                ROOT / "canonical/profiles/FA3-LANGUAGE-POLICY-001.json",
                root / "canonical/profiles/FA3-LANGUAGE-POLICY-001.json",
            )
            shutil.copy2(
                ROOT / "canonical/language-gateway-enforcement.json",
                root / "canonical/language-gateway-enforcement.json",
            )
            path = root / "canonical/profiles/FA3-LANGUAGE-POLICY-001.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["language_planes"]["canonical_platform_language"]["language"] = "hu"
            path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report = run_conformance(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(item["code"] == "CANLANG-001" for item in report["findings"]))

    def test_localized_identifier_authority_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "canonical/profiles").mkdir(parents=True)
            shutil.copy2(
                ROOT / "canonical/profiles/FA3-LANGUAGE-POLICY-001.json",
                root / "canonical/profiles/FA3-LANGUAGE-POLICY-001.json",
            )
            shutil.copy2(
                ROOT / "canonical/language-gateway-enforcement.json",
                root / "canonical/language-gateway-enforcement.json",
            )
            path = root / "canonical/profiles/FA3-LANGUAGE-POLICY-001.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["canonical_english_surface"]["localized_label_may_replace_machine_identifier"] = True
            path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report = run_conformance(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(item["code"] == "CANLANG-005" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
