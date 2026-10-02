#!/usr/bin/env bash
set -euo pipefail
FA3_REQUIRED=0
CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --fa3-required) FA3_REQUIRED=1 ;;
    --check-source-contract) CHECK_ONLY=1 ;;
    *) echo "usage: $0 [--fa3-required] [--check-source-contract]" >&2; exit 64 ;;
  esac
done
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/apps/workload-mode"
PREFIX="${HOME}/.local"
for path in   "$SRC/CMakeLists.txt"   "$SRC/src/ModeManager.cpp"   "$SRC/src/ModeManager.h"   "$SRC/src/main.cpp"   "$SRC/src/workmodectl.cpp"   "$SRC/src/workmoderun.cpp"   "$SRC/src/fa3_workload_mode_bridge.cpp"; do
  test -f "$path" || { echo "missing required Workload Mode source: $path" >&2; exit 66; }
done
if [[ "$CHECK_ONLY" -eq 1 ]]; then
  echo "Workload Mode source contract: PASS"
  exit 0
fi
if [[ ${EUID} -eq 0 ]]; then
  echo "Run Workload Mode installer as the desktop/session user, not root." >&2
  exit 2
fi
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y build-essential cmake ninja-build qt6-base-dev
fi
BUILD="$ROOT/.build/workload-mode"
rm -rf "$BUILD"
cmake -S "$SRC" -B "$BUILD" -GNinja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build "$BUILD" --parallel
cmake --install "$BUILD"
mkdir -p "$PREFIX/bin" "$HOME/.config/systemd/user"
ln -sfn "$PREFIX/bin/workmoderun" "$PREFIX/bin/aimoderun"
ln -sfn "$PREFIX/bin/workmoderun" "$PREFIX/bin/rendermoderun"
install -m 0644 "$ROOT/deployment/workload-mode/workmoded.service" "$HOME/.config/systemd/user/workmoded.service"
if [[ "$FA3_REQUIRED" -eq 1 ]]; then
  install -m 0644 "$ROOT/deployment/workload-mode/fa3-workload-mode-bridge.service" "$HOME/.config/systemd/user/fa3-workload-mode-bridge.service"
fi
if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload
  systemctl --user enable --now workmoded.service
  if [[ "$FA3_REQUIRED" -eq 1 ]]; then
    systemctl --user enable --now fa3-workload-mode-bridge.service
  fi
fi
"$PREFIX/bin/workmodectl" doctor >/dev/null
echo "Workload Mode installed and healthy."
if [[ "$FA3_REQUIRED" -eq 1 ]]; then
  echo "FA3 mandatory bridge enabled."
fi
