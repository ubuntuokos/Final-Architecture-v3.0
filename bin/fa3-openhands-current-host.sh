#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"

MODE="${1:-isolated}"
if [[ "$MODE" != "isolated" && "$MODE" != "production" ]]; then
  echo "Usage: $0 [isolated|production]" >&2
  exit 64
fi
: "${FA3_CURRENT_HOST:?FA3_CURRENT_HOST=1 is required on the authorized current host}"

./bin/fa3-enforce openhands

ARGS=(--root "$ROOT" --mode "$MODE")
if [[ -n "${FA3_OPENHANDS_HOME:-}" ]]; then
  ARGS+=(--source "$FA3_OPENHANDS_HOME/source-a9e0a8a1aab2164b46bae00a18157a343aaa94c9")
  ARGS+=(--venv "$FA3_OPENHANDS_HOME/venv-1.44.1")
fi
if [[ "$MODE" == "production" ]]; then
  : "${FA3_OPENHANDS_TOOL_AUTH_RECEIPT:?external canonical tool authorization receipt path required}"
  : "${FA3_OPENHANDS_LITELLM_KEY_FILE:?external LiteLLM key file path required}"
  ARGS+=(--tool-auth-receipt "$FA3_OPENHANDS_TOOL_AUTH_RECEIPT")
  ARGS+=(--router-key-file "$FA3_OPENHANDS_LITELLM_KEY_FILE")
  ARGS+=(--router-port "${FA3_OPENHANDS_LITELLM_PORT:-4000}")
  ARGS+=(--model-alias "${FA3_OPENHANDS_MODEL_ALIAS:-developer-agent-primary}")
fi

python3 evidence/collect-openhands-current-host.py "${ARGS[@]}"
if [[ "$MODE" == "production" ]]; then
  python3 src/fa3_openhands_current_host_gate.py --root "$ROOT" --mode production
else
  python3 src/fa3_openhands_current_host_gate.py --root "$ROOT" --mode isolated
fi
