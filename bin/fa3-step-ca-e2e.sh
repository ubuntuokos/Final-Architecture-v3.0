#!/usr/bin/env bash
set -euo pipefail

[[ "$(id -u)" -eq 0 ]] || {
  echo "root required for the temporary step-ca ACME test-port override" >&2
  exit 2
}

ROOT="${FA3_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STEP_CA_BIN="/usr/local/lib/fa3/step-ca/0.30.2/bin/step-ca"
STEP_BIN="/usr/local/lib/fa3/step-cli/0.30.6/bin/step"
[[ -x "$STEP_CA_BIN" && -x "$STEP_BIN" ]] || { echo "FA3-namespaced Smallstep binaries missing" >&2; exit 2; }
OUT="$ROOT/evidence/runtime/step-ca-current-host/e2e.json"
CA="https://127.0.0.1:9443"
RC="/var/lib/fa3-step-ca/certs/root_ca.crt"
IC="/var/lib/fa3-step-ca/certs/intermediate_ca.crt"
JP="/etc/fa3/secrets/fa3-jwk-password"
DROPIN_DIR="/run/systemd/system/fa3-step-ca.service.d"
DROPIN="$DROPIN_DIR/90-fa3-e2e-acme-port.conf"
TMP=""
PID=""
OVERRIDE_ACTIVE=false
PRODUCTION_EXECSTART_SIGNATURE=""

wait_for_ca() {
  local attempt
  for attempt in $(seq 1 50); do
    if systemctl is-active --quiet fa3-step-ca.service \
      && curl --fail --silent --show-error --cacert "$RC" "$CA/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
  done
  systemctl status fa3-step-ca.service --no-pager --full >&2 || true
  return 1
}

execstart_signature() {
  systemctl show fa3-step-ca.service --property=ExecStart --value |
    python3 -c '
import json
import re
import sys

raw = sys.stdin.read().strip()
path = re.search(r"(?:^|\{\s*)path=(.*?)\s*;\s*argv\[\]=", raw)
argv = re.search(r"\bargv\[\]=(.*?)\s*;\s*ignore_errors=", raw)
if not path or not argv:
    raise SystemExit(1)
print(json.dumps(
    {"path": path.group(1).strip(), "argv": argv.group(1).strip()},
    sort_keys=True,
    separators=(",", ":"),
))
'
}

production_execstart_is_safe() {
  local signature
  signature="$(execstart_signature)" || return 1
  [[ -n "$signature" && "$signature" != *"--acme-http-port"* && "$signature" != *"--acme-tls-port"* && "$signature" != *"--insecure"* ]]
}

production_execstart_restored() {
  local signature
  [[ -n "$PRODUCTION_EXECSTART_SIGNATURE" ]] || return 1
  signature="$(execstart_signature)" || return 1
  [[ "$signature" == "$PRODUCTION_EXECSTART_SIGNATURE" ]]
}

remove_override() {
  rm -f -- "$DROPIN"
  rmdir --ignore-fail-on-non-empty "$DROPIN_DIR" 2>/dev/null || true
  systemctl daemon-reload
  systemctl restart fa3-step-ca.service
  wait_for_ca
  production_execstart_restored || {
    echo "production step-ca ExecStart command signature was not restored" >&2
    return 1
  }
  OVERRIDE_ACTIVE=false
}

