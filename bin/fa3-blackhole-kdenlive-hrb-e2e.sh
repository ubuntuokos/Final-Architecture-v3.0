#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HRB_BIN="${FA3_HRB_BIN:-/usr/local/bin/fa3-host-resource-broker}"
PYTHON="${FA3_BLACKHOLE_PYTHON:-$ROOT/.venv-demucs/bin/python}"
MEMORY_BYTES="${FA3_DEMUCS_HRB_MEMORY_BYTES:-6442450944}"
TTL="${FA3_DEMUCS_HRB_TTL_SECONDS:-7200}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/blackhole-kdenlive-request.json" >&2
  exit 64
fi

REQUEST="$(realpath "$1")"
if [[ ! -f "$REQUEST" ]]; then
  echo "Request file not found: $REQUEST" >&2
  exit 66
fi
if [[ ! -x "$HRB_BIN" ]]; then
  echo "Canonical HRB binary not found/executable: $HRB_BIN" >&2
  exit 69
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "Python runtime not found/executable: $PYTHON" >&2
  echo "For Demucs preprocessing, point FA3_BLACKHOLE_PYTHON to the Demucs per-provider venv." >&2
  exit 69
fi
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi is required for broker UUID -> CUDA ordinal projection." >&2
  exit 69
fi

RUNDIR="$(mktemp -d -p "${XDG_RUNTIME_DIR:-/tmp}" fa3-blackhole-kdenlive-hrb.XXXXXX)"
LEASE="$RUNDIR/lease.json"
PATCHED="$RUNDIR/request.json"
LEASE_ID=""

cleanup() {
  set +e
  if [[ -n "$LEASE_ID" ]]; then
    sudo "$HRB_BIN" revoke-lease "$LEASE_ID" >/dev/null 2>&1 || true
  fi
  rm -rf "$RUNDIR"
}
trap cleanup EXIT INT TERM

sudo "$HRB_BIN" issue-lease   --memory-bytes "$MEMORY_BYTES"   --ttl "$TTL"   --purpose "FA3 Demucs Blackhole Kdenlive long-form preprocessing"   --output "$LEASE"

sudo chown "$(id -u):$(id -g)" "$LEASE"
chmod 0600 "$LEASE"

LEASE_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease_id"])' "$LEASE")"

"$PYTHON" - "$REQUEST" "$PATCHED" "$LEASE" "$HRB_BIN" <<'PY'
import json, subprocess, sys
src,dst,lease_path,hrb_bin=sys.argv[1:]
request=json.load(open(src,encoding="utf-8"))
lease=json.load(open(lease_path,encoding="utf-8"))
uuid=lease["accelerator_uuid"]
out=subprocess.run(
    ["nvidia-smi","--query-gpu=index,uuid","--format=csv,noheader,nounits"],
    check=True,stdout=subprocess.PIPE,text=True,
).stdout
mapping={}
for line in out.splitlines():
    idx,gpu_uuid=[x.strip() for x in line.split(",",1)]
    mapping[gpu_uuid]=int(idx)
if uuid not in mapping:
    raise SystemExit("broker-selected GPU UUID is not visible through current nvidia-smi inventory")
demucs=dict(request.get("demucs") or {})
demucs.update({
    "device":f"cuda:{mapping[uuid]}",
    "hrb_lease_path":lease_path,
    "hrb_verify_command":[hrb_bin,"validate-lease","{lease}"],
})
request["preprocessing"]="demucs_vocals"
request["demucs"]=demucs
json.dump(request,open(dst,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
open(dst,"a",encoding="utf-8").write("\n")
PY

echo "Running Blackhole/Kdenlive pipeline through HRB lease: $LEASE_ID"
PYTHONPATH="$ROOT/src" "$PYTHON" "$ROOT/evidence/collect-blackhole-kdenlive-current-host.py" --request "$PATCHED"
