from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OpenModelDbBrowserDownloadTests(unittest.TestCase):
    def load_json(self, rel: str) -> dict:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_canonical_overlay_preserves_authority_boundaries(self) -> None:
        policy = self.load_json("canonical/openmodeldb-browser-download-enforcement.json")
        decision = self.load_json("canonical/decisions/FA3-DEC-OPENMODELDB-BROWSER-DOWNLOAD-2026-09-13.json")
        self.assertEqual(policy["provider_id"], "FA3-PROVIDER-OPENMODELDB-001")
        self.assertEqual(policy["parent_profile_id"], "FA3-MODEL-MANAGER-001")
        self.assertFalse(policy["architectural_authority"])
        self.assertEqual(policy["new_capabilities"], 0)
        self.assertEqual(policy["capability_count_after"], 143)
        self.assertEqual(decision["status"], "CANONICAL_CLOSED")
        self.assertFalse(decision["runtime_promotion_claim"])

    def test_download_pipeline_is_staged_and_fail_closed(self) -> None:
        policy = self.load_json("canonical/openmodeldb-browser-download-enforcement.json")
        pipeline = policy["download_pipeline"]
        self.assertEqual(pipeline["parallelism"], 1)
        self.assertTrue(pipeline["https_only"])
        self.assertTrue(pipeline["sha256_required_before_transport"])
        self.assertEqual(pipeline["runtime_directory_write"], "FORBIDDEN")

    def test_reconciled_gui_and_service_wiring(self) -> None:
        qml = (ROOT / "apps/fa3-control-center/qml/OpenModelDbPage.qml").read_text(encoding="utf-8")
        service = (ROOT / "apps/fa3-control-center/src/OpenModelDbService.cpp").read_text(encoding="utf-8")
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
        main_cpp = (ROOT / "apps/fa3-control-center/src/main.cpp").read_text(encoding="utf-8")
        overlay = (ROOT / "apps/fa3-control-center/qml/OperationsExtensionsOverlay.qml").read_text(encoding="utf-8")
        self.assertIn('text: "Hugging Face ↗"', qml)
        self.assertIn('text: "★ OpenModelDB ↗"', qml)
        self.assertIn("highlighted: true", qml)
        self.assertIn("Download manager", qml)
        self.assertIn("https://www.openmodeldb.info/api/v1/models", service)
        self.assertIn("QCryptographicHash::Sha256", service)
        self.assertIn("OpenModelDbService.cpp", cmake)
        self.assertIn("OpenModelDbPage.qml", cmake)
        self.assertIn('setContextProperty("fa3OpenModelDb"', main_cpp)
        self.assertIn("OpenModelDbPage", overlay)


if __name__ == "__main__":
    unittest.main()
