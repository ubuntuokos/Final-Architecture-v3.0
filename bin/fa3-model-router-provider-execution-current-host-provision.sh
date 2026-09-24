#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROVIDER_ID=""
API_BASE=""
ADMISSION_RECEIPT=""
PREFERRED_MODEL=""
SECRET_ID_A="probe/provider-execution/a"
SECRET_ID_B="probe/provider-execution/b"
CONSUMER_ID="FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-001"
PROBE_USER="fa3-provider-exec-probe"
PROBE_UNIT="fa3-provider-exec-probe.service"
RUN_ROOT="/run/fa3/model-router-provider-execution"
SOURCE="$RUN_ROOT/current-host-source.json"
CONFIG="$RUN_ROOT/current-host-config.json"
RUNTIME_DIR="$RUN_ROOT/runtime"
SECRET_RECEIPT="/run/fa3/current-host-secret-broker/secret-broker-current-host.json"
CREATED_USER=false
LIFECYCLE_STARTED=false
POLICY_A=""
POLICY_B=""
SECRET_A_CREATED=false
SECRET_B_CREATED=false

usage() {
  cat <<'EOF'
Usage:
  sudo bash bin/fa3-model-router-provider-execution-current-host-provision.sh \
    --provider-id PROVIDER_ID \
    --api-base http://127.0.0.1:PORT/v1 \
    --admission-receipt /ABSOLUTE/PATH/provider-current-host.json \
    [--preferred-model MODEL_ID] \
    [--secret-id-a ID] [--secret-id-b ID]

The provider endpoint must already be current-host admitted and must enforce
Bearer authentication. Two distinct real provider credentials are read from
/dev/tty without command-line or environment exposure. The script generates
/run/fa3/model-router-provider-execution/current-host-source.json and removes
temporary policies, probe identity, and probe SecretReferences afterwards.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider-id) PROVIDER_ID="$2"; shift 2;;
    --api-base) API_BASE="$2"; shift 2;;
    --admission-receipt) ADMISSION_RECEIPT="$2"; shift 2;;
    --preferred-model) PREFERRED_MODEL="$2"; shift 2;;
    --secret-id-a) SECRET_ID_A="$2"; shift 2;;
    --secret-id-b) SECRET_ID_B="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2;;
  esac
done

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "run with sudo/root" >&2; exit 2; }
[[ -n "$PROVIDER_ID" && -n "$API_BASE" && -n "$ADMISSION_RECEIPT" ]] || { usage >&2; exit 2; }
[[ "$SECRET_ID_A" != "$SECRET_ID_B" ]] || { echo "credential SecretReferences must be distinct" >&2; exit 2; }
[[ -r /dev/tty && -w /dev/tty ]] || { echo "interactive /dev/tty is required" >&2; exit 2; }

for cmd in python3 systemctl systemd-run getent useradd userdel readlink install; do
  command -v "$cmd" >/dev/null || { echo "missing prerequisite: $cmd" >&2; exit 2; }
done
for path in /usr/local/bin/fa3-secretctl /usr/local/sbin/fa3-secret-policyctl /usr/local/sbin/fa3-secrets-lifecycle /usr/local/libexec/fa3-secret-broker-current-host-root; do
  [[ -x "$path" ]] || { echo "missing installed FA3 secrets component: $path" >&2; exit 2; }
done
getent group fa3-secret-clients >/dev/null || { echo "fa3-secret-clients group missing" >&2; exit 2; }
getent group fa3-secret-broker >/dev/null || { echo "fa3-secret-broker group missing" >&2; exit 2; }

ADMISSION_RECEIPT="$(readlink -f "$ADMISSION_RECEIPT")"
[[ -f "$ADMISSION_RECEIPT" && ! -L "$ADMISSION_RECEIPT" ]] || { echo "provider admission receipt missing or symlinked" >&2; exit 2; }

python3 - "$API_BASE" <<'PY'
import sys
from urllib.parse import urlparse
p=urlparse(sys.argv[1])
if p.scheme not in {"http","https"} or (p.hostname or "").lower() not in {"127.0.0.1","localhost","::1"}:
    raise SystemExit("provider endpoint must be loopback HTTP(S)")
PY

PYTHONPATH="$ROOT/src" python3 - "$ADMISSION_RECEIPT" "$PROVIDER_ID" "$API_BASE" <<'PY'
import sys
from pathlib import Path
from fa3_model_router_materialize import receipt_proves_provider
if not receipt_proves_provider(Path(sys.argv[1]),sys.argv[2],sys.argv[3]):
    raise SystemExit("configured provider endpoint is not proven by the supplied current-host admission receipt")
