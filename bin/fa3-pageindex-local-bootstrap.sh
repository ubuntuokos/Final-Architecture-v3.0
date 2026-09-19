#!/usr/bin/env bash
set -euo pipefail
PIN="9a8dd6658278fec90347e8ac3388a205305667a3"
BASE="${FA3_PAGEINDEX_LOCAL_PROVIDER_ROOT:-$HOME/.local/share/fa3/providers/pageindex-local}"
ROOT="$BASE/$PIN"; SRC="$ROOT/source"; VENV="$ROOT/venv"
mkdir -p "$ROOT"
if [[ ! -d "$SRC/.git" ]]; then rm -rf "$SRC"; git clone --filter=blob:none https://github.com/VectifyAI/PageIndex.git "$SRC"; fi
git -C "$SRC" fetch --force origin "$PIN"
git -C "$SRC" checkout --detach "$PIN"
git -C "$SRC" reset --hard "$PIN"; git -C "$SRC" clean -ffd
test "$(git -C "$SRC" rev-parse HEAD)" = "$PIN"; test -z "$(git -C "$SRC" status --porcelain)"
PYTHON_BIN="${FA3_PAGEINDEX_LOCAL_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for p in python3.13 python3.12 python3.11 python3.10; do if command -v "$p" >/dev/null 2>&1; then PYTHON_BIN="$(command -v "$p")"; break; fi; done
fi
test -n "$PYTHON_BIN" || { echo "No supported Python 3.10-3.13 found" >&2; exit 2; }
if [[ ! -x "$VENV/bin/python" ]]; then "$PYTHON_BIN" -m venv "$VENV"; fi
STAMP="$ROOT/install.stamp"; PYPROJECT_SHA="$(sha256sum "$SRC/pyproject.toml" | awk '{print $1}')"; NEED_INSTALL=1
if [[ -r "$STAMP" ]] && grep -qx "$PIN $PYPROJECT_SHA" "$STAMP" && "$VENV/bin/python" -m pip check >/dev/null 2>&1; then
  if "$VENV/bin/python" - <<'PY' >/dev/null 2>&1
from importlib.metadata import version
assert version("pageindex") == "0.2.10"
PY
  then NEED_INSTALL=0; fi
fi
if [[ "$NEED_INSTALL" -eq 1 ]]; then
  "$VENV/bin/python" -m pip install --disable-pip-version-check "$SRC"
  "$VENV/bin/python" -m pip check
  printf '%s %s\n' "$PIN" "$PYPROJECT_SHA" > "$STAMP"
fi
"$VENV/bin/python" - <<'PY'
from importlib.metadata import version
assert version("pageindex") == "0.2.10", version("pageindex")
PY
"$VENV/bin/python" -m pip freeze --all | LC_ALL=C sort > "$ROOT/resolved-requirements.txt"
"$VENV/bin/python" - "$ROOT/runtime-manifest.json" "$PIN" "$PYPROJECT_SHA" <<'PY'
import hashlib,json,platform,sys
from pathlib import Path
out,pin,pyproject_sha=sys.argv[1:]
freeze=Path(out).with_name("resolved-requirements.txt").read_bytes()
Path(out).write_text(json.dumps({"schema":"fa3.pageindex-local-runtime-manifest.v1","upstream_commit":pin,"pageindex_version":"0.2.10","pyproject_sha256":pyproject_sha,"resolved_requirements_sha256":hashlib.sha256(freeze).hexdigest(),"python":platform.python_version(),"global_promotion_claim":False},indent=2)+"\n")
PY
printf '%s\n' "$ROOT"
