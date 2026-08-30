# FA3 Presenton current-host deployment

This projection installs Presenton as an optional, rootless, loopback-only worker. It does not grant Presenton any FA3 authority and does not make the provider mandatory while disabled.

## Preconditions

- rootless Podman with Quadlet support;
- an existing `ai-creative.target` user target;
- PostgreSQL reachable from `host.containers.internal:5432`;
- LiteLLM on `host.containers.internal:4000` with the `presentation-primary` and `presentation-memory` aliases;
- ComfyUI on `host.containers.internal:9876`;
- Infisical CLI authenticated for the FA3 production environment;
- Caddy with the checked-in route imported;
- `pdfinfo` and `pdftoppm` for production render QA.

## Database bootstrap

The password is passed as a `psql` variable and is never stored in this repository:

```bash
infisical run --env=prod -- sh -c \
  'psql --set=presenton_password="$PRESENTON_DB_PASSWORD" --file deployment/presenton/postgresql-bootstrap.sql postgres'
```

The canonical `DATABASE_URL` secret must use PostgreSQL, for example `postgresql://presenton:...@host.containers.internal:5432/presenton`. SQLite fallback is prohibited.

## Rootless Podman secrets

Create the required secrets through Infisical without printing their values:

```bash
infisical run --env=prod -- sh -ceu '
  printf %s "$PRESENTON_DATABASE_URL" | podman secret create presenton-database-url -
  printf %s "$PRESENTON_AUTH_PASSWORD" | podman secret create presenton-auth-password -
  printf %s "$PRESENTON_LITELLM_API_KEY" | podman secret create presenton-litellm-api-key -
  printf %s "$PRESENTON_LITELLM_API_KEY" | podman secret create presenton-mem0-litellm-api-key -
  printf %s "$PRESENTON_COMFYUI_WORKFLOW" | podman secret create presenton-comfyui-workflow -
'
```

Secret rotation is an explicit stop/recreate/start operation. Never place these values in a committed `.env` file.

## Install and start

```bash
install -d "$HOME/.config/containers/systemd" "$HOME/Dokumentumok/Presenton/app_data" /ai-cache/presenton/tmp
install -m 0644 deployment/presenton/presenton.container "$HOME/.config/containers/systemd/presenton.container"
install -m 0644 deployment/presenton/ai-creative.target "$HOME/.config/systemd/user/ai-creative.target"
systemctl --user daemon-reload
systemctl --user enable --now ai-creative.target presenton.service
```

Import `deployment/presenton/presenton.caddy` into the local Caddy configuration. Do not expose port 5001 on a non-loopback address and do not publish the OAuth callback port 1455.

Create one Presenton admin access key in the UI, store it in Infisical, and make it available only to the Central MCP/Capability Gateway and the controlled current-host evidence runner. Direct agent possession is forbidden.

## Current-host production evidence

Run the collector only after the actual service is active and the LiteLLM and ComfyUI routes are healthy:

```bash
infisical run --env=prod -- bash bin/fa3-presenton-current-host.sh \
  --base-url http://127.0.0.1:5001 \
  --access-key-env PRESENTON_ACCESS_KEY
```

The collector performs a real asynchronous PPTX generation, re-exports the same presentation as PDF, renders the PDF pages, verifies artifact hashes, checks the running rootless container configuration, and writes `evidence/receipts/presenton-current-host.json`. The receipt is accepted only by `./bin/fa3-enforce presenton-current-host`.

GitHub-hosted tests and synthetic artifacts can prove contract conformance only; they cannot produce `CURRENT_HOST_PRODUCTION_E2E_PASS`.
