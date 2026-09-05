#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
python3 src/fa3_model_inventory_current_host_adapter.py
python3 evidence/collect-model-inventory-current-host.py --root "$ROOT"
python3 src/fa3_model_inventory_current_host_gate.py --root "$ROOT"
