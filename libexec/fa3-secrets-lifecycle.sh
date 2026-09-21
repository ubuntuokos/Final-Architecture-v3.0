#!/usr/bin/env bash
set -euo pipefail

[[ "$(id -u)" -eq 0 ]] || { echo "Run with sudo/root." >&2; exit 2; }

ACTION="${1:-}"
MAPPER="${FA3_MACHINE_STATE_MAPPER:-fa3-machine-state}"
MNT="${FA3_MACHINE_STATE_MOUNT:-/run/fa3/machine-state}"
MOUNT_UNIT="${FA3_MACHINE_STATE_MOUNT_UNIT:-run-fa3-machine\x2dstate.mount}"
BROKER_SOCKET="${FA3_SECRET_BROKER_SOCKET:-/run/fa3-secret-broker/broker.sock}"
BROKER_HEALTH_CLI="${FA3_SECRET_BROKER_CLI:-/usr/local/bin/fa3-secretctl}"
BROKER_READY_ATTEMPTS="${FA3_SECRET_BROKER_READY_ATTEMPTS:-100}"
BROKER_READY_DELAY="${FA3_SECRET_BROKER_READY_DELAY:-0.1}"
VAULT_MOUNT_HELPER="${FA3_SECRET_VAULT_MOUNT_HELPER:-/usr/local/libexec/fa3-secret-vault-mount}"

diagnose_runtime() {
  echo "FA3 secrets lifecycle diagnostics:" >&2
  systemctl --no-pager --full status fa3-secret-vault.service "$MOUNT_UNIT" fa3-secret-broker.service fa3-secrets.target >&2 || true
  journalctl --no-pager -n 160 -u fa3-secret-vault.service -u "$MOUNT_UNIT" -u fa3-secret-broker.service >&2 || true
}

assert_closed() {
  local failed=0
  if systemctl is-active --quiet fa3-secrets.target; then
    echo "FA3 secrets shutdown incomplete: target still active" >&2
    failed=1
  fi
  if systemctl is-active --quiet fa3-secret-broker.service; then
    echo "FA3 secrets shutdown incomplete: broker still active" >&2
    failed=1
  fi
  if systemctl is-active --quiet "$MOUNT_UNIT"; then
    echo "FA3 secrets shutdown incomplete: mount unit still active: $MOUNT_UNIT" >&2
    failed=1
  fi
  if systemctl is-active --quiet fa3-secret-vault.service; then
    echo "FA3 secrets shutdown incomplete: mapper service still active" >&2
    failed=1
  fi
  if mountpoint -q "$MNT"; then
    echo "FA3 secrets shutdown incomplete: vault still mounted at $MNT" >&2
    failed=1
  fi
  if [[ -e "/dev/mapper/$MAPPER" ]]; then
    echo "FA3 secrets shutdown incomplete: LUKS mapper still open: $MAPPER" >&2
    failed=1
  fi
  (( failed == 0 )) || return 2
}

force_host_cleanup() {
  local failed=0
  systemctl stop fa3-secret-broker.service >/dev/null 2>&1 || failed=1
  systemctl stop "$MOUNT_UNIT" >/dev/null 2>&1 || failed=1
  systemctl stop fa3-secret-vault.service >/dev/null 2>&1 || failed=1
  FA3_MACHINE_STATE_MAPPER="$MAPPER" \
  FA3_MACHINE_STATE_MOUNT="$MNT" \
    "$VAULT_MOUNT_HELPER" close-mapper >/dev/null 2>&1 || failed=1
  (( failed == 0 )) || return 2
}

rollback_to_closed() {
  local failed=0
  systemctl stop fa3-secrets.target >/dev/null 2>&1 || failed=1
  force_host_cleanup || failed=1
  assert_closed || failed=1
  (( failed == 0 )) || {
    echo "FA3 secrets rollback incomplete: CLOSED state not reached" >&2
    return 2
  }
}

wait_broker_ready() {
  local i
  [[ "$BROKER_READY_ATTEMPTS" =~ ^[0-9]+$ ]] && (( BROKER_READY_ATTEMPTS > 0 )) || {
    echo "invalid FA3_SECRET_BROKER_READY_ATTEMPTS: $BROKER_READY_ATTEMPTS" >&2
    return 2
  }
  for ((i=0; i<BROKER_READY_ATTEMPTS; i++)); do
    if systemctl is-active --quiet fa3-secret-broker.service \
      && [[ -S "$BROKER_SOCKET" ]] \
      && "$BROKER_HEALTH_CLI" --socket "$BROKER_SOCKET" health >/dev/null 2>&1; then
      return 0
    fi
    sleep "$BROKER_READY_DELAY"
  done
  echo "FA3 secrets start incomplete: broker readiness/health timeout" >&2
  return 2
}

assert_started() {
  local failed=0
  systemctl is-active --quiet fa3-secrets.target || { echo "FA3 secrets start incomplete: target not active" >&2; failed=1; }
  systemctl is-active --quiet fa3-secret-vault.service || { echo "FA3 secrets start incomplete: mapper service not active" >&2; failed=1; }
  systemctl is-active --quiet "$MOUNT_UNIT" || { echo "FA3 secrets start incomplete: mount unit not active" >&2; failed=1; }
  FA3_MACHINE_STATE_MAPPER="$MAPPER" FA3_MACHINE_STATE_MOUNT="$MNT" "$VAULT_MOUNT_HELPER" assert-open || failed=1
  wait_broker_ready || failed=1
  if (( failed != 0 )); then
    diagnose_runtime
    rollback_to_closed || true
    return 2
  fi
}

case "$ACTION" in
  start)
    if ! systemctl start fa3-secrets.target; then
      echo "FA3 secrets start failed: fa3-secrets.target job failed" >&2
      diagnose_runtime
      rollback_to_closed || true
      exit 2
    fi
    assert_started
    echo "FA3 secrets lifecycle STARTED"
    ;;
  stop|exit)
    failed=0
    systemctl stop fa3-secrets.target || failed=1
    force_host_cleanup || failed=1
    assert_closed || failed=1
    if (( failed != 0 )); then
      echo "FA3 secrets lifecycle exit failed: CLOSED state not reached cleanly" >&2
      diagnose_runtime
      exit 2
    fi
    echo "FA3 secrets lifecycle CLOSED"
    ;;
  assert-closed)
    assert_closed
    echo "FA3 secrets lifecycle CLOSED"
    ;;
  status)
    printf 'target=%s\n' "$(systemctl is-active fa3-secrets.target 2>/dev/null || true)"
    printf 'broker=%s\n' "$(systemctl is-active fa3-secret-broker.service 2>/dev/null || true)"
    printf 'mount_unit=%s\n' "$(systemctl is-active "$MOUNT_UNIT" 2>/dev/null || true)"
    printf 'mapper_service=%s\n' "$(systemctl is-active fa3-secret-vault.service 2>/dev/null || true)"
    printf 'mounted=%s\n' "$(mountpoint -q "$MNT" && echo yes || echo no)"
    printf 'mapper_open=%s\n' "$([[ -e "/dev/mapper/$MAPPER" ]] && echo yes || echo no)"
    printf 'broker_socket=%s\n' "$([[ -S "$BROKER_SOCKET" ]] && echo yes || echo no)"
    ;;
  *)
    echo "usage: $0 start|stop|exit|status|assert-closed" >&2
    exit 2
    ;;
esac
