#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${FA3_DEMUCS_VENV:-$ROOT/.venv-demucs}"
PY="${FA3_DEMUCS_PYTHON:-$VENV/bin/python}"

if [[ ! -x "$PY" ]]; then
  echo "Demucs provider Python not found: $PY" >&2
  echo "Run: bash bin/fa3-demucs-bootstrap.sh" >&2
  exit 3
fi

PYTHONPATH="$ROOT/src" "$PY" "$ROOT/evidence/collect-demucs-current-host.py" --root "$ROOT" "$@"
PYTHONPATH="$ROOT/src" "$PY" "$ROOT/src/fa3_enforce.py" --root "$ROOT" demucs-current-host
