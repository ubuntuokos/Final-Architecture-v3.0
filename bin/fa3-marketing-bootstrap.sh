#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="${FA3_MARKETING_STATE_DIR:-$HOME/.local/share/fa3/marketing}"
CONF="${FA3_MARKETING_CONFIG_DIR:-$HOME/.config/fa3/marketing}"
NET="fa3-marketing"
mkdir -p "$STATE"/{smtp,listmonk-uploads} "$CONF"
chmod 700 "$STATE" "$CONF"

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "FAIL: FA3 marketing runtime must run rootless" >&2
  exit 20
fi
command -v podman >/dev/null || { echo "FAIL: podman missing" >&2; exit 21; }
command -v openssl >/dev/null || { echo "FAIL: openssl missing" >&2; exit 22; }
command -v python3 >/dev/null || { echo "FAIL: python3 missing" >&2; exit 26; }
command -v curl >/dev/null || { echo "FAIL: curl missing" >&2; exit 27; }

secret() {
  local name="$1" bytes="${2:-24}" f="$CONF/$name"
  if [[ ! -s "$f" ]]; then
    umask 077
    openssl rand -hex "$bytes" > "$f"
  fi
  chmod 600 "$f"
  cat "$f"
}
MAUTIC_DB_PASSWORD="$(secret mautic-db-password 24)"
MAUTIC_DB_ROOT_PASSWORD="$(secret mautic-db-root-password 24)"
MAUTIC_ADMIN_PASSWORD="$(secret mautic-admin-password 24)"
TWENTY_DB_PASSWORD="$(secret twenty-db-password 24)"
TWENTY_ENCRYPTION_KEY="$(secret twenty-encryption-key 32)"
TWENTY_APP_SECRET="$(secret twenty-app-secret 32)"
TWENTY_ADMIN_PASSWORD="$(secret twenty-admin-password 24)"
LISTMONK_DB_PASSWORD="$(secret listmonk-db-password 24)"
LISTMONK_ADMIN_PASSWORD="$(secret listmonk-admin-password 24)"

declare -A TAGS=(
  [smtp]="docker.io/library/python:3.13-alpine"
  [mysql]="docker.io/library/mysql:8.4"
  [mautic]="docker.io/mautic/mautic:7.1.3-apache"
  [postgres]="docker.io/library/postgres:16-alpine"
  [redis]="docker.io/library/redis:7-alpine"
  [twenty]="docker.io/twentycrm/twenty:v2.37.4"
  [listmonk]="docker.io/listmonk/listmonk:v6.2.0"
)
declare -A IDS
for k in smtp mysql mautic postgres redis twenty listmonk; do
  podman pull --quiet "${TAGS[$k]}" >/dev/null
  IDS[$k]="$(podman image inspect --format '{{.Id}}' "${TAGS[$k]}")"
  [[ -n "${IDS[$k]}" ]] || { echo "FAIL: image resolution failed: $k" >&2; exit 23; }
done

python3 - "$STATE/image-lock.json" <<'PY'
import json, os, subprocess, sys
tags = {
 "smtp":"docker.io/library/python:3.13-alpine",
 "mysql":"docker.io/library/mysql:8.4",
 "mautic":"docker.io/mautic/mautic:7.1.3-apache",
 "postgres":"docker.io/library/postgres:16-alpine",
 "redis":"docker.io/library/redis:7-alpine",
 "twenty":"docker.io/twentycrm/twenty:v2.37.4",
 "listmonk":"docker.io/listmonk/listmonk:v6.2.0",
}
out={"schema":"fa3.marketing-image-lock.v1","images":{}}
for k,t in tags.items():
    raw=subprocess.check_output(["podman","image","inspect",t],text=True)
    obj=json.loads(raw)[0]
    out["images"][k]={"tag":t,"id":obj.get("Id"),"repo_digests":obj.get("RepoDigests") or []}
with open(sys.argv[1],"w",encoding="utf-8") as f:
    json.dump(out,f,indent=2); f.write("\n")
