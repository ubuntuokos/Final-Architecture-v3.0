# OpenYak integration profile

OpenYak is registered as `FA3-PROVIDER-OPENYAK-001`, an optional local desktop-agent workbench under `FA3-DESKTOP-AGENT-WORKBENCH-001`. It projects only to `CAP-008` and `CAP-096`; it is deliberately excluded from `CAP-107` and creates neither a capability nor an architectural authority.

## Pinned package

- release: `v1.4.0`
- commit: `73240597e17d31749f2dbc6c52e8820a6074acad`
- package: `OpenYak_1.4.0_amd64.deb`
- SHA-256: `dfa0358736312c8cdf8b88192cea9c5554efdc5a22643faee6e3e46a5157f531`

The package may be installed only after the digest and normal FA3 supply-chain admission checks pass. Provider self-update and floating `latest` are not activation evidence.

## Required runtime boundary

The desktop process owns the bundled FastAPI backend child. The production v1.4.0 shell binds it to `127.0.0.1` on a dynamically selected unused port and authenticates local requests with a rotated session token. `127.0.0.1:20882` is a previously observed current-host value, not a stable upstream or canonical port. A separate permanently resident backend system service is not the default topology.

Minimum environment policy:

```ini
OPENYAK_OLLAMA_AUTO_START=false
OPENYAK_OLLAMA_BASE_URL=
OPENYAK_LOCAL_BASE_URL=<FA3 LiteLLM loopback OpenAI-compatible endpoint>
OPENYAK_REMOTE_ACCESS_ENABLED=false
OPENYAK_CHANNELS_ENABLED=false
OPENYAK_DEBUG=false
GDK_BACKEND=wayland
```

OpenYak must use only the FA3 LiteLLM route for models and only the Central MCP/Capability Gateway for tools. Direct Ollama, cloud BYOK, stdio-spawned MCP, filesystem, shell, browser and database connectors are denied unless a separate, narrower FA3 admission explicitly exists.

## Workspace and permissions

Use a user-selected bounded project directory. `/`, an entire home directory, model stores, caches, credentials and browser profiles are not valid workspaces. Do not encode a particular username or home path in canonical configuration.

| Operation | Ceiling |
|---|---|
| Read inside admitted workspace | `allow` |
| Write, edit or delete inside workspace | `ask` |
| Shell or code execution | `ask` |
| `sudo`, `su`, `pkexec`, package/firewall/service administration | `deny` |
| System paths, credentials, browser profiles, model stores | `deny` |
| Direct PostgreSQL, Valkey or NATS access | `deny` |

Provider permissions are only an additional ceiling; they cannot grant an operation denied by FA3 policy. OpenYak SQLite remains application-local state. Shared memory is accessed through canonical `memory.*` MCP tools, and durable or long-running workflows escalate to Temporal.

## Verification

```bash
./bin/fa3-enforce openyak
PYTHONPATH=src python -m unittest tests.test_openyak_gate -v
```

This is static/reference conformance only. Current-host promotion additionally requires real package, Wayland/WebKitGTK, loopback/session-token, LiteLLM, MCP gateway, workspace-escape, approval, disabled-channel, shutdown and rollback evidence.
