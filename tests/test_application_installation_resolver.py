import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fa3_application_installation_resolver import (
    SUPPORTED_PACKAGING,
    application_spec,
    discover_registered_application,
    registry,
)


class ApplicationInstallationResolverTests(unittest.TestCase):
    def _root(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        target = root / "canonical/FA3-APPLICATION-INSTALLATION-REGISTRY-001.json"
        target.parent.mkdir(parents=True)
        source = Path("canonical/FA3-APPLICATION-INSTALLATION-REGISTRY-001.json")
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return root

    def test_registry_is_non_authoritative_and_multi_packaging(self):
        data = registry(self._root())
        self.assertFalse(data["authority"])
        self.assertFalse(data["automatic_install"])
        self.assertFalse(data["automatic_fallback"])
        self.assertEqual(set(data["supported_packaging"]), SUPPORTED_PACKAGING)
        ids = {row["application_id"] for row in data["applications"]}
        self.assertTrue({"bforartists", "blender", "gimp", "krita", "libreoffice"} <= ids)

    def test_blender_and_bforartists_are_parallel_not_fallback(self):
        root = self._root()
        bfa = application_spec(root, "bforartists")
        blender = application_spec(root, "blender")
        self.assertIn("de.bforartists.Bforartists", bfa["flatpak_app_ids"])
        self.assertIn("org.blender.Blender", blender["flatpak_app_ids"])
        self.assertIn("blender", blender["snap_names"])
        self.assertEqual(bfa["snap_names"], [])

    def test_deb_package_owned_executable_can_be_discovered_outside_path(self):
        root = self._root()
        fake = root / "opt/bforartists/bforartists"
        fake.parent.mkdir(parents=True)
        fake.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake.chmod(0o755)

        def runner(argv, timeout):
            if argv[:2] == ["dpkg-query", "-L"]:
                return subprocess.CompletedProcess(argv, 0, stdout=str(fake) + "\n", stderr="")
            if argv[0] == str(fake):
                return subprocess.CompletedProcess(argv, 0, stdout="FA3_APP_HEALTH_BFORARTISTS_PASS\n", stderr="")
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="not installed")

        with patch("fa3_application_installation_resolver.shutil.which") as which:
            which.side_effect = lambda name: "/usr/bin/dpkg-query" if name == "dpkg-query" else None
            rows = discover_registered_application(root, "bforartists", runner=runner)
        healthy = [row for row in rows if row["health"] == "HEALTHY"]
        self.assertEqual(len(healthy), 1)
        self.assertEqual(healthy[0]["packaging"], "DEB")
        self.assertEqual(healthy[0]["locator"], str(fake))

    def test_broken_blender_does_not_hide_healthy_bforartists(self):
        root = self._root()
        bfa = root / "bforartists"
        blender = root / "blender"
        for path in (bfa, blender):
            path.write_text("#!/bin/sh\n", encoding="utf-8")
            path.chmod(0o755)

        def runner(argv, timeout):
            if argv[0] == str(bfa):
                return subprocess.CompletedProcess(argv, 0, stdout="FA3_APP_HEALTH_BFORARTISTS_PASS\n", stderr="")
            if argv[0] == str(blender):
                return subprocess.CompletedProcess(argv, 127, stdout="", stderr="missing shared library")
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")

        mapping = {"bforartists": str(bfa), "bforartists-bin": None, "blender": str(blender),
                   "dpkg-query": None, "rpm": None, "flatpak": None, "snap": None}
        with patch("fa3_application_installation_resolver.shutil.which", side_effect=lambda name: mapping.get(name)):
            bfa_rows = discover_registered_application(root, "bforartists", runner=runner)
            blender_rows = discover_registered_application(root, "blender", runner=runner)
        self.assertTrue(any(row["health"] == "HEALTHY" for row in bfa_rows))
        self.assertTrue(any(row["health"] == "UNHEALTHY" for row in blender_rows))


if __name__ == "__main__":
    unittest.main()
