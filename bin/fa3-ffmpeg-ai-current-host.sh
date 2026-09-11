#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"

INPUT_MEDIA="${1:-.fa3-current-host/input/ffmpeg-ai-real-golden.mp4}"
INPUT_PROVENANCE="${2:-.fa3-current-host/input/ffmpeg-ai-real-golden-provenance.json}"
HRB_LEASE="${3:-.fa3-current-host/input/ffmpeg-ai-accelerator-lease.json}"
BUILD_TRUST="${4:-.fa3-current-host/input/ffmpeg-ai-build-trust.json}"

python3 evidence/collect-ffmpeg-ai-current-host.py \
  --root "$ROOT" \
  --input-media "$INPUT_MEDIA" \
  --input-provenance "$INPUT_PROVENANCE" \
  --hrb-lease "$HRB_LEASE" \
  --ffmpeg-build-trust "$BUILD_TRUST"

python3 src/fa3_ffmpeg_ai_current_host_gate.py --root "$ROOT"