PY

cleanup() {
  set +e
  unset CRED_A CRED_B
  if [[ "$SECRET_B_CREATED" == true ]]; then /usr/local/bin/fa3-secretctl delete "$SECRET_ID_B" >/dev/null 2>&1 || true; fi
  if [[ "$SECRET_A_CREATED" == true ]]; then /usr/local/bin/fa3-secretctl delete "$SECRET_ID_A" >/dev/null 2>&1 || true; fi
  if [[ -n "$POLICY_B" ]]; then /usr/local/sbin/fa3-secret-policyctl remove "$SECRET_ID_B" >/dev/null 2>&1 || true; fi
  if [[ -n "$POLICY_A" ]]; then /usr/local/sbin/fa3-secret-policyctl remove "$SECRET_ID_A" >/dev/null 2>&1 || true; fi
  if [[ "$LIFECYCLE_STARTED" == true ]]; then /usr/local/sbin/fa3-secrets-lifecycle exit >/dev/null 2>&1 || true; fi
  rm -rf "$CONFIG" "$RUNTIME_DIR"
  if [[ "$CREATED_USER" == true ]]; then userdel "$PROBE_USER" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT INT TERM

if systemctl is-active --quiet fa3-secrets.target; then
  [[ -s "$SECRET_RECEIPT" ]] || {
    echo "production secrets lifecycle is active but no current-host PASS receipt is staged; refusing disruptive restart" >&2
    exit 2
  }
else
  /usr/local/libexec/fa3-secret-broker-current-host-root >/dev/null
  [[ -s "$SECRET_RECEIPT" ]] || { echo "Secret Broker current-host PASS receipt missing" >&2; exit 2; }
  /usr/local/sbin/fa3-secrets-lifecycle start >/dev/null
  LIFECYCLE_STARTED=true
fi

python3 - "$SECRET_RECEIPT" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
if (
    r.get("schema")!="fa3.secret-broker-current-host-receipt.v1"
    or r.get("result")!="PASS"
    or r.get("status")!="CURRENT_HOST_PASS"
    or r.get("secret_values_collected") is not False
):
    raise SystemExit("Secret Broker current-host receipt is not a valid CURRENT_HOST_PASS")
PY
/usr/local/bin/fa3-secretctl health >/dev/null

if getent passwd "$PROBE_USER" >/dev/null; then
  echo "probe identity already exists; refusing to reuse it" >&2
  exit 2
fi
useradd --system --no-create-home --shell /usr/sbin/nologin --groups fa3-secret-clients "$PROBE_USER"
CREATED_USER=true

if /usr/local/bin/fa3-secretctl admin-metadata "$SECRET_ID_A" >/dev/null 2>&1 || /usr/local/bin/fa3-secretctl admin-metadata "$SECRET_ID_B" >/dev/null 2>&1; then
  echo "one or both probe SecretReference ids already exist; refusing to overwrite" >&2
  exit 2
fi

PYTHON_EXE="$(readlink -f "$(command -v python3)")"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"; cleanup' EXIT INT TERM
POLICY_A="$TMP/a.json"
POLICY_B="$TMP/b.json"

python3 - "$POLICY_A" "$POLICY_B" "$SECRET_ID_A" "$SECRET_ID_B" "$CONSUMER_ID" "$PROBE_USER" "$PYTHON_EXE" "$PROBE_UNIT" <<'PY'
import json,sys
from pathlib import Path
pa,pb,ida,idb,consumer,user,python_exe,unit=sys.argv[1:]
def policy(sid):
    return {
        "schema":"fa3.secret-projection-policy.v1",
        "secret_id":sid,
        "classification":"MACHINE_SERVICE_SECRET",
        "secret_kind":"PROVIDER_CREDENTIAL",
        "allowed_consumers":[{
            "consumer_id":consumer,
            "allowed_unix_users":[user],
            "allowed_executables":[python_exe],
            "allowed_systemd_units":[unit],
        }],
        "allowed_projections":["UDS_SINGLE_SECRET"],
        "exportable":False,
    }
Path(pa).write_text(json.dumps(policy(ida),indent=2)+"\n")
Path(pb).write_text(json.dumps(policy(idb),indent=2)+"\n")
PY
chmod 0600 "$POLICY_A" "$POLICY_B"
/usr/local/sbin/fa3-secret-policyctl check "$POLICY_A" >/dev/null
/usr/local/sbin/fa3-secret-policyctl check "$POLICY_B" >/dev/null
/usr/local/sbin/fa3-secret-policyctl install "$POLICY_A" >/dev/null
/usr/local/sbin/fa3-secret-policyctl install "$POLICY_B" >/dev/null

printf 'Credential A for %s: ' "$PROVIDER_ID" >/dev/tty
IFS= read -r -s CRED_A </dev/tty
printf '\nCredential B for %s: ' "$PROVIDER_ID" >/dev/tty
IFS= read -r -s CRED_B </dev/tty
printf '\n' >/dev/tty
[[ -n "$CRED_A" && -n "$CRED_B" ]] || { echo "credentials must be non-empty" >&2; exit 2; }
[[ "$CRED_A" != "$CRED_B" ]] || { echo "credentials must be distinct" >&2; exit 2; }

printf '%s' "$CRED_A" | /usr/local/bin/fa3-secretctl put "$SECRET_ID_A" --classification MACHINE_SERVICE_SECRET --kind PROVIDER_CREDENTIAL >/dev/null
SECRET_A_CREATED=true
printf '%s' "$CRED_B" | /usr/local/bin/fa3-secretctl put "$SECRET_ID_B" --classification MACHINE_SERVICE_SECRET --kind PROVIDER_CREDENTIAL >/dev/null
SECRET_B_CREATED=true
unset CRED_A CRED_B

install -d -o "$PROBE_USER" -g fa3-secret-clients -m0700 "$RUN_ROOT" "$RUNTIME_DIR"
python3 - "$CONFIG" "$PROVIDER_ID" "$API_BASE" "$ADMISSION_RECEIPT" "$SECRET_RECEIPT" "$CONSUMER_ID" "$SECRET_ID_A" "$SECRET_ID_B" "$PREFERRED_MODEL" <<'PY'
import json,sys
from pathlib import Path
out,provider,api,admission,secret_receipt,consumer,a,b,preferred=sys.argv[1:]
cfg={
 "schema":"fa3.model-router-provider-execution-current-host-config.v1",
 "provider_id":provider,
 "api_base":api,
 "logical_route":"fa3-text-primary",
 "consumer_id":consumer,
 "provider_current_host_admission_receipt":admission,
 "secret_broker_current_host_receipt":secret_receipt,
 "models_path":"/v1/models",
 "chat_path":"/v1/chat/completions",
 "preferred_models":[preferred] if preferred else [],
 "credentials":[
   {"credential_ref":"secretref:"+a,"secret_id":a},
   {"credential_ref":"secretref:"+b,"secret_id":b},
 ],
}
Path(out).write_text(json.dumps(cfg,indent=2)+"\n")
PY
chown "$PROBE_USER":fa3-secret-clients "$CONFIG"
chmod 0400 "$CONFIG"
rm -f "$SOURCE"
install -o "$PROBE_USER" -g fa3-secret-clients -m0600 /dev/null "$SOURCE"
rm -f "$SOURCE"

systemd-run --quiet --wait --pipe --collect \
  --unit="$PROBE_UNIT" \
  --uid="$PROBE_USER" \
  --property="SupplementaryGroups=fa3-secret-clients" \
  --property="NoNewPrivileges=yes" \
  --property="PrivateTmp=yes" \
  --property="ProtectSystem=strict" \
  --property="ReadWritePaths=$RUN_ROOT" \
  --working-directory="$ROOT" \
  /usr/bin/env "PYTHONPATH=$ROOT/src" "XDG_RUNTIME_DIR=$RUNTIME_DIR" \
  "$PYTHON_EXE" "$ROOT/bin/fa3-model-router-provider-execution-current-host.py" \
    --root "$ROOT" --config "$CONFIG" --output "$SOURCE"

[[ -s "$SOURCE" ]] || { echo "provider execution live probe was not produced" >&2; exit 2; }
chown root:root "$SOURCE"
chmod 0600 "$SOURCE"

SANITIZED="$RUN_ROOT/current-host-receipt.json"
python3 "$ROOT/evidence/collect-model-router-provider-execution-current-host.py" \
  --root "$ROOT" --input "$SOURCE" --output "$SANITIZED" >/dev/null
PYTHONPATH="$ROOT/src" python3 "$ROOT/src/fa3_model_router_provider_execution_current_host_gate.py" \
  --root "$ROOT" --receipt "$SANITIZED" >/dev/null

echo "FA3 PROVIDER EXECUTION CURRENT-HOST: PASS"
echo "SOURCE_EVIDENCE=$SOURCE"
echo "SANITIZED_RECEIPT=$SANITIZED"
echo "Repository HEAD: $(git -C "$ROOT" rev-parse HEAD)"
