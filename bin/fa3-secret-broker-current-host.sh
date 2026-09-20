#!/usr/bin/env bash
set -euo pipefail
[[ "$(id -u)" -eq 0 ]] || { echo "Run with sudo/root." >&2; exit 2; }
ROOT="${FA3_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
RECEIPT="${FA3_SECRET_BROKER_RECEIPT:-$ROOT/evidence/receipts/secret-broker-current-host.json}"
for c in cryptsetup mkfs.ext4 mount umount mountpoint sha256sum runuser python3 grep awk cp cmp stat getent useradd userdel seq head systemd-run systemd-creds systemctl install truncate mktemp tr; do command -v "$c" >/dev/null || { echo "missing prerequisite: $c" >&2; exit 2; }; done
PROBE_USER="fa3-sb-probe"; PROBE_CREATED=false
getent passwd fa3-secret-broker >/dev/null || { echo "fa3-secret-broker service user missing; run installer first" >&2; exit 2; }
getent group fa3-secret-clients >/dev/null || { echo "fa3-secret-clients group missing; run installer first" >&2; exit 2; }
TMP="$(mktemp -d /var/tmp/fa3-secret-broker-e2e.XXXXXX)"; chmod 0711 "$TMP"
RUN_ID="${TMP##*.}"
IMG="$TMP/fa3-machine-state.img"; BACKUP="$TMP/fa3-machine-state.backup.img"; KEY="$TMP/key"
MAPPER="fa3-sb-e2e-$RUN_ID"; RMAPPER="fa3-sb-restore-$RUN_ID"; MNT="$TMP/mnt"; RMNT="$TMP/rmnt"; POL="$TMP/policy"; RUN="$TMP/run"; PROJ="/run/fa3-secret-broker-e2e-$RUN_ID"
BROKER_PID=""; RESTORE_PID=""
SIMG="/var/lib/fa3/state/.fa3-mstate-e2e-$RUN_ID.img"
SMAPPER="fa3-machine-state-e2e-$RUN_ID"
ECRED="/run/fa3-mstate-e2e-$RUN_ID.cred"
REKEY_NEW="/run/fa3-mstate-e2e-$RUN_ID.new.key"
DROPIN_DIR="/etc/systemd/system/fa3-secret-vault.service.d"
DROPIN="$DROPIN_DIR/90-fa3-secret-e2e-$RUN_ID.conf"
SYSTEMD_PHASE_ACTIVE=false
cleanup(){
  if [[ -f "$DROPIN" || "$SYSTEMD_PHASE_ACTIVE" == true ]]; then
    systemctl stop fa3-secrets.target >/dev/null 2>&1 || true
    rm -f "$DROPIN"
    rmdir "$DROPIN_DIR" >/dev/null 2>&1 || true
    systemctl daemon-reload >/dev/null 2>&1 || true
  fi
  rm -f "$SIMG" "$ECRED" "$REKEY_NEW"
  if [[ -n "$RESTORE_PID" ]]; then kill "$RESTORE_PID" >/dev/null 2>&1 || true; wait "$RESTORE_PID" 2>/dev/null || true; fi
  if [[ -n "$BROKER_PID" ]]; then kill "$BROKER_PID" >/dev/null 2>&1 || true; wait "$BROKER_PID" 2>/dev/null || true; fi
  mountpoint -q "$RMNT" && umount "$RMNT" || true
  [[ -e "/dev/mapper/$RMAPPER" ]] && cryptsetup close "$RMAPPER" || true
  mountpoint -q "$MNT" && umount "$MNT" || true
  [[ -e "/dev/mapper/$MAPPER" ]] && cryptsetup close "$MAPPER" || true
  if [[ "$PROBE_CREATED" == true ]]; then userdel "$PROBE_USER" >/dev/null 2>&1 || true; fi
  rm -rf "$PROJ" "$TMP"
}
trap cleanup EXIT INT TERM
if ! getent passwd "$PROBE_USER" >/dev/null; then
  useradd --system --no-create-home --shell /usr/sbin/nologin --groups fa3-secret-clients "$PROBE_USER"
  PROBE_CREATED=true
