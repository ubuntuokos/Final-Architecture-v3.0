#!/usr/bin/env bash
set -euo pipefail

VERSION="v1.1.15"
BASE_URL="https://github.com/AlexsJones/llmfit/releases/download/${VERSION}"
INSTALL_DIR="${HOME}/.local/libexec/fa3"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_NAME="fa3-llmfit.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ${EUID} -eq 0 ]]; then
  echo "Run this installer as the desktop user, not root." >&2
  exit 2
fi

case "$(uname -m)" in
  x86_64)
    ASSET="llmfit-${VERSION}-x86_64-unknown-linux-gnu.tar.gz"
    SHA256="fe0d4987376fae21cc1461f72a348a93c88cfacd2aec4356c15ba30603dcc731"
    ;;
  aarch64|arm64)
    ASSET="llmfit-${VERSION}-aarch64-unknown-linux-gnu.tar.gz"
    SHA256="c68d8720bf86ae8894790c2e16bfe942e8bc1983ecc73958e86bdefab94e69f8"
    ;;
  *)
    echo "Unsupported architecture for this installer: $(uname -m)" >&2
    exit 3
    ;;
esac

for cmd in curl sha256sum tar systemctl; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing required command: $cmd" >&2; exit 4; }
done

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
ARCHIVE="$TMP_DIR/$ASSET"

curl --fail --location --proto '=https' --tlsv1.2 \
  "${BASE_URL}/${ASSET}" -o "$ARCHIVE"
printf '%s  %s\n' "$SHA256" "$ARCHIVE" | sha256sum --check --status

tar -xzf "$ARCHIVE" -C "$TMP_DIR"
BIN="$(find "$TMP_DIR" -type f -name llmfit -perm -u+x | head -n 1)"
[[ -n "$BIN" ]] || { echo "llmfit binary not found in release archive" >&2; exit 5; }

mkdir -p "$INSTALL_DIR" "$UNIT_DIR"
install -m 0755 "$BIN" "$INSTALL_DIR/llmfit"
install -m 0644 "$SCRIPT_DIR/$UNIT_NAME" "$UNIT_DIR/$UNIT_NAME"

systemctl --user daemon-reload
systemctl --user enable --now "$UNIT_NAME"

RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
SOCKET="$RUNTIME_DIR/fa3/llmfit.sock"
for _ in {1..40}; do
  [[ -S "$SOCKET" ]] && break
  sleep 0.1
done

if [[ ! -S "$SOCKET" ]]; then
  echo "Service started but Unix socket is not available: $SOCKET" >&2
  systemctl --user --no-pager status "$UNIT_NAME" || true
  exit 6
fi

printf 'Installed llmfit %s\n' "$VERSION"
printf 'Service: %s\n' "$UNIT_NAME"
printf 'Socket: %s\n' "$SOCKET"
