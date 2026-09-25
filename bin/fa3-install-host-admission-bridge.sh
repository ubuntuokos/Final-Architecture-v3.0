#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER=""

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
[[ -n "$TARGET_USER" ]] || { echo "FAIL: target user missing" >&2; exit 21; }

"$ROOT/bin/fa3-install-hrb-validator-bridge.sh" --user "$TARGET_USER"
"$ROOT/bin/fa3-install-hrb-acquire-bridge.sh" --user "$TARGET_USER"
"$ROOT/bin/fa3-install-hrb-admission-bridge.sh" --user "$TARGET_USER"

echo "FA3 HOST ADMISSION BRIDGE: INSTALLED"
echo "NORMAL_RUNTIME_ROOT_REQUIRED: NO"
echo "HRB_HMAC_KEY_EXPOSED: NO"
