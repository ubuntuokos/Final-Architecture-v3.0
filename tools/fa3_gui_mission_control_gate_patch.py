#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "src/fa3_gui_gate.py"
text = p.read_text(encoding="utf-8")
text = text.replace('"fa3Settings", "EmbeddedAppsPage", "ModelManagerPage", "SystemPage", "SettingsPage",', '"fa3Settings", "EmbeddedAppsPage", "ModelManagerHubPage", "SystemPage", "SettingsPage",')
p.write_text(text, encoding="utf-8")
print("Legacy GUI gate aligned with ModelManagerHubPage")
