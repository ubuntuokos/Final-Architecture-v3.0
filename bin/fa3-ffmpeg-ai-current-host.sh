#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"
HRB_LEASE="${1:-.fa3-current-host/input/ffmpeg-ai-accelerator-lease.json}"
BUILD_TRUST="${2:-.fa3-current-host/input/ffmpeg-ai-build-trust-v2.json}"
HRB_BIN="${FA3_HRB_BIN:-/usr/local/bin/fa3-host-resource-broker}"
python3 evidence/collect-ffmpeg-ai-current-host.py --root "$ROOT" --hrb-lease "$HRB_LEASE" --ffmpeg-build-trust "$BUILD_TRUST" --hrb-bin "$HRB_BIN"
python3 src/fa3_ffmpeg_ai_current_host_gate.py --root "$ROOT"
