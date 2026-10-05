#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# -ne 10 ]]; then
  echo "usage: $0 GEM_ROOT SOMA_X_ROOT CHECKPOINT CHECKPOINT_ADMISSION MODEL_LICENSE SOMA_ASSETS_ADMISSION SMPLX_LICENSE HRB_RECEIPT VIDEO VIDEO_ADMISSION" >&2
  exit 64
fi
exec python3 "$ROOT/evidence/collect-human-motion-current-host.py" \
  --root "$ROOT" \
  --gem-root "$1" \
  --soma-x-root "$2" \
  --checkpoint "$3" \
  --checkpoint-admission "$4" \
  --model-license "$5" \
  --soma-assets-admission "$6" \
  --smplx-license "$7" \
  --hrb-receipt "$8" \
  --video "$9" \
  --video-admission "${10}"
