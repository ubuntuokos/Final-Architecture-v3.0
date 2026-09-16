#!/usr/bin/env bash
set -euo pipefail

HELPER="/usr/local/libexec/fa3-host-resource-broker-authorize-root"

if [[ $# -lt 3 || $# -gt 4 || "$1" != "authorize-resource" ]]; then
  echo "usage: fa3-host-resource-broker-authorizer authorize-resource /absolute/workload.json /absolute/authorization.json [ttl_seconds]" >&2
  exit 3
fi
WORKLOAD="$2"
OUTPUT="$3"
TTL="${4:-300}"
[[ "$WORKLOAD" == /* ]] || { echo "DENIED: workload path must be absolute" >&2; exit 2; }
[[ "$OUTPUT" == /* ]] || { echo "DENIED: output path must be absolute" >&2; exit 2; }
[[ "$TTL" =~ ^[0-9]+$ ]] || { echo "DENIED: ttl must be an integer" >&2; exit 2; }

umask 077
mkdir -p -- "$(dirname -- "$OUTPUT")"
TMP="${OUTPUT}.tmp.$$"
trap 'rm -f -- "$TMP"' EXIT
sudo -n -- "$HELPER" "$WORKLOAD" "$TTL" >"$TMP"
chmod 0600 "$TMP"
mv -f -- "$TMP" "$OUTPUT"
trap - EXIT
printf '%s\n' "$OUTPUT"
