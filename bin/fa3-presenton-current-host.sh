#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT/evidence/collect-presenton-current-host.py" --root "$ROOT" "$@"
python3 "$ROOT/src/fa3_enforce.py" --root "$ROOT" presenton-current-host
