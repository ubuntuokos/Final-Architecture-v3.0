#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "[FA3-INIT][ERROR] Not inside an FA3 Git repository." >&2
  exit 1
}
cd "$ROOT"
HOOK_DIR=".githooks"
[[ -f "$HOOK_DIR/pre-commit" ]] || {
  echo "[FA3-INIT][ERROR] Missing $HOOK_DIR/pre-commit" >&2
  exit 1
}
chmod +x "$HOOK_DIR/pre-commit" bin/fa3-dev bin/fa3-update

git config --local core.hooksPath "$HOOK_DIR"
CONFIGURED="$(git config --local --get core.hooksPath)"
[[ "$CONFIGURED" == "$HOOK_DIR" ]] || {
  echo "[FA3-INIT][ERROR] Failed to configure core.hooksPath" >&2
  exit 1
}

python3 src/fa3_dev_update_gate.py >/dev/null

echo "[FA3-INIT] FA3 hooks active: $CONFIGURED"
echo "[FA3-INIT] Canonical Dev/Update gate: PASS"
