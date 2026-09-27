#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${FA3_DEMUCS_VENV:-$ROOT/.venv-demucs}"
PYTHON="${FA3_DEMUCS_BOOTSTRAP_PYTHON:-python3}"
LOCK_REGISTRY="$ROOT/canonical/FA3-UPSTREAM-LOCK-REGISTRY-001.json"

readarray -t LOCK_VALUES < <("$PYTHON" - "$LOCK_REGISTRY" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
o = json.loads(p.read_text(encoding="utf-8"))
lock = o["locks"]["demucs"]
print(lock["version"])
print(lock["revision"])
PY
)
DEMUCS_VERSION="${LOCK_VALUES[0]:-}"
DEMUCS_REVISION="${LOCK_VALUES[1]:-}"
if [[ -z "$DEMUCS_VERSION" || ! "$DEMUCS_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Invalid Demucs immutable lock in $LOCK_REGISTRY" >&2
  exit 65
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON" -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install "demucs==$DEMUCS_VERSION"

PYTHONPATH="$ROOT/src" "$VENV/bin/python" - "$DEMUCS_VERSION" <<'PY'
import importlib.metadata as m
import sys
expected = sys.argv[1]
actual = m.version("demucs")
assert actual == expected, (actual, expected)
for name in ("demucs","torch","safetensors","huggingface-hub","sphn"):
    print(f"{name}={m.version(name)}")
PY

echo "FA3 Demucs provider venv ready: $VENV"
echo "Model cache: ${FA3_DEMUCS_MODEL_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/fa3/demucs-hf}"
echo "Managed lock: FA3-UPSTREAM-LOCK-REGISTRY-001#demucs@$DEMUCS_REVISION"
echo "No conda/mamba environment is used."
