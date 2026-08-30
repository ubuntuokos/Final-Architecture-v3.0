#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HRB_BIN="${FA3_HRB_BIN:-/usr/local/bin/fa3-host-resource-broker}"
MEMORY_BYTES="${FA3_DEMUCS_HRB_MEMORY_BYTES:-6442450944}"
TTL="${FA3_DEMUCS_HRB_TTL_SECONDS:-3600}"
MODEL="${FA3_DEMUCS_MODEL:-htdemucs}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/real-audio.wav [collector args...]" >&2
  exit 64
fi

INPUT="$(realpath "$1")"
shift
if [[ ! -f "$INPUT" ]]; then
  echo "Input audio not found: $INPUT" >&2
  exit 66
fi
if [[ ! -x "$HRB_BIN" ]]; then
  echo "Canonical HRB binary not found/executable: $HRB_BIN" >&2
  exit 69
fi

RUNDIR="$(mktemp -d -p "${XDG_RUNTIME_DIR:-/tmp}" fa3-demucs-hrb.XXXXXX)"
LEASE="$RUNDIR/lease.json"
LEASE_ID=""

cleanup() {
  set +e
  if [[ -n "$LEASE_ID" ]]; then
    sudo "$HRB_BIN" revoke-lease "$LEASE_ID" >/dev/null 2>&1 || true
  fi
  rm -rf "$RUNDIR"
}
trap cleanup EXIT INT TERM

echo "Requesting broker-selected accelerator lease..."
sudo "$HRB_BIN" issue-lease \
  --memory-bytes "$MEMORY_BYTES" \
  --ttl "$TTL" \
  --purpose "FA3 Demucs provider current-host production E2E" \
  --output "$LEASE"

sudo chown "$(id -u):$(id -g)" "$LEASE"
chmod 0600 "$LEASE"
LEASE_ID="$("$ROOT/.venv-demucs/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease_id"])' "$LEASE")"

echo "Running Demucs through canonical HRB lease: $LEASE_ID"
bash "$ROOT/bin/fa3-demucs-current-host.sh" \
  --input "$INPUT" \
  --model "$MODEL" \
  --device auto \
  --hrb-lease "$LEASE" \
  "$@"