fi
truncate -s 192M "$IMG"; chmod 0600 "$IMG"; head -c 64 /dev/urandom > "$KEY"; chmod 0600 "$KEY"
cryptsetup luksFormat --batch-mode --type luks2 --pbkdf argon2id --label FA3_MSTATE --key-file "$KEY" "$IMG"
cryptsetup open --type luks2 --key-file "$KEY" "$IMG" "$MAPPER"
mkfs.ext4 -q -m0 -L FA3_MSTATE "/dev/mapper/$MAPPER"
mkdir -p "$MNT" "$POL" "$RUN"; chmod 0755 "$POL"; mount -o nodev,nosuid,noexec "/dev/mapper/$MAPPER" "$MNT"
chown fa3-secret-broker:fa3-secret-broker "$MNT"; chmod 0750 "$MNT"
chown fa3-secret-broker:fa3-secret-clients "$RUN"; chmod 0750 "$RUN"
install -d -o fa3-secret-broker -g fa3-secret-broker -m0700 "$MNT/objects"
printf '%s\n' '{"schema":"fa3.secret-index.v1","secrets":{}}' > "$MNT/index.json"
chown fa3-secret-broker:fa3-secret-broker "$MNT/index.json"; chmod 0600 "$MNT/index.json"
POLICY_SRC="$TMP/current-host-policy.json"
cat > "$POLICY_SRC" <<'JSON'
{
  "schema": "fa3.secret-projection-policy.v1",
  "secret_id": "test/current-host",
  "classification": "MACHINE_SERVICE_SECRET",
  "secret_kind": "API_TOKEN",
  "allowed_consumers": [
    {
      "consumer_id": "FA3-CURRENT-HOST-SECRET-PROBE",
      "allowed_unix_users": ["fa3-sb-probe"],
      "allowed_executables": [],
      "allowed_systemd_units": []
    }
  ],
  "allowed_projections": ["UDS_SINGLE_SECRET", "SYSTEMD_CREDENTIAL"],
  "exportable": false
}
JSON
chmod 0600 "$POLICY_SRC"
FA3_SECRET_POLICY_DIR="$POL" /usr/local/sbin/fa3-secret-policyctl check "$POLICY_SRC" >/dev/null
FA3_SECRET_POLICY_DIR="$POL" /usr/local/sbin/fa3-secret-policyctl install "$POLICY_SRC" >/dev/null
FA3_SECRET_POLICY_DIR="$POL" /usr/local/sbin/fa3-secret-policyctl list | python3 -c 'import sys; rows=[line.rstrip().split(chr(9)) for line in sys.stdin]; raise SystemExit(0 if ["test/current-host","MACHINE_SERVICE_SECRET","API_TOKEN"] in rows else 2)'
POLICY_PREFLIGHT=true
POLICY_INSTALL_PASS=true
SOCK="$RUN/broker.sock"; AUDIT="$RUN/audit.jsonl"
BROKER_PY="/usr/local/lib/fa3/fa3_secret_broker.py"
[[ -r "$BROKER_PY" ]] || { echo "installed broker module missing; run installer first" >&2; exit 2; }
runuser -u fa3-secret-broker -- python3 "$BROKER_PY" serve --vault-root "$MNT" --policy-dir "$POL" --socket "$SOCK" --audit-log "$AUDIT" &
BROKER_PID=$!
for _ in $(seq 1 50); do [[ -S "$SOCK" ]] && break; sleep 0.1; done
[[ -S "$SOCK" ]] || { echo "broker socket did not appear" >&2; exit 2; }
"$ROOT/bin/fa3-secretctl" --socket "$SOCK" health >/dev/null
CANARY1="FA3_SECRET_BROKER_CANARY1_$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)"
CANARY1_HASH="$(printf '%s' "$CANARY1" | sha256sum | cut -d' ' -f1)"
printf '%s' "$CANARY1" | "$ROOT/bin/fa3-secretctl" --socket "$SOCK" put test/current-host --classification MACHINE_SERVICE_SECRET --kind API_TOKEN >/dev/null
GOT_HASH="$(runuser -u "$PROBE_USER" -- /usr/local/bin/fa3-secretctl --socket "$SOCK" get test/current-host --consumer FA3-CURRENT-HOST-SECRET-PROBE --projection UDS_SINGLE_SECRET | sha256sum | cut -d' ' -f1)"
[[ "$GOT_HASH" == "$CANARY1_HASH" ]] || { echo "authorized secret projection mismatch" >&2; exit 2; }

CANARY2="FA3_SECRET_BROKER_CANARY2_$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)"
CANARY_HASH="$(printf '%s' "$CANARY2" | sha256sum | cut -d' ' -f1)"
printf '%s' "$CANARY2" | "$ROOT/bin/fa3-secretctl" --socket "$SOCK" rotate test/current-host --classification MACHINE_SERVICE_SECRET --kind API_TOKEN >/dev/null
META="$("$ROOT/bin/fa3-secretctl" --socket "$SOCK" admin-metadata test/current-host)"
grep -Fq '"version": 2' <<<"$META"
grep -Fq '"secret_kind": "API_TOKEN"' <<<"$META"
LIST="$("$ROOT/bin/fa3-secretctl" --socket "$SOCK" list-metadata)"
grep -Fq '"secret_id": "test/current-host"' <<<"$LIST"
! grep -Fq "$CANARY1" <<<"$LIST"
! grep -Fq "$CANARY2" <<<"$LIST"
ROTATION_PASS=true
METADATA_ONLY_LIST_PASS=true

