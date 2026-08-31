#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
python3 "$ROOT/evidence/collect-codex-current-host.py" --root "$ROOT" "$@"
python3 "$ROOT/src/fa3_codex_gate.py" --root "$ROOT" --current-host
