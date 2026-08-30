#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${FA3_WHISPER_VENV:-$ROOT/.venv-whisper}"
PYTHON_BOOTSTRAP="${FA3_PYTHON:-python3}"
UPSTREAM_COMMIT="31243bad24cc746f07d4c8bfdd2d974872cb1803"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required by Whisper audio loading / Blackhole integration." >&2
  exit 69
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON_BOOTSTRAP" -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install "openai-whisper @ git+https://github.com/openai/whisper.git@$UPSTREAM_COMMIT"

PYTHONPATH="$ROOT/src" "$VENV/bin/python" - <<'PY'
import whisper
assert whisper.__version__ == "20250625", whisper.__version__
print("Whisper runtime:", whisper.__version__)
PY

echo "FA3 Whisper venv ready: $VENV"
echo "Model cache: ${FA3_WHISPER_MODEL_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/whisper}"
