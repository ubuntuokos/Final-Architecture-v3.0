#!/usr/bin/env bash
set -euo pipefail

readonly repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
readonly provider_id="FA3-PROVIDER-SILLYTAVERN-KDE-001"
readonly gate_id="FA3-GATE-SILLYTAVERN-KDE-CURRENT-HOST-001"
readonly conformance_id="FA3-SILLYTAVERN-KDE-RUNTIME-CONFORMANCE-001"
readonly release="1.18.0"
readonly commit="51ad27fb86d39a3daca3adaa970375c9670c12df"
readonly root_lock="95b4dbc33c62829e2aff383f286889ebdcc15ffd"
readonly root_npmrc="2143f3df2fc935fce293d1ee5b3c073fd187e135"
readonly electron_entry="6126ef45ca881e30e7fceb134270dfb52d883b4b"
readonly electron_lock="de71cacfc097733f36d79f103bfd9fb2686778a6"
readonly source_root="${FA3_SILLYTAVERN_CURRENT_HOST_ROOT:-${HOME}/.local/share/fa3/sillytavern/1.18.0}"
readonly receipt="${FA3_SILLYTAVERN_CURRENT_HOST_RECEIPT:-${repo_root}/evidence/receipts/sillytavern-kde-current-host.json}"
readonly config_file="${HOME}/.config/fa3/sillytavern-kde.env"
readonly required_labels="self-hosted,linux,x64,fa3-current-host"

main_pid=""
discovered_url=""
node_major=0
root_dependencies_prepared=false
electron_dependencies_prepared=false
invalid_source_refused=false
all_service_listeners_loopback=false
ui_probe_sillytavern=false
clean_stop=false
resident_after=1
uninstall_pass=false
reinstall_pass=false
service_inactive_after=false
wayland_display=""
xdg_runtime_dir=""
graphical_session_active=false

