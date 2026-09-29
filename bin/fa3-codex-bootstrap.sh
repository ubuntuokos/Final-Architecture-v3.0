#!/usr/bin/env bash
set -euo pipefail
umask 077

VERSION="0.151.0"
TAG="rust-v0.151.0"
COMMIT="78c290807ce710180111df227df3b7a4fe845452"
ARCHIVE="codex-x86_64-unknown-linux-musl.tar.gz"
ARCHIVE_SHA256="605b4b183f22c645f5def63a5b7191767407fb66a6feaec4eaf10b5b7e0058f6"
URL="https://github.com/openai/codex/releases/download/${TAG}/${ARCHIVE}"
ROOT="${FA3_CODEX_ROOT:-$HOME/.local/lib/fa3/codex/$VERSION}"
SOURCE="$ROOT/source"
BIN="$ROOT/bin"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ "$(uname -s)" != "Linux" ] || [ "$(uname -m)" != "x86_64" ]; then
  echo "FA3 Codex v0.1 bootstrap supports Linux x86_64 only." >&2
  exit 2
fi
if [ "$(id -u)" -eq 0 ]; then
  echo "Run the FA3 Codex bootstrap as the normal user, not root." >&2
  exit 2
fi

command -v curl >/dev/null
command -v sha256sum >/dev/null
command -v tar >/dev/null
mkdir -p "$SOURCE" "$BIN"
ARCHIVE_PATH="$SOURCE/$ARCHIVE"

if [ -f "$ARCHIVE_PATH" ]; then
  printf '%s  %s\n' "$ARCHIVE_SHA256" "$ARCHIVE_PATH" | sha256sum --check --status || {
    echo "Cached Codex archive differs from pinned SHA256." >&2
    exit 2
  }
else
  curl --fail --location --proto '=https' --tlsv1.2 --output "$ARCHIVE_PATH.tmp" "$URL"
  printf '%s  %s\n' "$ARCHIVE_SHA256" "$ARCHIVE_PATH.tmp" | sha256sum --check --status
  mv -f "$ARCHIVE_PATH.tmp" "$ARCHIVE_PATH"
fi

mkdir "$TMP/extract"
tar -xzf "$ARCHIVE_PATH" -C "$TMP/extract"
CANDIDATE=""
for name in "$TMP/extract/codex-x86_64-unknown-linux-musl" "$TMP/extract/codex"; do
  if [ -f "$name" ]; then CANDIDATE="$name"; break; fi
done
if [ -z "$CANDIDATE" ]; then
  CANDIDATE="$(find "$TMP/extract" -type f \( -name 'codex' -o -name 'codex-x86_64-unknown-linux-*' \) | head -n 1)"
fi
test -n "$CANDIDATE"
install -m 0755 "$CANDIDATE" "$BIN/codex"

ACTUAL="$("$BIN/codex" --version 2>&1)"
case "$ACTUAL" in
  *"codex-cli $VERSION"*) ;;
  *) echo "Unexpected Codex version after install: $ACTUAL" >&2; exit 2 ;;
esac

# The Code Mode companion is a separate upstream release artifact.
FA3_CODEX_ROOT="$ROOT" bash "$(dirname "$0")/fa3-codex-code-mode-host-bootstrap.sh"
HOST_BINARY_SHA256="$(sha256sum "$BIN/codex-code-mode-host" | awk '{print $1}')"
HOST_ARCHIVE_SHA256="332da68215f070321cb52ebe792ecce8dfd614d02ea5541309d0a5df01e14894"
BINARY_SHA256="$(sha256sum "$BIN/codex" | awk '{print $1}')"
cat > "$ROOT/bootstrap-receipt.json" <<EOF
{
  "schema": "fa3.codex-bootstrap-receipt.v1",
  "version": "$VERSION",
  "release_tag": "$TAG",
  "release_commit": "$COMMIT",
  "archive": "$ARCHIVE_PATH",
  "archive_sha256": "$ARCHIVE_SHA256",
  "installed_binary": "$BIN/codex",
  "installed_binary_sha256": "$BINARY_SHA256",
  "code_mode_host_archive_sha256": "$HOST_ARCHIVE_SHA256",
  "code_mode_host_binary_sha256": "$HOST_BINARY_SHA256",
  "status": "PASS"
}
EOF

echo "FA3 Codex $VERSION installed at $BIN/codex"
echo "Pinned archive retained at $ARCHIVE_PATH"
if "$BIN/codex" login status >/dev/null 2>&1; then
  echo "Codex login status: available."
else
  echo "Codex is installed but not yet admitted: authenticate with ChatGPT using:"
  echo "  $BIN/codex login"
fi
