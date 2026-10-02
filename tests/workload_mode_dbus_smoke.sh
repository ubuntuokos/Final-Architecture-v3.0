#!/usr/bin/env bash
set -euo pipefail
BUILD_DIR="${1:?build directory required}"

"$BUILD_DIR/workmoded" &
daemon=$!
bridge=""
cleanup() {
  if [[ -n "$bridge" ]]; then kill "$bridge" 2>/dev/null || true; fi
  kill "$daemon" 2>/dev/null || true
}
trap cleanup EXIT

sleep 1
"$BUILD_DIR/workmodectl" doctor | tee /tmp/wm-normal.json
python3 - <<'PY'
import json
with open("/tmp/wm-normal.json", encoding="utf-8") as fh:
    d=json.load(fh)
assert d["effective_mode"] == "NORMAL", d
assert d["authority"] == "WORKLOAD_MODE_LOCAL", d
PY

"$BUILD_DIR/workmodectl" register AI ci-ai COORDINATED $$ >/dev/null
"$BUILD_DIR/workmodectl" status | tee /tmp/wm-ai.json
python3 - <<'PY'
import json
with open("/tmp/wm-ai.json", encoding="utf-8") as fh:
    d=json.load(fh)
assert d["effective_mode"] == "AI", d
assert d["active_workload_count"] == 1, d
PY

"$BUILD_DIR/fa3-workload-mode-bridge" &
bridge=$!
sleep 1
"$BUILD_DIR/workmodectl" status | tee /tmp/wm-fa3.json
python3 - <<'PY'
import json
with open("/tmp/wm-fa3.json", encoding="utf-8") as fh:
    d=json.load(fh)
assert d["authority"] == "FA3_HRB", d
assert d["fa3_state"] == "CONNECTED", d
PY

"$BUILD_DIR/workmodectl" release ci-ai >/dev/null
ln -sfn workmoderun "$BUILD_DIR/aimoderun"
ln -sfn workmoderun "$BUILD_DIR/rendermoderun"
"$BUILD_DIR/aimoderun" /bin/true
"$BUILD_DIR/rendermoderun" /bin/true

"$BUILD_DIR/workmodectl" status | tee /tmp/wm-final.json
python3 - <<'PY'
import json
with open("/tmp/wm-final.json", encoding="utf-8") as fh:
    d=json.load(fh)
assert d["effective_mode"] == "NORMAL", d
assert d["active_workload_count"] == 0, d
PY
