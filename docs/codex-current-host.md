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

## Failed real-worker diagnostic

A successful Codex JSONL `turn.completed` alone does not constitute a
successful delegated edit. If a real worker returns without the required
file change, the adapter fails closed with `NO_DELEGATED_FILE_CHANGE`.
If the Codex JSONL includes an `item.type=error` even alongside an exit-0
`turn.completed`, the result is instead `PROVIDER_ITEM_ERROR` and remains
FAIL regardless of apparent mutation. The report records only coarse error
categories (rate limit, authentication, transport, sandbox, model, quota or
other), not the provider's raw error messages.
A strictly bounded, local, mode-0600 diagnostic survives the temporary
worktree cleanup at:

```text
reports/codex-current-host-failure-diagnostic.json
```

The diagnostic includes only return codes, event/item categories, event
counts, token counts and hashes; it excludes raw prompts, Codex output,
final messages, skill text and credentials. It is **not** current-host
evidence or a replacement for an authorized PASS receipt. Re-run the
real probe and use the diagnostic categories to determine whether the
provider attempted any tool calls before changing the execution profile.

## Private local diagnostic for unclassified error items

The pinned Codex 0.151.0 emits `item.type=error` for non-fatal warnings
as well as other error messages. A generic `OTHER_PROVIDER_ERROR` category
does not establish whether an error item caused the missing edit.

For one real E2E repro on an interactive FA3 workstation, run:

```bash
bash bin/fa3-codex-current-host.sh --local-error-messages
```

This explicit opt-in displays up to three bounded original error messages
and the last agent message **only in the local terminal on a failed worker**.
They are not written to the evidence or failure diagnostic and the flag
is denied in CI or when stderr is redirected. The operator must examine
the text before sharing and redact any paths, usernames or secrets.
This is a diagnostic, **not** proof or a substitute for the physical gate.
Never enable it in GitHub-hosted workflows.

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
