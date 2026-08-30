#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${FA3_MODULAR_VENV:-$ROOT/.venv-modular}"
SPEC="${FA3_MODULAR_MAX_SPEC:-max[all]>=26.5,<26.6}"

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required. Install/admit uv separately; this bootstrap will not execute a network-fetched installer." >&2
  exit 2
fi

uv venv --python python3 "$VENV"
uv pip install --python "$VENV/bin/python" "$SPEC"

"$VENV/bin/max" --version
"$VENV/bin/mojo" --version

echo "FA3 Modular runtime ready: $VENV"
echo "Pinned stable package range: $SPEC"
