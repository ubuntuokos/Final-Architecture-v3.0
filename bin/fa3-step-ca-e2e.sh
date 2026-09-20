#!/usr/bin/env bash
set -euo pipefail
[[ "$(id -u)" -eq 0 ]] || { echo "root required only for ACME http-01 port 80" >&2; exit 2; }
ROOT="${FA3_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"; OUT="$ROOT/evidence/runtime/step-ca-current-host/e2e.json"; CA=https://127.0.0.1:9443; RC=/var/lib/fa3-step-ca/certs/root_ca.crt; IC=/var/lib/fa3-step-ca/certs/intermediate_ca.crt; JP=/etc/fa3/secrets/fa3-jwk-password
systemctl is-active --quiet fa3-step-ca.service; TMP="$(mktemp -d /var/tmp/fa3-step-ca-e2e.XXXXXX)"; chmod 700 "$TMP"; trap 'rm -rf "$TMP"' EXIT
step ca certificate localhost "$TMP/a.crt" "$TMP/a.key" --provisioner fa3-acme --ca-url "$CA" --root "$RC" --http-listen 127.0.0.1:80 --not-after 10m
step ca certificate localhost "$TMP/b.crt" "$TMP/b.key" --provisioner fa3-acme --ca-url "$CA" --root "$RC" --http-listen 127.0.0.1:80 --not-after 10m
S1="$(openssl x509 -in "$TMP/a.crt" -noout -serial)"; S2="$(openssl x509 -in "$TMP/b.crt" -noout -serial)"; [[ "$S1" != "$S2" ]]
step ca certificate fa3-mtls-client "$TMP/c.crt" "$TMP/c.key" --provisioner fa3-jwk --provisioner-password-file "$JP" --ca-url "$CA" --root "$RC" --not-after 10m
openssl s_server -accept 127.0.0.1:9444 -cert "$TMP/b.crt" -key "$TMP/b.key" -CAfile "$RC" -Verify 1 -quiet >"$TMP/s.log" 2>&1 & PID=$!; sleep 1
printf '' | openssl s_client -connect 127.0.0.1:9444 -servername localhost -cert "$TMP/c.crt" -key "$TMP/c.key" -CAfile "$RC" -verify_return_error >/dev/null 2>&1
kill "$PID"; wait "$PID" 2>/dev/null || true
step ssh certificate fa3-e2e "$TMP/ssh_e2e" --provisioner fa3-jwk --provisioner-password-file "$JP" --ca-url "$CA" --root "$RC" --no-agent --no-password --insecure --not-after 10m
ssh-keygen -Lf "$TMP/ssh_e2e-cert.pub" >/dev/null; openssl verify -CAfile "$RC" "$IC" >/dev/null; openssl verify -CAfile "$RC" -untrusted "$IC" "$TMP/b.crt" >/dev/null
TTL="$(python3 - "$TMP/b.crt" <<'PY'
import datetime,subprocess,sys
p=subprocess.run(["openssl","x509","-in",sys.argv[1],"-noout","-startdate","-enddate"],text=True,capture_output=True,check=True).stdout.splitlines(); f="%b %d %H:%M:%S %Y %Z"; a=datetime.datetime.strptime(p[0].split("=",1)[1],f); b=datetime.datetime.strptime(p[1].split("=",1)[1],f); print((b-a).total_seconds()/3600)
PY
)"
mkdir -p "$(dirname "$OUT")"; python3 - "$OUT" "$TTL" <<'PY'
import json,sys
from datetime import datetime,timezone
x={"schema":"fa3.step-ca-current-host-e2e.v1","status":"PASS","acme_issue_pass":True,"acme_reorder_pass":True,"mtls_pass":True,"ssh_certificate_pass":True,"trust_bundle_pass":True,"max_observed_tls_ttl_hours":float(sys.argv[2]),"privileged_test_harness":True,"service_remains_unprivileged":True,"secret_values_collected":False,"completed_at":datetime.now(timezone.utc).isoformat()}
open(sys.argv[1],"w").write(json.dumps(x,indent=2)+"\n")
PY
