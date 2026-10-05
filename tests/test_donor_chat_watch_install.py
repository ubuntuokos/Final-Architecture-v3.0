from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "bin/fa3-donor-chat-watch-install"


class DonorSystemdInstallerTests(unittest.TestCase):
    def test_installer_emits_absolute_directory_and_never_overwrites_user_units(self):
        with tempfile.TemporaryDirectory(prefix="fa3-donor-test-") as directory:
            home = Path(directory) / "home"
            bindir = Path(directory) / "mockbin"
            home.mkdir()
            bindir.mkdir()
            systemctl = bindir / "systemctl"
            systemctl.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$HOME/calls.log\"\n",
                encoding="utf-8",
            )
            systemctl.chmod(0o755)
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            created = subprocess.run(
                ["bash", str(INSTALLER)], env=env, capture_output=True,
                text=True, check=False
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            service = home / ".config/systemd/user/fa3-donor-chat-import.service"
            path = home / ".config/systemd/user/fa3-donor-chat-import.path"
            self.assertTrue(service.is_file())
            self.assertTrue(path.is_file())
            content = service.read_text(encoding="utf-8")
            self.assertIn(f"WorkingDirectory={ROOT}", content)
            self.assertIn(f"ExecStart=/usr/bin/env bash {ROOT}/bin/fa3-donor-chat-inbox", content)
            self.assertNotIn("WorkingDirectory=\\\"", content)
            self.assertNotIn('WorkingDirectory="', content)
            self.assertNotIn('ExecStart=/usr/bin/env bash "', content)
            self.assertTrue(str(ROOT).startswith("/"))
            self.assertEqual(service.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            log = (home / "calls.log").read_text(encoding="utf-8")
            self.assertIn("--user daemon-reload", log)
            self.assertIn("--user enable --now fa3-donor-chat-import.path", log)

            repeat = subprocess.run(
                ["bash", str(INSTALLER)], env=env,
                capture_output=True, text=True, check=False
            )
            self.assertEqual(repeat.returncode, 2)
            self.assertIn("already exists", repeat.stderr)
            self.assertEqual(service.read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
