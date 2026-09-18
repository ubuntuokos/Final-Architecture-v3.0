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
DROPIN_DIR="$UNIT_DIR/$UNIT_NAME.d"
DROPIN_PATH="$DROPIN_DIR/20-fa3-hrb-acquire.conf"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_INSTALLER="$SCRIPT_DIR/fa3-install-host-admission-bridge.sh"
VALIDATOR_CLIENT="/usr/local/bin/fa3-host-resource-broker-validator"
VALIDATOR_HELPER="/usr/local/libexec/fa3-host-resource-broker-validate-root"
ACQUIRE_CLIENT="/usr/local/bin/fa3-host-resource-broker-acquire"
ACQUIRE_HELPER="/usr/local/libexec/fa3-host-resource-broker-acquire-root"
ACQUIRE_TEMPLATE="/usr/local/bin/fa3-host-resource-broker-acquire --workload {workload} --lease-output {lease} --accelerator-uuid {gpu_uuid}"

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "FAIL: current-host runner must not run as root" >&2
  exit 20
fi

for cmd in curl tar sha256sum python3 systemctl sudo; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "FAIL: missing prerequisite: $cmd" >&2; exit 21; }
done

if [[ ! -x "$VALIDATOR_CLIENT" ]] \
  || [[ ! -x "$ACQUIRE_CLIENT" ]] \
  || [[ ! -x "$ACQUIRE_HELPER" ]] \
  || ! sudo -n -l "$VALIDATOR_HELPER" /dev/null >/dev/null 2>&1 \
  || ! sudo -n -l "$ACQUIRE_HELPER" /dev/null >/dev/null 2>&1; then
  echo "INFO: installing root-separated HRB validation + acquire bridges"
  sudo "$BRIDGE_INSTALLER" --user "$USER"
fi

ensure_acquire_environment() {
  mkdir -p "$UNIT_DIR" "$DROPIN_DIR"
  chmod 700 "$UNIT_DIR" "$DROPIN_DIR"
  cat >"$DROPIN_PATH" <<EOF
[Service]
Environment="FA3_HRB_ACQUIRE_COMMAND=$ACQUIRE_TEMPLATE"
EOF
  chmod 600 "$DROPIN_PATH"
}

write_service_unit() {
  local runner_root_abs
  runner_root_abs="$(readlink -f "$RUNNER_ROOT")"
  mkdir -p "$UNIT_DIR"
  chmod 700 "$UNIT_DIR"
  cat >"$UNIT_PATH" <<EOF
[Unit]
Description=FA3 GitHub Actions current-host runner
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$runner_root_abs
ExecStart=$runner_root_abs/run.sh
Restart=on-failure
RestartSec=10
TimeoutStopSec=120
KillMode=control-group

[Install]
WantedBy=default.target
EOF
  chmod 600 "$UNIT_PATH"
}

activate_service() {
  write_service_unit
  ensure_acquire_environment
  systemctl --user daemon-reload
  systemctl --user enable --now "$UNIT_NAME"
}

repair_remote_runner_labels() {
  command -v gh >/dev/null 2>&1 || {
    echo "FAIL: gh is required to repair existing runner labels" >&2
    exit 25
  }

  local tmp runner_id missing_csv self_hosted payload
  local -a state
  tmp="$(mktemp)"
  gh api "repos/\${REPO}/actions/runners?per_page=100" >"$tmp"

  mapfile -t state < <(
    python3 - "$RUNNER_ROOT/.runner" "$tmp" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path

runner_file, api_file = sys.argv[1:]
local = json.loads(Path(runner_file).read_text(encoding="utf-8-sig"))
api = json.loads(Path(api_file).read_text(encoding="utf-8-sig"))
name = local.get("agentName") or local.get("name")
if not name:
    raise SystemExit("FAIL: local .runner has no agentName")
remote = next((r for r in api.get("runners", []) if r.get("name") == name), None)
if remote is None:
    raise SystemExit(f"FAIL: runner {name!r} not found in repository runner inventory")
labels = {str(x.get("name", "")).lower() for x in remote.get("labels", []) if isinstance(x, dict)}
repairable = ("linux", "x64", "fa3-current-host")
missing = [label for label in repairable if label not in labels]
print(remote["id"])
print(",".join(missing))
print("1" if "self-hosted" in labels else "0")
PY
  )
  rm -f "$tmp"

  runner_id="\${state[0]:-}"
  missing_csv="\${state[1]:-}"
  self_hosted="\${state[2]:-0}"

  [[ -n "$runner_id" ]] || { echo "FAIL: unable to resolve runner id" >&2; exit 26; }
  [[ "$self_hosted" == "1" ]] || {
    echo "FAIL: existing runner lost the read-only self-hosted label; re-registration is required" >&2
    exit 27
  }

  if [[ -z "$missing_csv" ]]; then
    return 0
  fi

  echo "INFO: repairing runner labels: $missing_csv"
  payload="$(
    python3 - "$missing_csv" <<'PY'
import json
import sys
labels = [x for x in sys.argv[1].split(",") if x]
print(json.dumps({"labels": labels}))
PY
  )"
  printf '%s\n' "$payload" |
    gh api --method POST \
      -H "Accept: application/vnd.github+json" \
      "repos/\${REPO}/actions/runners/\${runner_id}/labels" \
      --input - >/dev/null
}

if [[ -e "$RUNNER_ROOT/.runner" ]]; then
  echo "INFO: runner is already configured at $RUNNER_ROOT; preserving registration and recovering service wiring"
  [[ -x "$RUNNER_ROOT/bin/Runner.Listener" ]] || { echo "FAIL: existing runner registration has no Runner.Listener" >&2; exit 24; }
  activate_service
  repair_remote_runner_labels
  exec "$SCRIPT_DIR/fa3-current-host-runner-doctor"
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
activate_service

if command -v loginctl >/dev/null 2>&1; then
  LINGER="$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || true)"
  if [[ "$LINGER" != "yes" ]]; then
    echo "NOTICE: enable boot-persistent user service with: sudo loginctl enable-linger '$USER'" >&2
  fi
fi

exec "$SCRIPT_DIR/fa3-current-host-runner-doctor"
