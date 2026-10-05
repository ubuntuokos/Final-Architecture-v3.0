#!/usr/bin/env bash
set -euo pipefail
PREFIX="${HOME}/.local"
rm -f "$PREFIX/bin/fa3-control-center"
rm -f "$PREFIX/libexec/fa3-control-center"
rm -f "$PREFIX/share/applications/org.fa3.ControlCenter.desktop"
update-desktop-database "$PREFIX/share/applications" >/dev/null 2>&1 || true
echo "FA3 Control Center user installation removed."
