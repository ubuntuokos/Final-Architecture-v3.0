#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-run}"
[[ $# -le 1 ]] || { echo "usage: $0 [run|doctor]" >&2; exit 3; }
[[ ${EUID:-$(id -u)} -ne 0 ]] || { echo "FAIL: bridge client must run as non-root runner user" >&2; exit 20; }

HELPER="/usr/local/libexec/fa3-secret-broker-current-host-root"
PACKAGE_ROOT="/usr/local/lib/fa3/current-host-secret-broker"
SOURCE_COMMIT_FILE="$PACKAGE_ROOT/SOURCE_COMMIT"
OUT_ROOT="/run/fa3/current-host-secret-broker"
REPO_ROOT="${FA3_REPO_ROOT:-$PWD}"

for cmd in sudo git cp install grep; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "FAIL: missing prerequisite: $cmd" >&2; exit 21; }
done

[[ -x "$HELPER" ]] || { echo "FAIL: privileged helper missing: $HELPER" >&2; exit 22; }
[[ -s "$SOURCE_COMMIT_FILE" ]] || { echo "FAIL: source binding missing: $SOURCE_COMMIT_FILE" >&2; exit 23; }
sudo -n -l "$HELPER" >/dev/null 2>&1 || { echo "FAIL: exact non-interactive sudo bridge unavailable" >&2; exit 24; }

INSTALLED_COMMIT="$(tr -d '\r\n' < "$SOURCE_COMMIT_FILE")"
[[ "$INSTALLED_COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo "FAIL: invalid installed source commit" >&2; exit 25; }

[[ -d "$REPO_ROOT/.git" ]] || { echo "FAIL: FA3_REPO_ROOT is not a git checkout: $REPO_ROOT" >&2; exit 26; }
CHECKOUT_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD)"
[[ "$CHECKOUT_COMMIT" == "$INSTALLED_COMMIT" ]] || {
  echo "FAIL: privileged bridge source drift: installed=$INSTALLED_COMMIT checkout=$CHECKOUT_COMMIT" >&2
  echo "Run ./bin/fa3-current-host-runner-bootstrap.sh from the checked-out commit to refresh the bridge." >&2
  exit 27
}

case "$ACTION" in
  doctor)
    echo "FA3 SECRET BROKER CURRENT-HOST BRIDGE DOCTOR: PASS"
    echo "SOURCE_COMMIT: $INSTALLED_COMMIT"
    ;;
  run)
    sudo -n "$HELPER"
    [[ -s "$OUT_ROOT/secret-broker-current-host.json" ]] || { echo "FAIL: root receipt missing" >&2; exit 28; }
    [[ -s "$OUT_ROOT/secret-broker-current-host-gate-report.json" ]] || { echo "FAIL: root gate report missing" >&2; exit 29; }
    install -d -m0755 "$REPO_ROOT/evidence/receipts" "$REPO_ROOT/reports"
    cp "$OUT_ROOT/secret-broker-current-host.json" "$REPO_ROOT/evidence/receipts/secret-broker-current-host.json"
    cp "$OUT_ROOT/secret-broker-current-host-gate-report.json" "$REPO_ROOT/reports/secret-broker-current-host-gate-report.json"
    chmod 0644 "$REPO_ROOT/evidence/receipts/secret-broker-current-host.json" "$REPO_ROOT/reports/secret-broker-current-host-gate-report.json"
    echo "FA3 SECRET BROKER CURRENT-HOST BRIDGE: EVIDENCE COPIED"
    ;;
  *)
    echo "usage: $0 [run|doctor]" >&2
    exit 3
    ;;
esac
