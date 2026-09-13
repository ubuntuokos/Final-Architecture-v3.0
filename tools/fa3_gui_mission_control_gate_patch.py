#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Legacy GUI gate: the active Model Manager is the responsive hub.
p = ROOT / "src/fa3_gui_gate.py"
text = p.read_text(encoding="utf-8")
text = text.replace(
    '"fa3Settings", "EmbeddedAppsPage", "ModelManagerPage", "SystemPage", "SettingsPage",',
    '"fa3Settings", "EmbeddedAppsPage", "ModelManagerHubPage", "SystemPage", "SettingsPage",',
)
p.write_text(text, encoding="utf-8")

# Animation integration remains active through the transitive shell chain:
# MissionControlAppShell -> OperationsAwareAppShell -> AnimationAwareAppShell.
p = ROOT / "src/fa3_gui_animation_integration_gate.py"
text = p.read_text(encoding="utf-8")
text = text.replace(
    '    operations_shell_path = ROOT / "apps/fa3-control-center/qml/OperationsAwareAppShell.qml"\n',
    '    operations_shell_path = ROOT / "apps/fa3-control-center/qml/OperationsAwareAppShell.qml"\n'
    '    mission_shell_path = ROOT / "apps/fa3-control-center/qml/MissionControlAppShell.qml"\n',
)
text = text.replace(
    '    transitive_animation = False\n'
    '    if "OperationsAwareAppShell.qml" in main and operations_shell_path.exists():\n'
    '        operations_shell = operations_shell_path.read_text(encoding="utf-8")\n'
    '        transitive_animation = "AnimationAwareAppShell" in operations_shell\n'
    '    if not direct_animation and not transitive_animation:\n',
    '    transitive_animation = False\n'
    '    if "OperationsAwareAppShell.qml" in main and operations_shell_path.exists():\n'
    '        operations_shell = operations_shell_path.read_text(encoding="utf-8")\n'
    '        transitive_animation = "AnimationAwareAppShell" in operations_shell\n'
    '    if "MissionControlAppShell.qml" in main and mission_shell_path.exists() and operations_shell_path.exists():\n'
    '        mission_shell = mission_shell_path.read_text(encoding="utf-8")\n'
    '        operations_shell = operations_shell_path.read_text(encoding="utf-8")\n'
    '        transitive_animation = (\n'
    '            "OperationsAwareAppShell" in mission_shell\n'
    '            and "AnimationAwareAppShell" in operations_shell\n'
    '        )\n'
    '    if not direct_animation and not transitive_animation:\n',
)
p.write_text(text, encoding="utf-8")

print("Legacy GUI gate aligned with ModelManagerHubPage")
print("Animation gate aligned with MissionControl -> Operations -> Animation inheritance")
