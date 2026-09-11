#!/usr/bin/env bash
set -euo pipefail

REPO="ubuntuokos/Final-Architecture-v3.0"
REPO_URL="https://github.com/${REPO}"
RUNNER_VERSION="2.337.0"
RUNNER_ASSET="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
RUNNER_SHA256="70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613"
RUNNER_ROOT="${FA3_RUNNER_ROOT:-$HOME/.local/share/fa3/actions-runner}"
RUNNER_NAME="${FA3_RUNNER_NAME:-fa3-current-host-$(hostname -s)}"
CUSTOM_LABEL="fa3-current-host"
UNIT_NAME="fa3-github-runner.service"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_PATH="$UNIT_DIR/$UNIT_NAME"

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "FAIL: current-host runner must not run as root" >&2
  exit 20
fi

for cmd in curl tar sha256sum python3 systemctl; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "FAIL: missing prerequisite: $cmd" >&2; exit 21; }
done

if [[ -e "$RUNNER_ROOT/.runner" ]]; then
  echo "INFO: runner is already configured at $RUNNER_ROOT; refusing implicit re-registration"
  exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fa3-current-host-runner-doctor"
fi

mkdir -p "$RUNNER_ROOT" "$UNIT_DIR"
chmod 700 "$RUNNER_ROOT" "$UNIT_DIR"

if [[ -n "${FA3_GITHUB_RUNNER_TOKEN:-}" ]]; then
  RUNNER_TOKEN="$FA3_GITHUB_RUNNER_TOKEN"
elif command -v gh >/dev/null 2>&1; then
  RUNNER_TOKEN="$(gh api --method POST "repos/${REPO}/actions/runners/registration-token" --jq .token)"
else
  echo "FAIL: provide FA3_GITHUB_RUNNER_TOKEN or install/authenticate gh with repository administration permission" >&2
  exit 22
fi

if [[ -z "$RUNNER_TOKEN" ]]; then
  echo "FAIL: empty runner registration token" >&2
  exit 23
fi

TMPDIR_FA3="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_FA3"; unset RUNNER_TOKEN FA3_GITHUB_RUNNER_TOKEN' EXIT
ARCHIVE="$TMPDIR_FA3/$RUNNER_ASSET"
URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_ASSET}"

curl --fail --location --proto '=https' --tlsv1.2 --output "$ARCHIVE" "$URL"
printf '%s  %s\n' "$RUNNER_SHA256" "$ARCHIVE" | sha256sum --check --strict

tar -xzf "$ARCHIVE" -C "$RUNNER_ROOT"
chmod -R u+rwX,go-rwx "$RUNNER_ROOT"

pushd "$RUNNER_ROOT" >/dev/null
./config.sh \
  --unattended \
  --url "$REPO_URL" \
  --token "$RUNNER_TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "$CUSTOM_LABEL" \
  --work _work \
  --disableupdate
popd >/dev/null

unset RUNNER_TOKEN FA3_GITHUB_RUNNER_TOKEN
RUNNER_ROOT_ABS="$(readlink -f "$RUNNER_ROOT")"
cat >"$UNIT_PATH" <<EOF
[Unit]
Description=FA3 GitHub Actions current-host runner
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$RUNNER_ROOT_ABS
ExecStart=$RUNNER_ROOT_ABS/run.sh
Restart=on-failure
RestartSec=10
TimeoutStopSec=120
KillMode=control-group

[Install]
WantedBy=default.target
EOF
chmod 600 "$UNIT_PATH"

systemctl --user daemon-reload
systemctl --user enable --now "$UNIT_NAME"

if command -v loginctl >/dev/null 2>&1; then
  LINGER="$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || true)"
  if [[ "$LINGER" != "yes" ]]; then
    echo "NOTICE: enable boot-persistent user service with: sudo loginctl enable-linger '$USER'" >&2
  fi
fi

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fa3-current-host-runner-doctor"
