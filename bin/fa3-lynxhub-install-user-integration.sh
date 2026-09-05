#!/usr/bin/env bash
set -euo pipefail

readonly repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
readonly source_root="$repo_root/deployment/lynxhub"
readonly libexec_dir="${HOME}/.local/libexec/fa3"
readonly unit_dir="${HOME}/.config/systemd/user"
readonly desktop_dir="${HOME}/.local/share/applications"
readonly config_dir="${HOME}/.config/fa3"

install_integration() {
  local installed_identity
  installed_identity=$(dpkg-query -W -f='${Package}\t${Version}\t${Architecture}' lynxhub 2>/dev/null || true)
  if [[ "$installed_identity" != $'lynxhub\t3.5.8\tamd64' || ! -x /opt/LynxHub/lynxhub ]]; then
    printf 'FA3 LynxHub: expected installed package lynxhub 3.5.8 amd64 was not found.\n' >&2
    exit 65
  fi

  install -d -m 0755 "$libexec_dir" "$unit_dir" "$desktop_dir" "$config_dir"
  install -m 0755 "$source_root/bin/lynxhub-launch" "$libexec_dir/lynxhub-launch"
  install -m 0755 "$source_root/bin/lynxhub-start" "$libexec_dir/lynxhub-start"
  install -m 0755 "$source_root/bin/lynxhub-action" "$libexec_dir/lynxhub-action"
  install -m 0644 "$source_root/systemd/user/lynxhub.service" "$unit_dir/lynxhub.service"
  install -m 0644 "$source_root/systemd/user/ai-creative-ops.target" "$unit_dir/ai-creative-ops.target"

  local temporary_desktop
  temporary_desktop=$(mktemp "${desktop_dir}/.lynxhub-desktop.XXXXXX")
  sed "s#@START_WRAPPER@#${libexec_dir}/lynxhub-start#" \
    "$source_root/applications/ai.kindabrazy.lynxhub.desktop.in" >"$temporary_desktop"
  chmod 0644 "$temporary_desktop"
  if [[ -e "$desktop_dir/ai.kindabrazy.lynxhub.desktop" ]] \
    && ! cmp -s "$temporary_desktop" "$desktop_dir/ai.kindabrazy.lynxhub.desktop"; then
    cp -p "$desktop_dir/ai.kindabrazy.lynxhub.desktop" \
      "$desktop_dir/ai.kindabrazy.lynxhub.desktop.fa3-backup"
  fi
  mv -f "$temporary_desktop" "$desktop_dir/ai.kindabrazy.lynxhub.desktop"

  if [[ ! -e "$config_dir/lynxhub-actions.env" ]]; then
    install -m 0600 "$source_root/lynxhub-actions.env.example" "$config_dir/lynxhub-actions.env"
  fi

  systemctl --user daemon-reload
  printf 'Installed FA3 LynxHub user integration. The service remains disabled and on demand.\n'
}

check_integration() {
  test -x /opt/LynxHub/lynxhub
  test -x "$libexec_dir/lynxhub-launch"
  test -x "$libexec_dir/lynxhub-start"
  test -x "$libexec_dir/lynxhub-action"
  test -f "$unit_dir/lynxhub.service"
  test -f "$unit_dir/ai-creative-ops.target"
  test -f "$desktop_dir/ai.kindabrazy.lynxhub.desktop"
  ! grep -q -- '--no-sandbox' "$desktop_dir/ai.kindabrazy.lynxhub.desktop" "$libexec_dir/lynxhub-launch"
  systemctl --user cat lynxhub.service >/dev/null
  printf 'FA3 LynxHub user integration files are present. Runtime E2E still requires the evidence collector.\n'
}

uninstall_integration() {
  systemctl --user stop lynxhub.service 2>/dev/null || true
  rm -f \
    "$libexec_dir/lynxhub-launch" \
    "$libexec_dir/lynxhub-start" \
    "$libexec_dir/lynxhub-action" \
    "$unit_dir/lynxhub.service" \
    "$unit_dir/ai-creative-ops.target" \
    "$desktop_dir/ai.kindabrazy.lynxhub.desktop"
  systemctl --user daemon-reload
  printf 'Removed FA3 LynxHub user integration. The vendor Debian package and user data were preserved.\n'
}

case "${1:---install}" in
  --install) install_integration ;;
  --check) check_integration ;;
  --uninstall) uninstall_integration ;;
  *) printf 'usage: %s [--install|--check|--uninstall]\n' "$0" >&2; exit 64 ;;
esac
