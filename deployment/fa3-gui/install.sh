#!/usr/bin/env bash
set -euo pipefail

CHECK_SOURCE_CONTRACT_ONLY=0
if [[ "${1:-}" == "--check-source-contract" ]]; then
  CHECK_SOURCE_CONTRACT_ONLY=1
  shift
fi
if [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--check-source-contract]" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_SRC="$REPO_ROOT/apps/fa3-control-center"
MAIN_QML="$APP_SRC/qml/Main.qml"
BUILD_DIR="$REPO_ROOT/.build/fa3-control-center"
PREFIX="${HOME}/.local"
INSTALLED_BIN="$PREFIX/libexec/fa3-control-center"
WRAPPER_BIN="$PREFIX/bin/fa3-control-center"
DESKTOP_FILE="$PREFIX/share/applications/org.fa3.ControlCenter.desktop"

if [[ ${EUID} -eq 0 ]]; then
  echo "Run this installer as the desktop user, not root." >&2
  exit 2
fi

# Fail closed before building if the source tree does not contain the GUI
# surfaces that the FA3 Control Center contract requires. This catches the
# exact class of regression where the repository and the installed UI drift.
required_markers=(
  'linkText: "Hugging Face"'
  'linkText: "CivitAI"'
  'linkText: "OpenModelDB"'
  'text: "Kérdezd: "'
  'property var routeTable'
  'function navigate(routeId)'
  'routeId: "agents.action-center"'
  'routeId: "decision.fabric"'
  'routeId: "decision.inspector"'
  'routeId: "decision.context-inspector"'
  'routeId: "decision.project-radar"'
  'routeId: "home.work-management"'
  'routeId: "system.accelerator-guard"'
  'routeId: "integrations.fa3-os"'
  'text: "⌕  Keresés"'
  'label: "Model Manager"'
  'label: "Rendszerbeállítások"'
  'title: "Weboldal"'
  'title: "Prezentáció"'
  'labelText: "CPU"'
  'labelText: "GPU"'
  'labelText: "NPU"'
  'Generic Linux · Wayland primary / X11 supported'
  'import QtWebEngine'
  'openInternalWeb'
)

for marker in "${required_markers[@]}"; do
  if ! grep -Fq "$marker" "$MAIN_QML"; then
    echo "FA3 GUI source-contract check FAILED: missing $marker" >&2
    exit 3
  fi
done

nav_start="$(grep -n 'component NavButton' "$MAIN_QML" | head -n1 | cut -d: -f1 || true)"
module_start="$(grep -n 'component ModuleCard' "$MAIN_QML" | head -n1 | cut -d: -f1 || true)"
if [[ -n "$nav_start" && -n "$module_start" ]]; then
  if sed -n "${nav_start},${module_start}p" "$MAIN_QML" | grep -Fq 'property int pageIndex'; then
    echo "FA3 GUI source-contract check FAILED: NavButton is still coupled to pageIndex" >&2
    exit 3
  fi
fi

if grep -Fq 'Qt.openUrlExternally(quickLinkRoot.targetUrl)' "$MAIN_QML"; then
  echo "FA3 GUI source-contract check FAILED: QuickLink still escapes to an external browser" >&2
  exit 3
fi

if [[ "$CHECK_SOURCE_CONTRACT_ONLY" -eq 1 ]]; then
  echo "FA3 GUI source contract: PASS (${#required_markers[@]} required surfaces)"
  exit 0
fi

if command -v git >/dev/null 2>&1 && git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  SOURCE_REV="$(git -C "$REPO_ROOT" rev-parse --short=12 HEAD)"
else
  SOURCE_REV="source-tree"
fi

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y \
    build-essential cmake ninja-build \
    qt6-base-dev qt6-declarative-dev qt6-webengine-dev \
    qml6-module-qtquick qml6-module-qtquick-controls qml6-module-qtquick-dialogs qml6-module-qtwebengine \
    qml6-module-qtquick-layouts qml6-module-qtqml-workerscript
fi

# QML is embedded in the executable. Reusing a previous build tree can leave
# an operator looking at a stale embedded resource even when Main.qml changed.
# Always build the desktop shell from a clean tree.
rm -rf "$BUILD_DIR"
cmake -S "$APP_SRC" -B "$BUILD_DIR" -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build "$BUILD_DIR" --parallel

# Remove the old executable before installing the freshly linked one. A
# currently running old instance is terminated after the new binary is safely
# installed so the next launch cannot keep displaying the previous UI image.
rm -f "$INSTALLED_BIN"
cmake --install "$BUILD_DIR"

test -x "$INSTALLED_BIN" || {
  echo "Install verification FAILED: $INSTALLED_BIN was not created." >&2
  exit 4
}

mkdir -p "$PREFIX/bin" "$PREFIX/share/applications" "$PREFIX/share/fa3-control-center"
cat >"$WRAPPER_BIN" <<EOF
#!/usr/bin/env bash
export FA3_REPO_ROOT="${REPO_ROOT}"
export FA3_GUI_SOURCE_REV="${SOURCE_REV}"
exec "${INSTALLED_BIN}" "\$@"
EOF
chmod 0755 "$WRAPPER_BIN"

# Install a user desktop entry with an absolute Exec path. The previous static
# `Exec=fa3-control-center` could resolve to an older system-wide binary when
# the desktop session PATH differed from the interactive shell PATH.
cat >"$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=FA3 Control Center
GenericName=AI Studio and Architecture Operations Console
Comment=Native operator projection for Final Architecture 3.0
Exec=${WRAPPER_BIN}
Icon=applications-system
Terminal=false
Categories=Development;System;Utility;
StartupNotify=true
StartupWMClass=fa3-control-center
EOF

printf '%s\n' "$SOURCE_REV" >"$PREFIX/share/fa3-control-center/source-revision"
update-desktop-database "$PREFIX/share/applications" >/dev/null 2>&1 || true

# An already-running executable keeps its old embedded QML even after the file
# on disk is replaced. Stop only the per-user FA3 instance installed here.
if pgrep -u "$USER" -f "^${INSTALLED_BIN}([[:space:]]|$)" >/dev/null 2>&1; then
  pkill -TERM -u "$USER" -f "^${INSTALLED_BIN}([[:space:]]|$)" || true
  sleep 1
fi

echo "FA3 GUI source contract: PASS (${#required_markers[@]} required surfaces)"
echo "Installed binary: $INSTALLED_BIN"
echo "Desktop launcher: $DESKTOP_FILE"
echo "Repository revision: $SOURCE_REV"
echo "Launch exactly: $WRAPPER_BIN"
