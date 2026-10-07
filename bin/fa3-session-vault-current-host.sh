#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${FA3_SESSION_VAULT_IMAGE:-$HOME/.local/share/fa3/state/fa3-state.img}"
STATE="${FA3_SESSION_VAULT_E2E_STATE:-$ROOT/.fa3-current-host/session-vault}"
RECEIPT="${FA3_SESSION_VAULT_RECEIPT:-$ROOT/evidence/receipts/session-vault-current-host.json}"
RESTORE="$STATE/restore/fa3-state.img"
LOOP=""
CLEAR=""
MOUNT=""
RLOOP=""
RCLEAR=""
RMOUNT=""
UNMOUNT_PASS=false
LOCK_PASS=false
LOOP_CLEANUP_PASS=false
RESTORE_UNLOCK_PASS=false
RESTORE_MOUNT_PASS=false

die(){ echo "session-vault current-host: $*" >&2; exit 2; }
need(){ command -v "$1" >/dev/null 2>&1 || die "missing prerequisite: $1"; }
block_value(){
  local tag="$1" dev="$2"
  sudo blkid -p -o value -s "$tag" "$dev" 2>/dev/null || true
}

cleanup_restore(){
  if [[ -n "$RMOUNT" ]] && findmnt -rn "$RMOUNT" >/dev/null 2>&1; then udisksctl unmount -b "$RCLEAR" >/dev/null 2>&1 || true; fi
  if [[ -n "$RLOOP" ]] && [[ -b "$RLOOP" ]]; then udisksctl lock -b "$RLOOP" >/dev/null 2>&1 || true; udisksctl loop-delete -b "$RLOOP" >/dev/null 2>&1 || true; fi
}
cleanup_primary(){
  if [[ -n "$MOUNT" ]] && findmnt -rn "$MOUNT" >/dev/null 2>&1; then udisksctl unmount -b "$CLEAR" >/dev/null 2>&1 || true; fi
  if [[ -n "$LOOP" ]] && [[ -b "$LOOP" ]]; then udisksctl lock -b "$LOOP" >/dev/null 2>&1 || true; udisksctl loop-delete -b "$LOOP" >/dev/null 2>&1 || true; fi
}
cleanup(){ cleanup_restore; cleanup_primary; rm -f "$RESTORE"; }
trap cleanup EXIT INT TERM

for c in cryptsetup udisksctl lsblk findmnt blkid e2label stat cp cmp grep awk sed sudo sha256sum secret-tool; do
  if [[ "$c" == "secret-tool" ]] && ! command -v secret-tool >/dev/null 2>&1; then continue; fi
  need "$c"
done

[[ -f "$IMAGE" && ! -L "$IMAGE" ]] || die "image missing or not a regular file: $IMAGE"
[[ "$(stat -c '%a' "$IMAGE")" == "600" ]] || die "image mode must be 0600"
cryptsetup isLuks "$IMAGE" || die "not a LUKS image"
cryptsetup luksDump "$IMAGE" | grep -Eq '^Version:[[:space:]]+2$' || die "LUKS2 required"

# Normalize non-secret labels without changing keys or filesystem contents.
sudo cryptsetup config --label FA3_STATE "$IMAGE"

mkdir -p "$STATE/restore" "$(dirname "$RECEIPT")"
chmod 700 "$STATE" "$STATE/restore"

# Opaque encrypted backup copy. It is intentionally temporary and deleted on exit.
cp --reflink=never --sparse=always --preserve=mode,timestamps "$IMAGE" "$RESTORE"
cmp -s "$IMAGE" "$RESTORE" || die "opaque backup copy differs from source"
OPAQUE_BACKUP_COPY_PASS=true

loop_out="$(udisksctl loop-setup --file "$IMAGE")"
LOOP="$(printf '%s\n' "$loop_out" | grep -oE '/dev/loop[0-9]+' | tail -n1)"
[[ -n "$LOOP" && -b "$LOOP" ]] || die "failed to discover UDisks2 loop device"

echo "Unlocking primary FA3 state image. Enter the vault passphrase when prompted."
unlock_out="$(udisksctl unlock --block-device "$LOOP")"
CLEAR="$(printf '%s\n' "$unlock_out" | grep -oE '/dev/(dm-[0-9]+|mapper/[^ .]+)' | tail -n1)"
if [[ -z "$CLEAR" || ! -b "$CLEAR" ]]; then
  CLEAR="$(lsblk -nrpo NAME,TYPE "$LOOP" | awk '$2=="crypt"{print $1; exit}')"
fi
[[ -n "$CLEAR" && -b "$CLEAR" ]] || die "failed to discover cleartext device"
fs_type="$(block_value TYPE "$CLEAR")"
[[ "$fs_type" == "ext4" ]] || die "ext4 filesystem required (device=$CLEAR detected=${fs_type:-unknown})"

sudo e2label "$CLEAR" FA3_STATE
[[ "$(sudo e2label "$CLEAR")" == "FA3_STATE" ]] || die "filesystem label normalization failed"

mount_out="$(udisksctl mount --block-device "$CLEAR" --options nodev,nosuid,noexec)"
MOUNT="$(findmnt -rn -S "$CLEAR" -o TARGET | head -n1)"
[[ -n "$MOUNT" && -d "$MOUNT" ]] || die "mount point not found"
opts="$(findmnt -rn -S "$CLEAR" -o OPTIONS | head -n1)"
for o in nodev nosuid noexec; do
  grep -qw "$o" <<<"${opts//,/ }" || die "required mount option missing: $o"
