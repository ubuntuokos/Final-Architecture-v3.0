#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER=""
HELPER_DST="/usr/local/libexec/fa3-host-resource-broker-acquire-root"
CLIENT_DST="/usr/local/bin/fa3-host-resource-broker-acquire"
BROKER="/usr/local/bin/fa3-host-resource-broker"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)
      [[ $# -ge 2 ]] || { echo "FAIL: --user requires a value" >&2; exit 3; }
      TARGET_USER="$2"; shift 2 ;;
    *)
      echo "usage: sudo $0 --user USER" >&2
      exit 3 ;;
  esac
done

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "FAIL: installer must run through sudo/root" >&2
  exit 20
fi
[[ -n "$TARGET_USER" ]] || TARGET_USER="${SUDO_USER:-}"
[[ "$TARGET_USER" =~ ^[a-z_][a-z0-9_-]*\$?$ ]] || { echo "FAIL: invalid target user" >&2; exit 21; }
id "$TARGET_USER" >/dev/null 2>&1 || { echo "FAIL: target user does not exist" >&2; exit 22; }
[[ "$TARGET_USER" != "root" ]] || { echo "FAIL: root cannot be the runtime target" >&2; exit 23; }
[[ -x "$BROKER" ]] || { echo "FAIL: HRB broker missing: $BROKER" >&2; exit 24; }

for cmd in install visudo sudo stat python3; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "FAIL: missing prerequisite: $cmd" >&2; exit 25; }
done

install -d -o root -g root -m 0755 /usr/local/libexec /usr/local/bin
install -o root -g root -m 0755 \
  "$ROOT/libexec/fa3-host-resource-broker-acquire-root.py" \
  "$HELPER_DST"
install -o root -g root -m 0755 \
  "$ROOT/libexec/fa3-host-resource-broker-acquire.py" \
  "$CLIENT_DST"

SUDOERS="/etc/sudoers.d/fa3-hrb-acquire-${TARGET_USER}"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
printf '%s ALL=(root) NOPASSWD: %s *\n' "$TARGET_USER" "$HELPER_DST" >"$TMP"
chmod 0440 "$TMP"
visudo -cf "$TMP" >/dev/null
install -o root -g root -m 0440 "$TMP" "$SUDOERS"
visudo -cf "$SUDOERS" >/dev/null

KEY="/etc/fa3/host-resource-broker/lease-hmac.key"
if [[ -e "$KEY" ]]; then
  mode="$(stat -c '%a' "$KEY")"
  owner_uid="$(stat -c '%u' "$KEY")"
  [[ "$owner_uid" == "0" ]] || { echo "FAIL: HRB HMAC key is not root-owned" >&2; exit 26; }
  other_group_bits=$(( 8#$mode & 077 ))
  (( other_group_bits == 0 )) || { echo "FAIL: HRB HMAC key permissions are broader than owner-only: $mode" >&2; exit 27; }
fi

sudo -u "$TARGET_USER" "$CLIENT_DST" --doctor \
  || { echo "FAIL: acquire bridge doctor failed" >&2; exit 28; }

echo "FA3 HRB ACQUIRE BRIDGE: INSTALLED"
echo "USER: $TARGET_USER"
echo "CLIENT: $CLIENT_DST"
echo "SECRET_ACCESS: ROOT_ONLY"
echo "AUTHORITY: FA3-HOST-RESOURCE-BROKER-001"
