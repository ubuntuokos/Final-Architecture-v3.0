#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROVIDER_ID="FA3-PROVIDER-OPENAI-API-001"
PREFERRED_MODEL="${FA3_OPENAI_PROBE_MODEL:-}"
RUN_ROOT="/run/fa3/openai-provider"
BRIDGE_COPY="$RUN_ROOT/fa3-openai-loopback-bridge.py"
ADMISSION_RECEIPT="$RUN_ROOT/openai-current-host-admission.json"
UNIT="fa3-openai-provider-bridge.service"
POLICY_ID="FA3-OPENAI-API-EXTERNAL-POLICY-001"
PROVIDER_RUN_ROOT="/run/fa3/model-router-provider-execution"
PROVIDER_SOURCE="$PROVIDER_RUN_ROOT/current-host-source.json"
PROVIDER_RECEIPT="$PROVIDER_RUN_ROOT/current-host-receipt.json"

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "run with sudo/root" >&2; exit 2; }
command -v python3 >/dev/null || { echo "python3 missing" >&2; exit 2; }
command -v systemd-run >/dev/null || { echo "systemd-run missing" >&2; exit 2; }
command -v systemctl >/dev/null || { echo "systemctl missing" >&2; exit 2; }
command -v getent >/dev/null || { echo "getent missing" >&2; exit 2; }
command -v pgrep >/dev/null || { echo "pgrep missing" >&2; exit 2; }

[[ -f "$ROOT/canonical/providers/$PROVIDER_ID.json" ]] || {
  echo "canonical OpenAI provider record missing" >&2
  exit 2
}
[[ -f "$ROOT/canonical/$POLICY_ID.json" ]] || {
  echo "canonical OpenAI external policy missing" >&2
  exit 2
}
[[ -f "$ROOT/bin/fa3-openai-loopback-bridge.py" ]] || {
  echo "OpenAI loopback bridge missing" >&2
  exit 2
}
[[ -f "$ROOT/bin/fa3-model-router-provider-execution-current-host-provision.sh" ]] || {
  echo "provider execution provisioning harness missing" >&2
  exit 2
}

if getent passwd fa3-provider-exec-probe >/dev/null; then
  if systemctl is-active --quiet fa3-provider-exec-probe.service \
    || pgrep -u fa3-provider-exec-probe >/dev/null 2>&1; then
    echo "provider execution probe identity is active; refusing cleanup or reuse" >&2
    exit 2
  fi
  echo "stale provider execution probe identity detected from an interrupted prior run" >&2
  echo "safe recovery: sudo userdel fa3-provider-exec-probe" >&2
  echo "then rerun this closure command" >&2
  exit 2
fi

install -d -m0755 "$RUN_ROOT"
install -m0555 "$ROOT/bin/fa3-openai-loopback-bridge.py" "$BRIDGE_COPY"

PORT="$(python3 - <<'PY'
import socket
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.bind(("127.0.0.1",0))
print(s.getsockname()[1])
s.close()
PY
)"
API_BASE="http://127.0.0.1:$PORT/v1"