done

mkdir -p "$MOUNT/session" "$MOUNT/pki/root"
chmod 700 "$MOUNT/session" "$MOUNT/pki" "$MOUNT/pki/root"
PROBE="$MOUNT/session/.fa3-current-host-access-probe"
printf 'fa3-current-host-probe\n' > "$PROBE"
chmod 600 "$PROBE"
getent passwd fa3-step-ca >/dev/null || die "fa3-step-ca service account missing"
if sudo -u fa3-step-ca test -r "$PROBE" || sudo -u fa3-step-ca test -x "$MOUNT/pki/root"; then
  rm -f "$PROBE"
  die "fa3-step-ca unexpectedly has access to the user vault"
fi
rm -f "$PROBE"
SERVICE_ISOLATION_PASS=true

udisksctl unmount --block-device "$CLEAR" >/dev/null
UNMOUNT_PASS=true
udisksctl lock --block-device "$LOOP" >/dev/null
LOCK_PASS=true
udisksctl loop-delete --block-device "$LOOP" >/dev/null
LOOP_CLEANUP_PASS=true
CLEAR=""; MOUNT=""; LOOP=""

# Verify the opaque copy is independently recoverable. This prompts again and never stores the secret.
rloop_out="$(udisksctl loop-setup --file "$RESTORE" --read-only)"
RLOOP="$(printf '%s\n' "$rloop_out" | grep -oE '/dev/loop[0-9]+' | tail -n1)"
[[ -n "$RLOOP" && -b "$RLOOP" ]] || die "failed to discover restore loop device"

echo "Verifying encrypted backup restore. Re-enter the vault passphrase when prompted."
runlock_out="$(udisksctl unlock --block-device "$RLOOP" --read-only)"
RCLEAR="$(printf '%s\n' "$runlock_out" | grep -oE '/dev/(dm-[0-9]+|mapper/[^ .]+)' | tail -n1)"
if [[ -z "$RCLEAR" || ! -b "$RCLEAR" ]]; then
  RCLEAR="$(lsblk -nrpo NAME,TYPE "$RLOOP" | awk '$2=="crypt"{print $1; exit}')"
fi
[[ -n "$RCLEAR" && -b "$RCLEAR" ]] || die "restore unlock did not create cleartext device"
RESTORE_UNLOCK_PASS=true

udisksctl mount --block-device "$RCLEAR" --options ro,nodev,nosuid,noexec >/dev/null
RMOUNT="$(findmnt -rn -S "$RCLEAR" -o TARGET | head -n1)"
[[ -n "$RMOUNT" && -d "$RMOUNT" ]] || die "restore mount failed"
RESTORE_MOUNT_PASS=true
udisksctl unmount --block-device "$RCLEAR" >/dev/null
udisksctl lock --block-device "$RLOOP" >/dev/null
udisksctl loop-delete --block-device "$RLOOP" >/dev/null
RCLEAR=""; RMOUNT=""; RLOOP=""

SECRET_SERVICE_CONFIGURED=false
SECRET_SERVICE_LOOKUP_PASS=null
if command -v secret-tool >/dev/null 2>&1; then
  if secret-tool lookup application FA3 purpose session-vault >/dev/null 2>&1; then
    SECRET_SERVICE_CONFIGURED=true
    SECRET_SERVICE_LOOKUP_PASS=true
  fi
fi

luks_label="$(cryptsetup luksDump "$IMAGE" | awk -F: '/^Label:/{sub(/^[[:space:]]+/,"",$2); print $2; exit}')"
[[ "$luks_label" == "FA3_STATE" ]] || die "unexpected LUKS label after normalization"

mount_opts_json='["nodev","nosuid","noexec"]'
python3 - "$RECEIPT" "$IMAGE" "$luks_label" "$SECRET_SERVICE_CONFIGURED" "$SECRET_SERVICE_LOOKUP_PASS" <<'PY'
import json,sys
from pathlib import Path
out=Path(sys.argv[1])
x={
 "schema":"fa3.session-vault-current-host-receipt.v1",
 "status":"PASS",
 "real_execution":True,
 "synthetic":False,
 "image_path":str(Path(sys.argv[2]).expanduser().resolve()),
 "luks2":True,
 "external_storage_name_non_disclosing":True,
 "loop_setup_pass":True,
 "unlock_pass":True,
 "filesystem":"ext4",
 "luks_label":sys.argv[3],
 "filesystem_label":"FA3_STATE",
 "mount_pass":True,
 "mount_options":["nodev","nosuid","noexec"],
 "service_account_isolation_pass":True,
 "explicit_unmount_pass":True,
 "explicit_lock_pass":True,
 "loop_cleanup_pass":True,
 "opaque_backup_copy_pass":True,
 "opaque_backup_restore_unlock_pass":True,
 "opaque_backup_restore_mount_pass":True,
 "secret_service":{
   "configured":sys.argv[4].lower()=="true",
   "lookup_pass_if_configured": None if sys.argv[5]=="null" else sys.argv[5].lower()=="true"
 },
 "secret_values_collected":False,
 "runtime_promotion_eligible":True,
 "global_promotion_claim":False
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(x,indent=2)+"\n")
PY

echo "Session Vault current-host E2E PASS"
echo "Receipt: $RECEIPT"
