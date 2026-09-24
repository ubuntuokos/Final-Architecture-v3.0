#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
IMAGE="${FA3_MACHINE_STATE_IMAGE:-/var/lib/fa3/state/fa3-machine-state.img}"
MAPPER="${FA3_MACHINE_STATE_MAPPER:-fa3-machine-state}"
MNT="${FA3_MACHINE_STATE_MOUNT:-/run/fa3/machine-state}"
KEY="${CREDENTIALS_DIRECTORY:-}/fa3-machine-state-key"

require_root(){
  [[ "$(id -u)" -eq 0 ]] || { echo "root required" >&2; return 2; }
}

assert_mapper_open(){
  [[ -e "/dev/mapper/$MAPPER" ]] || { echo "LUKS mapper missing: $MAPPER" >&2; return 2; }
  [[ "$(blkid -p -o value -s TYPE "/dev/mapper/$MAPPER")" == "ext4" ]] || { echo "ext4 required" >&2; return 2; }
  [[ "$(blkid -p -o value -s LABEL "/dev/mapper/$MAPPER")" == "FA3_MSTATE" ]] || { echo "FA3_MSTATE filesystem label required" >&2; return 2; }
}

assert_mount_common(){
  local fstype opts owner mode
  mountpoint -q "$MNT" || { echo "vault mountpoint not active: $MNT" >&2; return 2; }
  fstype="$(findmnt -rn -T "$MNT" -o FSTYPE)"
  [[ "$fstype" == "ext4" ]] || { echo "mounted vault filesystem must be ext4" >&2; return 2; }
  opts="$(findmnt -rn -T "$MNT" -o OPTIONS)"
  for o in nodev nosuid noexec; do
    grep -qw "$o" <<<"${opts//,/ }" || { echo "mount option missing: $o" >&2; return 2; }
  done
  owner="$(stat -c '%U:%G' "$MNT")"
  mode="$(stat -c '%a' "$MNT")"
  [[ "$owner" == "fa3-secret-broker:fa3-secret-broker" ]] || { echo "vault root ownership mismatch: $owner" >&2; return 2; }
  [[ "$mode" == "750" ]] || { echo "vault root mode mismatch: $mode" >&2; return 2; }
  [[ -d "$MNT/objects" && -f "$MNT/index.json" ]] || { echo "vault structure incomplete" >&2; return 2; }
}

assert_broker_open(){
  assert_mount_common
}

assert_open(){
  local source source_real mapper_real
  assert_mount_common
  assert_mapper_open
  source="$(findmnt -rn -T "$MNT" -o SOURCE)"
  source_real="$(readlink -f "$source")"
  mapper_real="$(readlink -f "/dev/mapper/$MAPPER")"
  [[ -n "$source_real" && "$source_real" == "$mapper_real" ]] || {
    echo "vault mount source mismatch: expected mapper $MAPPER" >&2
    return 2
  }
}

open_mapper(){
  require_root
  local opened=false
  rollback_open(){
    rc=$?
    if [[ "$opened" == true && -e "/dev/mapper/$MAPPER" ]]; then
      cryptsetup close "$MAPPER" >/dev/null 2>&1 || true
    fi
    exit "$rc"
  }
  trap rollback_open ERR
  [[ -f "$IMAGE" && ! -L "$IMAGE" ]] || { echo "machine-state image missing" >&2; exit 2; }
  [[ "$(stat -c '%a' "$IMAGE")" == "600" ]] || { echo "machine-state image mode must be 0600" >&2; exit 2; }
  [[ -r "$KEY" ]] || { echo "systemd encrypted credential not materialized" >&2; exit 2; }
  [[ ! -e "/dev/mapper/$MAPPER" ]] || { echo "LUKS mapper already open: $MAPPER" >&2; exit 2; }
  cryptsetup isLuks "$IMAGE"
  cryptsetup luksDump "$IMAGE" | grep -Eq '^Version:[[:space:]]+2$'
  cryptsetup open --type luks2 --key-file "$KEY" "$IMAGE" "$MAPPER"
  opened=true
  assert_mapper_open
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

close_mapper(){
  require_root
  local attempts="${FA3_MAPPER_CLOSE_ATTEMPTS:-20}"
  local delay="${FA3_MAPPER_CLOSE_DELAY:-0.1}"
  local i

  [[ "$attempts" =~ ^[0-9]+$ ]] && (( attempts > 0 )) || {
    echo "invalid FA3_MAPPER_CLOSE_ATTEMPTS: $attempts" >&2
    return 2
  }

  if mountpoint -q "$MNT"; then
    echo "refusing LUKS close while vault mount is active: $MNT" >&2
    return 2
  fi

  if findmnt -rn -S "/dev/mapper/$MAPPER" >/dev/null 2>&1; then
    echo "refusing LUKS close while mapper still has a mounted filesystem: $MAPPER" >&2
    return 2
  fi

  if [[ -e "/dev/mapper/$MAPPER" ]]; then
    for ((i=1; i<=attempts; i++)); do
      if cryptsetup close "$MAPPER" >/dev/null 2>&1; then
        break
      fi
      if (( i == attempts )); then
        echo "LUKS mapper remained busy after $attempts bounded close attempts: $MAPPER" >&2
        return 2
      fi
      sleep "$delay"
    done
  fi

  assert_closed
}

case "$ACTION" in
  open|open-mapper) open_mapper;;
  close|close-mapper) close_mapper;;
  assert-open) assert_open;;
  assert-broker-open) assert_broker_open;;
  assert-closed) assert_closed;;
  *) echo "usage: $0 open|close|open-mapper|close-mapper|assert-open|assert-broker-open|assert-closed" >&2; exit 2;;
esac
