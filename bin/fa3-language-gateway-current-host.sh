#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 evidence/collect-language-gateway-current-host.py "$@"
python3 src/fa3_language_gateway_current_host_gate.py --root "$ROOT"