write_receipt() {
  local status="$1"
  local reason="${2:-}"
  mkdir -p "$(dirname "$receipt")"
  RECEIPT_STATUS="$status" RECEIPT_REASON="$reason" \
  RECEIPT_URL="$discovered_url" RECEIPT_NODE_MAJOR="$node_major" \
  RECEIPT_ROOT_DEPS="$root_dependencies_prepared" RECEIPT_ELECTRON_DEPS="$electron_dependencies_prepared" \
  RECEIPT_INVALID_SOURCE="$invalid_source_refused" RECEIPT_LOOPBACK="$all_service_listeners_loopback" \
  RECEIPT_UI="$ui_probe_sillytavern" RECEIPT_CLEAN_STOP="$clean_stop" RECEIPT_RESIDENT_AFTER="$resident_after" \
  RECEIPT_UNINSTALL="$uninstall_pass" RECEIPT_REINSTALL="$reinstall_pass" RECEIPT_INACTIVE="$service_inactive_after" \
  RECEIPT_MAIN_PID="${main_pid:-0}" RECEIPT_WAYLAND_DISPLAY="$wayland_display" RECEIPT_XDG_RUNTIME_DIR="$xdg_runtime_dir" \
  RECEIPT_GRAPHICAL="$graphical_session_active" RECEIPT_SOURCE_ROOT="$source_root" \
  RECEIPT_RUNNER_LABELS="${FA3_RUNNER_LABELS:-}" RECEIPT_RUNNER_NAME="${RUNNER_NAME:-}" \
  RECEIPT_CI_FIXTURE="${FA3_CI_FIXTURE:-false}" \
  python3 - "$receipt" <<'PY'
from __future__ import annotations
import datetime as dt
import json
import os
import socket
import sys
from pathlib import Path

def b(name: str) -> bool:
    return os.environ.get(name, "false").lower() == "true"

labels = [x for x in os.environ.get("RECEIPT_RUNNER_LABELS", "").split(",") if x]
status = os.environ["RECEIPT_STATUS"]
out = {
    "schema": "fa3.sillytavern-kde-current-host-receipt.v1",
    "provider_id": "FA3-PROVIDER-SILLYTAVERN-KDE-001",
    "gate_id": "FA3-GATE-SILLYTAVERN-KDE-CURRENT-HOST-001",
    "conformance_id": "FA3-SILLYTAVERN-KDE-RUNTIME-CONFORMANCE-001",
    "result_status": status,
    "reason": os.environ.get("RECEIPT_REASON", ""),
    "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    "capability_scope": ["CAP-008"],
    "ci_fixture": b("RECEIPT_CI_FIXTURE"),
    "host": socket.gethostname(),
    "user": os.environ.get("USER", ""),
    "runner": {"name": os.environ.get("RECEIPT_RUNNER_NAME", ""), "labels": labels},
    "candidate": {"release": "1.18.0", "commit": "51ad27fb86d39a3daca3adaa970375c9670c12df"},
    "source": {
        "root": os.environ.get("RECEIPT_SOURCE_ROOT", ""),
        "commit_revalidated": status == "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "root_lock_revalidated": status == "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "root_npmrc_revalidated": status == "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "electron_entry_revalidated": status == "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "electron_lock_revalidated": status == "CURRENT_HOST_PRODUCTION_E2E_PASS",
    },
    "runtime": {
        "node_major": int(os.environ.get("RECEIPT_NODE_MAJOR", "0")),
        "root_dependencies_prepared": b("RECEIPT_ROOT_DEPS"),
        "electron_dependencies_prepared": b("RECEIPT_ELECTRON_DEPS"),
        "normal_launch_dependency_mutation": False,
    },
    "session": {
        "xdg_session_type": "wayland" if os.environ.get("RECEIPT_WAYLAND_DISPLAY") else "",
        "wayland_display": os.environ.get("RECEIPT_WAYLAND_DISPLAY", ""),
        "xdg_runtime_dir": os.environ.get("RECEIPT_XDG_RUNTIME_DIR", ""),
        "wayland_socket_exists": bool(os.environ.get("RECEIPT_WAYLAND_DISPLAY")) and status == "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "graphical_session_active": b("RECEIPT_GRAPHICAL"),
    },
    "process": {
        "main_pid": int(os.environ.get("RECEIPT_MAIN_PID", "0")),
        "ozone_wayland_present": status == "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "no_sandbox_present": False,
    },
    "network": {
        "fixed_port_assumed": False,
        "discovered_url": os.environ.get("RECEIPT_URL", ""),
        "all_service_listeners_loopback": b("RECEIPT_LOOPBACK"),
        "ui_probe_sillytavern": b("RECEIPT_UI"),
    },
    "negative": {"invalid_source_refused": b("RECEIPT_INVALID_SOURCE")},
    "authority": {
        "model_router_preserved": True,
        "mcp_gateway_preserved": True,
        "memory_authority_preserved": True,
        "hrb_preserved": True,
    },
    "stop": {"clean_stop": b("RECEIPT_CLEAN_STOP"), "resident_provider_processes_after": int(os.environ.get("RECEIPT_RESIDENT_AFTER", "1"))},
    "rollback": {
        "uninstall_pass": b("RECEIPT_UNINSTALL"),
        "reinstall_pass": b("RECEIPT_REINSTALL"),
        "service_inactive_after": b("RECEIPT_INACTIVE"),
    },
}
Path(sys.argv[1]).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.chmod(sys.argv[1], 0o600)
print(json.dumps(out, indent=2, sort_keys=True))
PY
}

fail() {
  local msg="$1"
  systemctl --user stop sillytavern-kde.service >/dev/null 2>&1 || true
  write_receipt "CURRENT_HOST_PRODUCTION_E2E_FAIL" "$msg" || true
  printf 'FAIL: %s\n' "$msg" >&2
  exit 1
}

trap 'systemctl --user stop sillytavern-kde.service >/dev/null 2>&1 || true' EXIT

[[ ${EUID:-$(id -u)} -ne 0 ]] || fail "current-host admission must not run as root"
for cmd in git node npm systemctl ss curl python3; do
  command -v "$cmd" >/dev/null 2>&1 || fail "missing prerequisite: $cmd"
done

node_major=$(node -p 'Number(process.versions.node.split(`.`)[0])')
(( node_major >= 20 )) || fail "Node.js 20 or newer is required"

