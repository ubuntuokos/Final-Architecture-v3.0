import unittest
from pathlib import Path

from src import fa3_gui_gate


ROOT = Path(__file__).resolve().parents[1]


class Fa3GuiGateTests(unittest.TestCase):
    def test_gui_materialization_is_fail_closed_and_authority_neutral(self):
        self.assertEqual([], fa3_gui_gate.validate())

    def test_checkpoint_manager_is_operational_shared_model_library(self):
        qml = (ROOT / "apps/fa3-control-center/qml/CheckpointManagerPage.qml").read_text(encoding="utf-8")
        service = (ROOT / "apps/fa3-control-center/src/ModelLibraryService.cpp").read_text(encoding="utf-8")
        main_cpp = (ROOT / "apps/fa3-control-center/src/main.cpp").read_text(encoding="utf-8")
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")

        for token in [
            "SHARED STORAGE", "Checkpoints", "LoRA", "VAE", "Diffusion / Video",
            "CivitAI böngészés", "Hugging Face böngészés", "Built-in Model Downloader",
            "ComfyUI", "Automatic1111", "Forge", "Fooocus", "DropArea", "Metadata & Preview",
        ]:
            self.assertIn(token, qml)

        for token in [
            "importFiles", "moveModel", "saveMetadata", "setPreview", "linkClient",
            "create_directory_symlink", "startDownload", "NoLessSafeRedirectPolicy",
            "Credential/token nem kerülhet URL-be",
        ]:
            self.assertIn(token, service)

        self.assertIn('setContextProperty("fa3ModelLibrary"', main_cpp)
        self.assertIn("ModelLibraryService.cpp", cmake)
        self.assertIn("Qt6::Network", cmake)

    def test_integrations_follows_ai_studio_and_application_search_is_fa3_scoped(self):
        main = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")

        self.assertIn("property var fa3ApplicationIndex", main)
        self.assertIn("function searchFa3Applications", main)
        self.assertIn("var apps = searchFa3Applications(needle)", main)
        self.assertNotIn("fa3Repository.searchInstalledApplications(needle)", main)
        for app in ["ComfyUI", "Automatic1111", "Forge", "Fooocus", "Krita", "GIMP", "Kdenlive", "Open WebUI", "OpenYak", "Ollama", "LM Studio"]:
            self.assertIn('title: "' + app + '"', main)

        studio = 'NavButton { iconText: "✦"; label: "AI Studio"; pageIndex: 3 }'
        integrations = 'NavButton { iconText: "↔"; label: "Integrations"; pageIndex: 14 }'
        self.assertEqual(1, main.count(integrations))
        self.assertIn(studio + "\n                        " + integrations, main)


if __name__ == "__main__":
    unittest.main()
