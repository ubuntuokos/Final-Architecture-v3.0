#!/usr/bin/env bash
set -euo pipefail

COMMIT="a9e0a8a1aab2164b46bae00a18157a343aaa94c9"
TREE="342a369f498b826cf51d1644bcbef8d503af7628"
VERSION="1.44.1"
BASE="${FA3_OPENHANDS_HOME:-$HOME/.local/share/fa3/openhands}"
SOURCE="$BASE/source-$COMMIT"
VENV="$BASE/venv-$VERSION"
ALLOW_NETWORK=0
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --allow-network-bootstrap) ALLOW_NETWORK=1; shift ;;
    --force) FORCE=1; shift ;;
    --base) BASE="$2"; SOURCE="$BASE/source-$COMMIT"; VENV="$BASE/venv-$VERSION"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 64 ;;
  esac
done

for v in CONDA_PREFIX CONDA_DEFAULT_ENV MAMBA_ROOT_PREFIX; do
  if [[ -n "${!v:-}" ]]; then
    echo "Refusing OpenHands bootstrap while $v is active" >&2
    exit 2
  fi
done

command -v git >/dev/null
command -v bwrap >/dev/null
PYTHON_BIN="$(command -v python3.12 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "python3.12 is required for pinned OpenHands 1.44.1" >&2
  exit 2
fi
mkdir -p "$BASE"

if [[ ! -d "$SOURCE/.git" ]]; then
  if [[ "$ALLOW_NETWORK" -ne 1 ]]; then
    echo "Pinned OpenHands source is absent. Re-run once with --allow-network-bootstrap." >&2
    exit 2
  fi
  rm -rf "$SOURCE"
  git init "$SOURCE"
  git -C "$SOURCE" remote add origin https://github.com/OpenHands/software-agent-sdk.git
  git -C "$SOURCE" fetch --depth=1 origin "$COMMIT"
  git -C "$SOURCE" checkout --detach FETCH_HEAD
fi

ACTUAL_COMMIT="$(git -C "$SOURCE" rev-parse HEAD)"
ACTUAL_TREE="$(git -C "$SOURCE" rev-parse 'HEAD^{tree}')"
DIRTY="$(git -C "$SOURCE" status --porcelain)"
[[ "$ACTUAL_COMMIT" == "$COMMIT" ]] || { echo "OpenHands commit mismatch: $ACTUAL_COMMIT" >&2; exit 2; }
[[ "$ACTUAL_TREE" == "$TREE" ]] || { echo "OpenHands tree mismatch: $ACTUAL_TREE" >&2; exit 2; }
[[ -z "$DIRTY" ]] || { echo "OpenHands source checkout is dirty" >&2; exit 2; }

if [[ "$FORCE" -eq 1 ]]; then
  rm -rf "$VENV"
fi
if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi

if [[ "$ALLOW_NETWORK" -eq 1 ]]; then
  "$VENV/bin/python" -m pip install --disable-pip-version-check --no-input     "$SOURCE/openhands-sdk"     "$SOURCE/openhands-tools"     "$SOURCE/openhands-agent-server"     "$SOURCE/openhands-workspace"
fi

"$VENV/bin/python" - <<'PY'
import importlib.metadata as m
expected={
 "openhands-sdk":"1.44.1",
 "openhands-tools":"1.44.1",
 "openhands-agent-server":"1.44.1",
 "openhands-workspace":"1.44.1",
}
actual={k:m.version(k) for k in expected}
if actual != expected:
    raise SystemExit(f"OpenHands component tuple mismatch: {actual}")
print(actual)
PY
"$VENV/bin/python" -m pip check

FREEZE="$BASE/requirements.freeze-$VERSION.txt"
"$VENV/bin/python" -m pip freeze --all | LC_ALL=C sort > "$FREEZE"
chmod 0644 "$FREEZE"
UV_LOCK_SHA256=""
if [[ -f "$SOURCE/uv.lock" ]]; then
  UV_LOCK_SHA256="$(sha256sum "$SOURCE/uv.lock" | awk '{print $1}')"
fi
FREEZE_SHA256="$(sha256sum "$FREEZE" | awk '{print $1}')"
BWRAP_BIN="$(command -v bwrap)"
BWRAP_SHA256="$(sha256sum "$BWRAP_BIN" | awk '{print $1}')"

cat > "$BASE/bootstrap-$VERSION.json" <<EOF
{
  "schema": "fa3.openhands-bootstrap-receipt.v1",
  "provider_id": "FA3-PROVIDER-OPENHANDS-001",
  "source_commit": "$ACTUAL_COMMIT",
  "source_tree": "$ACTUAL_TREE",
  "component_version": "$VERSION",
  "python": "$("$VENV/bin/python" -c 'import platform; print(platform.python_version())')",
  "packaging": "pip-venv",
  "conda_or_mamba": false,
  "network_bootstrap_explicitly_authorized": $([[ "$ALLOW_NETWORK" -eq 1 ]] && echo true || echo false),
  "upstream_uv_lock_sha256": "$UV_LOCK_SHA256",
  "resolved_pip_freeze_sha256": "$FREEZE_SHA256",
  "bwrap_sha256": "$BWRAP_SHA256",
  "source_path": "$SOURCE",
  "venv_path": "$VENV"
}
EOF
chmod 0600 "$BASE/bootstrap-$VERSION.json"

echo "OpenHands pinned runtime materialized:"
echo "  source: $SOURCE"
echo "  venv:   $VENV"
echo "  freeze: $FREEZE"