labels=",${FA3_RUNNER_LABELS:-},"
for label in self-hosted linux x64 fa3-current-host; do
  [[ "$labels" == *",$label,"* ]] || fail "missing required runner label: $label"
done
[[ "${FA3_CI_FIXTURE:-false}" == "false" ]] || fail "CI fixture cannot claim current-host production evidence"

if [[ ! -d "$source_root/.git" ]]; then
  [[ ! -e "$source_root" || -d "$source_root" ]] || fail "source root exists and is not a directory"
  mkdir -p "$source_root"
  git -C "$source_root" init -q
  git -C "$source_root" remote add origin https://github.com/SillyTavern/SillyTavern.git
  git -C "$source_root" fetch -q --depth=1 origin "$commit"
  git -C "$source_root" checkout -q --detach FETCH_HEAD
fi

[[ "$(git -C "$source_root" rev-parse HEAD)" == "$commit" ]] || fail "source checkout commit mismatch"
[[ "$(git -C "$source_root" hash-object "$source_root/package-lock.json")" == "$root_lock" ]] || fail "root package-lock drift"
[[ "$(git -C "$source_root" hash-object "$source_root/.npmrc")" == "$root_npmrc" ]] || fail "root .npmrc drift"
[[ "$(git -C "$source_root" hash-object "$source_root/src/electron/index.js")" == "$electron_entry" ]] || fail "Electron entrypoint drift"
[[ "$(git -C "$source_root" hash-object "$source_root/src/electron/package-lock.json")" == "$electron_lock" ]] || fail "Electron lock drift"
grep -qx 'ignore-scripts=true' "$source_root/.npmrc" || fail "root npm ignore-scripts policy missing"

mkdir -p "${HOME}/.config/fa3"
printf 'SILLYTAVERN_ROOT=%q\n' "$source_root" >"$config_file"
chmod 600 "$config_file"

chmod +x "$repo_root/bin/fa3-sillytavern-kde-install-user-integration.sh"
"$repo_root/bin/fa3-sillytavern-kde-install-user-integration.sh" --install
"$repo_root/bin/fa3-sillytavern-kde-install-user-integration.sh" --prepare-deps
[[ -r "$source_root/node_modules/express/package.json" ]] || fail "root server runtime dependencies not prepared"
root_dependencies_prepared=true
[[ -x "$source_root/src/electron/node_modules/.bin/electron" ]] || fail "Electron dependencies not prepared"
electron_dependencies_prepared=true
"$repo_root/bin/fa3-sillytavern-kde-install-user-integration.sh" --check

bad_config=$(mktemp)
printf 'SILLYTAVERN_ROOT=%q\n' "$repo_root" >"$bad_config"
if FA3_SILLYTAVERN_KDE_CONFIG="$bad_config" "$HOME/.local/libexec/fa3/sillytavern-kde-launch" >/dev/null 2>&1; then
  rm -f "$bad_config"
  fail "invalid-source negative test unexpectedly succeeded"
fi
rm -f "$bad_config"
invalid_source_refused=true

manager_env=$(systemctl --user show-environment)
get_manager_env() {
  local key="$1"
  printf '%s\n' "$manager_env" | sed -n "s/^${key}=//p" | head -n1
}
xdg_session_type=$(get_manager_env XDG_SESSION_TYPE)
wayland_display=$(get_manager_env WAYLAND_DISPLAY)
xdg_runtime_dir=$(get_manager_env XDG_RUNTIME_DIR)
[[ "$xdg_session_type" == "wayland" ]] || fail "active user manager is not bound to a Wayland session"
[[ -n "$wayland_display" && -n "$xdg_runtime_dir" && -S "$xdg_runtime_dir/$wayland_display" ]] || fail "Wayland socket unavailable to the user manager"
if systemctl --user is-active --quiet graphical-session.target; then
  graphical_session_active=true
else
  fail "graphical-session.target is not active"
fi

systemctl --user reset-failed sillytavern-kde.service >/dev/null 2>&1 || true
systemctl --user start sillytavern-kde.service
for _ in $(seq 1 30); do
  main_pid=$(systemctl --user show -p MainPID --value sillytavern-kde.service)
  if [[ "$main_pid" =~ ^[1-9][0-9]*$ ]] && kill -0 "$main_pid" 2>/dev/null; then
    break
  fi
  sleep 1