PY
chmod 600 "$STATE/image-lock.json"

podman network exists "$NET" || podman network create "$NET" >/dev/null
for v in fa3-mkt-mautic-db fa3-mkt-mautic-config fa3-mkt-mautic-logs fa3-mkt-mautic-media-files fa3-mkt-mautic-media-images fa3-mkt-twenty-db fa3-mkt-twenty-storage fa3-mkt-listmonk-db; do
  podman volume exists "$v" || podman volume create "$v" >/dev/null
done

rmc(){ podman rm -f "$1" >/dev/null 2>&1 || true; }
wait_http(){
  local url="$1" max="${2:-180}" i
  for ((i=0;i<max;i++)); do
    if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  echo "FAIL: HTTP readiness timeout: $url" >&2
  return 1
}
wait_cmd(){
  local name="$1"; shift
  local i
  for ((i=0;i<90;i++)); do
    if podman exec "$name" "$@" >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  echo "FAIL: readiness timeout: $name" >&2
  return 1
}

# Test-only SMTP sink: internal network, no published port.
rmc fa3-mkt-smtp-sink
podman run -d --name fa3-mkt-smtp-sink --replace   --network "$NET" --network-alias smtp-sink   -v "$ROOT/runtime/marketing/fa3_smtp_sink.py:/sink.py:ro"   -v "$STATE/smtp:/data"   "${IDS[smtp]}" python /sink.py --host 0.0.0.0 --port 1025 --output /data/messages.jsonl >/dev/null

# Mautic MySQL + web. Public UI is loopback only.
rmc fa3-mkt-mautic-db
podman run -d --name fa3-mkt-mautic-db --replace --network "$NET" --network-alias mautic-db   -e MYSQL_DATABASE=mautic -e MYSQL_USER=mautic   -e MYSQL_PASSWORD="$MAUTIC_DB_PASSWORD" -e MYSQL_ROOT_PASSWORD="$MAUTIC_DB_ROOT_PASSWORD"   -v fa3-mkt-mautic-db:/var/lib/mysql "${IDS[mysql]}" >/dev/null
wait_cmd fa3-mkt-mautic-db mysqladmin ping -h 127.0.0.1 -uroot "-p$MAUTIC_DB_ROOT_PASSWORD"

rmc fa3-mkt-mautic-web
podman run -d --name fa3-mkt-mautic-web --replace --network "$NET" --network-alias mautic-web   -p 127.0.0.1:8180:80   -e MAUTIC_DB_HOST=mautic-db -e MAUTIC_DB_PORT=3306 -e MAUTIC_DB_DATABASE=mautic   -e MAUTIC_DB_USER=mautic -e MAUTIC_DB_PASSWORD="$MAUTIC_DB_PASSWORD"   -e MAUTIC_MESSENGER_DSN_EMAIL=doctrine://default -e MAUTIC_MESSENGER_DSN_HIT=doctrine://default   -v fa3-mkt-mautic-config:/var/www/html/config   -v fa3-mkt-mautic-logs:/var/www/html/var/logs   -v fa3-mkt-mautic-media-files:/var/www/html/docroot/media/files   -v fa3-mkt-mautic-media-images:/var/www/html/docroot/media/images   -v "$ROOT/runtime/marketing/fa3_mautic_config.php:/opt/fa3-mautic-config.php:ro"   "${IDS[mautic]}" >/dev/null
sleep 8
if ! podman exec fa3-mkt-mautic-db mysql -uroot "-p$MAUTIC_DB_ROOT_PASSWORD" -D mautic -Nse "SHOW TABLES LIKE 'users'" | grep -qx users; then
  podman exec --user www-data --workdir /var/www/html fa3-mkt-mautic-web     php ./bin/console mautic:install --force     --admin_email="fa3-marketing@localhost.invalid"     --admin_password="$MAUTIC_ADMIN_PASSWORD"     http://127.0.0.1:8180
