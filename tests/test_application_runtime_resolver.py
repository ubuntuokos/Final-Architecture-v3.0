from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_application_runtime_resolver as resolver


class ApplicationRuntimeResolverTests(unittest.TestCase):
    def test_registry_is_shared_non_authoritative_and_extensible(self):
        registry = resolver.load_registry(ROOT)
        self.assertEqual(175, registry["capability_count"])
        self.assertFalse(registry["authority"])
        self.assertFalse(registry["source_of_execution_truth"])
        self.assertEqual(
            {"NATIVE", "DEB", "RPM", "PACMAN", "FLATPAK", "SNAP", "APPIMAGE", "PORTABLE", "MANUAL"},
            set(registry["supported_packaging_classes"]),
        )
        app_ids = {row["application_id"] for row in registry["applications"]}
        self.assertTrue({"BFORARTISTS", "BLENDER", "GIMP", "KRITA", "LIBREOFFICE"} <= app_ids)

    def test_dcc_group_accepts_either_engine_without_requiring_both(self):
        group = resolver.group_spec(ROOT, "DCC_3D")
        self.assertEqual(1, group["minimum_healthy_instances"])
        self.assertEqual(["BFORARTISTS", "BLENDER"], group["qualification_preference"])
        self.assertEqual(
            "QUALIFICATION_PROBE_ONLY_NOT_USER_RUNTIME_SELECTION",
            group["qualification_selection_semantics"],
        )

    def test_manual_appimage_is_discovered_without_install_authority(self):
        with tempfile.TemporaryDirectory() as td:
            app = Path(td) / "Bforartists.AppImage"
            app.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            app.chmod(0o755)
            with mock.patch.dict(os.environ, {"FA3_BFORARTISTS_PORTABLE_EXECUTABLE": str(app)}, clear=False):
                rows = resolver.discover_candidates(ROOT, "BFORARTISTS")
        match = next(row for row in rows if row["source"] == "PORTABLE_ENV:FA3_BFORARTISTS_PORTABLE_EXECUTABLE")
        self.assertEqual("APPIMAGE", match["packaging"])
        self.assertFalse(match["selectable"])
        self.assertEqual("UNPROBED", match["health"])

    def test_flatpak_can_be_healthy_while_broken_native_candidate_is_rejected(self):
        spec = resolver.application_spec(ROOT, "BLENDER")
        native = {
            "application_id": "BLENDER",
            "display_name": "Blender",
            "packaging": "NATIVE",
            "launch_prefix": ["/usr/bin/blender"],
            "identity": "NATIVE:/usr/bin/blender",
            "source": "PATH:blender",
            "package_id": None,
            "health": "UNPROBED",
            "selectable": False,
        }
        flatpak = {
            **native,
            "packaging": "FLATPAK",
            "launch_prefix": ["/usr/bin/flatpak", "run", "org.blender.Blender"],
            "identity": "FLATPAK:org.blender.Blender",
            "source": "FLATPAK",
            "package_id": "org.blender.Blender",
        }

        def fake_run(argv, timeout=20):
            if argv[0] == "/usr/bin/blender":
                return mock.Mock(returncode=127, stdout="", stderr="missing shared library")
            return mock.Mock(returncode=0, stdout="FA3_APPLICATION_RUNTIME_PASS\n", stderr="")

        with mock.patch.object(resolver, "_run", side_effect=fake_run):
            bad = resolver.probe_candidate(native, spec)
            good = resolver.probe_candidate(flatpak, spec)
        self.assertEqual("UNHEALTHY", bad["health"])
        self.assertFalse(bad["selectable"])
        self.assertEqual("HEALTHY", good["health"])
        self.assertTrue(good["selectable"])

    def test_desktop_entry_can_discover_non_path_deb_style_install(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            apps = root / "applications"
            apps.mkdir()
            executable = root / "bforartists"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            desktop = apps / "de.bforartists.Bforartists.desktop"
            desktop.write_text(
                "[Desktop Entry]\nType=Application\nName=Bforartists\n"
                f"Exec={executable} %F\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(root)}, clear=False):
                with mock.patch.object(resolver, "_package_class_for_path", return_value=("DEB", "bforartists")):
                    rows = resolver.discover_candidates(ROOT, "BFORARTISTS")
        desktop_rows = [row for row in rows if row["source"].startswith("DESKTOP:")]
        self.assertTrue(desktop_rows)
        self.assertEqual("DEB", desktop_rows[0]["packaging"])
        self.assertEqual("bforartists", desktop_rows[0]["package_id"])

    def test_qualification_selection_ignores_ambient_engine_override(self):
        group = resolver.group_spec(ROOT, "DCC_3D")
        self.assertNotIn("selection_env", group)
        source = (ROOT / "src/fa3_application_runtime_resolver.py").read_text(encoding="utf-8")
        self.assertNotIn("FA3_CURRENT_HOST_DCC_APPLICATION", source)

    def test_package_presence_is_not_runtime_health(self):
        candidate = {
            "application_id": "GIMP",
            "display_name": "GIMP",
            "packaging": "SNAP",
            "launch_prefix": ["/usr/bin/snap", "run", "gimp"],
            "identity": "SNAP:gimp",
            "source": "SNAP",
            "package_id": "gimp",
            "health": "UNPROBED",
            "selectable": False,
        }
        spec = resolver.application_spec(ROOT, "GIMP")
        with mock.patch.object(
            resolver,
            "_run",
            return_value=mock.Mock(returncode=1, stdout="", stderr="runtime failed"),
        ):
            probed = resolver.probe_candidate(candidate, spec)
        self.assertEqual("UNHEALTHY", probed["health"])
        self.assertFalse(probed["selectable"])


if __name__ == "__main__":
    unittest.main()
