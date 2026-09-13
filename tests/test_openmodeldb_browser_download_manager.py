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
        decision = self.load_json(
            "canonical/decisions/FA3-DEC-OPENMODELDB-BROWSER-DOWNLOAD-2026-09-13.json"
        )
        self.assertEqual(policy["provider_id"], "FA3-PROVIDER-OPENMODELDB-001")
        self.assertEqual(policy["parent_profile_id"], "FA3-MODEL-MANAGER-001")
        self.assertFalse(policy["architectural_authority"])
        self.assertEqual(policy["new_capabilities"], 0)
        self.assertEqual(policy["new_architectural_authorities"], 0)
        self.assertEqual(policy["capability_count_after"], 143)
        self.assertEqual(decision["status"], "CANONICAL_CLOSED")
        self.assertFalse(decision["runtime_promotion_claim"])
        self.assertFalse(decision["model_artifact_security_bypass"])

    def test_openmodeldb_tags_remain_discovery_metadata(self) -> None:
        policy = self.load_json("canonical/openmodeldb-browser-download-enforcement.json")
        self.assertEqual(
            policy["catalog"]["upstream_tag_fields"],
            ["id", "name", "category", "color"],
        )
        self.assertEqual(
            policy["catalog"]["tag_semantics"],
            "DISPLAY_UPSTREAM_DISCOVERY_METADATA_WITHOUT_UPGRADING_TO_RUNTIME_EVIDENCE",
        )
        self.assertIn("tag", policy["gui"]["catalog_filters"])
        self.assertIn(
            "OPENMODELDB_TAGS_MUST_NOT_BE_TREATED_AS_RUNTIME_CONFORMANCE_EVIDENCE",
            policy["fail_closed_rules"],
        )

    def test_download_pipeline_is_staged_and_fail_closed(self) -> None:
        policy = self.load_json("canonical/openmodeldb-browser-download-enforcement.json")
        pipeline = policy["download_pipeline"]
        self.assertEqual(pipeline["parallelism"], 1)
        self.assertTrue(pipeline["https_only"])
        self.assertTrue(pipeline["sha256_required_before_transport"])
        self.assertEqual(pipeline["runtime_directory_write"], "FORBIDDEN")
        self.assertEqual(
            pipeline["post_download_state"],
            "VERIFIED_STAGED_AWAITING_SECURITY_ADMISSION",
        )
        self.assertEqual(pipeline["unknown_license"], "ALLOW_STAGING_BUT_BLOCK_PROMOTION")

    def test_gui_has_adjacent_huggingface_and_highlighted_openmodeldb_sources(self) -> None:
        qml = (ROOT / "apps/fa3-control-center/qml/ModelsProvidersPage.qml").read_text(
            encoding="utf-8"
        )
        hf = qml.index('text: "Hugging Face ↗"')
        omdb = qml.index('text: "★ OpenModelDB ↗"')
        self.assertLess(hf, omdb)
        self.assertLess(omdb - hf, 900)
        openmodeldb_button_block = qml[omdb : omdb + 500]
        self.assertIn("highlighted: true", openmodeldb_button_block)
        self.assertIn('https://openmodeldb.info/', openmodeldb_button_block)
        self.assertIn("tagFilter", qml)
        self.assertIn("scaleFilter", qml)
        self.assertIn("architectureFilter", qml)
        self.assertIn("platformFilter", qml)
        self.assertIn("Download manager", qml)

    def test_native_service_uses_openmodeldb_api_sha256_and_app_local_staging(self) -> None:
        source = (ROOT / "apps/fa3-control-center/src/OpenModelDbService.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("https://www.openmodeldb.info/api/v1/models", source)
        self.assertIn("QStandardPaths::AppLocalDataLocation", source)
        self.assertIn("QCryptographicHash::Sha256", source)
        self.assertIn("BLOCKED_CHECKSUM_MISMATCH", source)
        self.assertIn("VERIFIED_STAGED_AWAITING_SECURITY_ADMISSION", source)
        self.assertNotIn("/AI-modells", source)
        self.assertNotIn("ComfyUI/models", source)
        self.assertNotIn("InvokeAI/models", source)

    def test_qt_build_wires_network_service_and_preserves_existing_shell(self) -> None:
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
        main_qml = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
        self.assertIn("Network", cmake)
        self.assertIn("Qt6::Network", cmake)
        self.assertIn("src/OpenModelDbService.cpp", cmake)
        self.assertIn("qml/LegacyMain.qml", cmake)
        self.assertIn("qml/ModelsProvidersPage.qml", cmake)
        self.assertIn("LegacyMain", main_qml)
        self.assertIn("ModelsProvidersPage", main_qml)


if __name__ == "__main__":
    unittest.main()