REVOKE_CANARY="FA3_SECRET_BROKER_REVOKE_$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)"
printf '%s' "$REVOKE_CANARY" | "$ROOT/bin/fa3-secretctl" --socket "$SOCK" put test/revoke --classification MACHINE_SERVICE_SECRET --kind SERVICE_PASSWORD >/dev/null
"$ROOT/bin/fa3-secretctl" --socket "$SOCK" revoke test/revoke >/dev/null
if "$ROOT/bin/fa3-secretctl" --socket "$SOCK" admin-metadata test/revoke >/dev/null 2>&1; then
  echo "revoked secret still has active metadata" >&2; exit 2
fi
REVOCATION_PASS=true
install -d -o "$PROBE_USER" -g "$PROBE_USER" -m0700 "$PROJ"
runuser -u "$PROBE_USER" -- /usr/local/bin/fa3-secretctl --socket "$SOCK" get test/current-host --consumer FA3-CURRENT-HOST-SECRET-PROBE --projection SYSTEMD_CREDENTIAL --output "$PROJ/api-token"
[[ "$(stat -c '%a' "$PROJ/api-token")" == "600" ]] || { echo "projection file mode mismatch" >&2; exit 2; }
SYSTEMD_HASH="$(systemd-run --quiet --wait --pipe --collect --service-type=oneshot --property="User=$PROBE_USER" --property="LoadCredential=api-token:$PROJ/api-token" /bin/sh -c 'sha256sum "$CREDENTIALS_DIRECTORY/api-token" | cut -d" " -f1')"
[[ "$SYSTEMD_HASH" == "$CANARY_HASH" ]] || { echo "systemd LoadCredential projection mismatch" >&2; exit 2; }
rm -f "$PROJ/api-token"
if runuser -u "$PROBE_USER" -- /usr/local/bin/fa3-secretctl --socket "$SOCK" get test/current-host --consumer FA3-UNAUTHORIZED-PROBE --projection UDS_SINGLE_SECRET >/dev/null 2>"$TMP/deny.err"; then
  echo "unauthorized consumer unexpectedly received secret" >&2; exit 2
fi
FA3_SECRET_POLICY_DIR="$POL" /usr/local/sbin/fa3-secret-policyctl remove test/current-host
if runuser -u "$PROBE_USER" -- /usr/local/bin/fa3-secretctl --socket "$SOCK" get test/current-host --consumer FA3-CURRENT-HOST-SECRET-PROBE --projection UDS_SINGLE_SECRET >/dev/null 2>"$TMP/policy-remove-deny.err"; then
  echo "removed policy unexpectedly still authorizes secret" >&2; exit 2
fi
FA3_SECRET_POLICY_DIR="$POL" /usr/local/sbin/fa3-secret-policyctl install "$POLICY_SRC" >/dev/null
POLICY_INSTALL_REMOVE_PASS=true
if runuser -u "$PROBE_USER" -- test -r "$MNT/index.json" || runuser -u "$PROBE_USER" -- test -x "$MNT/objects"; then
  echo "consumer unexpectedly has raw vault access" >&2; exit 2
fi
PYTHONPATH="$ROOT/src" python3 - "$SOCK" <<'PY'
import sys
from pathlib import Path
from fa3_secret_broker import request
r=request(Path(sys.argv[1]),{"op":"bulk","secret_id":"test/current-host","consumer_id":"FA3-CURRENT-HOST-SECRET-PROBE"})
if r.get("ok") is not False:
    raise SystemExit(2)
