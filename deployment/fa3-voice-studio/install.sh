#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PREFIX="${HOME}/.local/lib/fa3"
install -d -m0755 "$PREFIX/bin" "$PREFIX/src" "${HOME}/.config/systemd/user"
install -m0555 "$ROOT/bin/fa3-voice-studio" "$PREFIX/bin/fa3-voice-studio"
install -m0444 "$ROOT/src/fa3_voice_studio_server.py" "$PREFIX/src/fa3_voice_studio_server.py"
install -m0444 "$ROOT/src/fa3_voice_workspace.py" "$PREFIX/src/fa3_voice_workspace.py"
install -m0444 "$ROOT/src/fa3_piper_provider.py" "$PREFIX/src/fa3_piper_provider.py"
sed "s|%h/.local/lib/fa3|${HOME}/.local/lib/fa3|g" "$ROOT/deployment/fa3-voice-studio/fa3-voice-studio.service" > "${HOME}/.config/systemd/user/fa3-voice-studio.service"
systemctl --user daemon-reload
systemctl --user enable --now fa3-voice-studio.service
