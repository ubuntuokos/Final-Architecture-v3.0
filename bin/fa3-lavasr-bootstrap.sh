#!/usr/bin/env bash
set -euo pipefail

RUNTIME_REPO="https://github.com/Topping1/LavaSR-ONNX.git"
RUNTIME_REV="1a979b80d760f00d973b13d530fdd8da51be160b"
RELEASE_BASE="https://github.com/Topping1/LavaSR-ONNX/releases/download/Alpha-v0.1"
DEST="${1:-$HOME/.local/share/fa3/lavasr}"
RUNTIME_DIR="$DEST/runtime"
MODEL_DIR="$DEST/models/LAVASR-ONNX-ALPHA-V0.1-001"

command -v git >/dev/null || { echo "git is required" >&2; exit 2; }
command -v curl >/dev/null || { echo "curl is required" >&2; exit 2; }
command -v sha256sum >/dev/null || { echo "sha256sum is required" >&2; exit 2; }

mkdir -p "$DEST" "$MODEL_DIR"
if [[ -e "$RUNTIME_DIR" ]]; then
  echo "Refusing to overwrite existing runtime checkout: $RUNTIME_DIR" >&2
  exit 2
fi

git clone --filter=blob:none --no-checkout "$RUNTIME_REPO" "$RUNTIME_DIR"
git -C "$RUNTIME_DIR" checkout --detach "$RUNTIME_REV"
[[ "$(git -C "$RUNTIME_DIR" rev-parse HEAD)" == "$RUNTIME_REV" ]] || { echo "runtime revision verification failed" >&2; exit 2; }
[[ -z "$(git -C "$RUNTIME_DIR" status --porcelain)" ]] || { echo "runtime checkout is dirty" >&2; exit 2; }

fetch_asset() {
  local name="$1"
  local digest="$2"
  curl --fail --location --proto '=https' --tlsv1.2 "$RELEASE_BASE/$name" -o "$MODEL_DIR/$name"
  printf '%s  %s\n' "$digest" "$MODEL_DIR/$name" | sha256sum --check --strict
}

fetch_asset "denoiser_core_legacy_fixed63.onnx" "8afa7f4db9f356f7bfb575bb207d8673a728a7baf6773e0b10226a5e15687f2a"
fetch_asset "enhancer_backbone.onnx" "841e96d261dffdf1dc974f3d29e2cfcf1b16fd0b358749c1ace0bbfa1d4c8ddd"
fetch_asset "enhancer_backbone.onnx.data" "a125a4ede7cfdd1073d906a3cadf2171a30be6a40f296ad28772e0ba258de8c5"
fetch_asset "enhancer_spec_head.onnx" "f66fd164c55fd1b07e5cea5e687c71522b192f452691128fd7ae4e6b26dbc683"
fetch_asset "enhancer_spec_head.onnx.data" "b855e309b027af9aa75285b97b345571b6bd695a30fde434d06c979d83885fd6"

cat <<EOF
LavaSR source/model quarantine materialization complete.
Runtime: $RUNTIME_DIR @ $RUNTIME_REV
Models:  $MODEL_DIR

This bootstrap intentionally does NOT install Python packages or promote runtime status.
Use an FA3-admitted isolated environment providing onnxruntime, numpy, scipy, soundfile and PyYAML,
then run evidence/collect-lavasr-current-host.py to obtain current-host evidence.
EOF
