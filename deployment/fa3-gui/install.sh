#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_SRC="$REPO_ROOT/apps/fa3-control-center"
BUILD_DIR="$REPO_ROOT/.build/fa3-control-center"
PREFIX="${HOME}/.local"

if [[ ${EUID} -eq 0 ]]; then
  echo "Run this installer as the desktop user, not root." >&2
  exit 2
fi

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y \
    build-essential cmake ninja-build \
    qt6-base-dev qt6-declarative-dev \
    qml6-module-qtquick qml6-module-qtquick-controls \
    qml6-module-qtquick-layouts qml6-module-qtqml-workerscript
fi

cmake -S "$APP_SRC" -B "$BUILD_DIR" -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build "$BUILD_DIR" --parallel
cmake --install "$BUILD_DIR"

mkdir -p "$PREFIX/bin"
cat >"$PREFIX/bin/fa3-control-center" <<EOF
#!/usr/bin/env bash
export FA3_REPO_ROOT="${REPO_ROOT}"
exec "${PREFIX}/libexec/fa3-control-center" "\$@"
EOF
chmod 0755 "$PREFIX/bin/fa3-control-center"
update-desktop-database "$PREFIX/share/applications" >/dev/null 2>&1 || true

echo "Installed: $PREFIX/bin/fa3-control-center"
echo "Repository: $REPO_ROOT"