cleanup() {
  local rc=$?
  trap - EXIT INT TERM
  set +e
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null
    wait "$PID" 2>/dev/null
  fi
  if [[ "$OVERRIDE_ACTIVE" == true ]]; then
    rm -f -- "$DROPIN" || rc=1
    rmdir --ignore-fail-on-non-empty "$DROPIN_DIR" 2>/dev/null || true
    systemctl daemon-reload || rc=1
    systemctl restart fa3-step-ca.service || rc=1
    wait_for_ca || rc=1
    production_execstart_restored || rc=1
  fi
  [[ -n "$TMP" ]] && rm -rf -- "$TMP"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for command in curl flock openssl python3 sed seq ssh-keygen ss systemctl; do
  command -v "$command" >/dev/null || {
    echo "required command missing: $command" >&2
    exit 2
  }
done

exec 9>/run/lock/fa3-step-ca-e2e.lock
flock -n 9 || {
  echo "another step-ca E2E run is active" >&2
  exit 3
}

systemctl is-active --quiet fa3-step-ca.service

if [[ -e "$DROPIN" ]]; then
  echo "recovering stale step-ca E2E runtime override" >&2
  rm -f -- "$DROPIN"
  rmdir --ignore-fail-on-non-empty "$DROPIN_DIR" 2>/dev/null || true
  systemctl daemon-reload
  systemctl restart fa3-step-ca.service
  wait_for_ca
fi

production_execstart_is_safe || {
  echo "production step-ca ExecStart contains a test-only flag; refusing E2E" >&2
  exit 1
}
PRODUCTION_EXECSTART_SIGNATURE="$(execstart_signature)"

TMP="$(mktemp -d /var/tmp/fa3-step-ca-e2e.XXXXXX)"
chmod 700 "$TMP"

read -r ACME_HTTP_PORT MTLS_PORT < <(python3 - <<'PY'
import socket

sockets = []
ports = []
try:
    for _ in range(2):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sockets.append(sock)
        ports.append(sock.getsockname()[1])
    print(*ports)
finally:
    for sock in sockets:
        sock.close()
PY
)
[[ "$ACME_HTTP_PORT" =~ ^[0-9]+$ && "$MTLS_PORT" =~ ^[0-9]+$ ]]

PORT80_BEFORE="$(ss -H -ltnp 'sport = :80' || true)"

install -d -m0755 "$DROPIN_DIR"
OVERRIDE_ACTIVE=true
{
  printf '%s\n' '[Service]' 'ExecStart='
  printf '%s\n' \
    "ExecStart=$STEP_CA_BIN /etc/fa3/step-ca/ca.json --password-file=%d/step-ca-password --insecure --acme-http-port=$ACME_HTTP_PORT"
} >"$DROPIN"
chmod 0644 "$DROPIN"

systemctl daemon-reload
systemctl restart fa3-step-ca.service
wait_for_ca

"$STEP_BIN" ca certificate localhost "$TMP/a.crt" "$TMP/a.key" \
  --provisioner fa3-acme \
  --ca-url "$CA" \
  --root "$RC" \
  --standalone \
  --http-listen "127.0.0.1:$ACME_HTTP_PORT" \
  --not-after 10m
"$STEP_BIN" ca certificate localhost "$TMP/b.crt" "$TMP/b.key" \
  --provisioner fa3-acme \
  --ca-url "$CA" \
  --root "$RC" \
  --standalone \
  --http-listen "127.0.0.1:$ACME_HTTP_PORT" \
  --not-after 10m

S1="$(openssl x509 -in "$TMP/a.crt" -noout -serial)"
S2="$(openssl x509 -in "$TMP/b.crt" -noout -serial)"
[[ "$S1" != "$S2" ]]

remove_override

PORT80_AFTER="$(ss -H -ltnp 'sport = :80' || true)"
[[ "$PORT80_AFTER" == "$PORT80_BEFORE" ]] || {
  echo "port 80 listener changed during step-ca E2E; refusing PASS" >&2
  exit 1
}

"$STEP_BIN" ca certificate fa3-mtls-client "$TMP/c.crt" "$TMP/c.key" \
  --provisioner fa3-jwk \
  --provisioner-password-file "$JP" \
  --ca-url "$CA" \
  --root "$RC" \
  --not-after 10m

# Prove both leaf certificates are valid for their intended TLS roles before
# attempting the live handshake.  Keep the trust anchor limited to the Root
# and supply the issuing intermediate explicitly as untrusted chain material.
openssl verify -purpose sslserver -CAfile "$RC" -untrusted "$IC" "$TMP/b.crt" >/dev/null
openssl verify -purpose sslclient -CAfile "$RC" -untrusted "$IC" "$TMP/c.crt" >/dev/null

openssl s_server \
  -accept "127.0.0.1:$MTLS_PORT" \
  -cert "$TMP/b.crt" \
  -cert_chain "$IC" \
  -key "$TMP/b.key" \
  -CAfile "$RC" \
  -Verify 1 \
  -quiet >"$TMP/s.log" 2>&1 &
PID=$!
sleep 1
if ! printf '' | openssl s_client \
  -connect "127.0.0.1:$MTLS_PORT" \
  -servername localhost \
  -cert "$TMP/c.crt" \
  -cert_chain "$IC" \
  -key "$TMP/c.key" \
  -CAfile "$RC" \
  -verify_return_error >"$TMP/c.log" 2>&1; then
  echo "mTLS handshake failed" >&2
  echo "--- openssl s_server ---" >&2
  sed -n '1,160p' "$TMP/s.log" >&2
  echo "--- openssl s_client ---" >&2
  sed -n '1,200p' "$TMP/c.log" >&2
  exit 1
fi
kill "$PID"
wait "$PID" 2>/dev/null || true
PID=""

"$STEP_BIN" ssh certificate fa3-e2e "$TMP/ssh_e2e" \
  --provisioner fa3-jwk \
  --provisioner-password-file "$JP" \
  --ca-url "$CA" \
  --root "$RC" \
  --no-agent \
  --no-password \
  --insecure \
  --not-after 10m
ssh-keygen -Lf "$TMP/ssh_e2e-cert.pub" >/dev/null
openssl verify -CAfile "$RC" "$IC" >/dev/null
openssl verify -CAfile "$RC" -untrusted "$IC" "$TMP/b.crt" >/dev/null

TTL="$(python3 - "$TMP/b.crt" <<'PY'
import datetime
import subprocess
import sys

p = subprocess.run(
    ["openssl", "x509", "-in", sys.argv[1], "-noout", "-startdate", "-enddate"],
    text=True,
    capture_output=True,
    check=True,
).stdout.splitlines()
f = "%b %d %H:%M:%S %Y %Z"
a = datetime.datetime.strptime(p[0].split("=", 1)[1], f)
b = datetime.datetime.strptime(p[1].split("=", 1)[1], f)
print((b - a).total_seconds() / 3600)
PY
)"

mkdir -p "$(dirname "$OUT")"
python3 - "$OUT" "$TTL" "$ACME_HTTP_PORT" "$MTLS_PORT" <<'PY'
import json
import sys
from datetime import datetime, timezone

x = {
    "schema": "fa3.step-ca-current-host-e2e.v1",
    "status": "PASS",
    "acme_issue_pass": True,
    "acme_reorder_pass": True,
    "acme_challenge": "http-01",
    "acme_validation_port": int(sys.argv[3]),
    "host_port_80_untouched": True,
    "temporary_ca_override_restored": True,
    "mtls_pass": True,
    "mtls_listener_port": int(sys.argv[4]),
    "ssh_certificate_pass": True,
    "trust_bundle_pass": True,
    "max_observed_tls_ttl_hours": float(sys.argv[2]),
    "privileged_test_harness": True,
    "service_remains_unprivileged": True,
    "secret_values_collected": False,
    "completed_at": datetime.now(timezone.utc).isoformat(),
}
open(sys.argv[1], "w").write(json.dumps(x, indent=2) + "\n")
PY
