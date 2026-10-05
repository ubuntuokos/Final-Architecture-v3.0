#!/usr/bin/env bash
set -euo pipefail
ROOT="${FA3_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export FA3_MODEL_SECURITY_HOME="${FA3_MODEL_SECURITY_HOME:-/ai-cache/fa3/model-security}"
"$ROOT/bin/fa3-model-artifact-security-bootstrap.sh"
PYTHONPATH="$ROOT/src" python3 "$ROOT/evidence/collect-model-artifact-security-current-host.py"
PYTHONPATH="$ROOT/src" python3 "$ROOT/src/fa3_model_artifact_security_current_host_gate.py" --root "$ROOT"
