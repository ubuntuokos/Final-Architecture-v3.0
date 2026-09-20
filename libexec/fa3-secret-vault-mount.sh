#!/usr/bin/env bash
set -euo pipefail
[[ "$(id -u)" -eq 0 ]] || { echo "root required" >&2; exit 2; }
ACTION="${1:-}"
IMAGE="${FA3_MACHINE_STATE_IMAGE:-/var/lib/fa3/state/fa3-machine-state.img}"
MAPPER="${FA3_MACHINE_STATE_MAPPER:-fa3-machine-state}"
MNT="${FA3_MACHINE_STATE_MOUNT:-/run/fa3/machine-state}"
KEY="${CREDENTIALS_DIRECTORY:-}/fa3-machine-state-key"
open_vault(){
  rollback_open(){
    rc=$?
    mountpoint -q "$MNT" && umount "$MNT" >/dev/null 2>&1 || true
    [[ -e "/dev/mapper/$MAPPER" ]] && cryptsetup close "$MAPPER" >/dev/null 2>&1 || true
    exit "$rc"
  }
  trap rollback_open ERR
  [[ -f "$IMAGE" && ! -L "$IMAGE" ]] || { echo "machine-state image missing" >&2; exit 2; }
  [[ "$(stat -c '%a' "$IMAGE")" == "600" ]] || { echo "machine-state image mode must be 0600" >&2; exit 2; }
  [[ -r "$KEY" ]] || { echo "systemd encrypted credential not materialized" >&2; exit 2; }
  cryptsetup isLuks "$IMAGE"
  cryptsetup luksDump "$IMAGE" | grep -Eq '^Version:[[:space:]]+2$'
  install -d -o fa3-secret-broker -g fa3-secret-broker -m0750 "$MNT"
  if [[ ! -e "/dev/mapper/$MAPPER" ]]; then cryptsetup open --type luks2 --key-file "$KEY" "$IMAGE" "$MAPPER"; fi
  [[ "$(blkid -p -o value -s TYPE "/dev/mapper/$MAPPER")" == "ext4" ]] || { echo "ext4 required" >&2; return 2; }
  [[ "$(blkid -p -o value -s LABEL "/dev/mapper/$MAPPER")" == "FA3_MSTATE" ]] || { echo "FA3_MSTATE filesystem label required" >&2; return 2; }
  if ! mountpoint -q "$MNT"; then mount -o nodev,nosuid,noexec "/dev/mapper/$MAPPER" "$MNT"; fi
  chown fa3-secret-broker:fa3-secret-broker "$MNT"; chmod 0750 "$MNT"
  opts="$(findmnt -rn -T "$MNT" -o OPTIONS)"
  for o in nodev nosuid noexec; do grep -qw "$o" <<<"${opts//,/ }" || { echo "mount option missing: $o" >&2; return 2; }; done
  trap - ERR
}
assert_closed(){
  if mountpoint -q "$MNT"; then
    echo "vault remains mounted: $MNT" >&2
    return 2
  fi
  if [[ -e "/dev/mapper/$MAPPER" ]]; then
    echo "LUKS mapper remains open: $MAPPER" >&2
    return 2
  fi
}
close_vault(){
  if mountpoint -q "$MNT"; then umount "$MNT"; fi
  if [[ -e "/dev/mapper/$MAPPER" ]]; then cryptsetup close "$MAPPER"; fi
  assert_closed
}
case "$ACTION" in
  open) open_vault;;
  close) close_vault;;
  assert-closed) assert_closed;;
  *) echo "usage: $0 open|close|assert-closed" >&2; exit 2;;
esac
