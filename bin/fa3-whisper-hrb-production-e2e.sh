#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HRB_BIN="${FA3_HRB_BIN:-/usr/local/bin/fa3-host-resource-broker}"
PYTHON="${FA3_WHISPER_PYTHON:-$ROOT/.venv-whisper/bin/python}"
MEMORY_BYTES="${FA3_WHISPER_HRB_MEMORY_BYTES:-6442450944}"
TTL="${FA3_WHISPER_HRB_TTL_SECONDS:-7200}"
MODEL="${FA3_WHISPER_MODEL:-turbo}"
MODEL_CACHE="${FA3_WHISPER_MODEL_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/whisper}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/fa3-stt-media-request.json [--allow-network-model-fetch]" >&2
  exit 64
fi
REQUEST="$(realpath "$1")"
FETCH=""
if [[ "${2:-}" == "--allow-network-model-fetch" ]]; then FETCH="--allow-network-model-fetch"; fi
[[ -f "$REQUEST" ]] || { echo "Request file not found: $REQUEST" >&2; exit 66; }
[[ -x "$HRB_BIN" ]] || { echo "HRB binary unavailable: $HRB_BIN" >&2; exit 69; }
[[ -x "$PYTHON" ]] || { echo "Whisper Python unavailable: $PYTHON" >&2; exit 69; }
command -v nvidia-smi >/dev/null 2>&1 || { echo "nvidia-smi required" >&2; exit 69; }

RUNDIR="$(mktemp -d -p "${XDG_RUNTIME_DIR:-/tmp}" fa3-whisper-hrb.XXXXXX)"
LEASE="$RUNDIR/lease.json"
LEASE_ID=""
cleanup(){
  set +e
  if [[ -n "$LEASE_ID" ]]; then sudo "$HRB_BIN" revoke-lease "$LEASE_ID" >/dev/null 2>&1 || true; fi
  rm -rf "$RUNDIR"
}
trap cleanup EXIT INT TERM

sudo "$HRB_BIN" issue-lease --memory-bytes "$MEMORY_BYTES" --ttl "$TTL" --purpose "FA3 Whisper STT production E2E" --output "$LEASE"
sudo chown "$(id -u):$(id -g)" "$LEASE"
chmod 0600 "$LEASE"
LEASE_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease_id"])' "$LEASE")"
UUID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["accelerator_uuid"])' "$LEASE")"
ORDINAL="$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader,nounits | awk -F',' -v u="$UUID" '{gsub(/ /,"",$2); if($2==u){gsub(/ /,"",$1); print $1}}')"
[[ -n "$ORDINAL" ]] || { echo "Broker GPU UUID not visible via nvidia-smi" >&2; exit 70; }

ARGS=(--request "$REQUEST" --model "$MODEL" --device "cuda:$ORDINAL" --model-cache "$MODEL_CACHE" --hrb-lease "$LEASE" --hrb-verifier-bin "$HRB_BIN")
if [[ -n "$FETCH" ]]; then ARGS+=("$FETCH"); fi
PYTHONPATH="$ROOT/src" "$PYTHON" "$ROOT/evidence/collect-whisper-stt-current-host.py" "${ARGS[@]}"
