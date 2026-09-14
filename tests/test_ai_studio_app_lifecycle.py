from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class AiStudioAppLifecycleGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.lifecycle = json.loads(
            (cls.repo_root / "canonical/FA3-APP-LIFECYCLE-001.json").read_text(encoding="utf-8")
        )
        cls.request_policy = json.loads(
            (cls.repo_root / "canonical/FA3-APP-REQUEST-001.json").read_text(encoding="utf-8")
        )
        cls.catalog = json.loads(
            (cls.repo_root / "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json").read_text(encoding="utf-8")
        )

    def test_base_install_is_lazy(self) -> None:
        base = self.lifecycle["base_install"]
        self.assertFalse(base["optional_applications_installed_with_fa3"])
        self.assertTrue(base["catalog_metadata_installed_with_fa3"])
        self.assertTrue(base["provisioning_runtime_installed_with_fa3"])
        self.assertEqual(self.lifecycle["installation"]["default_mode"], "FIRST_USE")
        self.assertTrue(self.lifecycle["installation"]["confirmation_required_before_materialization"])

    def test_direct_user_install_is_denied(self) -> None:
        boundary = self.lifecycle["admission_boundary"]
        self.assertTrue(boundary["catalog_is_allowlist"])
        self.assertFalse(boundary["user_supplied_install_source_allowed"])
        self.assertFalse(boundary["install_from_url_allowed"])
        self.assertFalse(boundary["github_search_to_install_allowed"])
        self.assertFalse(boundary["direct_shell_install_from_gui_allowed"])
        self.assertTrue(boundary["unknown_application_fails_closed"])

    def test_request_never_grants_install_authority(self) -> None:
        security = self.request_policy["security_boundary"]
        self.assertTrue(self.request_policy["submission"]["enabled"])
        self.assertEqual(self.request_policy["submission"]["initial_status"], "PENDING_REVIEW")
        self.assertFalse(security["request_is_executable"])
        self.assertFalse(security["request_grants_install_authority"])
        self.assertFalse(security["request_grants_catalog_membership"])
        self.assertFalse(security["source_url_may_be_executed"])
        self.assertFalse(security["source_url_may_be_cloned_automatically"])

    def test_catalog_is_canonical_allowlist(self) -> None:
        self.assertEqual(self.catalog["catalog_mode"], "ALLOWLIST")
        self.assertFalse(self.catalog["user_defined_entries_allowed"])
        apps = self.catalog["applications"]
        self.assertGreater(len(apps), 0)
        ids = [app["id"] for app in apps]
        self.assertEqual(len(ids), len(set(ids)), "catalog app IDs must be unique")
        for app in apps:
            with self.subTest(app=app["id"]):
                self.assertEqual(app["admission"], "APPROVED")
                self.assertEqual(app["install_mode"], "FIRST_USE")
                self.assertFalse(app["direct_source_install_allowed"])
                self.assertTrue(app["provider_recipe"].endswith(".json"))

    def test_provisioner_rejects_unknown_application(self) -> None:
        script = self.repo_root / "scripts/fa3-app-provisioner.py"
        result = subprocess.run(
            [sys.executable, str(script), "--repo-root", str(self.repo_root), "status", "not-in-fa3-catalog"],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DENY", result.stderr)
        self.assertIn("canonical allowlist", result.stderr)

    def test_provisioner_rejects_url_as_application_id(self) -> None:
        script = self.repo_root / "scripts/fa3-app-provisioner.py"
        result = subprocess.run(
            [sys.executable, str(script), "--repo-root", str(self.repo_root), "install", "https://github.com/example/app"],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid application identifier", result.stderr)

    def test_gui_contains_catalog_and_review_request_surface(self) -> None:
        qml = (self.repo_root / "apps/fa3-control-center/qml/AiStudioPage.qml").read_text(encoding="utf-8")
        self.assertIn("fa3AppCatalog.applications", qml)
        self.assertIn("fa3AppCatalog.requestFirstUse", qml)
        self.assertIn("fa3AppCatalog.submitApplicationRequest", qml)
        self.assertIn("Saját URL-ről közvetlen telepítés nincs", qml)
        self.assertNotIn("Install from URL", qml)

    def test_control_center_embeds_canonical_catalog(self) -> None:
        cmake = (self.repo_root / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn("src/AppCatalogService.cpp", cmake)
        self.assertIn("FA3-AI-STUDIO-APP-CATALOG-001.json", cmake)
        self.assertIn("fa3-app-provisioner.py", cmake)


if __name__ == "__main__":
    unittest.main()
