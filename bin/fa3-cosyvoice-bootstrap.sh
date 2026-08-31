#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${FA3_COSYVOICE_VENV:-$ROOT/.venv-cosyvoice}"
PYTHON="${FA3_COSYVOICE_BOOTSTRAP_PYTHON:-python3.10}"
SRC="${FA3_COSYVOICE_SRC:-$ROOT/.providers/CosyVoice}"
MODEL_DIR="${FA3_COSYVOICE_MODEL_DIR:-$ROOT/.providers/models/Fun-CosyVoice3-0.5B}"
UPSTREAM_COMMIT="074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc"
MODEL_ID="FunAudioLLM/Fun-CosyVoice3-0.5B-2512"
MODEL_REVISION="29e01c4e8d000f4bcd70751be16fa94bf3d85a18"

command -v "$PYTHON" >/dev/null 2>&1 || { echo "Python 3.10 is required: $PYTHON" >&2; exit 69; }
"$PYTHON" - <<'PY'
import sys
assert sys.version_info[:2] == (3,10), sys.version
PY
command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 69; }
command -v sox >/dev/null 2>&1 || { echo "SoX is required (Ubuntu: sudo apt install sox libsox-dev)" >&2; exit 69; }

mkdir -p "$(dirname "$SRC")" "$(dirname "$MODEL_DIR")"
if [[ ! -d "$SRC/.git" ]]; then
  git clone --recursive https://github.com/QwenAudio/CosyVoice.git "$SRC"
fi
git -C "$SRC" fetch origin "$UPSTREAM_COMMIT"
git -C "$SRC" checkout --detach "$UPSTREAM_COMMIT"
git -C "$SRC" submodule update --init --recursive

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON" -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install -r "$SRC/requirements.txt"
"$VENV/bin/python" -m pip install huggingface_hub

MODEL_DIR="$MODEL_DIR" MODEL_ID="$MODEL_ID" MODEL_REVISION="$MODEL_REVISION" "$VENV/bin/python" - <<'PY'
import json, os
from pathlib import Path
from huggingface_hub import snapshot_download
model_id=os.environ["MODEL_ID"]; rev=os.environ["MODEL_REVISION"]; dest=Path(os.environ["MODEL_DIR"])
snapshot_download(model_id,revision=rev,local_dir=str(dest))
(dest/"FA3-MODEL-METADATA.json").write_text(json.dumps({
  "schema":"fa3.model-materialization.v1",
  "model_id":model_id,
  "revision":rev,
  "download_mode":"EXPLICIT_BOOTSTRAP",
  "network_fetch_at_runtime":False
},indent=2)+"\n",encoding="utf-8")
PY

echo "FA3 CosyVoice bootstrap complete"
echo "venv: $VENV"
echo "source: $SRC"
echo "model: $MODEL_DIR"
