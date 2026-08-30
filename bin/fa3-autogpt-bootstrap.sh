#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMIT="f49bcca95ed327396d8ebdd0bdf7810de482ac1a"
RELEASE="autogpt-platform-beta-v0.7.3"
PROVIDER_ID="FA3-PROVIDER-AUTOGPT-001"
BASE_SELECTOR="docker.io/library/python:3.13-slim-bookworm"
PG_SELECTOR="docker.io/pgvector/pgvector:pg15"
REDIS_SELECTOR="docker.io/library/redis:7"
RABBIT_SELECTOR="docker.io/library/rabbitmq:4.1.4"
STATE_DIR="${FA3_AUTOGPT_STATE_DIR:-}"
ACTION="${1:-}"
if [[ -n "$ACTION" ]]; then shift; fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --state-dir) STATE_DIR="$2"; shift 2;;
    *) echo "Unknown argument: $1" >&2; exit 64;;
  esac
done
[[ -n "$STATE_DIR" ]] || { echo "--state-dir is required" >&2; exit 64; }
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"

command -v podman >/dev/null
command -v git >/dev/null
command -v python3 >/dev/null

PREFIX="fa3-autogpt-e2e"
NET="$PREFIX-net"
DB="$PREFIX-db"
R0="$PREFIX-redis-0"
R1="$PREFIX-redis-1"
R2="$PREFIX-redis-2"
RABBIT="$PREFIX-rabbit"
REST="$PREFIX-rest"
SERVER_TAG="localhost/fa3-autogpt-backend:${COMMIT:0:12}"
CACHE_ROOT="${FA3_AUTOGPT_CACHE_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/fa3/autogpt}"
SOURCE="$CACHE_ROOT/source-$COMMIT"

json_secret() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
}
fernet_secret() {
  python3 - <<'PY'
import base64,secrets
print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
PY
}
resolve_digest() {
  local selector="$1"
  podman pull "$selector" >/dev/null
  podman image inspect "$selector" --format '{{json .RepoDigests}}' | python3 -c 'import json,sys; x=json.load(sys.stdin); assert x, "image has no RepoDigest"; print(x[0])'
}
image_id() {
  podman image inspect "$1" --format '{{.Id}}'
}

cleanup_runtime() {
  set +e
  if podman container exists "$REST" 2>/dev/null; then
    mkdir -p "$STATE_DIR/logs"
    podman logs "$REST" >"$STATE_DIR/logs/rest.log" 2>&1 || true
  fi
  for c in "$REST" "$RABBIT" "$R2" "$R1" "$R0" "$DB"; do
    podman rm -f "$c" >/dev/null 2>&1 || true
  done
  podman network rm "$NET" >/dev/null 2>&1 || true
  rm -f "$STATE_DIR/runtime-secrets.env"
}

if [[ "$ACTION" == "stop" ]]; then
  cleanup_runtime
  python3 - "$STATE_DIR/state.json" <<'PY'
import json,sys,datetime
p=sys.argv[1]
try:
    o=json.load(open(p,encoding="utf-8"))
except Exception:
    o={}
