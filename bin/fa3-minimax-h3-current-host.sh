#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"

if [[ "${FA3_MINIMAX_H3_BILLABLE_E2E_ACK:-}" != "I_ACKNOWLEDGE_BILLABLE_MINIMAX_H3_E2E" ]]; then
  echo "FAIL: explicit billable E2E acknowledgement is required" >&2
  exit 2
fi

python3 -m unittest tests.test_minimax_h3_runtime_admission -v
python3 src/fa3_minimax_h3_runtime_admission_gate.py --root "$ROOT"
python3 evidence/collect-minimax-h3-current-host.py --root "$ROOT" --duration "${FA3_MINIMAX_H3_E2E_DURATION:-4}" --resolution "${FA3_MINIMAX_H3_E2E_RESOLUTION:-768P}" --ratio "${FA3_MINIMAX_H3_E2E_RATIO:-16:9}"
python3 src/fa3_minimax_h3_runtime_admission_gate.py --root "$ROOT" --current-host
