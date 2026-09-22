#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${FA3_MODEL_ROUTER_PROVIDER_CATALOG:?FA3_MODEL_ROUTER_PROVIDER_CATALOG is required}"
PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
  python3 "$ROOT/evidence/collect-model-router-current-host.py" \
  --catalog "$FA3_MODEL_ROUTER_PROVIDER_CATALOG" "$@"
PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
  python3 "$ROOT/src/fa3_model_router_current_host_gate.py" --root "$ROOT"
