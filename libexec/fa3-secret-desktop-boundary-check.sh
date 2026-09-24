#!/usr/bin/env bash
set -euo pipefail

MAPPER="${FA3_MACHINE_STATE_MAPPER:-fa3-machine-state}"
DEV="/dev/mapper/$MAPPER"

case "$MAPPER" in
  fa3-machine-state|fa3-machine-state-e2e-*|fa3-sb-e2e-*|fa3-sb-restore-*) ;;
  *)
    echo "unrecognized FA3 Secret Broker mapper: $MAPPER" >&2
    exit 2
    ;;
esac

[[ -e "$DEV" ]] || {
  echo "Secret Broker mapper missing for desktop-boundary check: $MAPPER" >&2
  exit 2
}

udevadm settle
PROPS="$(udevadm info --query=property --name="$DEV")"
grep -Fxq 'UDISKS_IGNORE=1' <<<"$PROPS" || {
  echo "Secret Broker mapper is not excluded from UDisks: $MAPPER" >&2
  exit 2
}
grep -Fxq 'UDISKS_SYSTEM_INTERNAL=1' <<<"$PROPS" || {
  echo "Secret Broker mapper is not marked system-internal: $MAPPER" >&2
  exit 2
}

if findmnt -rn -S "$DEV" >/dev/null 2>&1; then
  echo "Secret Broker mapper was mounted before the canonical systemd mount unit: $MAPPER" >&2
  findmnt -rn -S "$DEV" -o TARGET,SOURCE,FSTYPE,OPTIONS >&2 || true
  exit 2
fi

echo "FA3 Secret Broker desktop automount boundary: PASS"