fi
podman exec -e FA3_MAUTIC_SITE_URL=http://127.0.0.1:8180   -e FA3_MAUTIC_MAILER_DSN=smtp://smtp-sink:1025   --user www-data fa3-mkt-mautic-web php /opt/fa3-mautic-config.php
podman exec --user www-data --workdir /var/www/html fa3-mkt-mautic-web php ./bin/console cache:clear --env=prod >/dev/null
wait_http http://127.0.0.1:8180 120

for role in cron worker; do
  name="fa3-mkt-mautic-$role"
  rmc "$name"
  env_role="mautic_$role"
  podman run -d --name "$name" --replace --network "$NET"     -e DOCKER_MAUTIC_ROLE="$env_role"     -e MAUTIC_DB_HOST=mautic-db -e MAUTIC_DB_PORT=3306 -e MAUTIC_DB_DATABASE=mautic     -e MAUTIC_DB_USER=mautic -e MAUTIC_DB_PASSWORD="$MAUTIC_DB_PASSWORD"     -e MAUTIC_MESSENGER_DSN_EMAIL=doctrine://default -e MAUTIC_MESSENGER_DSN_HIT=doctrine://default     -v fa3-mkt-mautic-config:/var/www/html/config     -v fa3-mkt-mautic-logs:/var/www/html/var/logs     -v fa3-mkt-mautic-media-files:/var/www/html/docroot/media/files     -v fa3-mkt-mautic-media-images:/var/www/html/docroot/media/images     "${IDS[mautic]}" >/dev/null
done

# Twenty Postgres + Redis + production server/worker.
rmc fa3-mkt-twenty-db
podman run -d --name fa3-mkt-twenty-db --replace --network "$NET" --network-alias twenty-db   -e POSTGRES_USER=twenty -e POSTGRES_PASSWORD="$TWENTY_DB_PASSWORD" -e POSTGRES_DB=twenty   -v fa3-mkt-twenty-db:/var/lib/postgresql/data "${IDS[postgres]}" >/dev/null
wait_cmd fa3-mkt-twenty-db pg_isready -U twenty -d twenty

rmc fa3-mkt-twenty-redis
podman run -d --name fa3-mkt-twenty-redis --replace --network "$NET" --network-alias twenty-redis   "${IDS[redis]}" redis-server --maxmemory-policy noeviction >/dev/null
wait_cmd fa3-mkt-twenty-redis redis-cli ping

TWENTY_ENV=(
  -e NODE_ENV=production
  -e NODE_PORT=3000
  -e SERVER_URL=http://127.0.0.1:3020
  -e "PG_DATABASE_URL=postgres://twenty:$TWENTY_DB_PASSWORD@twenty-db:5432/twenty"
  -e REDIS_URL=redis://twenty-redis:6379
  -e STORAGE_TYPE=local
  -e ENCRYPTION_KEY="$TWENTY_ENCRYPTION_KEY"
  -e APP_SECRET="$TWENTY_APP_SECRET"
  -e IS_MULTIWORKSPACE_ENABLED=false
  -e IS_CONFIG_VARIABLES_IN_DB_ENABLED=false
  -e ANALYTICS_ENABLED=false
  -e TELEMETRY_ENABLED=false
  -e EMAIL_DRIVER=smtp
  -e EMAIL_SMTP_HOST=smtp-sink
  -e EMAIL_SMTP_PORT=1025
  -e EMAIL_FROM_ADDRESS=fa3-marketing@localhost.invalid
  -e EMAIL_FROM_NAME="FA3 Marketing"
)
rmc fa3-mkt-twenty-server
podman run -d --name fa3-mkt-twenty-server --replace --network "$NET" --network-alias twenty-server   -p 127.0.0.1:3020:3000 -v fa3-mkt-twenty-storage:/app/packages/twenty-server/.local-storage   "${TWENTY_ENV[@]}" "${IDS[twenty]}" >/dev/null
wait_http http://127.0.0.1:3020/healthz 180

