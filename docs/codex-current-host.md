# FA3 Codex adapter v0.1 — current-host admission

Provider: `FA3-PROVIDER-CODEX-001`  
Adapter: `FA3-CODEX-ADAPTER-001`  
Pinned upstream: Codex CLI `0.151.0`, tag `rust-v0.151.0`, commit `78c290807ce710180111df227df3b7a4fe845452`.

This provider is optional and disabled by default. It does not become an FA3 identity, authorization, secrets, MCP, model-routing, host-resource, evidence or repository-integration authority.

## Bootstrap

Run as the normal non-root user:

```bash
bash bin/fa3-codex-bootstrap.sh
```

The bootstrap downloads the pinned Linux x86_64 release archive, verifies SHA-256
`605b4b183f22c645f5def63a5b7191767407fb66a6feaec4eaf10b5b7e0058f6`,
installs the binary under `~/.local/lib/fa3/codex/0.151.0/bin/codex`, and retains the archive for later binary reproducibility evidence.

## Authentication

FA3 Codex v0.1 admits only an existing ChatGPT login:

```bash
~/.local/lib/fa3/codex/0.151.0/bin/codex login
~/.local/lib/fa3/codex/0.151.0/bin/codex login status
```

API-key/access-token environment passthrough is intentionally excluded from the v0.1 adapter.

## Real current-host E2E

```bash
bash bin/fa3-codex-current-host.sh
```

The collector creates two isolated Git worktrees, invokes two real Codex workers, requires exact scoped file mutations, rejects worker commits and forbidden MCP/collab/web-search events, integrates through the single `FA3 Integration` committer, and verifies cleanup.

A production PASS is written only by the real collector to:

```text
evidence/receipts/codex-current-host.json
reports/codex-current-host-gate-report.json
```

The static CI adapter fixture never creates or substitutes this receipt.

## Execution profile

The adapter uses `codex exec` with:
- `--strict-config`
- `--ignore-user-config`
- `--ignore-rules`
- `--ephemeral`
- `--json`
- `--sandbox workspace-write`
- prompt via stdin

It also explicitly disables web search, MCP servers, nested Codex multi-agent execution, plugins, memories, and login shells. `--approve-for-me`, `--dangerously-bypass-approvals-and-sandbox`, hook-trust bypass and additional writable directories are forbidden.

## Admission state

Until a real current-host receipt passes, canonical status remains:

`NOT_ADMITTED_PENDING_CURRENT_HOST`.