o["stopped_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
o["runtime_stopped"]=True
json.dump(o,open(p,"w",encoding="utf-8"),indent=2)
open(p,"a",encoding="utf-8").write("\n")
PY
  exit 0
fi
[[ "$ACTION" == "start" ]] || { echo "Usage: $0 start|stop --state-dir DIR" >&2; exit 64; }

cleanup_runtime
mkdir -p "$CACHE_ROOT"
if [[ ! -d "$SOURCE/.git" ]]; then
  rm -rf "$SOURCE"
  git clone --filter=blob:none --no-checkout https://github.com/Significant-Gravitas/AutoGPT.git "$SOURCE"
fi
git -C "$SOURCE" fetch --depth=1 origin "$COMMIT"
git -C "$SOURCE" checkout --detach --force "$COMMIT"
ACTUAL="$(git -C "$SOURCE" rev-parse HEAD)"
[[ "$ACTUAL" == "$COMMIT" ]] || { echo "AutoGPT source commit mismatch" >&2; exit 65; }
git -C "$SOURCE" diff --quiet
git -C "$SOURCE" diff --cached --quiet

BASE_DIGEST="$(resolve_digest "$BASE_SELECTOR")"
PG_DIGEST="$(resolve_digest "$PG_SELECTOR")"
REDIS_DIGEST="$(resolve_digest "$REDIS_SELECTOR")"
RABBIT_DIGEST="$(resolve_digest "$RABBIT_SELECTOR")"
BASE_ID="$(image_id "$BASE_DIGEST")"
PG_ID="$(image_id "$PG_DIGEST")"
REDIS_ID="$(image_id "$REDIS_DIGEST")"
RABBIT_ID="$(image_id "$RABBIT_DIGEST")"

podman build --pull-never   --build-arg "BASE_IMAGE=$BASE_DIGEST"   --label "fa3.provider_id=$PROVIDER_ID"   --label "fa3.autogpt.source_commit=$COMMIT"   --label "fa3.autogpt.release=$RELEASE"   --label "fa3.runtime_profile=FA3_AUTOGPT_CONSTRAINED_BLOCK_RUNTIME_V1"   -t "$SERVER_TAG"   -f "$ROOT/deployment/autogpt/Dockerfile.fa3"   "$SOURCE"
SERVER_ID="$(image_id "$SERVER_TAG")"

DB_PASS="$(json_secret)"
RABBIT_USER="fa3_autogpt"
RABBIT_PASS="$(json_secret)"
JWT_KEY="$(json_secret)$(json_secret)"
ENC_KEY="$(fernet_secret)"
UNSUB_KEY="$(json_secret)"

cat >"$STATE_DIR/runtime-secrets.env" <<EOF
DB_PASS=$DB_PASS
RABBIT_USER=$RABBIT_USER
RABBIT_PASS=$RABBIT_PASS
JWT_KEY=$JWT_KEY
ENC_KEY=$ENC_KEY
UNSUB_KEY=$UNSUB_KEY
EOF
chmod 600 "$STATE_DIR/runtime-secrets.env"

podman network create --internal "$NET" >/dev/null

podman run -d --name "$DB" --network "$NET" --network-alias db   --cap-drop=all --security-opt=no-new-privileges   -e POSTGRES_USER=postgres -e "POSTGRES_PASSWORD=$DB_PASS" -e POSTGRES_DB=postgres   -v "$SOURCE/autogpt_platform/db/init/00-init.sql:/docker-entrypoint-initdb.d/00-init.sql:ro"   "$PG_DIGEST" >/dev/null

for i in {1..60}; do
  if podman exec "$DB" pg_isready -U postgres >/dev/null 2>&1; then break; fi
  sleep 1
  [[ "$i" -lt 60 ]] || { echo "Postgres readiness timeout" >&2; exit 70; }
done

for spec in "$R0:redis-0" "$R1:redis-1" "$R2:redis-2"; do
  name="${spec%%:*}"; alias="${spec##*:}"
  podman run -d --name "$name" --network "$NET" --network-alias "$alias"     --cap-drop=all --security-opt=no-new-privileges     "$REDIS_DIGEST" redis-server       --port 6379 --cluster-enabled yes --cluster-config-file nodes.conf       --cluster-node-timeout 5000 --appendonly no --protected-mode no       --cluster-announce-hostname "$alias" --cluster-announce-port 6379       --cluster-announce-bus-port 16379 >/dev/null
done
for c in "$R0" "$R1" "$R2"; do
  for i in {1..30}; do
    if podman exec "$c" redis-cli -p 6379 ping 2>/dev/null | grep -q PONG; then break; fi
    sleep 1
    [[ "$i" -lt 30 ]] || { echo "Redis readiness timeout: $c" >&2; exit 70; }
  done
done
podman exec "$R0" redis-cli --cluster create redis-0:6379 redis-1:6379 redis-2:6379   --cluster-replicas 0 --cluster-yes >/dev/null

podman run -d --name "$RABBIT" --network "$NET" --network-alias rabbitmq   --cap-drop=all --security-opt=no-new-privileges   -e "RABBITMQ_DEFAULT_USER=$RABBIT_USER" -e "RABBITMQ_DEFAULT_PASS=$RABBIT_PASS"   "$RABBIT_DIGEST" >/dev/null
for i in {1..60}; do
  if podman exec "$RABBIT" rabbitmq-diagnostics -q ping >/dev/null 2>&1; then break; fi
  sleep 1
  [[ "$i" -lt 60 ]] || { echo "RabbitMQ readiness timeout" >&2; exit 70; }
done

COMMON_ENV=(
  -e APP_ENV=local -e BEHAVE_AS=local
  -e DB_USER=postgres -e "DB_PASS=$DB_PASS" -e DB_NAME=postgres -e DB_HOST=db -e DB_PORT=5432 -e DB_SCHEMA=platform
  -e "DATABASE_URL=postgresql://postgres:$DB_PASS@db:5432/postgres?schema=platform&connect_timeout=60"
  -e "DIRECT_URL=postgresql://postgres:$DB_PASS@db:5432/postgres?schema=platform&connect_timeout=60"
  -e REDIS_CLUSTER_HOST=redis-0 -e REDIS_CLUSTER_PORT=6379 -e REDIS_USE_ANNOUNCED_ADDRESS=true
  -e RABBITMQ_CLUSTER_HOST=rabbitmq -e RABBITMQ_CLUSTER_PORT=5672
  -e "RABBITMQ_DEFAULT_USER=$RABBIT_USER" -e "RABBITMQ_DEFAULT_PASS=$RABBIT_PASS"
  -e "JWT_VERIFY_KEY=$JWT_KEY" -e JWT_JWKS_URL=
  -e "ENCRYPTION_KEY=$ENC_KEY" -e "UNSUBSCRIBE_SECRET_KEY=$UNSUB_KEY"
  -e AGENT_API_HOST=0.0.0.0 -e AGENT_API_PORT=8006
  -e PLATFORM_BASE_URL=http://127.0.0.1:58006 -e FRONTEND_BASE_URL=http://127.0.0.1:58006
  -e BACKEND_CORS_ALLOW_ORIGINS='["http://127.0.0.1:58006"]'
  -e WORKSPACE_STORAGE_DIR=/tmp/fa3-autogpt-workspaces
  -e CUDA_VISIBLE_DEVICES=
  -e OPENAI_API_KEY= -e ANTHROPIC_API_KEY= -e SENTRY_DSN= -e POSTHOG_API_KEY=
)

podman run --rm --network "$NET"   --cap-drop=all --security-opt=no-new-privileges   "${COMMON_ENV[@]}" "$SERVER_TAG" prisma migrate deploy >/dev/null

podman run -d --name "$REST" --network "$NET" --network-alias rest_server   -p 127.0.0.1:58006:8006   --cap-drop=all --security-opt=no-new-privileges   --cpus=8 --memory=12g --pids-limit=2048   --label "fa3.provider_id=$PROVIDER_ID"   --label "fa3.autogpt.source_commit=$COMMIT"   --label "fa3.runtime_profile=FA3_AUTOGPT_CONSTRAINED_BLOCK_RUNTIME_V1"   "${COMMON_ENV[@]}" "$SERVER_TAG" >/dev/null

for i in {1..180}; do
  if python3 - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("http://127.0.0.1:58006/health",timeout=2).read()
PY
  then break; fi
  sleep 1
  [[ "$i" -lt 180 ]] || {
    podman logs "$REST" >&2 || true
    echo "AutoGPT REST readiness timeout" >&2
    exit 70
  }
done

LOCK_SHA="$(python3 - "$SOURCE/autogpt_platform/backend/poetry.lock" <<'PY'
import hashlib,sys
print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())
PY
)"

