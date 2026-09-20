#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
case "${1:-}" in preflight) shift; exec python3 "$ROOT/evidence/collect-step-ca-current-host.py" --mode preflight "$@";; collect) shift; python3 "$ROOT/evidence/collect-step-ca-current-host.py" --mode full "$@"; exec "$ROOT/bin/fa3-enforce" step-ca-current-host;; gate) shift; exec "$ROOT/bin/fa3-enforce" step-ca-current-host "$@";; *) echo "usage: $0 {preflight|collect|gate}" >&2; exit 2;; esac
