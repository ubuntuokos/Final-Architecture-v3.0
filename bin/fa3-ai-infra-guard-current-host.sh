#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="v4.6.0"
RUNTIME_ROOT="${FA3_AIG_RUNTIME_ROOT:-$HOME/.local/lib/fa3/ai-infra-guard/$VERSION}"
BINARY="${FA3_AIG_BINARY:-$RUNTIME_ROOT/bin/ai-infra-guard}"
SOURCE_ROOT="${FA3_AIG_SOURCE_ROOT:-$RUNTIME_ROOT/source/tree}"
META="${FA3_AIG_BUILD_METADATA:-$RUNTIME_ROOT/build-metadata.json}"

if [[ ! -x "$BINARY" || ! -f "$META" ]]; then
  bash "$ROOT/bin/fa3-ai-infra-guard-bootstrap.sh"
fi

PYTHONPATH="$ROOT/src" python3 "$ROOT/evidence/collect-ai-infra-guard-current-host.py"   --root "$ROOT"   --binary "$BINARY"   --source-root "$SOURCE_ROOT"   --build-metadata "$META"   "$@"

PYTHONPATH="$ROOT/src" python3 "$ROOT/src/fa3_ai_infra_guard_gate.py" --root "$ROOT" --current-host
