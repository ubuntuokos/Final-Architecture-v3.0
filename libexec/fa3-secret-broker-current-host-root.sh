#!/usr/bin/env bash
set -euo pipefail

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "FAIL: privileged helper must run as root" >&2; exit 20; }
[[ $# -eq 0 ]] || { echo "FAIL: privileged helper accepts no arguments" >&2; exit 21; }

PACKAGE_ROOT="/usr/local/lib/fa3/current-host-secret-broker"
SOURCE_COMMIT_FILE="$PACKAGE_ROOT/SOURCE_COMMIT"
OUT_ROOT="/run/fa3/current-host-secret-broker"
RECEIPT="$OUT_ROOT/secret-broker-current-host.json"
REPORT="$OUT_ROOT/secret-broker-current-host-gate-report.json"

for cmd in install stat python3; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "FAIL: missing prerequisite: $cmd" >&2; exit 22; }
done

[[ -s "$SOURCE_COMMIT_FILE" ]] || { echo "FAIL: installed source binding missing" >&2; exit 23; }
SOURCE_COMMIT="$(tr -d '\r\n' < "$SOURCE_COMMIT_FILE")"
[[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo "FAIL: invalid installed source commit" >&2; exit 24; }

for path in   "$PACKAGE_ROOT/bin/fa3-secret-broker-current-host.sh"   "$PACKAGE_ROOT/bin/fa3-secretctl"   "$PACKAGE_ROOT/src/fa3_secret_broker.py"   "$PACKAGE_ROOT/src/fa3_secret_broker_current_host_gate.py"; do
  [[ -f "$path" && ! -L "$path" ]] || { echo "FAIL: trusted package file missing: $path" >&2; exit 25; }
  [[ "$(stat -c '%u' "$path")" == "0" ]] || { echo "FAIL: trusted package file not root-owned: $path" >&2; exit 26; }
  mode="$(stat -c '%a' "$path")"
  (( (8#$mode & 022) == 0 )) || { echo "FAIL: trusted package file is group/other writable: $path ($mode)" >&2; exit 27; }
done

install -d -o root -g root -m0755 "$OUT_ROOT"
rm -f "$RECEIPT" "$REPORT"

FA3_REPO_ROOT="$PACKAGE_ROOT" FA3_SECRET_BROKER_RECEIPT="$RECEIPT" FA3_CURRENT_HOST_PRIVILEGED_BRIDGE_SOURCE_COMMIT="$SOURCE_COMMIT"   "$PACKAGE_ROOT/bin/fa3-secret-broker-current-host.sh"

[[ -s "$RECEIPT" ]] || { echo "FAIL: current-host receipt missing" >&2; exit 28; }
[[ -s "$PACKAGE_ROOT/reports/secret-broker-current-host-gate-report.json" ]] || { echo "FAIL: current-host gate report missing" >&2; exit 29; }

install -o root -g root -m0644   "$PACKAGE_ROOT/reports/secret-broker-current-host-gate-report.json"   "$REPORT"
chmod 0644 "$RECEIPT"
chown root:root "$RECEIPT"

echo "FA3 SECRET BROKER CURRENT-HOST PRIVILEGED BRIDGE: PASS"
echo "SOURCE_COMMIT: $SOURCE_COMMIT"
