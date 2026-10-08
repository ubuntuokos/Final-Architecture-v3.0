#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PREFIX="${HOME}/.local/lib/fa3"
install -d -m0755 "$PREFIX/bin" "$PREFIX/src" "$PREFIX/canonical" "${HOME}/.config/systemd/user" "${HOME}/.local/state/fa3"
install -m0555 "$ROOT/bin/fa3-voice-studio" "$PREFIX/bin/fa3-voice-studio"
install -m0444 "$ROOT/src/fa3_voice_studio_server.py" "$PREFIX/src/fa3_voice_studio_server.py"
install -m0444 "$ROOT/src/fa3_voice_workspace.py" "$PREFIX/src/fa3_voice_workspace.py"
install -m0444 "$ROOT/src/fa3_piper_provider.py" "$PREFIX/src/fa3_piper_provider.py"
install -m0444 "$ROOT/src/fa3_model_router_voice.py" "$PREFIX/src/fa3_model_router_voice.py"
install -m0444 "$ROOT/src/fa3_whisper_stt_provider.py" "$PREFIX/src/fa3_whisper_stt_provider.py"
install -m0444 "$ROOT/src/fa3_voice_synthesis_gate.py" "$PREFIX/src/fa3_voice_synthesis_gate.py"
install -m0444 "$ROOT/canonical/FA3-VOICE-PROVIDER-ADMISSION-001.json" "$PREFIX/canonical/FA3-VOICE-PROVIDER-ADMISSION-001.json"
install -m0444 "$ROOT/canonical/FA3-VOICE-QUALITY-ROUTING-001.json" "$PREFIX/canonical/FA3-VOICE-QUALITY-ROUTING-001.json"
install -m0444 "$ROOT/canonical/FA3-WHISPER-MODEL-ALLOWLIST-001.json" "$PREFIX/canonical/FA3-WHISPER-MODEL-ALLOWLIST-001.json"
sed "s|%h/.local/lib/fa3|${HOME}/.local/lib/fa3|g" "$ROOT/deployment/fa3-voice-studio/fa3-voice-studio.service" > "${HOME}/.config/systemd/user/fa3-voice-studio.service"
systemctl --user daemon-reload
systemctl --user enable --now fa3-voice-studio.service