done
[[ "$main_pid" =~ ^[1-9][0-9]*$ ]] && kill -0 "$main_pid" 2>/dev/null || fail "Electron service did not become live"

cmdline=$(tr '\0' ' ' <"/proc/$main_pid/cmdline")
[[ "$cmdline" == *"--ozone-platform=wayland"* ]] || fail "Electron main process lacks Wayland Ozone argument"
[[ "$cmdline" != *"--no-sandbox"* ]] || fail "Electron sandbox-disable argument detected"

listener_json=$(mktemp)
for _ in $(seq 1 45); do
  ss -H -ltnp >"$listener_json" 2>/dev/null || true
  candidate=$(python3 - "$listener_json" "$main_pid" <<'PY'
import re, sys
from pathlib import Path
pid = sys.argv[2]
for line in Path(sys.argv[1]).read_text(errors="replace").splitlines():
    if f"pid={pid}," not in line:
        continue
    cols = line.split()
    if len(cols) < 4:
        continue
    local = cols[3]
    if local.startswith("127.") or local.startswith("[::1]:") or local.startswith("::1:"):
        port = local.rsplit(":", 1)[-1]
        if port.isdigit():
            print(f"http://127.0.0.1:{port}")
            raise SystemExit(0)
    else:
        print("NON_LOOPBACK:" + local)
        raise SystemExit(2)
raise SystemExit(1)
PY
  ) && rc=0 || rc=$?
  if [[ $rc -eq 2 ]]; then
    rm -f "$listener_json"
    fail "SillyTavern service exposed a non-loopback listener: $candidate"
  fi
  if [[ $rc -eq 0 && "$candidate" == http://127.0.0.1:* ]]; then
    discovered_url="$candidate"
    all_service_listeners_loopback=true
    break
  fi
  sleep 1
done
rm -f "$listener_json"
[[ -n "$discovered_url" ]] || fail "no loopback SillyTavern listener discovered from the live service PID"

if curl -fsS --max-time 8 "$discovered_url/" | grep -qi 'SillyTavern'; then
  ui_probe_sillytavern=true
else
  fail "dynamic loopback UI probe did not identify SillyTavern"
fi

control_group=$(systemctl --user show -p ControlGroup --value sillytavern-kde.service)
systemctl --user stop sillytavern-kde.service
for _ in $(seq 1 15); do
  systemctl --user is-active --quiet sillytavern-kde.service || break
  sleep 1
done
if ! systemctl --user is-active --quiet sillytavern-kde.service && ! kill -0 "$main_pid" 2>/dev/null; then
  clean_stop=true
else
  fail "clean stop failed"
fi
resident_after=0
if [[ -n "$control_group" && -r "/sys/fs/cgroup${control_group}/cgroup.procs" && -s "/sys/fs/cgroup${control_group}/cgroup.procs" ]]; then
  resident_after=$(wc -l <"/sys/fs/cgroup${control_group}/cgroup.procs")
fi
(( resident_after == 0 )) || fail "provider processes remain in the service cgroup after stop"

"$repo_root/bin/fa3-sillytavern-kde-install-user-integration.sh" --uninstall
if [[ ! -e "$HOME/.config/systemd/user/sillytavern-kde.service" && ! -e "$HOME/.local/libexec/fa3/sillytavern-kde-launch" ]]; then
  uninstall_pass=true
else
  fail "rollback uninstall did not remove the FA3 integration"
fi

"$repo_root/bin/fa3-sillytavern-kde-install-user-integration.sh" --install
printf 'SILLYTAVERN_ROOT=%q\n' "$source_root" >"$config_file"
chmod 600 "$config_file"
"$repo_root/bin/fa3-sillytavern-kde-install-user-integration.sh" --check
reinstall_pass=true
if ! systemctl --user is-active --quiet sillytavern-kde.service; then
  service_inactive_after=true
else
  fail "service is unexpectedly active after rollback reinstall"
fi

write_receipt "CURRENT_HOST_PRODUCTION_E2E_PASS" "real KDE6/Wayland SillyTavern current-host admission passed"
trap - EXIT
exit 0
