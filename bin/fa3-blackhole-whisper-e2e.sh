#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${FA3_BLACKHOLE_PYTHON:-python3}"
WHISPER_CLI="${FA3_WHISPER_CLI:-$ROOT/bin/fa3-whisper-stt}"
MODEL="${FA3_WHISPER_MODEL:-turbo}"
DEVICE="${FA3_WHISPER_DEVICE:-cpu}"
MODEL_CACHE="${FA3_WHISPER_MODEL_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/whisper}"
LEASE="${FA3_WHISPER_HRB_LEASE:-}"
FETCH="${FA3_WHISPER_ALLOW_NETWORK_MODEL_FETCH:-0}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/blackhole-kdenlive-request.json" >&2
  exit 64
fi
REQUEST="$(realpath "$1")"
[[ -f "$REQUEST" ]] || { echo "Request not found: $REQUEST" >&2; exit 66; }
[[ -f "$WHISPER_CLI" ]] || { echo "Whisper CLI unavailable: $WHISPER_CLI" >&2; exit 69; }

RUNDIR="$(mktemp -d -p "${XDG_RUNTIME_DIR:-/tmp}" fa3-blackhole-whisper.XXXXXX)"
PATCHED="$RUNDIR/request.json"
trap 'rm -rf "$RUNDIR"' EXIT INT TERM

"$PYTHON" - "$REQUEST" "$PATCHED" "$WHISPER_CLI" "$MODEL" "$DEVICE" "$MODEL_CACHE" "$LEASE" "$FETCH" <<'PY'
import json,sys
src,dst,cli,model,device,cache,lease,fetch=sys.argv[1:]
r=json.load(open(src,encoding="utf-8"))
cmd=["bash",cli,"transcribe","--request","{request}","--result","{result}","--model",model,"--device",device,"--model-cache",cache]
if fetch=="1":
    cmd.append("--allow-network-model-fetch")
if device.startswith("cuda:"):
    if not lease:
        raise SystemExit("CUDA Whisper requires FA3_WHISPER_HRB_LEASE")
    cmd += ["--hrb-lease",lease]
r["stt_command"]=cmd
json.dump(r,open(dst,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
open(dst,"a",encoding="utf-8").write("\n")
PY

PYTHONPATH="$ROOT/src" "$PYTHON" "$ROOT/evidence/collect-blackhole-kdenlive-current-host.py" --request "$PATCHED"
