#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROVIDERS="${FA3_MODEL_ROUTER_PROVIDERS:-$HOME/.config/fa3/model-router/providers.json}"
CREDENTIAL="${FA3_MODEL_ROUTER_MASTER_KEY_FILE:-}"
PORT="${FA3_MODEL_ROUTER_PORT:-4000}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --providers) PROVIDERS="$2"; shift 2;;
    --credential-file) CREDENTIAL="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    *) echo "unknown argument: $1" >&2; exit 2;;
  esac
done

cleanup_on_fail() {
  rc=$?
  if [[ $rc -ne 0 ]]; then
    systemctl --user stop fa3-model-router.service >/dev/null 2>&1 || true
  fi
  exit $rc
}
trap cleanup_on_fail EXIT

bash bin/fa3-model-router-install --providers "$PROVIDERS" --credential-file "$CREDENTIAL" --port "$PORT" --start
XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
python3 evidence/collect-model-router-current-host.py   --endpoint "http://127.0.0.1:$PORT"   --credential-file "$CREDENTIAL"   --selection-receipt "$XDG_RUNTIME_DIR/fa3-model-router/selection.json"
python3 src/fa3_model_router_current_host_gate.py --root "$ROOT"
trap - EXIT
