#!/usr/bin/env bash
set -euo pipefail

COMMIT="bda946b4b6fffaaf6926aa8809bc62e0098f30e8"
DEFAULT_DEST="/opt/fa3/providers/pageindex-mcp-$COMMIT"
DEST="$DEFAULT_DEST"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest) DEST="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

for cmd in git node corepack; do
  command -v "$cmd" >/dev/null || { echo "missing dependency: $cmd" >&2; exit 2; }
done

if [[ -d "$DEST/.git" ]]; then
  current="$(git -C "$DEST" rev-parse HEAD)"
  if [[ "$current" == "$COMMIT" ]] && git -C "$DEST" diff --quiet && git -C "$DEST" diff --cached --quiet && [[ -f "$DEST/build/index.js" ]]; then
    echo "PageIndex MCP pinned source build already present: $DEST"
    exit 0
  fi
  echo "refusing to overwrite non-conformant existing destination: $DEST" >&2
  exit 2
fi

parent="$(dirname "$DEST")"
mkdir -p "$parent"
tmp="$DEST.tmp.$$"
trap 'rm -rf "$tmp"' EXIT

git clone --no-checkout https://github.com/VectifyAI/pageindex-mcp.git "$tmp"
git -C "$tmp" checkout --detach "$COMMIT"
test "$(git -C "$tmp" rev-parse HEAD)" = "$COMMIT"
git -C "$tmp" diff --quiet
git -C "$tmp" diff --cached --quiet

(
  cd "$tmp"
  corepack pnpm install --frozen-lockfile
  corepack pnpm run build
)

test -f "$tmp/build/index.js"
mv "$tmp" "$DEST"
trap - EXIT
echo "PageIndex MCP pinned source build materialized: $DEST"
