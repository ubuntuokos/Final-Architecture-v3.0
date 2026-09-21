#!/usr/bin/env bash
set -euo pipefail

[[ "$(id -u)" -eq 0 ]] || { echo "Run with sudo/root." >&2; exit 2; }

ACTION="${1:-}"
MAPPER="${FA3_MACHINE_STATE_MAPPER:-fa3-machine-state}"
MNT="${FA3_MACHINE_STATE_MOUNT:-/run/fa3/machine-state}"
BROKER_SOCKET="${FA3_SECRET_BROKER_SOCKET:-/run/fa3-secret-broker/broker.sock}"
BROKER_HEALTH_CLI="${FA3_SECRET_BROKER_CLI:-/usr/local/bin/fa3-secretctl}"
BROKER_READY_ATTEMPTS="${FA3_SECRET_BROKER_READY_ATTEMPTS:-100}"
BROKER_READY_DELAY="${FA3_SECRET_BROKER_READY_DELAY:-0.1}"

diagnose_runtime() {
  echo "FA3 secrets lifecycle diagnostics:" >&2
  systemctl --no-pager --full status fa3-secret-vault.service fa3-secret-broker.service fa3-secrets.target >&2 || true
  journalctl --no-pager -n 120 -u fa3-secret-vault.service -u fa3-secret-broker.service >&2 || true
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
  if systemctl is-active --quiet fa3-secret-vault.service; then
    echo "FA3 secrets shutdown incomplete: vault service still active" >&2
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
  systemctl is-active --quiet fa3-secret-vault.service || { echo "FA3 secrets start incomplete: vault service not active" >&2; failed=1; }
  mountpoint -q "$MNT" || { echo "FA3 secrets start incomplete: vault not mounted at $MNT" >&2; failed=1; }
  [[ -e "/dev/mapper/$MAPPER" ]] || { echo "FA3 secrets start incomplete: LUKS mapper not open: $MAPPER" >&2; failed=1; }
  wait_broker_ready || failed=1
  if (( failed != 0 )); then
    diagnose_runtime
    systemctl stop fa3-secrets.target >/dev/null 2>&1 || true
    assert_closed || true
    return 2
  fi
}

case "$ACTION" in
  start)
    if ! systemctl start fa3-secrets.target; then
      echo "FA3 secrets start failed: fa3-secrets.target job failed" >&2
      diagnose_runtime
      systemctl stop fa3-secrets.target >/dev/null 2>&1 || true
      assert_closed || true
      exit 2
    fi
    assert_started
    echo "FA3 secrets lifecycle STARTED"
    ;;
  stop|exit)
    systemctl stop fa3-secrets.target
    assert_closed
    echo "FA3 secrets lifecycle CLOSED"
    ;;
  assert-closed)
    assert_closed
    echo "FA3 secrets lifecycle CLOSED"
    ;;
  status)
    printf 'target=%s\n' "$(systemctl is-active fa3-secrets.target 2>/dev/null || true)"
    printf 'broker=%s\n' "$(systemctl is-active fa3-secret-broker.service 2>/dev/null || true)"
    printf 'vault_service=%s\n' "$(systemctl is-active fa3-secret-vault.service 2>/dev/null || true)"
    printf 'mounted=%s\n' "$(mountpoint -q "$MNT" && echo yes || echo no)"
    printf 'mapper_open=%s\n' "$([[ -e "/dev/mapper/$MAPPER" ]] && echo yes || echo no)"
    printf 'broker_socket=%s\n' "$([[ -S "$BROKER_SOCKET" ]] && echo yes || echo no)"
    ;;
  *)
    echo "usage: $0 start|stop|exit|status|assert-closed" >&2
    exit 2
    ;;
esac