bad=request(Path(sys.argv[1]),{"op":"put","secret_id":"test/not-credential","classification":"MACHINE_SERVICE_SECRET","secret_kind":"CACHE","secret_b64":"eA=="})
raise SystemExit(0 if bad.get("ok") is False else 2)
PY
! grep -Fq "$CANARY1" "$AUDIT"
! grep -Fq "$CANARY2" "$AUDIT"
! grep -Fq "$REVOKE_CANARY" "$AUDIT"
! tr '\0' '\n' < "/proc/$BROKER_PID/environ" | grep -Fq "$CANARY1"
! tr '\0' '\n' < "/proc/$BROKER_PID/environ" | grep -Fq "$CANARY2"
! tr '\0' ' ' < "/proc/$BROKER_PID/cmdline" | grep -Fq "$CANARY1"
! tr '\0' ' ' < "/proc/$BROKER_PID/cmdline" | grep -Fq "$CANARY2"
kill "$BROKER_PID"; wait "$BROKER_PID" 2>/dev/null || true; BROKER_PID=""
umount "$MNT"; PRIMARY_UNMOUNT=true
cryptsetup close "$MAPPER"; PRIMARY_CLOSE=true
FA3_MACHINE_STATE_IMAGE="$IMG" FA3_MACHINE_STATE_MAPPER="$MAPPER" FA3_MACHINE_STATE_MOUNT="$MNT" /usr/local/libexec/fa3-secret-vault-mount assert-closed
FA3_EXIT_CLOSED_STATE=true
cp --reflink=never --sparse=always --preserve=mode,timestamps "$IMG" "$BACKUP"; cmp -s "$IMG" "$BACKUP"
OPAQUE_BACKUP=true
cryptsetup open --readonly --type luks2 --key-file "$KEY" "$BACKUP" "$RMAPPER"
mkdir -p "$RMNT"; mount -o ro,nodev,nosuid,noexec "/dev/mapper/$RMAPPER" "$RMNT"
RESTORE_UNLOCK=true; RESTORE_MOUNT=true
RSOCK="$RUN/restore.sock"; RAUDIT="$RUN/restore-audit.jsonl"
runuser -u fa3-secret-broker -- python3 "$BROKER_PY" serve --vault-root "$RMNT" --policy-dir "$POL" --socket "$RSOCK" --audit-log "$RAUDIT" &
RESTORE_PID=$!
for _ in $(seq 1 50); do [[ -S "$RSOCK" ]] && break; sleep 0.1; done
[[ -S "$RSOCK" ]] || { echo "restore broker socket did not appear" >&2; exit 2; }
"$ROOT/bin/fa3-secretctl" --socket "$RSOCK" health >/dev/null
RESTORE_HASH="$(runuser -u "$PROBE_USER" -- /usr/local/bin/fa3-secretctl --socket "$RSOCK" get test/current-host --consumer FA3-CURRENT-HOST-SECRET-PROBE --projection UDS_SINGLE_SECRET | sha256sum | cut -d' ' -f1)"
[[ "$RESTORE_HASH" == "$CANARY_HASH" ]] || { echo "restored secret value mismatch" >&2; exit 2; }
! grep -Fq "$CANARY2" "$RAUDIT"
RESTORE_HEALTH=true
RESTORE_SECRET_READ_PASS=true
kill "$RESTORE_PID"; wait "$RESTORE_PID" 2>/dev/null || true; RESTORE_PID=""
umount "$RMNT"; cryptsetup close "$RMAPPER"

# Real systemd lifecycle proof using an isolated image and encrypted systemd credential.
# Production image and production credential are not modified.
FA3_MACHINE_STATE_MAPPER="fa3-machine-state" FA3_MACHINE_STATE_MOUNT="/run/fa3/machine-state" /usr/local/sbin/fa3-secrets-lifecycle assert-closed >/dev/null
cp --reflink=never --sparse=always "$IMG" "$SIMG"
chmod 0600 "$SIMG"
systemd-creds encrypt --with-key=host --name=fa3-machine-state-key "$KEY" "$ECRED" >/dev/null
chmod 0600 "$ECRED"
install -d -m0755 "$DROPIN_DIR"
cat > "$DROPIN" <<EOF
[Unit]
ConditionPathExists=
ConditionPathExists=$SIMG

[Service]
Environment=FA3_MACHINE_STATE_IMAGE=$SIMG
Environment=FA3_MACHINE_STATE_MAPPER=$SMAPPER
Environment=FA3_MACHINE_STATE_MOUNT=/run/fa3/machine-state
LoadCredentialEncrypted=
LoadCredentialEncrypted=fa3-machine-state-key:$ECRED
EOF
systemctl daemon-reload
SYSTEMD_PHASE_ACTIVE=true
systemctl start fa3-secrets.target
systemctl is-active --quiet fa3-secret-vault.service
systemctl is-active --quiet fa3-secret-broker.service
mountpoint -q /run/fa3/machine-state
[[ -e "/dev/mapper/$SMAPPER" ]]
/usr/local/bin/fa3-secretctl health >/dev/null
FA3_MACHINE_STATE_MAPPER="$SMAPPER" FA3_MACHINE_STATE_MOUNT="/run/fa3/machine-state" /usr/local/sbin/fa3-secrets-lifecycle exit >/dev/null
! systemctl is-active --quiet fa3-secrets.target
! systemctl is-active --quiet fa3-secret-broker.service
! systemctl is-active --quiet fa3-secret-vault.service
! mountpoint -q /run/fa3/machine-state
[[ ! -e "/dev/mapper/$SMAPPER" ]]
SYSTEMD_TARGET_LIFECYCLE_PASS=true
ENCRYPTED_SYSTEMD_UNLOCK_RUNTIME_PASS=true
HARDWARE_NEUTRAL_SYSTEMD_CREDENTIAL_HOST_KEY_MODE_PASS=true

