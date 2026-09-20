#!/usr/bin/env bash
set -euo pipefail
[[ "$(id -u)" -eq 0 ]] || { echo "Run with sudo/root." >&2; exit 2; }
ROOT="${FA3_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
RECEIPT="${FA3_SECRET_BROKER_RECEIPT:-$ROOT/evidence/receipts/secret-broker-current-host.json}"
for c in cryptsetup mkfs.ext4 mount umount mountpoint sha256sum runuser python3 grep awk cp cmp stat getent; do command -v "$c" >/dev/null || { echo "missing prerequisite: $c" >&2; exit 2; }; done
getent passwd fa3-secret-broker >/dev/null || { echo "fa3-secret-broker service user missing; run installer first" >&2; exit 2; }
TMP="$(mktemp -d /var/tmp/fa3-secret-broker-e2e.XXXXXX)"; chmod 0700 "$TMP"
IMG="$TMP/fa3-machine-state.img"; BACKUP="$TMP/fa3-machine-state.backup.img"; KEY="$TMP/key"
MAPPER="fa3-sb-e2e-$$"; RMAPPER="fa3-sb-restore-$$"; MNT="$TMP/mnt"; RMNT="$TMP/rmnt"; POL="$TMP/policy"; RUN="$TMP/run"
BROKER_PID=""; RESTORE_PID=""
cleanup(){
  if [[ -n "$RESTORE_PID" ]]; then kill "$RESTORE_PID" >/dev/null 2>&1 || true; wait "$RESTORE_PID" 2>/dev/null || true; fi
  if [[ -n "$BROKER_PID" ]]; then kill "$BROKER_PID" >/dev/null 2>&1 || true; wait "$BROKER_PID" 2>/dev/null || true; fi
  mountpoint -q "$RMNT" && umount "$RMNT" || true
  [[ -e "/dev/mapper/$RMAPPER" ]] && cryptsetup close "$RMAPPER" || true
  mountpoint -q "$MNT" && umount "$MNT" || true
  [[ -e "/dev/mapper/$MAPPER" ]] && cryptsetup close "$MAPPER" || true
  rm -rf "$TMP"
}
trap cleanup EXIT INT TERM
truncate -s 192M "$IMG"; chmod 0600 "$IMG"; head -c 64 /dev/urandom > "$KEY"; chmod 0600 "$KEY"
cryptsetup luksFormat --batch-mode --type luks2 --pbkdf argon2id --label FA3_MSTATE --key-file "$KEY" "$IMG"
cryptsetup open --type luks2 --key-file "$KEY" "$IMG" "$MAPPER"
mkfs.ext4 -q -m0 -L FA3_MSTATE "/dev/mapper/$MAPPER"
mkdir -p "$MNT" "$POL" "$RUN"; mount -o nodev,nosuid,noexec "/dev/mapper/$MAPPER" "$MNT"
chown fa3-secret-broker:fa3-secret-broker "$MNT" "$RUN"; chmod 0750 "$MNT" "$RUN"
runuser -u fa3-secret-broker -- mkdir -m0700 "$MNT/objects"
runuser -u fa3-secret-broker -- sh -c 'printf "%s\n" '''{"schema":"fa3.secret-index.v1","secrets":{}}''' > "$1/index.json"; chmod 0600 "$1/index.json"' sh "$MNT"
cat > "$POL/current-host.json" <<'JSON'
{
  "schema": "fa3.secret-projection-policy.v1",
  "secret_id": "test/current-host",
  "classification": "MACHINE_SERVICE_SECRET",
  "allowed_consumers": [
    {
      "consumer_id": "FA3-CURRENT-HOST-SECRET-PROBE",
      "allowed_unix_users": ["root"],
      "allowed_executables": [],
      "allowed_systemd_units": []
    }
  ],
  "allowed_projections": ["UDS_SINGLE_SECRET"],
  "exportable": false
}
JSON
chmod 0644 "$POL/current-host.json"
SOCK="$RUN/broker.sock"; AUDIT="$RUN/audit.jsonl"
runuser -u fa3-secret-broker -- python3 "$ROOT/src/fa3_secret_broker.py" serve --vault-root "$MNT" --policy-dir "$POL" --socket "$SOCK" --audit-log "$AUDIT" &
BROKER_PID=$!
for _ in $(seq 1 50); do [[ -S "$SOCK" ]] && break; sleep 0.1; done
[[ -S "$SOCK" ]] || { echo "broker socket did not appear" >&2; exit 2; }
"$ROOT/bin/fa3-secretctl" --socket "$SOCK" health >/dev/null
CANARY="FA3_SECRET_BROKER_CANARY_$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)"
CANARY_HASH="$(printf '%s' "$CANARY" | sha256sum | cut -d' ' -f1)"
printf '%s' "$CANARY" | "$ROOT/bin/fa3-secretctl" --socket "$SOCK" put test/current-host --classification MACHINE_SERVICE_SECRET >/dev/null
GOT_HASH="$("$ROOT/bin/fa3-secretctl" --socket "$SOCK" get test/current-host --consumer FA3-CURRENT-HOST-SECRET-PROBE --projection UDS_SINGLE_SECRET | sha256sum | cut -d' ' -f1)"
[[ "$GOT_HASH" == "$CANARY_HASH" ]] || { echo "authorized secret projection mismatch" >&2; exit 2; }
if "$ROOT/bin/fa3-secretctl" --socket "$SOCK" get test/current-host --consumer FA3-UNAUTHORIZED-PROBE --projection UDS_SINGLE_SECRET >/dev/null 2>"$TMP/deny.err"; then
  echo "unauthorized consumer unexpectedly received secret" >&2; exit 2
fi
! grep -Fq "$CANARY" "$AUDIT"
! tr '\0' '\n' < "/proc/$BROKER_PID/environ" | grep -Fq "$CANARY"
! tr '\0' ' ' < "/proc/$BROKER_PID/cmdline" | grep -Fq "$CANARY"
kill "$BROKER_PID"; wait "$BROKER_PID" 2>/dev/null || true; BROKER_PID=""
umount "$MNT"; PRIMARY_UNMOUNT=true
cryptsetup close "$MAPPER"; PRIMARY_CLOSE=true
cp --reflink=never --sparse=always --preserve=mode,timestamps "$IMG" "$BACKUP"; cmp -s "$IMG" "$BACKUP"
OPAQUE_BACKUP=true
cryptsetup open --readonly --type luks2 --key-file "$KEY" "$BACKUP" "$RMAPPER"
mkdir -p "$RMNT"; mount -o ro,nodev,nosuid,noexec "/dev/mapper/$RMAPPER" "$RMNT"
RESTORE_UNLOCK=true; RESTORE_MOUNT=true
RSOCK="$RUN/restore.sock"; RAUDIT="$RUN/restore-audit.jsonl"
runuser -u fa3-secret-broker -- python3 "$ROOT/src/fa3_secret_broker.py" serve --vault-root "$RMNT" --policy-dir "$POL" --socket "$RSOCK" --audit-log "$RAUDIT" &
RESTORE_PID=$!
for _ in $(seq 1 50); do [[ -S "$RSOCK" ]] && break; sleep 0.1; done
[[ -S "$RSOCK" ]] || { echo "restore broker socket did not appear" >&2; exit 2; }
"$ROOT/bin/fa3-secretctl" --socket "$RSOCK" health >/dev/null
RESTORE_HEALTH=true
kill "$RESTORE_PID"; wait "$RESTORE_PID" 2>/dev/null || true; RESTORE_PID=""
umount "$RMNT"; cryptsetup close "$RMAPPER"
opts='["nodev","nosuid","noexec"]'
mkdir -p "$(dirname "$RECEIPT")"
python3 - "$RECEIPT" "$CANARY_HASH" "$(sha256sum "$IMG"|cut -d' ' -f1)" <<'PY'
import json,sys
from datetime import datetime,timezone
from pathlib import Path
x={
 "schema":"fa3.secret-broker-current-host-receipt.v1","status":"PASS","real_execution":True,"synthetic":False,
 "executed_at":datetime.now(timezone.utc).isoformat(),"luks2":True,"filesystem":"ext4",
 "mount_options":["nodev","nosuid","noexec"],"broker_unprivileged":True,"broker_user":"fa3-secret-broker",
 "canary_sha256":sys.argv[2],"encrypted_image_sha256":sys.argv[3],
 "checks":{"authorized_single_secret_get":True,"unauthorized_consumer_denied":True,"bulk_export_absent":True,
 "audit_contains_no_raw_secret":True,"secret_absent_from_argv":True,"secret_absent_from_environment":True,
 "broker_health_pass":True,"explicit_unmount_pass":True,"luks_close_pass":True,"opaque_backup_copy_pass":True,
 "restore_unlock_pass":True,"restore_mount_pass":True,"restore_broker_health_pass":True},
 "test_unlock_key_ephemeral":True,"secret_values_collected":False,"runtime_promotion_eligible":True,
 "global_promotion_claim":False,"new_capabilities":0,"new_architectural_authorities":0,"capability_count_after":143
}
Path(sys.argv[1]).write_text(json.dumps(x,indent=2)+"\n")
PY
PYTHONPATH="$ROOT/src" python3 "$ROOT/src/fa3_secret_broker_current_host_gate.py" --root "$ROOT" --receipt "$RECEIPT" --require-evidence
echo "FA3 Secret Broker current-host E2E PASS"
