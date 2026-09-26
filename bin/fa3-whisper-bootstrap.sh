#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${FA3_WHISPER_VENV:-$ROOT/.venv-whisper}"
PYTHON_BOOTSTRAP="${FA3_PYTHON:-python3}"
LOCK_REGISTRY="$ROOT/canonical/FA3-UPSTREAM-LOCK-REGISTRY-001.json"

readarray -t LOCK_VALUES < <("$PYTHON_BOOTSTRAP" - "$LOCK_REGISTRY" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
o = json.loads(p.read_text(encoding="utf-8"))
lock = o["locks"]["whisper"]
print(lock["revision"])
print(lock["version"])
PY
)
UPSTREAM_COMMIT="${LOCK_VALUES[0]:-}"
EXPECTED_VERSION="${LOCK_VALUES[1]:-}"
if [[ ! "$UPSTREAM_COMMIT" =~ ^[0-9a-f]{40}$ || -z "$EXPECTED_VERSION" ]]; then
  echo "Invalid Whisper immutable lock in $LOCK_REGISTRY" >&2
  exit 65
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required by Whisper audio loading / Blackhole integration." >&2
  exit 69
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON_BOOTSTRAP" -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install "openai-whisper @ git+https://github.com/openai/whisper.git@$UPSTREAM_COMMIT"

PYTHONPATH="$ROOT/src" "$VENV/bin/python" - "$EXPECTED_VERSION" <<'PY'
import sys
import whisper
expected = sys.argv[1]
assert whisper.__version__ == expected, (whisper.__version__, expected)
print("Whisper runtime:", whisper.__version__)
PY

echo "FA3 Whisper venv ready: $VENV"
echo "Managed lock: FA3-UPSTREAM-LOCK-REGISTRY-001#whisper@$UPSTREAM_COMMIT"
echo "Model cache: ${FA3_WHISPER_MODEL_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/fa3/whisper}"
