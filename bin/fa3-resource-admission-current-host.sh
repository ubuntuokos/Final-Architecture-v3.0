#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cmd="${1:-gate}"
if [[ $# -gt 0 ]]; then shift; fi
case "$cmd" in
  collect)
    exec python3 "$ROOT/evidence/collect-resource-admission-current-host.py" --root "$ROOT" "$@"
    ;;
  gate)
    exec env PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python3 "$ROOT/src/fa3_resource_admission_current_host_gate.py" --root "$ROOT" "$@"
    ;;
  *)
    echo "usage: $0 {collect|gate} [args...]" >&2
    exit 3
    ;;
esac