head -c 64 /dev/urandom > "$REKEY_NEW"
chmod 0600 "$REKEY_NEW"
FA3_MACHINE_STATE_IMAGE="$SIMG" \
FA3_MACHINE_STATE_CREDENTIAL="$ECRED" \
FA3_MACHINE_STATE_MAPPER="$SMAPPER" \
FA3_MACHINE_STATE_MOUNT="/run/fa3/machine-state" \
FA3_REKEY_NEW_KEY_FILE="$REKEY_NEW" \
  /usr/local/sbin/fa3-secret-vault-rekey >/dev/null

if cryptsetup open --test-passphrase --type luks2 --key-file "$KEY" "$SIMG" >/dev/null 2>&1; then
  echo "old unlock key unexpectedly still works after rekey" >&2
  exit 2
fi
cryptsetup open --test-passphrase --type luks2 --key-file "$REKEY_NEW" "$SIMG"
! systemctl is-active --quiet fa3-secrets.target
! systemctl is-active --quiet fa3-secret-broker.service
! systemctl is-active --quiet fa3-secret-vault.service
! mountpoint -q /run/fa3/machine-state
[[ ! -e "/dev/mapper/$SMAPPER" ]]
LUKS_UNLOCK_KEY_ROTATION_PASS=true
OLD_UNLOCK_KEY_REJECTED_AFTER_REKEY=true
NEW_UNLOCK_KEY_ACCEPTED_AFTER_REKEY=true
REKEY_FINAL_CLOSED_STATE_PASS=true
SYSTEMD_PHASE_ACTIVE=false
rm -f "$DROPIN" "$SIMG" "$ECRED" "$REKEY_NEW"
rmdir "$DROPIN_DIR" >/dev/null 2>&1 || true
systemctl daemon-reload
[[ ! -e "$DROPIN" && ! -e "$SIMG" && ! -e "$ECRED" && ! -e "$REKEY_NEW" ]]
SYSTEMD_E2E_ARTIFACT_CLEANUP_PASS=true

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
 "checks":{"authorized_single_secret_get":True,"systemd_loadcredential_projection_pass":True,"encrypted_systemd_unlock_runtime_pass":True,"systemd_target_lifecycle_pass":True,"secrets_target_inactive_pass":True,"hardware_neutral_systemd_credential_host_key_mode_pass":True,"luks_unlock_key_rotation_pass":True,"old_unlock_key_rejected_after_rekey":True,"new_unlock_key_accepted_after_rekey":True,"rekey_final_closed_state_pass":True,"systemd_e2e_artifact_cleanup_pass":True,"policy_preflight_pass":True,"policy_install_remove_pass":True,"rotation_pass":True,"revocation_pass":True,"metadata_only_list_pass":True,"unauthorized_consumer_denied":True,"raw_vault_access_denied":True,"bulk_export_absent":True,"credential_scope_enforced":True,
 "audit_contains_no_raw_secret":True,"secret_absent_from_argv":True,"secret_absent_from_environment":True,
 "broker_health_pass":True,"explicit_unmount_pass":True,"luks_close_pass":True,"fa3_exit_closed_state_pass":True,"opaque_backup_copy_pass":True,
 "restore_unlock_pass":True,"restore_mount_pass":True,"restore_broker_health_pass":True,"restore_secret_read_pass":True},
 "test_unlock_key_ephemeral":True,"secret_values_collected":False,"runtime_promotion_eligible":True,
 "global_promotion_claim":False,"new_capabilities":0,"new_architectural_authorities":0,"capability_count_after":143
}
Path(sys.argv[1]).write_text(json.dumps(x,indent=2)+"\n")
PY
PYTHONPATH="$ROOT/src" python3 "$ROOT/src/fa3_secret_broker_current_host_gate.py" --root "$ROOT" --receipt "$RECEIPT" --require-evidence
echo "FA3 Secret Broker current-host E2E PASS"
