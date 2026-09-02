# FA3 OpenHands current-host runtime

This runbook materializes the optional `FA3-PROVIDER-OPENHANDS-001` runtime on the authorized FA3 workstation without granting OpenHands any architectural authority.

## Immutable runtime identity

- repository: `OpenHands/software-agent-sdk`
- commit: `a9e0a8a1aab2164b46bae00a18157a343aaa94c9`
- source tree: `342a369f498b826cf51d1644bcbef8d503af7628`
- `openhands-sdk`: `1.44.1`
- `openhands-agent-server`: `1.44.1`
- `openhands-tools`: `1.44.1`
- `openhands-workspace`: `1.44.1`
- Python: 3.12
- packaging: pip venv only; conda/mamba is rejected

## Materialize the pinned runtime

The first bootstrap may use the network only when explicitly requested. The source commit/tree and installed component tuple are verified after materialization.

```bash
export FA3_OPENHANDS_HOME="$HOME/.local/share/fa3/openhands"
bash bin/fa3-openhands-bootstrap.sh --allow-network-bootstrap
```

Subsequent validation can run without source/package download:

```bash
bash bin/fa3-openhands-bootstrap.sh
```

## Isolation model

The worker runs in Bubblewrap with:

- `--unshare-all`;
- no host root bind;
- no host home mount;
- no general sandbox network namespace access;
- read-only `/fa3` repository view;
- read-only `/venv`;
- one explicit read/write delegated workspace at `/workspace`;
- a minimal process environment;
- no OpenHands TerminalTool, FileEditorTool, provider MCP or direct `Conversation.execute_tool()` execution path.

Production model traffic is the only intentional external execution path. It is carried through a Unix-domain socket mounted into the network-isolated sandbox. A host-side byte bridge forwards that socket only to loopback LiteLLM, normally `127.0.0.1:4000`. OpenHands never owns model routing.

## Isolated real-runtime evidence

This uses the actual pinned OpenHands Agent/Conversation/persistence/custom-tool stack and the upstream OpenHands `TestLLM` only as a deterministic local model fixture.

```bash
export FA3_CURRENT_HOST=1
bash bin/fa3-openhands-current-host.sh isolated
```

Expected evidence level:

`CURRENT_HOST_OPENHANDS_ISOLATED_RUNTIME_PASS`

This proves runtime installation, isolation, exact mutation scope, OpenHands event/persistence flow, reopen/resume behavior, secret-free persistence, negative scope tests and cleanup. **It cannot promote OpenHands for production use.**

## Production E2E

Production requires two inputs issued/materialized outside OpenHands:

1. an FA3 Central MCP/Capability Gateway single-use tool authorization receipt;
2. a read-only LiteLLM credential file with mode 0600 or stricter.

The production task ID must be known before the authorization receipt is issued. The fixed E2E mutation is:

- operation: `workspace.write.exact`
- relative path: `work/openhands.txt`
- exact content SHA-256: `2f04b7d0937a480c8875f78a1d0305a0911488d9de5e8c13e51316704cf714e0`

Receipt shape:

```json
{
  "schema": "fa3.canonical-tool-authorization-receipt.v1",
  "issuer_id": "FA3-AUTH-MCP-GATEWAY-001",
  "provider_id": "FA3-PROVIDER-OPENHANDS-001",
  "task_id": "fa3-openhands-production-v1",
  "authorized": true,
  "single_use": true,
  "issued_at": "<UTC timestamp>",
  "expires_at": "<future UTC timestamp>",
  "scope": {
    "operation": "workspace.write.exact",
    "relative_path": "work/openhands.txt",
    "content_sha256": "2f04b7d0937a480c8875f78a1d0305a0911488d9de5e8c13e51316704cf714e0"
  }
}
```

The receipt must actually be issued by the existing canonical authorization/tool-mediation boundary. A locally fabricated file is not production evidence.

Run:

```bash
export FA3_CURRENT_HOST=1
export FA3_OPENHANDS_TASK_ID=fa3-openhands-production-v1
export FA3_OPENHANDS_TOOL_AUTH_RECEIPT=/run/user/$UID/fa3-openhands/tool-auth.json
export FA3_OPENHANDS_LITELLM_KEY_FILE=/run/user/$UID/fa3-openhands/litellm-key
export FA3_OPENHANDS_LITELLM_PORT=4000
export FA3_OPENHANDS_MODEL_ALIAS=developer-agent-primary
bash bin/fa3-openhands-current-host.sh production
```

Expected evidence level:

`CURRENT_HOST_OPENHANDS_PRODUCTION_E2E_PASS`

The key value is never placed in OpenHands persisted LLM configuration. The worker stores only a non-secret placeholder in the OpenHands LLM object and reads the external key file only when constructing the HTTP Authorization header. Evidence stores response hashes, not model-router secrets.

## Evidence and gates

- isolated receipt: `evidence/receipts/openhands-current-host-isolated.json`
- production receipt: `evidence/receipts/openhands-current-host.json`
- runtime evidence: `evidence/runtime/openhands-current-host/`
- report: `reports/openhands-current-host-gate-report.json`

Validation:

```bash
./bin/fa3-enforce openhands-current-host-isolated
./bin/fa3-enforce openhands-current-host
```

The production gate rejects fixture evidence, GitHub-hosted runner evidence, missing external authorization, missing central model-router responses, direct provider tool bypass, widened mutation scope, worker commits, secret persistence or incomplete cleanup.

## GitHub self-hosted execution

`.github/workflows/fa3-openhands-current-host.yml` runs on:

`[self-hosted, linux, x64, fa3-current-host]`

Branch pushes run only the isolated real-runtime path. Production uses the separate `.github/workflows/fa3-openhands-production-current-host.yml` workflow and is explicit `workflow_dispatch`; it requires the externally provisioned receipt/key files to already exist on the current-host runner.

Neither evidence class changes the canonical capability count (143) or creates an authority. OpenHands provider admission is component-scoped; global FA3 promotion remains governed by the existing Evidence Registry and 19-point Acceptance Gate.
