#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
chmod +x bin/fa3-marketing-bootstrap.sh evidence/collect-marketing-current-host.py src/fa3_marketing_current_host_gate.py
./bin/fa3-marketing-bootstrap.sh
python3 evidence/collect-marketing-current-host.py --output evidence/receipts/marketing-current-host.json
python3 src/fa3_marketing_current_host_gate.py --receipt evidence/receipts/marketing-current-host.json
