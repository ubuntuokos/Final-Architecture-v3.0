#!/usr/bin/env bash
set -euo pipefail
[[ "$(id -u)" -eq 0 ]] || exit 2
ROOT="${FA3_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"; T=""; C=""; IP=""; JP=""
while (($#)); do case "$1" in --transfer-dir) T="$2"; shift 2;; --ceremony-receipt) C="$2"; shift 2;; --intermediate-password-file) IP="$2"; shift 2;; --jwk-password-file) JP="$2"; shift 2;; *) exit 2;; esac; done
[[ -d "$T" && -f "$C" && -f "$IP" && -f "$JP" ]]; for f in root_ca.crt intermediate_ca.crt intermediate_ca_key; do [[ -f "$T/$f" ]]; done
for bad in root_ca_key root_ca.key root.key; do [[ ! -e "$T/$bad" ]] || { echo "root private key transfer forbidden" >&2; exit 2; }; done
openssl verify -CAfile "$T/root_ca.crt" "$T/intermediate_ca.crt" >/dev/null; grep -q "ENCRYPTED PRIVATE KEY" "$T/intermediate_ca_key"
python3 - "$C" "$T/root_ca.crt" "$T/intermediate_ca.crt" <<'PY'
import hashlib,json,sys
from pathlib import Path
x=json.loads(Path(sys.argv[1]).read_text()); h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert x["status"]=="PASS" and x["root_private_key_exported_online"] is False
assert x["root_certificate"]["sha256"]==h(sys.argv[2]) and x["intermediate_certificate"]["sha256"]==h(sys.argv[3])
PY
id fa3-step-ca >/dev/null
install -d -o fa3-step-ca -g fa3-step-ca -m0755 /var/lib/fa3-step-ca/{certs,evidence}
install -d -o fa3-step-ca -g fa3-step-ca -m0711 /var/lib/fa3-step-ca/secrets
install -d -o fa3-step-ca -g fa3-step-ca -m0700 /var/lib/fa3-step-ca/db
install -d -m0755 /etc/fa3/step-ca; install -d -m0700 /etc/fa3/secrets
install -o fa3-step-ca -g fa3-step-ca -m0644 "$T/root_ca.crt" /var/lib/fa3-step-ca/certs/root_ca.crt; install -o fa3-step-ca -g fa3-step-ca -m0644 "$T/intermediate_ca.crt" /var/lib/fa3-step-ca/certs/intermediate_ca.crt; install -o fa3-step-ca -g fa3-step-ca -m0600 "$T/intermediate_ca_key" /var/lib/fa3-step-ca/secrets/intermediate_ca_key
install -m0600 "$IP" /etc/fa3/secrets/step-ca-password; install -m0600 "$JP" /etc/fa3/secrets/fa3-jwk-password; install -m0644 "$ROOT/deployment/step-ca/ca.json.example" /etc/fa3/step-ca/ca.json
if [[ ! -f /var/lib/fa3-step-ca/secrets/ssh_host_ca_key ]]; then
 step crypto keypair /var/lib/fa3-step-ca/certs/ssh_host_ca_key.pub /var/lib/fa3-step-ca/secrets/ssh_host_ca_key --kty EC --curve P-256 --password-file /etc/fa3/secrets/step-ca-password
 step crypto keypair /var/lib/fa3-step-ca/certs/ssh_user_ca_key.pub /var/lib/fa3-step-ca/secrets/ssh_user_ca_key --kty EC --curve P-256 --password-file /etc/fa3/secrets/step-ca-password
 chown fa3-step-ca:fa3-step-ca /var/lib/fa3-step-ca/certs/ssh_* /var/lib/fa3-step-ca/secrets/ssh_*; chmod 0600 /var/lib/fa3-step-ca/secrets/ssh_*
fi
if find /etc/fa3 /var/lib/fa3-step-ca -type f \( -name root_ca_key -o -name root_ca.key -o -name root.key \) -print -quit | grep -q .; then
 echo "online Root private key forbidden" >&2
 exit 2
fi
grep -q '"name": "fa3-jwk"' /etc/fa3/step-ca/ca.json || step ca provisioner add fa3-jwk --type JWK --create --password-file /etc/fa3/secrets/fa3-jwk-password --ca-url https://127.0.0.1:9443 --root /var/lib/fa3-step-ca/certs/root_ca.crt --ca-config /etc/fa3/step-ca/ca.json
systemctl daemon-reload; systemctl enable --now fa3-step-ca.service
for i in $(seq 1 30); do curl -fsS --cacert /var/lib/fa3-step-ca/certs/root_ca.crt https://127.0.0.1:9443/health >/dev/null && break; sleep 1; done
curl -fsS --cacert /var/lib/fa3-step-ca/certs/root_ca.crt https://127.0.0.1:9443/health >/dev/null

# The Session Vault can recreate this short-lived bundle.  Once activation is
# healthy, remove the paired encrypted key and passwords from the user runtime
# directory so they cannot remain readable for the rest of the login session.
for f in root_ca.crt intermediate_ca.crt intermediate_ca_key intermediate-password.txt jwk-password.txt step-ca-root-ceremony.json; do
 rm -f -- "$T/$f"
done
rmdir -- "$T"

python3 - /var/lib/fa3-step-ca/evidence/activation.json <<'PY'
import json,sys
from datetime import datetime,timezone
from pathlib import Path
x={"schema":"fa3.step-ca-activation-receipt.v1","status":"PASS","service_user":"fa3-step-ca","root_private_key_present_online":False,"intermediate_key_encrypted":True,"systemd_credential_unlock":True,"transfer_bundle_removed":True,"activated_at":datetime.now(timezone.utc).isoformat(),"secret_values_collected":False}
Path(sys.argv[1]).write_text(json.dumps(x,indent=2)+"\n")
PY
chmod 0644 /var/lib/fa3-step-ca/evidence/activation.json
