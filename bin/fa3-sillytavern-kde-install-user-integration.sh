#!/usr/bin/env bash
set -euo pipefail

readonly repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
readonly source_root="$repo_root/deployment/sillytavern-kde"
readonly libexec_dir="${HOME}/.local/libexec/fa3"
readonly unit_dir="${HOME}/.config/systemd/user"
readonly desktop_dir="${HOME}/.local/share/applications"
readonly config_dir="${HOME}/.config/fa3"
readonly config_file="$config_dir/sillytavern-kde.env"
readonly expected_commit="51ad27fb86d39a3daca3adaa970375c9670c12df"
readonly expected_entry_blob="6126ef45ca881e30e7fceb134270dfb52d883b4b"
readonly expected_lock_blob="de71cacfc097733f36d79f103bfd9fb2686778a6"

load_config() {
  [[ -r "$config_file" ]] || {
    printf 'FA3 SillyTavern KDE: missing %s; run --install then set SILLYTAVERN_ROOT.\n' "$config_file" >&2
    exit 64
  }
  # shellcheck disable=SC1090
  source "$config_file"
  : "${SILLYTAVERN_ROOT:?Set SILLYTAVERN_ROOT in $config_file}"
}

verify_source() {
  load_config
  local root actual_commit entry_blob lock_blob
  root=$(readlink -f -- "$SILLYTAVERN_ROOT")
  [[ -d "$root/.git" ]] || { printf 'FA3 SillyTavern KDE: not a git checkout: %s\n' "$root" >&2; exit 65; }
  actual_commit=$(git -C "$root" rev-parse HEAD)
  [[ "$actual_commit" == "$expected_commit" ]] || {
    printf 'FA3 SillyTavern KDE: expected commit %s, got %s\n' "$expected_commit" "$actual_commit" >&2
    exit 65
  }
  entry_blob=$(git -C "$root" hash-object "$root/src/electron/index.js")
  lock_blob=$(git -C "$root" hash-object "$root/src/electron/package-lock.json")
  [[ "$entry_blob" == "$expected_entry_blob" && "$lock_blob" == "$expected_lock_blob" ]] || {
    printf 'FA3 SillyTavern KDE: Electron entrypoint/lockfile pin mismatch.\n' >&2
    exit 65
  }
  printf '%s\n' "$root"
}

install_integration() {
  install -d -m 0755 "$libexec_dir" "$unit_dir" "$desktop_dir" "$config_dir"
  install -m 0755 "$source_root/bin/sillytavern-kde-launch" "$libexec_dir/sillytavern-kde-launch"
  install -m 0755 "$source_root/bin/sillytavern-kde-start" "$libexec_dir/sillytavern-kde-start"
  install -m 0644 "$source_root/systemd/user/sillytavern-kde.service" "$unit_dir/sillytavern-kde.service"

  local temporary_desktop
  temporary_desktop=$(mktemp "${desktop_dir}/.sillytavern-kde-desktop.XXXXXX")
  sed "s#@START_WRAPPER@#${libexec_dir}/sillytavern-kde-start#" \
    "$source_root/applications/fa3-sillytavern-kde.desktop.in" >"$temporary_desktop"
  chmod 0644 "$temporary_desktop"
  if [[ -e "$desktop_dir/fa3-sillytavern-kde.desktop" ]] \
    && ! cmp -s "$temporary_desktop" "$desktop_dir/fa3-sillytavern-kde.desktop"; then
    cp -p "$desktop_dir/fa3-sillytavern-kde.desktop" \
      "$desktop_dir/fa3-sillytavern-kde.desktop.fa3-backup"
  fi
  mv -f "$temporary_desktop" "$desktop_dir/fa3-sillytavern-kde.desktop"

  if [[ ! -e "$config_file" ]]; then
    install -m 0600 "$source_root/sillytavern-kde.env.example" "$config_file"
  fi

  systemctl --user daemon-reload
  printf 'Installed FA3 SillyTavern KDE user integration. It remains disabled and on demand.\n'
  printf 'Set SILLYTAVERN_ROOT in %s, then run --prepare-deps explicitly.\n' "$config_file"
}

prepare_deps() {
  command -v npm >/dev/null 2>&1 || { printf 'FA3 SillyTavern KDE: npm is required for explicit dependency preparation.\n' >&2; exit 69; }
  local root
  root=$(verify_source)
  printf 'FA3 SillyTavern KDE: preparing pinned Electron dependencies for %s\n' "$root"
  (
    cd "$root/src/electron"
    npm ci --no-audit --no-fund --loglevel=error --no-progress
  )
  [[ -x "$root/src/electron/node_modules/.bin/electron" ]] || {
    printf 'FA3 SillyTavern KDE: Electron binary missing after dependency preparation.\n' >&2
    exit 70
  }
  printf 'FA3 SillyTavern KDE: dependency preparation complete. Normal launches remain mutation-free.\n'
}

check_integration() {
  test -x "$libexec_dir/sillytavern-kde-launch"
  test -x "$libexec_dir/sillytavern-kde-start"
  test -f "$unit_dir/sillytavern-kde.service"
  test -f "$desktop_dir/fa3-sillytavern-kde.desktop"
  test -f "$config_file"
  ! grep -Eq -- '--no-sandbox|npm (i|install|ci)|sudo|pkexec' "$libexec_dir/sillytavern-kde-launch"
  grep -q -- '--ozone-platform=wayland' "$libexec_dir/sillytavern-kde-launch"
  ! grep -q '^\[Install\]' "$unit_dir/sillytavern-kde.service"
  systemctl --user cat sillytavern-kde.service >/dev/null
  printf 'FA3 SillyTavern KDE user integration files are present. Current-host promotion still requires runtime E2E evidence.\n'
}

uninstall_integration() {
  systemctl --user stop sillytavern-kde.service 2>/dev/null || true
  rm -f \
    "$libexec_dir/sillytavern-kde-launch" \
    "$libexec_dir/sillytavern-kde-start" \
    "$unit_dir/sillytavern-kde.service" \
    "$desktop_dir/fa3-sillytavern-kde.desktop"
  systemctl --user daemon-reload
  printf 'Removed FA3 SillyTavern KDE integration. SillyTavern checkout, dependencies, user data and %s were preserved.\n' "$config_file"
}

case "${1:---install}" in
  --install) install_integration ;;
  --prepare-deps) prepare_deps ;;
  --check) check_integration ;;
  --uninstall) uninstall_integration ;;
  *) printf 'usage: %s [--install|--prepare-deps|--check|--uninstall]\n' "$0" >&2; exit 64 ;;
esac
