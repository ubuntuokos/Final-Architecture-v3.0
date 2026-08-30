#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${FA3_MODULAR_VENV:-$ROOT/.venv-modular}"

if [[ ! -x "$VENV/bin/python" || ! -x "$VENV/bin/max" || ! -x "$VENV/bin/mojo" ]]; then
  echo "ERROR: Modular runtime is not materialized at $VENV. Run: bash bin/fa3-modular-bootstrap.sh" >&2
  exit 2
fi

export PATH="$VENV/bin:$PATH"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

"$VENV/bin/python" "$ROOT/evidence/collect-modular-current-host.py" "$@"
"$VENV/bin/python" "$ROOT/src/fa3_modular_current_host_gate.py" --root "$ROOT"
