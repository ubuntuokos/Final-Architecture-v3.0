import json
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_pr_watch_service_render import render,validated_endpoint,PERMISSIONS,EVENTS
from fa3_pr_watch import PRWatchDenied

class ServiceRenderTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        target=self.root/"deployment/pr-watch"
        target.mkdir(parents=True)
        shutil.copy2(ROOT/"deployment/pr-watch/fa3-pr-watch.service",target/"fa3-pr-watch.service")
        canonical=self.root/"canonical"
        canonical.mkdir()
        (canonical/"FA3-DONOR-REFERENCE-REGISTRY-001.json").write_text("{}")

    def test_real_service_and_read_only_app_manifest(self):
        report=render(self.root,"fa3/reference","https://relay.example.org/github")
        self.assertEqual("PREPARED_NOT_INSTALLED",report["status"])
        unit=Path(report["unit"]).read_text()
        manifest=json.loads(Path(report["manifest"]).read_text())
        self.assertNotIn("__FA3_",unit)
        self.assertIn("PartOf=fa3-secrets.target",unit)
        self.assertIn("User=fa3-pr-watch",unit)
        self.assertIn("--allow-repo fa3/reference",unit)
        self.assertIn("--operator-export-path",unit)
        self.assertFalse(report["service_started"])
        self.assertFalse(report["github_app_registered"])
        self.assertTrue(all(x=="read" for x in manifest["default_permissions"].values()))
        self.assertEqual(list(EVENTS),manifest["default_events"])
        self.assertEqual("https://relay.example.org/github",manifest["hook_attributes"]["url"])
        self.assertEqual(0o644,stat.S_IMODE(Path(report["unit"]).stat().st_mode))

    def test_local_or_insecure_or_ambiguous_relays_denied(self):
        for url in ("http://relay.example.org/github","https://localhost/github",
                    "https://relay.example.invalid/github","https://relay.example.org/github?token=x",
                    "https://user@relay.example.org/github","https://relay.example.org:8080/github"):
            with self.subTest(url=url):
                with self.assertRaises(PRWatchDenied):
                    validated_endpoint(url)

    def test_invalid_repository_or_symlink_output_denied(self):
        with self.assertRaises(PRWatchDenied):
            render(self.root,"bad", "https://relay.example.org/github")
        report=self.root/"reports"
        report.mkdir()
        (report/"pr-watch").symlink_to(self.root)
        with self.assertRaises(PRWatchDenied):
            render(self.root,"fa3/reference","https://relay.example.org/github")

if __name__=="__main__":unittest.main()
