#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${FA3_DEMUCS_VENV:-$ROOT/.venv-demucs}"
PYTHON="${FA3_DEMUCS_BOOTSTRAP_PYTHON:-python3}"

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON" -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install "demucs==4.1.0"

PYTHONPATH="$ROOT/src" "$VENV/bin/python" - <<'PY'
import importlib.metadata as m
for name in ("demucs","torch","safetensors","huggingface-hub","sphn"):
    print(f"{name}={m.version(name)}")
PY

echo "FA3 Demucs provider venv ready: $VENV"
echo "No conda/mamba environment is used."
