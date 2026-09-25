#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER=""
HELPER_DST="/usr/local/libexec/fa3-host-resource-broker-admission-root"
CLIENT_DST="/usr/local/bin/fa3-host-resource-broker-admission"
KEY_DIR="/etc/fa3/host-resource-broker"
KEY_FILE="$KEY_DIR/admission-hmac-keys.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user) [[ $# -ge 2 ]] || { echo "FAIL: --user requires value" >&2; exit 3; }; TARGET_USER="$2"; shift 2 ;;
    *) echo "usage: sudo $0 --user USER" >&2; exit 3 ;;
  esac
done
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "FAIL: installer must run as root" >&2; exit 20; }
[[ -n "$TARGET_USER" ]] || TARGET_USER="${SUDO_USER:-}"
[[ "$TARGET_USER" =~ ^[a-z_][a-z0-9_-]*\$?$ ]] || { echo "FAIL: invalid target user" >&2; exit 21; }
id "$TARGET_USER" >/dev/null 2>&1 || { echo "FAIL: target user missing" >&2; exit 22; }
[[ "$TARGET_USER" != root ]] || { echo "FAIL: root cannot be runtime target" >&2; exit 23; }
for cmd in install visudo sudo stat python3 mktemp; do command -v "$cmd" >/dev/null || { echo "FAIL: missing $cmd" >&2; exit 24; }; done

install -d -o root -g root -m 0755 /usr/local/libexec /usr/local/bin
install -d -o root -g root -m 0700 "$KEY_DIR"
install -o root -g root -m 0755 "$ROOT/libexec/fa3-host-resource-broker-admission-root.py" "$HELPER_DST"
install -o root -g root -m 0755 "$ROOT/libexec/fa3-host-resource-broker-admission.py" "$CLIENT_DST"

if [[ ! -e "$KEY_FILE" ]]; then
  tmpkey="$(mktemp)"
  trap 'rm -f "$tmpkey" "${TMP:-}"' EXIT
  python3 - "$tmpkey" <<'PY'
import json,secrets,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({
  "scope":"HRB_INTERNAL_EPHEMERAL_ADMISSION_AUTH",
  "active_key_id":"admission-v1",
  "keys":[{"key_id":"admission-v1","secret_hex":secrets.token_hex(32)}]
},separators=(",",":"))+"\n",encoding="utf-8")
PY
  chmod 0600 "$tmpkey"
  install -o root -g root -m 0600 "$tmpkey" "$KEY_FILE"
  rm -f "$tmpkey"
fi
owner="$(stat -c '%u' "$KEY_FILE")"; mode="$(stat -c '%a' "$KEY_FILE")"
[[ "$owner" == 0 ]] || { echo "FAIL: admission keyring not root-owned" >&2; exit 25; }
(( 8#$mode & 077 == 0 )) || { echo "FAIL: admission keyring permissions too broad: $mode" >&2; exit 26; }

SUDOERS="/etc/sudoers.d/fa3-hrb-admission-$TARGET_USER"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
printf '%s ALL=(root) NOPASSWD: %s *\n' "$TARGET_USER" "$HELPER_DST" >"$TMP"
chmod 0440 "$TMP"; visudo -cf "$TMP" >/dev/null
install -o root -g root -m 0440 "$TMP" "$SUDOERS"; visudo -cf "$SUDOERS" >/dev/null
sudo -u "$TARGET_USER" "$CLIENT_DST" --doctor >/dev/null || { echo "FAIL: HRB admission bridge doctor failed" >&2; exit 27; }

echo "FA3 HRB ADMISSION BRIDGE: INSTALLED"
echo "USER: $TARGET_USER"
echo "CLIENT: $CLIENT_DST"
echo "AUTHORITY: FA3-AUTH-HOST-RESOURCE-BROKER-001"
echo "SECRET_ACCESS: ROOT_ONLY"
