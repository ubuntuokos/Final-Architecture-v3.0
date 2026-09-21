#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER=""
PACKAGE_ROOT="/usr/local/lib/fa3/current-host-secret-broker"
HELPER_DST="/usr/local/libexec/fa3-secret-broker-current-host-root"
CLIENT_DST="/usr/local/bin/fa3-secret-broker-current-host-bridge"

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

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "FAIL: installer must run through sudo/root" >&2; exit 20; }
[[ -n "$TARGET_USER" ]] || TARGET_USER="${SUDO_USER:-}"
[[ "$TARGET_USER" =~ ^[a-z_][a-z0-9_-]*\$?$ ]] || { echo "FAIL: invalid target user" >&2; exit 21; }
id "$TARGET_USER" >/dev/null 2>&1 || { echo "FAIL: target user does not exist" >&2; exit 22; }
[[ "$TARGET_USER" != "root" ]] || { echo "FAIL: root cannot be the runner target" >&2; exit 23; }

for cmd in git install visudo sudo tar mktemp chmod chown; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "FAIL: missing prerequisite: $cmd" >&2; exit 24; }
done

SOURCE_COMMIT="$(sudo -u "$TARGET_USER" git -C "$ROOT" rev-parse HEAD)"
[[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo "FAIL: unable to bind installer to git commit" >&2; exit 25; }

ARCHIVE_PATHS=(
  "src/fa3_secret_broker.py"
  "src/fa3_secret_broker_current_host_gate.py"
  "bin/fa3-secret-broker-current-host.sh"
  "bin/fa3-secret-broker-install"
  "bin/fa3-secretctl"
  "bin/fa3-secret-vault-init"
  "bin/fa3-secret-policyctl"
  "bin/fa3-secret-vault-recovery"
  "bin/fa3-secret-vault-rekey"
  "bin/fa3-secrets-admin"
  "libexec/fa3-secret-vault-mount.sh"
  "libexec/fa3-secrets-lifecycle.sh"
  "libexec/fa3-secret-broker-current-host-root.sh"
  "libexec/fa3-secret-broker-current-host-bridge.sh"
  "deployment/secrets/fa3-secret-vault.service"
  "deployment/secrets/fa3-secret-broker.service"
  "deployment/secrets/fa3-secrets.target"
)

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
SRC="$TMP/source"
mkdir -p "$SRC"

sudo -u "$TARGET_USER" git -C "$ROOT" archive --format=tar "$SOURCE_COMMIT" -- "${ARCHIVE_PATHS[@]}" | tar -xf - -C "$SRC"

for path in "${ARCHIVE_PATHS[@]}"; do
  [[ -e "$SRC/$path" ]] || { echo "FAIL: immutable source archive missing: $path" >&2; exit 26; }
done

FA3_REPO_ROOT="$SRC" "$SRC/bin/fa3-secret-broker-install"

install -d -o root -g root -m0755   "$PACKAGE_ROOT/bin"   "$PACKAGE_ROOT/src"   "$PACKAGE_ROOT/reports"   "$PACKAGE_ROOT/evidence/receipts"   /usr/local/libexec   /usr/local/bin

install -o root -g root -m0755 "$SRC/bin/fa3-secret-broker-current-host.sh" "$PACKAGE_ROOT/bin/fa3-secret-broker-current-host.sh"
install -o root -g root -m0755 "$SRC/bin/fa3-secretctl" "$PACKAGE_ROOT/bin/fa3-secretctl"
install -o root -g root -m0644 "$SRC/src/fa3_secret_broker.py" "$PACKAGE_ROOT/src/fa3_secret_broker.py"
install -o root -g root -m0644 "$SRC/src/fa3_secret_broker_current_host_gate.py" "$PACKAGE_ROOT/src/fa3_secret_broker_current_host_gate.py"

printf '%s\n' "$SOURCE_COMMIT" > "$PACKAGE_ROOT/SOURCE_COMMIT"
chown root:root "$PACKAGE_ROOT/SOURCE_COMMIT"
chmod 0444 "$PACKAGE_ROOT/SOURCE_COMMIT"

install -o root -g root -m0755 "$SRC/libexec/fa3-secret-broker-current-host-root.sh" "$HELPER_DST"
install -o root -g root -m0755 "$SRC/libexec/fa3-secret-broker-current-host-bridge.sh" "$CLIENT_DST"

SUDOERS="/etc/sudoers.d/fa3-secret-broker-current-host-${TARGET_USER}"
SUDO_TMP="$(mktemp)"
printf '%s ALL=(root) NOPASSWD: %s ""\n' "$TARGET_USER" "$HELPER_DST" > "$SUDO_TMP"
chmod 0440 "$SUDO_TMP"
visudo -cf "$SUDO_TMP" >/dev/null
install -o root -g root -m0440 "$SUDO_TMP" "$SUDOERS"
rm -f "$SUDO_TMP"
visudo -cf "$SUDOERS" >/dev/null

sudo -u "$TARGET_USER" env FA3_REPO_ROOT="$ROOT" "$CLIENT_DST" doctor >/dev/null   || { echo "FAIL: Secret Broker current-host bridge doctor failed" >&2; exit 27; }

echo "FA3 SECRET BROKER CURRENT-HOST PRIVILEGED BRIDGE: INSTALLED"
echo "USER: $TARGET_USER"
echo "SOURCE_COMMIT: $SOURCE_COMMIT"
echo "ROOT_HELPER: $HELPER_DST"
echo "GENERAL_PASSWORDLESS_SUDO: NO"
