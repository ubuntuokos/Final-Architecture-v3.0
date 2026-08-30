#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${FA3_AUTOGPT_STATE_DIR:-$(mktemp -d -p "${RUNNER_TEMP:-${XDG_RUNTIME_DIR:-/tmp}}" fa3-autogpt-current-host.XXXXXX)}"
STATE_FILE="$STATE_DIR/state.json"
STARTED=0

cleanup() {
  set +e
  if [[ "$STARTED" == "1" ]]; then
    bash "$ROOT/bin/fa3-autogpt-bootstrap.sh" stop --state-dir "$STATE_DIR" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

export FA3_CURRENT_HOST_ASSERTION=1
bash "$ROOT/bin/fa3-autogpt-bootstrap.sh" start --state-dir "$STATE_DIR"
STARTED=1
PYTHONPATH="$ROOT/src" python3 "$ROOT/evidence/collect-autogpt-current-host.py" --state-file "$STATE_FILE"

bash "$ROOT/bin/fa3-autogpt-bootstrap.sh" stop --state-dir "$STATE_DIR"
STARTED=0
PYTHONPATH="$ROOT/src" python3 "$ROOT/evidence/collect-autogpt-current-host.py" --state-file "$STATE_FILE" --finalize-cleanup
PYTHONPATH="$ROOT/src" python3 "$ROOT/src/fa3_autogpt_gate.py" --root "$ROOT" --current-host

echo "AutoGPT current-host production E2E completed."
