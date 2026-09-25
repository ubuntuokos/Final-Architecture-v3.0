#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ $# -lt 3 ]]; then
  echo "usage: $0 <selection-receipt> <provider-manifest> <video-generation-ir> [hrb-receipt]" >&2
  exit 2
fi
SELECTION="$1"; MANIFEST="$2"; IR="$3"; HRB="${4:-}"
args=(--selection "$SELECTION" --manifest "$MANIFEST" --ir "$IR")
if [[ -n "$HRB" ]]; then args+=(--hrb "$HRB"); fi
PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python3 "$ROOT/evidence/collect-motion-video-current-host.py" "${args[@]}"
PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python3 "$ROOT/src/fa3_motion_video_current_host_gate.py" --root "$ROOT"
