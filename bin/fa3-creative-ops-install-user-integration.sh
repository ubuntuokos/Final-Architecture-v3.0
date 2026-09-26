#!/usr/bin/env bash
set -euo pipefail
readonly repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
readonly source_root="$repo_root/deployment/creative-operations-dashboard"
readonly libexec_dir="${HOME}/.local/libexec/fa3"
readonly unit_dir="${HOME}/.config/systemd/user"
readonly config_dir="${HOME}/.config/fa3"

case "${1:---install}" in
  --install)
    install -d -m 0755 "$libexec_dir" "$unit_dir" "$config_dir"
    install -m 0755 "$source_root/bin/fa3-creative-ops-action" "$libexec_dir/fa3-creative-ops-action"
    install -m 0644 "$source_root/systemd/user/fa3-creative-ops.target" "$unit_dir/fa3-creative-ops.target"
    if [[ ! -e "$config_dir/creative-ops-actions.env" ]]; then
      install -m 0600 "$source_root/creative-ops-actions.env.example" "$config_dir/creative-ops-actions.env"
    fi
    systemctl --user daemon-reload
    ;;
  --check)
    test -x "$libexec_dir/fa3-creative-ops-action"
    test -f "$unit_dir/fa3-creative-ops.target"
    ! grep -Eq '\b(eval|sudo|su |pkexec)\b' "$libexec_dir/fa3-creative-ops-action"
    ;;
  --uninstall)
    rm -f "$libexec_dir/fa3-creative-ops-action" "$unit_dir/fa3-creative-ops.target"
    systemctl --user daemon-reload
    ;;
  *) printf 'usage: %s [--install|--check|--uninstall]\n' "$0" >&2; exit 64 ;;
esac
