#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"
HRB_RECEIPT="${1:-.fa3-current-host/input/ffmpeg-ai-hrb-placement.json}"
BUILD_TRUST="${2:-.fa3-current-host/input/ffmpeg-ai-build-trust.json}"
python3 evidence/collect-ffmpeg-ai-current-host.py --root "$ROOT" --hrb-receipt "$HRB_RECEIPT" --ffmpeg-build-trust "$BUILD_TRUST"
python3 src/fa3_ffmpeg_ai_current_host_gate.py --root "$ROOT"
