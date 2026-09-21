#!/usr/bin/env bash
set -euo pipefail

[[ "$(id -u)" -eq 0 ]] || { echo "Run with sudo/root." >&2; exit 2; }

ACTION="${1:-}"
MAPPER="${FA3_MACHINE_STATE_MAPPER:-fa3-machine-state}"
MNT="${FA3_MACHINE_STATE_MOUNT:-/run/fa3/machine-state}"

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

case "$ACTION" in
  start)
    systemctl start fa3-secrets.target
    systemctl is-active --quiet fa3-secret-vault.service
    systemctl is-active --quiet fa3-secret-broker.service
    mountpoint -q "$MNT"
    [[ -e "/dev/mapper/$MAPPER" ]]
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
    ;;
  *)
    echo "usage: $0 start|stop|exit|status|assert-closed" >&2
    exit 2
    ;;
esac