rmc fa3-mkt-twenty-worker
podman run -d --name fa3-mkt-twenty-worker --replace --network "$NET"   -v fa3-mkt-twenty-storage:/app/packages/twenty-server/.local-storage   "${TWENTY_ENV[@]}" -e DISABLE_DB_MIGRATIONS=true -e DISABLE_CRON_JOBS_REGISTRATION=true   "${IDS[twenty]}" yarn worker:prod >/dev/null

# listmonk Postgres + explicit first-install API user.
rmc fa3-mkt-listmonk-db
podman run -d --name fa3-mkt-listmonk-db --replace --network "$NET" --network-alias listmonk-db   -e POSTGRES_USER=listmonk -e POSTGRES_PASSWORD="$LISTMONK_DB_PASSWORD" -e POSTGRES_DB=listmonk   -v fa3-mkt-listmonk-db:/var/lib/postgresql/data "${IDS[postgres]}" >/dev/null
wait_cmd fa3-mkt-listmonk-db pg_isready -U listmonk -d listmonk

LM_COMMON=(
  --network "$NET"
  -e LISTMONK_app__address=0.0.0.0:9000
  -e LISTMONK_db__user=listmonk
  -e LISTMONK_db__password="$LISTMONK_DB_PASSWORD"
  -e LISTMONK_db__database=listmonk
  -e LISTMONK_db__host=listmonk-db
  -e LISTMONK_db__port=5432
  -e LISTMONK_db__ssl_mode=disable
  -e TZ=Europe/Budapest
)
if [[ -z "$(podman exec fa3-mkt-listmonk-db psql -U listmonk -d listmonk -Atc "select to_regclass('public.settings')" | tr -d '[:space:]')" ]]; then
  set +e
  INSTALL_OUT="$(podman run --rm "${LM_COMMON[@]}"     -e LISTMONK_ADMIN_USER=fa3admin -e LISTMONK_ADMIN_PASSWORD="$LISTMONK_ADMIN_PASSWORD"     -e LISTMONK_ADMIN_API_USER=fa3api "${IDS[listmonk]}"     ./listmonk --install --yes --config '' 2>&1)"
  rc=$?
  set -e
  printf '%s\n' "$INSTALL_OUT" | sed -E 's/(LISTMONK_ADMIN_API_TOKEN=)"[^"]*"/\\1"[REDACTED]"/g'
  [[ $rc -eq 0 ]] || exit $rc
  token="$(printf '%s\n' "$INSTALL_OUT" | sed -n 's/^export LISTMONK_ADMIN_API_TOKEN="\([^"]*\)".*/\1/p' | tail -n1)"
  [[ -n "$token" ]] || { echo "FAIL: listmonk installer did not emit API token" >&2; exit 24; }
  umask 077
  printf '%s' "$token" > "$CONF/listmonk-api-token"
  chmod 600 "$CONF/listmonk-api-token"
fi
[[ -s "$CONF/listmonk-api-token" ]] || { echo "FAIL: listmonk API token missing for existing database" >&2; exit 25; }

rmc fa3-mkt-listmonk
podman run -d --name fa3-mkt-listmonk --replace "${LM_COMMON[@]}"   -p 127.0.0.1:9020:9000   -v "$STATE/listmonk-uploads:/listmonk/uploads"   "${IDS[listmonk]}" sh -c "./listmonk --upgrade --yes --config '' && exec ./listmonk --config ''" >/dev/null
wait_http http://127.0.0.1:9020 120

cat > "$STATE/runtime.json" <<EOF
{
  "schema": "fa3.marketing-current-host-runtime.v1",
  "status": "RUNNING_PENDING_E2E",
  "mautic": {"url": "http://127.0.0.1:8180", "image_tag": "${TAGS[mautic]}"},
  "twenty": {"url": "http://127.0.0.1:3020", "image_tag": "${TAGS[twenty]}"},
  "listmonk": {"url": "http://127.0.0.1:9020", "image_tag": "${TAGS[listmonk]}"},
  "smtp_sink": {"network_only": true}
}
EOF
chmod 600 "$STATE/runtime.json"
echo "FA3 marketing runtime materialized: $STATE"