python3 - "$STATE_DIR/state.json" <<PY
import json,datetime
o={
 "schema":"fa3.autogpt-current-host-runtime-state.v1",
 "provider_id":"$PROVIDER_ID",
 "release":"$RELEASE",
 "source_commit":"$COMMIT",
 "source_dir":"$SOURCE",
 "network":"$NET",
 "containers":{"db":"$DB","redis":["$R0","$R1","$R2"],"rabbitmq":"$RABBIT","rest":"$REST"},
 "selectors":{"base":"$BASE_SELECTOR","postgres":"$PG_SELECTOR","redis":"$REDIS_SELECTOR","rabbitmq":"$RABBIT_SELECTOR"},
 "repo_digests":{"base":"$BASE_DIGEST","postgres":"$PG_DIGEST","redis":"$REDIS_DIGEST","rabbitmq":"$RABBIT_DIGEST"},
 "image_ids":{"base":"$BASE_ID","postgres":"$PG_ID","redis":"$REDIS_ID","rabbitmq":"$RABBIT_ID","autogpt_server":"$SERVER_ID"},
 "server_tag":"$SERVER_TAG",
 "poetry_lock_sha256":"$LOCK_SHA",
 "base_url":"http://127.0.0.1:58006",
 "launch_security":{"rootless_required":True,"internal_network":True,"loopback_publish":True,"cap_drop_all":True,"no_new_privileges":True,"gpu_devices":False,"cpu_limit":8,"memory_bytes":12884901888,"pids_limit":2048},
 "started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "runtime_stopped":False,
}
json.dump(o,open("$STATE_DIR/state.json","w",encoding="utf-8"),indent=2)
open("$STATE_DIR/state.json","a",encoding="utf-8").write("\n")
PY
echo "$STATE_DIR/state.json"
