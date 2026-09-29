#!/usr/bin/env bash
# Pinned Codex 0.151.0 Linux x86_64 Code Mode companion, FA3 namespace only.
set -euo pipefail
umask 077

VERSION="0.151.0"
TAG="rust-v0.151.0"
ARCHIVE="codex-code-mode-host-x86_64-unknown-linux-musl.tar.gz"
ARCHIVE_SHA256="332da68215f070321cb52ebe792ecce8dfd614d02ea5541309d0a5df01e14894"
URL="https://github.com/openai/codex/releases/download/${TAG}/${ARCHIVE}"
ROOT="${FA3_CODEX_ROOT:-$HOME/.local/lib/fa3/codex/$VERSION}"
SOURCE="$ROOT/source"
BIN="$ROOT/bin"
ARCHIVE_PATH="$SOURCE/$ARCHIVE"
HOST_BINARY="$BIN/codex-code-mode-host"

if [ "$(id -u)" -eq 0 ] || [ "$(uname -s)" != "Linux" ] || [ "$(uname -m)" != "x86_64" ]; then
  echo "FA3 pinned Code Mode companion requires non-root Linux x86_64." >&2
  exit 2
fi
command -v curl >/dev/null
command -v sha256sum >/dev/null
command -v tar >/dev/null
command -v cmp >/dev/null
mkdir -p "$SOURCE" "$BIN"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ -f "$ARCHIVE_PATH" ]; then
  if ! printf '%s  %s\n' "$ARCHIVE_SHA256" "$ARCHIVE_PATH" | sha256sum --check --status; then
    echo "Existing companion archive differs from the pinned SHA256; refusing to overwrite it." >&2
    exit 2
  fi
else
  curl --fail --location --proto '=https' --tlsv1.2 --output "$TMP/$ARCHIVE" "$URL"
  printf '%s  %s\n' "$ARCHIVE_SHA256" "$TMP/$ARCHIVE" | sha256sum --check --status
  mv -- "$TMP/$ARCHIVE" "$ARCHIVE_PATH"
fi

# The verified vendor archive is never extracted as an arbitrary directory tree.
LIST="$(tar -tzf "$ARCHIVE_PATH")"
MEMBER=""
while IFS= read -r item; do
  case "$item" in
    codex-code-mode-host|./codex-code-mode-host|codex-code-mode-host-x86_64-unknown-linux-musl|./codex-code-mode-host-x86_64-unknown-linux-musl)
      if [ -n "$MEMBER" ]; then
        echo "Multiple Code Mode host candidates in pinned release archive." >&2
        exit 2
      fi
      MEMBER="$item"
      ;;
  esac
done <<< "$LIST"
if [ -z "$MEMBER" ]; then
  echo "Pinned companion archive lacks the expected Linux x86_64 host." >&2
  exit 2
fi
tar -xOzf "$ARCHIVE_PATH" "$MEMBER" > "$TMP/codex-code-mode-host"
test -s "$TMP/codex-code-mode-host"
if [ -f "$HOST_BINARY" ] && cmp -s "$TMP/codex-code-mode-host" "$HOST_BINARY"; then
  test -x "$HOST_BINARY" || chmod 0755 "$HOST_BINARY"
else
  install -m 0755 "$TMP/codex-code-mode-host" "$HOST_BINARY"
fi
cmp -s "$TMP/codex-code-mode-host" "$HOST_BINARY" || {
  echo "Installed Code Mode companion differs from pinned archive." >&2
  exit 2
}
BINARY_SHA256="$(sha256sum "$HOST_BINARY" | awk '{print $1}')"
cat > "$ROOT/code-mode-host-bootstrap-receipt.json" <<EOF
{
  "schema": "fa3.codex-code-mode-host-bootstrap-receipt.v1",
  "version": "$VERSION",
  "release_tag": "$TAG",
  "archive": "$ARCHIVE_PATH",
  "archive_sha256": "$ARCHIVE_SHA256",
  "installed_binary": "$HOST_BINARY",
  "installed_binary_sha256": "$BINARY_SHA256",
  "status": "PASS"
}
EOF
echo "FA3 pinned Codex Code Mode companion installed: $HOST_BINARY"
echo "Verified upstream companion archive retained: $ARCHIVE_PATH"