cleanup() {
  set +e
  systemctl stop "$UNIT" >/dev/null 2>&1 || true
  systemctl reset-failed "$UNIT" >/dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
cleanup

systemd-run --quiet   --unit="$UNIT"   --property="DynamicUser=yes"   --property="NoNewPrivileges=yes"   --property="PrivateTmp=yes"   --property="ProtectSystem=strict"   --property="ProtectHome=yes"   --property="RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX"   --working-directory="$RUN_ROOT"   /usr/bin/python3 "$BRIDGE_COPY" --bind 127.0.0.1 --port "$PORT"

python3 - "$API_BASE" <<'PY'
import json,sys,time,urllib.request
base=sys.argv[1]
last=None
for _ in range(80):
    try:
        with urllib.request.urlopen(base.removesuffix("/v1")+"/healthz",timeout=1.0) as r:
            obj=json.loads(r.read().decode())
            if r.status==200 and obj.get("status")=="READY" and obj.get("credential_storage") is False:
                raise SystemExit(0)
    except Exception as exc:
        last=exc
        time.sleep(0.1)
raise SystemExit(f"OpenAI loopback bridge did not become ready: {type(last).__name__ if last else 'unknown'}")
PY

python3 - "$API_BASE" <<'PY'
import sys,urllib.error,urllib.request
base=sys.argv[1]
req=urllib.request.Request(
    base+"/models",
    method="GET",
    headers={"Authorization":"Bearer fa3-intentionally-invalid-current-host-probe","Accept":"application/json"},
)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with opener.open(req,timeout=20.0):
        raise SystemExit("invalid bearer credential was unexpectedly accepted")
except urllib.error.HTTPError as exc:
    if int(exc.code) not in (401,403):
        raise SystemExit(f"invalid bearer credential returned unexpected HTTP {int(exc.code)}")
except urllib.error.URLError as exc:
    raise SystemExit(f"OpenAI upstream is unavailable through the loopback adapter: {type(exc.reason).__name__}")
PY

python3 - "$ADMISSION_RECEIPT" "$PROVIDER_ID" "$API_BASE" "$POLICY_ID" "$PREFERRED_MODEL" "$ROOT" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
out,provider,api,policy,model,root=sys.argv[1:]
head=subprocess.check_output(["git","-C",root,"rev-parse","HEAD"],text=True).strip()
bridge=Path(root)/"bin/fa3-openai-loopback-bridge.py"
obj={
  "schema":"fa3.openai-api-current-host-admission.v1",
  "result":"PASS",
  "status":"PASS",
  "evidence_level":"CURRENT_HOST_EXTERNAL_PROVIDER_ADAPTER_PASS",
  "provider_id":provider,
  "api_base":api,
  "repository_head":head,
  "external_egress_policy_id":policy,
  "explicit_external_policy":True,
  "normal_application_routing_enabled":False,
  "silent_local_to_cloud_fallback":False,
  "remote_origin":"https://api.openai.com/v1",
  "loopback_adapter":True,
  "credential_storage":False,
  "invalid_bearer_rejected":True,
  "preferred_probe_model":model if model else None,
  "model_selection":"RUNTIME_CATALOG_PLUS_LIVE_CHAT_COMPATIBILITY_PROBE" if not model else "EXPLICIT_OPERATOR_MODEL",
  "bridge_sha256":hashlib.sha256(bridge.read_bytes()).hexdigest(),
  "raw_secret_present":False,
  "provider_execution_pass_claim":False,
  "global_promotion_claim":False
}
Path(out).write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
Path(out).chmod(0o600)
PY

echo "OpenAI loopback adapter admitted for evidence scope:"
echo "  provider: $PROVIDER_ID"
echo "  api_base: $API_BASE"
if [[ -n "$PREFERRED_MODEL" ]]; then
  echo "  model:    $PREFERRED_MODEL (operator override)"
else
  echo "  model:    runtime discovery from this API project"
fi
echo
echo "The next step asks for Credential A and Credential B on /dev/tty."
echo "Do not paste either API key into chat, a command line, or an environment variable."
echo

PROVISION_ARGS=(
  --provider-id "$PROVIDER_ID"
  --api-base "$API_BASE"
  --admission-receipt "$ADMISSION_RECEIPT"
)
if [[ -n "$PREFERRED_MODEL" ]]; then
  PROVISION_ARGS+=(--preferred-model "$PREFERRED_MODEL")
fi

rm -f "$PROVIDER_SOURCE" "$PROVIDER_RECEIPT"

set +e
bash "$ROOT/bin/fa3-model-router-provider-execution-current-host-provision.sh" "${PROVISION_ARGS[@]}"
PROVISION_RC=$?
set -e

if (( PROVISION_RC != 0 )); then
  echo "provider execution provisioning failed with exit code $PROVISION_RC; closure PASS withheld" >&2
  exit "$PROVISION_RC"
fi

[[ -s "$PROVIDER_RECEIPT" ]] || {
  echo "provider execution sanitized receipt missing after successful provisioner exit" >&2
  exit 2
}

python3 - "$PROVIDER_RECEIPT" "$PROVIDER_ID" "$ROOT" <<'PY'
import json,subprocess,sys
from pathlib import Path
receipt_path,provider_id,root=sys.argv[1:]
x=json.loads(Path(receipt_path).read_text(encoding="utf-8"))
head=subprocess.check_output(["git","-C",root,"rev-parse","HEAD"],text=True).strip()
checks=x.get("checks",{})
if (
    x.get("schema")!="fa3.model-router-provider-execution-current-host.v1"
    or x.get("result")!="PASS"
    or x.get("evidence_level")!="CURRENT_HOST_REAL_PROVIDER_EXECUTION_E2E_PASS"
    or x.get("repository_head")!=head
    or x.get("provider_id")!=provider_id
    or x.get("raw_secret_present") is not False
    or x.get("synthetic_or_mock_provider") is not False
    or x.get("global_promotion_claim") is not False
    or checks.get("provisioning_cleanup_pass") is not True
    or not checks
    or any(v is not True for v in checks.values())
):
    raise SystemExit("provider execution sanitized receipt is not an exact-head clean PASS")
PY

echo
echo "FA3 OPENAI PROVIDER EXECUTION CURRENT-HOST CLOSURE: PASS"
echo "ADMISSION_RECEIPT=$ADMISSION_RECEIPT"
echo "PROVIDER_EXECUTION_RECEIPT=$PROVIDER_RECEIPT"
echo "Repository HEAD: $(git -C "$ROOT" rev-parse HEAD)"
