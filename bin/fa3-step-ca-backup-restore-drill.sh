#!/usr/bin/env bash
set -euo pipefail
[[ "$(id -u)" -eq 0 && "${FA3_STEP_CA_MAINTENANCE_ACK:-}" == YES ]] || { echo "root + FA3_STEP_CA_MAINTENANCE_ACK=YES required" >&2; exit 2; }
ROOT="${FA3_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"; STEP_CA_BIN="/usr/local/lib/fa3/step-ca/0.30.2/bin/step-ca"; STEP_BIN="/usr/local/lib/fa3/step-cli/0.30.6/bin/step"; [[ -x "$STEP_CA_BIN" && -x "$STEP_BIN" ]] || { echo "FA3-namespaced Smallstep binaries missing" >&2; exit 2; }; OUT="$ROOT/evidence/runtime/step-ca-current-host/backup-restore.json"; TMP="$(mktemp -d /var/tmp/fa3-step-ca-restore.XXXXXX)"; chmod 0755 "$TMP"
PID=""; PRIMARY_STOPPED=false
cleanup(){
 local rc=$?
 set +e
 if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then kill "$PID"; wait "$PID" 2>/dev/null; fi
 if [[ "$PRIMARY_STOPPED" == true ]]; then systemctl start fa3-step-ca.service; fi
 rm -rf -- "$TMP"
 return "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
PRIMARY_STOPPED=true
systemctl stop fa3-step-ca.service
mkdir -p "$TMP/backup/state/secrets" "$TMP/backup/config"; cp -a /var/lib/fa3-step-ca/db /var/lib/fa3-step-ca/certs "$TMP/backup/state/"; cp -a /var/lib/fa3-step-ca/secrets/intermediate_ca_key /var/lib/fa3-step-ca/secrets/ssh_host_ca_key /var/lib/fa3-step-ca/secrets/ssh_user_ca_key "$TMP/backup/state/secrets/"; cp -a /etc/fa3/step-ca/ca.json "$TMP/backup/config/ca.json"
systemctl start fa3-step-ca.service; PRIMARY_STOPPED=false; tar -C "$TMP/backup" -czf "$TMP/backup.tar.gz" .; LIST="$(tar -tzf "$TMP/backup.tar.gz")"; ! grep -Eq 'root_ca_key|step-ca-password|fa3-jwk-password' <<<"$LIST"
mkdir -p "$TMP/restore"; tar -xzf "$TMP/backup.tar.gz" -C "$TMP/restore"
python3 - "$TMP/restore/config/ca.json" "$TMP/restore" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); r=Path(sys.argv[2]); x=json.loads(p.read_text()); x["root"]=str(r/"state/certs/root_ca.crt"); x["crt"]=str(r/"state/certs/intermediate_ca.crt"); x["key"]=str(r/"state/secrets/intermediate_ca_key"); x["address"]="127.0.0.1:9445"; x["db"]["dataSource"]=str(r/"state/db"); x["ssh"]["hostKey"]=str(r/"state/secrets/ssh_host_ca_key"); x["ssh"]["userKey"]=str(r/"state/secrets/ssh_user_ca_key"); p.write_text(json.dumps(x,indent=2)+"\n")
PY
cp /etc/fa3/secrets/step-ca-password "$TMP/shadow-pass"; chown -R fa3-step-ca:fa3-step-ca "$TMP/restore" "$TMP/shadow-pass"; chmod 0600 "$TMP/shadow-pass"
runuser -u fa3-step-ca -- $STEP_CA_BIN "$TMP/restore/config/ca.json" --password-file="$TMP/shadow-pass" >"$TMP/shadow.log" 2>&1 & PID=$!
for i in $(seq 1 20); do curl -fsS --cacert "$TMP/restore/state/certs/root_ca.crt" https://127.0.0.1:9445/health >/dev/null && break; sleep 1; done
curl -fsS --cacert "$TMP/restore/state/certs/root_ca.crt" https://127.0.0.1:9445/health >/dev/null
"$STEP_BIN" ca certificate fa3-restore-check "$TMP/r.crt" "$TMP/r.key" --provisioner fa3-jwk --provisioner-password-file /etc/fa3/secrets/fa3-jwk-password --ca-url https://127.0.0.1:9445 --root "$TMP/restore/state/certs/root_ca.crt" --not-after 10m
kill "$PID"; wait "$PID" 2>/dev/null || true; PID=""; SHA="$(sha256sum "$TMP/backup.tar.gz"|awk '{print $1}')"; mkdir -p "$(dirname "$OUT")"
python3 - "$OUT" "$SHA" <<'PY'
import json,sys
from datetime import datetime,timezone
x={"schema":"fa3.step-ca-backup-restore-drill.v1","status":"PASS","backup_sha256":sys.argv[2],"root_private_key_in_backup":False,"unlock_secret_in_backup":False,"shadow_health_pass":True,"post_restore_issuance_pass":True,"maintenance_stop_used":True,"persistent_backup_created":False,"secret_values_collected":False,"completed_at":datetime.now(timezone.utc).isoformat()}
open(sys.argv[1],"w").write(json.dumps(x,indent=2)+"\n")
PY
